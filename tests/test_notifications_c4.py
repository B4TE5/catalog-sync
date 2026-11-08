from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from vinted_hunter.config import load_config
from vinted_hunter.notify.ntfy import notifier_for
from vinted_hunter.pipeline.models import Listing
from vinted_hunter.replay import evaluate_fixture
from vinted_hunter.storage.sqlite_store import SQLiteStore
from vinted_hunter.tune import profile_scores

ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize("profile", ["twojeys", "yzy-gap", "heron-preston", "rhude", "unknown"])
def test_other_profiles_never_reach_preflight_or_delivery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, profile: str,
) -> None:
    row = evaluate_fixture(ROOT, ROOT / "tests/recall/10690539539")
    item = Listing.model_validate(row["body"]).model_copy(update={"availability": "active"})
    monkeypatch.setenv("NTFY_TOPIC", "unit-test-topic")
    monkeypatch.setenv("NTFY_HEALTH_TOPIC", "unit-test-health")
    with SQLiteStore(tmp_path / "state.sqlite") as store:
        store.save(item, profile, "top", 100, row["trace"], False)
        checks = []
        sent = []
        notifier = notifier_for(ROOT, store, lambda row: checks.append(row["id"]) or True)
        notifier.post = lambda payload: sent.append(payload) or 200
        notifier.publish_listing(store.record(item.id))
        assert checks == [] and sent == []


def test_only_top_stone_reaches_delivery_and_diagnostic_is_not_a_listing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = evaluate_fixture(ROOT, ROOT / "tests/recall/10690539539")
    item = Listing.model_validate(row["body"]).model_copy(update={"availability": "active"})
    monkeypatch.setenv("NTFY_TOPIC", "unit-test-topic")
    monkeypatch.setenv("NTFY_HEALTH_TOPIC", "unit-test-health")
    with SQLiteStore(tmp_path / "state.sqlite") as store:
        store.save(item, "stone-island", "good", 74, row["trace"], False)
        sent = []
        notifier = notifier_for(ROOT, store, lambda row: True)
        notifier.clock = lambda: datetime.fromisoformat(row["body"]["uploaded_at"])
        notifier.post = lambda payload: sent.append(payload) or 200
        assert notifier.publish_listing(store.record(item.id)) is None
        store.save(item, "stone-island", row["tier"], row["score"], row["trace"], False)
        assert notifier.publish_listing(store.record(item.id)) == 200
        assert len(sent) == 1
        assert notifier.test_configuration() == 200
        assert "click" not in sent[-1] and "No es un anuncio" in sent[-1]["message"]
    config = load_config(ROOT)
    assert all(p.notify_min_tier == "top" for p in config.profiles)


def test_calibration_baseline_respects_profile_overrides() -> None:
    config = load_config(ROOT)
    rows = [evaluate_fixture(ROOT, ROOT / "tests/recall" / identifier)
            for identifier in ("10690539539", "10653233816")]
    keys = sorted({key for row in rows for key in row["trace"]["signals"]})
    features = np.array([[row["trace"]["signals"].get(key, 0) for key in keys] for row in rows])
    scores = profile_scores(features, rows, keys, config, config.scoring.weights)
    assert scores.tolist() == [75, 70]
    assert config.scoring.weights["authenticity_mentioned"] == 10
    assert rows[0]["trace"]["score"]["points"]["authenticity_mentioned"] == 20
