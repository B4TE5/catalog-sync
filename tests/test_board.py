import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from shutil import copytree

from vinted_hunter.board.build import build
from vinted_hunter.pipeline.models import Listing
from vinted_hunter.replay import evaluate_fixture
from vinted_hunter.storage.sqlite_store import SQLiteStore

ROOT = Path(__file__).parents[1]


def test_board_refreshes_old_offers_without_rewriting_decision_history(tmp_path: Path) -> None:
    copytree(ROOT / "config", tmp_path / "config")
    row = evaluate_fixture(ROOT, ROOT / "tests/recall/10690539539")
    # Caso real, envejecido para comprobar el límite temporal del tablero.
    item = Listing.model_validate(row["body"]).model_copy(update={
        "availability": "active", "uploaded_at": datetime.now(UTC) - timedelta(days=8),
    })
    original = row["trace"]["pricing"].copy()
    with SQLiteStore(tmp_path / "data/vh.sqlite") as store:
        store.save(item, row["profile"], row["tier"], row["score"], row["trace"], True)
    html = build(tmp_path).read_text(encoding="utf-8")
    payload = json.loads(re.search(
        r'<script type="application/json" id="payload">([^<]+)</script>', html,
    )[1])
    displayed = payload["listings"][0]["display_pricing"]
    assert displayed["negotiable"] and not displayed["buy_now"]
    assert not original["negotiable"]
    # La única observación de marca fija p10 en 60 EUR; se respeta ese suelo.
    assert displayed["offer"] == "60"
    with SQLiteStore(tmp_path / "data/vh.sqlite") as store:
        assert store.record(item.id)["trace"]["pricing"] == original
