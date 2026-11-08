import gzip
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from shutil import copytree

import pytest

from vinted_hunter.notify.ntfy import (
    NtfyNotifier,
    notification_eligible,
    notifier_for,
    post_message,
)
from vinted_hunter.sources.vinted.catalog import parse_catalog
from vinted_hunter.storage.sqlite_store import SQLiteStore

ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize("repository_var", ["GITHUB_REPO", "GITHUB_REPOSITORY"])
def test_notifier_derives_public_pages_link(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, repository_var: str
) -> None:
    copytree(ROOT / "config", tmp_path / "config")
    monkeypatch.delenv("GITHUB_REPO", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.delenv("BOARD_URL", raising=False)
    monkeypatch.setenv(repository_var, "Example/catalog-sync")
    with SQLiteStore(tmp_path / "state.sqlite") as store:
        assert notifier_for(tmp_path, store).board_url == "https://example.github.io/catalog-sync/"
        monkeypatch.setenv("BOARD_URL", "https://example.org/board/")
        assert notifier_for(tmp_path, store).board_url == "https://example.org/board/"


def test_listing_payload_and_deduplication(tmp_path: Path) -> None:
    fixture = ROOT / "tests/fixtures/catalog-size-XL.html.gz"
    item = parse_catalog(gzip.decompress(fixture.read_bytes()).decode()).listings[0]
    trace = {
        "score": {"reasons": ["Muy buen estado", "Buena nota"]},
        "pricing": {"total": "50", "negotiable": False},
        "timing": {"age_minutes": 4},
        "evidence": {"price_drop": False},
    }
    sent = []

    def post(payload: dict) -> int:
        sent.append(payload)
        return 200

    with SQLiteStore(tmp_path / "state.sqlite") as store:
        store.save(item, "test", "top", 82, trace, False)
        notifier = NtfyNotifier(
            store,
            "fake-listing-topic",
            "fake-health-topic",
            shadow_mode=False,
            board_url="https://example.org/board?token=test#k=private",
            post=post,
            check_active=lambda row: True,
        )
        summary = {"errors": [], "scored_ids": [item.id]}
        notifier.publish(summary)
        notifier.publish(summary)
        assert len(sent) == 1
        assert sent[0]["priority"] == 5 and sent[0]["click"] == str(item.url)
        assert sent[0]["attach"] == str(item.photos[0])
        assert sent[0]["actions"] == [
            {"action": "view", "label": "Tablero", "url": "https://example.org/board"}
        ]
        assert "Subida hace 4 min" in sent[0]["message"]
        price = item.price - Decimal("0.01")
        trace["evidence"]["price_drop"] = True
        store.save(item.model_copy(update={"price": price}), "test", "top", 82, trace, False)
        notifier.publish(summary)
        notifier.publish(summary)
        assert len(sent) == 2 and sent[1]["title"].startswith("📉")


def test_shadow_mode_only_sends_health_transitions(tmp_path: Path) -> None:
    sent = []

    def post(payload: dict) -> int:
        sent.append(payload)
        return 200

    with SQLiteStore(tmp_path / "state.sqlite") as store:
        notifier = NtfyNotifier(store, "fake-listing-topic", "fake-health-topic", post=post)
        errors = {"errors": ["parser_suspect"], "scored_ids": [1]}
        store.set_setting("failures", "2")
        notifier.publish(errors)
        store.set_setting("failures", "3")
        notifier.publish(errors)
        notifier.publish(errors)
        notifier.publish({"errors": [], "deferred": True})
        assert len(sent) == 1
        store.set_setting("failures", "0")
        notifier.publish({"errors": [], "scored_ids": [1]})
        notifier.publish({"errors": [], "scored_ids": [1]})
    assert len(sent) == 2
    assert all(payload["topic"] == "fake-health-topic" for payload in sent)
    assert "recuperado" in sent[1]["title"]


@pytest.mark.parametrize("availability", ["sold", "reserved", "hidden", "gone"])
def test_closed_listings_are_never_notified(tmp_path: Path, availability: str) -> None:
    from vinted_hunter.replay import evaluate_fixture

    row = evaluate_fixture(ROOT, ROOT / "tests/recall/10690539539")
    row["body"]["availability"] = availability
    assert not notification_eligible(row, "good")[0]
    assert notification_eligible(row, "good", simulate_active=True,
                                 at=datetime.fromisoformat(row["body"]["uploaded_at"]))[0]
    sent = []
    with SQLiteStore(tmp_path / "state.sqlite") as store:
        notifier = NtfyNotifier(store, "fake-topic", None, shadow_mode=False,
                                min_tiers={"stone-island": "good"},
                                check_active=lambda row: True,
                                post=lambda payload: sent.append(payload) or 200)
        notifier.publish_listing(row)
    assert sent == []


def test_failed_delivery_retries_and_missing_live_check_denies(tmp_path: Path) -> None:
    from vinted_hunter.pipeline.models import Listing
    from vinted_hunter.replay import evaluate_fixture

    row = evaluate_fixture(ROOT, ROOT / "tests/recall/10690539539")
    item = Listing.model_validate(row["body"]).model_copy(update={"availability": "active"})
    with SQLiteStore(tmp_path / "state.sqlite") as store:
        store.save(item, row["profile"], row["tier"], row["score"], row["trace"], False)
        notifier = NtfyNotifier(store, "fake-topic", None, shadow_mode=False,
                                min_tiers={"stone-island": "good"}, post=lambda payload: 500,
                                clock=lambda: datetime.fromisoformat(row["body"]["uploaded_at"]))
        assert notifier.publish_listing(store.record(item.id)) is None
        notifier.check_active = lambda row: True
        assert notifier.publish_listing(store.record(item.id)) == 500
        assert not store.setting(f"ntfy:listing:{item.id}")
        notifier.post = lambda payload: 200
        assert notifier.publish_listing(store.record(item.id)) == 200
        assert store.setting(f"ntfy:listing:{item.id}") == str(item.price)


def test_http_post_uses_json_and_never_follows_redirects(monkeypatch) -> None:
    from vinted_hunter.notify import ntfy

    def mock_post(url, **kwargs):
        assert url == "https://ntfy.sh/"
        assert kwargs["json"] == {"topic": "fake-health-topic"}
        assert kwargs["allow_redirects"] is False
        return type("Response", (), {"status_code": 200})()

    monkeypatch.setattr(ntfy.requests, "post", mock_post)
    assert post_message({"topic": "fake-health-topic"}) == 200
