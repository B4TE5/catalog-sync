from datetime import UTC, datetime, timedelta
from pathlib import Path

from vinted_hunter.history import merge_history
from vinted_hunter.pipeline.models import Listing
from vinted_hunter.replay import evaluate_fixture
from vinted_hunter.storage.sqlite_store import SQLiteStore

ROOT = Path(__file__).parents[1]


def test_history_merge_is_additive_idempotent_and_preserves_newer_feedback(tmp_path: Path) -> None:
    stone = evaluate_fixture(ROOT, ROOT / "tests/recall/10690539539")
    rhude = evaluate_fixture(ROOT, ROOT / "tests/recall/10653233816")
    now = datetime.now(UTC)
    path = tmp_path / "history.sqlite"
    with SQLiteStore(path) as old:
        for row in (stone, rhude):
            old.save(Listing.model_validate(row["body"]), row["profile"], row["tier"],
                     row["score"], row["trace"], False)
        old.label(stone["id"], "good", (now - timedelta(days=1)).isoformat())
        old.observe_price(Listing.model_validate(stone["body"]), stone["profile"], now.isoformat())
    with SQLiteStore(tmp_path / "current.sqlite") as store:
        store.save(Listing.model_validate(stone["body"]), stone["profile"], stone["tier"],
                   stone["score"], stone["trace"], False)
        store.label(stone["id"], "meh", now.isoformat())
        assert merge_history(store, path)["added"] == 1
        assert merge_history(store, path)["added"] == 0
        assert {r["id"] for r in store.records()} == {stone["id"], rhude["id"]}
        assert store.db.execute("SELECT label FROM labels").fetchone()[0] == "meh"
        assert store.db.execute("SELECT count(*) FROM price_history").fetchone()[0] == 1
