"""Sesión anónima de Vinted con cuotas y pausa entre peticiones."""

import random
import time
from collections.abc import Callable
from threading import Lock
from types import TracebackType
from typing import Any, Literal, Self
from urllib.parse import urlsplit, urlunsplit

from curl_cffi.requests import RequestsError, Response, Session
from curl_cffi.requests import get as request_get

Budget = Literal["catalog", "enrich"]
Event = Callable[..., None]


class BudgetExhausted(RuntimeError):
    """Se agotó la cuota de la pasada."""


class HttpFailure(RuntimeError):
    """Respuesta no utilizable."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class CircuitOpen(HttpFailure):
    """El servidor ha pedido interrumpir la pasada."""


class VintedClient:
    def __init__(
        self,
        base: str = "https://www.vinted.es",
        catalog_limit: int = 12,
        enrich_limit: int = 12,
        wait: tuple[float, float] = (3, 8),
        emit: Event | None = None,
    ) -> None:
        self.base = base.rstrip("/")
        self.limits = {"catalog": catalog_limit, "enrich": enrich_limit}
        self.counts = {"catalog": 0, "enrich": 0}
        self.wait = wait
        self.emit = emit
        self.session = Session(impersonate="chrome")
        self.requests = 0
        self.pages = 0
        self.lock = Lock()
        self.blocked = False

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.session.close()

    def home(self) -> Response:
        return self.get("/")

    def remaining(self, budget: Budget) -> int:
        with self.lock:
            return self.limits[budget] - self.counts[budget]

    def claim(self, budget: Budget | None) -> None:
        with self.lock:
            if self.blocked:
                raise CircuitOpen("Circuito abierto para esta sesión")
            if budget is not None:
                if self.counts[budget] >= self.limits[budget]:
                    raise BudgetExhausted(f"Cuota agotada: {budget}")
                self.counts[budget] += 1
            self.requests += 1

    def checked(self, response: Response, started: float, budget: Budget | None) -> Response:
        if self.emit:
            log_url = urlsplit(response.url)
            if log_url.hostname != urlsplit(self.base).hostname:
                log_url = log_url._replace(query="", fragment="")
            self.emit(
                "request",
                url=urlunsplit(log_url),
                status=response.status_code,
                ms=round((time.monotonic() - started) * 1000),
                budget=budget,
            )
        if response.status_code in (403, 429):
            with self.lock:
                self.blocked = True
            raise CircuitOpen(f"HTTP {response.status_code}")
        if response.status_code != 200:
            raise HttpFailure(f"HTTP {response.status_code}", response.status_code)
        return response

    def get(self, path: str, budget: Budget | None = None, params: Any = None) -> Response:
        self.claim(budget)
        if self.pages:
            time.sleep(random.uniform(*self.wait))
        self.pages += 1
        started = time.monotonic()
        url = self.base + path if path.startswith("/") else path
        return self.checked(self.session.get(url, params=params, timeout=30), started, budget)

    def get_cdn(self, url: str, timeout: float) -> Response:
        """Descarga una imagen pública sin cookies ni pausa de páginas."""
        parts = urlsplit(url)
        if parts.scheme != "https" or not (parts.hostname or "").endswith(".vinted.net"):
            raise ValueError("URL de CDN no admitida")
        for attempt in range(2):
            self.claim("enrich")
            started = time.monotonic()
            try:
                response = request_get(
                    url,
                    timeout=timeout,
                    impersonate="chrome",
                    allow_redirects=False,
                )
            except RequestsError:
                if attempt:
                    raise
                continue
            if attempt == 0 and (response.status_code == 408 or response.status_code >= 500):
                try:
                    self.checked(response, started, "enrich")
                except HttpFailure:
                    continue
            return self.checked(response, started, "enrich")
        raise AssertionError("Se agotó el bucle de descarga")
