from datetime import UTC, datetime, timedelta
from pathlib import Path
from shutil import copytree

import numpy as np

from vinted_hunter.config import Tuning, load_config
from vinted_hunter.pipeline.daily import advance, prepare
from vinted_hunter.replay import evaluate_fixture
from vinted_hunter.storage.sqlite_store import SQLiteStore
from vinted_hunter.tune import fit_logistic, propose

ROOT = Path(__file__).parents[1]


def test_daily_plan_resumes_all_real_queries_and_waits_twenty_four_hours(tmp_path: Path) -> None:
    config = load_config(ROOT)
    now = datetime(2026, 11, 8, 2, tzinfo=UTC)  # 03:00 Europe/Madrid.
    with SQLiteStore(tmp_path / "state.sqlite") as store:
        assert not prepare(store, config, now - timedelta(hours=1))
        plan = prepare(store, config, now)
        assert plan["jobs"]
        queries = {job["query_index"] for job in plan["jobs"]}
        for index in queries:
            assert {job["page"] for job in plan["jobs"] if job["query_index"] == index} == \
                set(range(1, 11))
        advance(store, plan, empty=False, stop_on_empty=True, now=now)
        assert prepare(store, config, now + timedelta(minutes=10))["cursor"] == 1
        while plan["cursor"] < len(plan["jobs"]):
            advance(store, plan, empty=True, stop_on_empty=True, now=now)
        assert plan["completed_at"] and plan["skipped_empty"] > 0
        assert not prepare(store, config, now + timedelta(hours=23))
        assert prepare(store, config, now + timedelta(hours=24))["cursor"] == 0


def test_local_logistic_fit_is_finite_and_learns_signal() -> None:
    # Prueba matemática, sin respuestas o IDs sintéticos de Vinted.
    x = np.array([[0, 1], [1, 0]] * 30, dtype=float)
    y = np.array([0, 1] * 30)
    weights, intercept = fit_logistic(x, y, Tuning())
    assert np.isfinite(weights).all() and np.isfinite(intercept)
    assert ((x @ weights + intercept >= 0) == y).mean() > 0.95


def test_tuning_requires_real_labels_and_never_applies_weights(tmp_path: Path) -> None:
    copytree(ROOT / "config", tmp_path / "config")
    from vinted_hunter.pipeline.models import Listing

    with SQLiteStore(tmp_path / "data/vh.sqlite") as store:
        for directory, label in (("recall/10690539539", "good"),
                                 ("precision/10685333948", "fake")):
            row = evaluate_fixture(ROOT, ROOT / "tests" / directory)
            store.save(Listing.model_validate(row["body"]), row["profile"], row["tier"],
                       row["score"], row["trace"], False)
            store.label(row["id"], label, datetime.now(UTC).isoformat())
    original = (tmp_path / "config/scoring.yaml").read_bytes()
    result = propose(tmp_path)
    assert not result["ready"] and result["usable"] == 2 and result["required"] == 50
    assert not (tmp_path / "config/scoring.proposed.yaml").exists()
    assert (tmp_path / "config/scoring.yaml").read_bytes() == original
