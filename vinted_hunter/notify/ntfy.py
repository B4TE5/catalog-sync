"""Avisos de novedades y estado por ntfy."""

import re
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from curl_cffi import requests

from vinted_hunter.config import load_config
from vinted_hunter.notify.base import Notifier
from vinted_hunter.secrets import board_address, local_secret
from vinted_hunter.storage.sqlite_store import SQLiteStore

NTFY = "https://ntfy.sh/"
Post = Callable[[dict[str, Any]], int]


def post_message(payload: dict[str, Any]) -> int:
    try:
        return requests.post(NTFY, json=payload, timeout=12, allow_redirects=False).status_code
    except requests.RequestsError:
        return 0


def topic_name(value: str | None) -> str | None:
    if value is None:
        return None
    topic = value.removeprefix(NTFY)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", topic):
        raise ValueError("Formato de topic ntfy no admitido")
    return topic


def https_url(url: str) -> bool:
    parts = urlsplit(url)
    return parts.scheme == "https" and bool(parts.hostname) and parts.username is None


def listing_message(row: dict[str, Any], board_url: str | None, priority: int) -> dict[str, Any]:
    body, trace = row["body"], row["trace"]
    pricing = trace["pricing"]
    reasons = trace["score"]["reasons"][:3]
    timing = trace.get("timing") or {}
    age = timing.get("age_minutes")
    when = ""
    if age is not None:
        label = "Primera observación" if timing.get("age_estimated") else "Subida"
        when = f"\n{label} hace {age} min"
    drop = "📉 " if trace.get("evidence", {}).get("price_drop") else ""
    symbol = "🔥 " if row["tier"] == "top" else "✅ "
    size = f" · {body['size']}" if body.get("size") else ""
    message: dict[str, Any] = {
        "title": (
            f"{drop}{symbol}{body['title'][:92]}{size} · {body['price']} € "
            f"({pricing['total']} total) · {row['score']}"
        ),
        "message": (" · ".join(reasons) or "Detalles disponibles en el anuncio") + when,
        "click": body["url"],
        "priority": priority,
    }
    if body["photos"] and https_url(body["photos"][0]):
        message["attach"] = body["photos"][0]
    if board_url and https_url(board_url):
        public_url = urlsplit(board_url)._replace(query="", fragment="").geturl()
        message["actions"] = [{"action": "view", "label": "Tablero", "url": public_url}]
    return message


class NtfyNotifier(Notifier):
    def __init__(
        self,
        store: SQLiteStore,
        topic: str | None,
        health_topic: str | None,
        *,
        shadow_mode: bool = True,
        board_url: str | None = None,
        unhealthy_after: int = 3,
        post: Post = post_message,
        report: Callable[[str], None] = print,
    ) -> None:
        self.store = store
        self.topic = topic_name(topic)
        self.health_topic = topic_name(health_topic)
        self.shadow_mode = shadow_mode
        self.board_url = board_url
        self.unhealthy_after = unhealthy_after
        self.post = post
        self.report = report

    def publish(self, summary: dict[str, Any]) -> None:
        if not summary.get("deferred") and not summary.get("interrupted"):
            self.publish_health(bool(summary["errors"]))
        if self.shadow_mode or not self.topic:
            return
        for listing_id in summary.get("scored_ids", []):
            row = self.store.record(listing_id)
            if row:
                self.publish_listing(row)

    def publish_health(self, failed: bool) -> None:
        if not self.health_topic:
            return
        key = "ntfy:health"
        prior = self.store.setting(key)
        failures = int(self.store.setting("failures", "0"))
        if failed and failures >= self.unhealthy_after and prior != "incident":
            current = "incident"
            title, message, priority = (
                "⚠️ Monitor con incidencias",
                f"{failures} pasadas fallidas seguidas.",
                4,
            )
        elif not failed and prior == "incident":
            current = "healthy"
            title, message, priority = (
                "✅ Monitor recuperado",
                "La última pasada fue correcta.",
                3,
            )
        else:
            return
        if self.store.claim_setting(key, prior, current):
            status = self.post(
                {
                    "topic": self.health_topic,
                    "title": title,
                    "message": message,
                    "priority": priority,
                }
            )
            self.report(f"ntfy salud · HTTP {status}")

    def publish_listing(self, row: dict[str, Any]) -> None:
        if self.shadow_mode or not self.topic or row["tier"] not in ("top", "good"):
            return
        trace = row["trace"]
        pricing = trace.get("pricing")
        if not pricing or trace.get("score", {}).get("flags") or not https_url(row["body"]["url"]):
            return
        negotiable = pricing.get("negotiable", False)
        if negotiable and row["score"] < 75:
            return
        key = f"ntfy:listing:{row['id']}"
        old = self.store.setting(key)
        price = row["body"]["price"]
        if old and not (
            trace.get("evidence", {}).get("price_drop") and Decimal(price) < Decimal(old)
        ):
            return
        if self.store.claim_setting(key, old, price):
            priority = 3 if negotiable else 5 if row["tier"] == "top" else 4
            status = self.post(
                {
                    **listing_message(row, self.board_url, priority),
                    "topic": self.topic,
                }
            )
            self.report(f"ntfy anuncio · HTTP {status}")

    def test(self, row: dict[str, Any]) -> tuple[int, int]:
        if not self.topic or not self.health_topic:
            raise ValueError("Se requieren ambos topics de ntfy")
        payload = listing_message(row, self.board_url, 3)
        title = payload["title"]
        return (
            self.post({**payload, "topic": self.topic, "title": "Prueba · " + title}),
            self.post(
                {**payload, "topic": self.health_topic, "title": "Prueba de salud · " + title}
            ),
        )


def notifier_for(root: Path, store: SQLiteStore) -> NtfyNotifier:
    config = load_config(root)
    return NtfyNotifier(
        store,
        local_secret(root, "NTFY_TOPIC"),
        local_secret(root, "NTFY_HEALTH_TOPIC"),
        shadow_mode=config.scoring.shadow_mode,
        board_url=local_secret(root, "BOARD_URL") or board_address(root),
        unhealthy_after=config.scoring.capture.unhealthy_after,
    )
