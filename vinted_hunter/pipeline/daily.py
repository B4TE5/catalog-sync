"""Backfill diario persistente y reanudable dentro de la cuota de cada pasada."""

import json
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from vinted_hunter.config import Config
from vinted_hunter.sources.vinted.search import all_searches
from vinted_hunter.storage.base import StateStore

KEY = "daily_backfill"


def prepare(
    store: StateStore, config: Config, now: datetime, *, manual: bool = False,
) -> dict[str, Any]:
    settings = config.scoring.daily_backfill
    state = json.loads(store.setting(KEY, "{}"))
    if state.get("jobs") and state.get("cursor", 0) < len(state["jobs"]):
        return state
    local = now.astimezone(ZoneInfo(settings.timezone))
    elapsed = (local.hour * 60 + local.minute - settings.hour * 60) % (24 * 60)
    if not settings.enabled or not manual and elapsed >= settings.start_window_minutes:
        return {}
    previous = state.get("started_at")
    if previous and now-datetime.fromisoformat(previous) < timedelta(hours=settings.interval_hours):
        return {}
    state = {
        "started_at": now.isoformat(), "manual": manual,
        "cursor": 0, "requested": 0, "skipped_empty": 0,
        "jobs": [{"params": search.query(page),
                  "profiles": [profile.id for profile in search.profiles],
                  "expects_items": search.expects_items,
                  "query_index": index, "page": page}
                 for index, search in enumerate(all_searches(config))
                 for page in range(1, settings.pages + 1)],
    }
    save(store, state)
    return state


def advance(
    store: StateStore, state: dict[str, Any], *, empty: bool, stop_on_empty: bool,
    now: datetime, reused: bool = False,
) -> None:
    job = state["jobs"][state["cursor"]]
    state["cursor"] += 1
    state["requested"] += int(not reused)
    if empty and stop_on_empty:
        while state["cursor"] < len(state["jobs"]) and (
            state["jobs"][state["cursor"]]["query_index"] == job["query_index"]
        ):
            state["cursor"] += 1
            state["skipped_empty"] += 1
    if state["cursor"] == len(state["jobs"]):
        state["completed_at"] = now.isoformat()
    save(store, state)


def save(store: StateStore, state: dict[str, Any]) -> None:
    store.set_setting(KEY, json.dumps(state))
    store.flush()


def summary(state: dict[str, Any]) -> dict[str, Any]:
    return {key: state.get(key) for key in (
        "started_at", "cursor", "requested", "skipped_empty", "completed_at",
    )} | {"planned": len(state.get("jobs", []))}
