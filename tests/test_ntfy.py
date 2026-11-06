import gzip
from decimal import Decimal
from pathlib import Path

from vinted_hunter.notify.ntfy import NtfyNotifier, post_message
from vinted_hunter.sources.vinted.catalog import parse_catalog
from vinted_hunter.storage.sqlite_store import SQLiteStore

ROOT = Path(__file__).parents[1]


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


def test_http_post_uses_json_and_never_follows_redirects(monkeypatch) -> None:
    from vinted_hunter.notify import ntfy

    def mock_post(url, **kwargs):
        assert url == "https://ntfy.sh/"
        assert kwargs["json"] == {"topic": "fake-health-topic"}
        assert kwargs["allow_redirects"] is False
        return type("Response", (), {"status_code": 200})()

    monkeypatch.setattr(ntfy.requests, "post", mock_post)
    assert post_message({"topic": "fake-health-topic"}) == 200
