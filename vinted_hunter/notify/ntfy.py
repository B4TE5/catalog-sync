"""Avisos de novedades y estado por ntfy."""

import re
from collections.abc import Callable
from datetime import UTC, datetime
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
CheckActive = Callable[[dict[str, Any]], bool]
TIER_RANK = {"low": 0, "maybe": 1, "good": 2, "top": 3}


def notification_eligible(
    row: dict[str, Any], minimum: str = "top", *, simulate_active: bool = False,
    negotiable_days: int = 7,
    at: datetime | None = None,
) -> tuple[bool, str]:
    if TIER_RANK.get(row["tier"], -1) < TIER_RANK[minimum]:
        return False, "tier_inferior_al_perfil"
    trace = row["trace"]
    if trace.get("gate_rejected") or not trace.get("pricing"):
        return False, "sin_candidato_validado"
    if trace.get("score", {}).get("flags"):
        return False, "requiere_revision"
    if not simulate_active and row["body"].get("availability") in {
        "sold", "reserved", "gone", "hidden",
    }:
        return False, "anuncio_no_activo"
    source = row["body"].get("uploaded_at") or row["body"].get("first_seen")
    age = ((at or datetime.now(UTC))-datetime.fromisoformat(source)).total_seconds()/60 \
        if source else 0
    if age >= negotiable_days * 1440 and not trace.get("evidence", {}).get("price_drop"):
        return False, "negociable_sin_bajada"
    return True, "candidato_apto"


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
        elapsed = f"{age} min" if age < 60 else f"{age // 60} h" \
            if age < 1440 else f"{age // 1440} días"
        when = f"\n{label} hace {elapsed}"
    drop = "📉 " if trace.get("evidence", {}).get("price_drop") else ""
    symbol = "🔥 " if row["tier"] == "top" else "✅ "
    size = f" · {body['size']}" if body.get("size") else ""
    name = body["title"]
    brand = body.get("brand")
    if brand and brand.casefold() not in name.casefold():
        name = f"{brand} · {name}"
    color = f" · {body['color']}" if body.get("color") else ""
    message: dict[str, Any] = {
        "title": (
            f"{drop}{symbol}{name[:92]}{size}{color} · {body['price']} € "
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
        min_tiers: dict[str, str] | None = None,
        check_active: CheckActive | None = None,
        negotiable_days: int = 7,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.store = store
        self.topic = topic_name(topic)
        self.health_topic = topic_name(health_topic)
        self.shadow_mode = shadow_mode
        self.board_url = board_url
        self.unhealthy_after = unhealthy_after
        self.post = post
        self.report = report
        self.min_tiers = min_tiers or {}
        self.check_active = check_active
        self.negotiable_days = negotiable_days
        self.clock = clock or (lambda: datetime.now(UTC))

    def publish(self, summary: dict[str, Any]) -> None:
        if not summary.get("deferred") and not summary.get("interrupted"):
            self.publish_health(bool(summary["errors"]))
        if self.shadow_mode or not self.topic or summary.get("notifications_handled"):
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

    def publish_listing(self, row: dict[str, Any]) -> int | None:
        if self.shadow_mode or not self.topic:
            return None
        minimum = self.min_tiers.get(row["profile"], "top")
        if not notification_eligible(row, minimum, negotiable_days=self.negotiable_days,
                                     at=self.clock())[0]:
            return None
        if self.check_active is None or not self.check_active(row):
            return None
        row = self.store.record(row["id"]) or row
        if not notification_eligible(row, minimum, negotiable_days=self.negotiable_days,
                                     at=self.clock())[0]:
            return None
        trace = row["trace"]
        pricing = trace.get("pricing")
        if not pricing or trace.get("score", {}).get("flags") or not https_url(row["body"]["url"]):
            return
        negotiable = pricing.get("negotiable", False)
        key = f"ntfy:listing:{row['id']}"
        old = self.store.setting(key)
        price = row["body"]["price"]
        if old and not (
            trace.get("evidence", {}).get("price_drop") and Decimal(price) < Decimal(old)
        ):
            return
        priority = 3 if negotiable else 5 if row["tier"] == "top" else 4
        status = self.post({
            **listing_message(row, self.board_url, priority), "topic": self.topic,
        })
        if status == 200:
            self.store.claim_setting(key, old, price)
        self.report(f"ntfy anuncio · HTTP {status}")
        return status

    def test(
        self, row: dict[str, Any], *, announcements_only: bool = False,
    ) -> tuple[int, int | None]:
        if not self.topic or not announcements_only and not self.health_topic:
            raise ValueError("Faltan los topics de prueba")
        if self.check_active is None or not self.check_active(row):
            raise ValueError("La prueba requiere un anuncio confirmado activo")
        row = self.store.record(row["id"]) or row
        if row["body"].get("availability") in {"sold", "reserved", "hidden", "gone"}:
            raise ValueError("La prueba requiere un anuncio activo")
        payload = listing_message(row, self.board_url, 3)
        title = payload["title"]
        return (
            self.post({**payload, "topic": self.topic, "title": "Prueba · " + title}),
            None if announcements_only else self.post(
                {**payload, "topic": self.health_topic, "title": "Prueba de salud · " + title}
            ),
        )


def notifier_for(
    root: Path, store: SQLiteStore, check_active: CheckActive | None = None,
) -> NtfyNotifier:
    config = load_config(root)
    return NtfyNotifier(
        store,
        local_secret(root, "NTFY_TOPIC"),
        local_secret(root, "NTFY_HEALTH_TOPIC"),
        shadow_mode=config.scoring.shadow_mode,
        board_url=local_secret(root, "BOARD_URL") or board_address(root),
        unhealthy_after=config.scoring.capture.unhealthy_after,
        min_tiers={p.id: p.notify_min_tier for p in config.profiles},
        check_active=check_active,
        negotiable_days=int(config.scoring.pricing["negotiable_days"]),
    )
