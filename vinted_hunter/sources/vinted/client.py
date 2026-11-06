"""Sesión anónima de Vinted con cuotas y pausa entre peticiones."""

import random
import time
from collections.abc import Callable
from types import TracebackType
from typing import Any, Literal, Self

from curl_cffi.requests import Response, Session

Budget = Literal["catalog", "enrich"]
Event = Callable[..., None]


class BudgetExhausted(RuntimeError):
    """Se agotó la cuota de la pasada."""


class HttpFailure(RuntimeError):
    """Respuesta no utilizable."""


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
        self.blocked = False

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, kind: type[BaseException] | None, value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.session.close()

    def home(self) -> Response:
        return self.get("/")

    def remaining(self, budget: Budget) -> int:
        return self.limits[budget] - self.counts[budget]

    def get(
        self, path: str, budget: Budget | None = None, params: Any = None,
    ) -> Response:
        if self.blocked:
            raise CircuitOpen("Circuito abierto para esta sesión")
        if budget is not None:
            if not self.remaining(budget):
                raise BudgetExhausted(f"Cuota agotada: {budget}")
            self.counts[budget] += 1
        if self.requests:
            time.sleep(random.uniform(*self.wait))
        self.requests += 1
        started = time.monotonic()
        url = self.base + path if path.startswith("/") else path
        response = self.session.get(url, params=params, timeout=30)
        if self.emit:
            self.emit("request", url=response.url, status=response.status_code,
                      ms=round((time.monotonic() - started) * 1000), budget=budget)
        if response.status_code in (403, 429):
            self.blocked = True
            raise CircuitOpen(f"HTTP {response.status_code}")
        if response.status_code != 200:
            raise HttpFailure(f"HTTP {response.status_code}")
        return response
