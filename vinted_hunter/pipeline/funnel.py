"""Contadores del embudo sobre una cohorte de anuncios únicos."""

from collections import Counter
from collections.abc import Iterable
from typing import Any


def funnel(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    tiers: Counter[str] = Counter()
    rejected: Counter[str] = Counter()
    outcomes: dict[str, list[int]] = {}
    enriched = 0
    for row in rows:
        trace = row["trace"]
        tier = row["tier"] or "pending"
        tiers[tier] += 1
        reason = trace.get("gate_rejected")
        if reason:
            rejected[reason] += 1
        enriched += int(trace.get("enriched", row["body"].get("category_id") is not None))
        outcome = f"rejected:{reason}" if reason else tier
        outcomes.setdefault(outcome, []).append(row["id"])
    return {
        "seen": tiers.total(),
        "enriched": enriched,
        "tiers": dict(tiers),
        "rejected": dict(rejected),
        "ids_by_outcome": outcomes,
    }
