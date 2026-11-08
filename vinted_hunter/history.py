"""Fusión aditiva del histórico: conserva anuncios, observaciones y feedback."""

import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from vinted_hunter.pipeline.models import Listing
from vinted_hunter.storage.sqlite_store import SQLiteStore


def merge_history(store: SQLiteStore, source: Path) -> dict[str, int]:
    counts = {"added": 0, "sizes": 0, "states": 0, "observations": 0}
    with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as old:
        old.row_factory = sqlite3.Row
        for row in old.execute("SELECT * FROM listings"):
            incoming = Listing.model_validate_json(row["body"])
            existing = store.record(incoming.id)
            if existing is None:
                store.save(incoming, row["profile"], row["tier"], row["score"],
                           json.loads(row["trace"]), True)
                counts["added"] += 1
                continue
            current = Listing.model_validate(existing["body"])
            update = {}
            if incoming.size and not current.size:
                update.update(size=incoming.size, size_source=incoming.size_source)
                counts["sizes"] += 1
            elif not current.size and incoming.size_source in {"absent", "unavailable"}:
                update["size_source"] = incoming.size_source
            if incoming.first_seen and (
                not current.first_seen or incoming.first_seen < current.first_seen
            ):
                update["first_seen"] = incoming.first_seen
            if incoming.availability_checked_at and (
                not current.availability_checked_at
                or incoming.availability_checked_at > current.availability_checked_at
            ):
                update.update({key: getattr(incoming, key) for key in (
                    "availability", "availability_checked_at", "last_active_at",
                    "closed_observed_at", "observed_sale_price",
                )})
                counts["states"] += 1
            if update:
                store.update_listing(current.model_copy(update=update), datetime.now(UTC))
        for table, columns in (
            ("photos", "listing_id,hash,is_primary"),
            ("price_history", "listing_id,profile,captured,amount"),
            ("sellers", "id,captured,body"),
        ):
            names = columns.split(",")
            for row in old.execute(f"SELECT {columns} FROM {table}"):
                result = store.db.execute(
                    f"INSERT OR IGNORE INTO {table}({columns}) "
                    f"VALUES ({','.join('?' for _ in names)})", tuple(row),
                )
                if table == "price_history":
                    counts["observations"] += result.rowcount
        for row in old.execute("SELECT * FROM labels"):
            store.db.execute(
                "INSERT INTO labels VALUES (?,?,?) ON CONFLICT(listing_id) DO UPDATE "
                "SET label=excluded.label,captured=excluded.captured "
                "WHERE labels.captured < excluded.captured", tuple(row),
            )
        if old.execute("SELECT 1 FROM sqlite_master WHERE name='listing_events'").fetchone():
            for row in old.execute("SELECT listing_id,captured,kind,body FROM listing_events"):
                if not store.db.execute(
                    "SELECT 1 FROM listing_events WHERE listing_id=? AND captured=? "
                    "AND kind=? AND body=?", tuple(row),
                ).fetchone():
                    store.db.execute(
                        "INSERT INTO listing_events(listing_id,captured,kind,body) "
                        "VALUES (?,?,?,?)",
                        tuple(row),
                    )
    return counts
