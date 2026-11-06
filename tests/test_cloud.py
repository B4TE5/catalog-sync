import json
from base64 import urlsafe_b64encode
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag

from vinted_hunter.cloud import archive_database, label_request, restore_database
from vinted_hunter.cloud_crypto import BOARD_CONTEXT, STATE_CONTEXT, seal, unseal
from vinted_hunter.storage.sqlite_store import SQLiteStore

KEY = urlsafe_b64encode(bytes(range(32))).decode().rstrip("=")


def test_aead_uses_fresh_nonce_and_authenticates_context() -> None:
    first = seal(b"plain listing data", KEY, BOARD_CONTEXT)
    second = seal(b"plain listing data", KEY, BOARD_CONTEXT)
    assert first != second and "plain listing data" not in first
    assert unseal(first, KEY, BOARD_CONTEXT) == b"plain listing data"
    with pytest.raises(InvalidTag):
        unseal(first, KEY, STATE_CONTEXT)
    envelope = json.loads(first)
    envelope["data"] = ("A" if envelope["data"][0] != "A" else "B") + envelope["data"][1:]
    with pytest.raises(InvalidTag):
        unseal(json.dumps(envelope), KEY, BOARD_CONTEXT)


def test_sqlite_encrypted_snapshot_retains_state(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite"
    dest = tmp_path / "destination.sqlite"
    with SQLiteStore(source) as store:
        store.set_setting("failures", "3")
        store.save_run({"seen": 7, "new": 2, "errors": []})
    ciphertext = archive_database(source, KEY)
    assert "SQLite format" not in ciphertext
    restore_database(dest, ciphertext, KEY)
    with SQLiteStore(dest) as store:
        assert store.setting("failures") == "3"
        assert store.runs(1)[0]["seen"] == 7


@pytest.mark.parametrize(
    ("author", "title", "expected"),
    [
        ("owner", "label:10685333948:meh", (10685333948, "meh")),
        ("other", "label:10685333948:fake", None),
        ("owner", "label:0000:good", None),
        ("owner", "label:10685333948:good\nanything", None),
        ("owner", "label:9223372036854775808:fake", None),
        ("owner", "label:10685333948:invalid", None),
    ],
)
def test_feedback_requires_owner_and_strict_title(author, title, expected) -> None:
    assert label_request("owner", author, title) == expected
