"""SQLite local con migraciones versionadas."""

import json
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import TracebackType
from typing import Any, Self

from vinted_hunter.pipeline.models import Listing, Seller
from vinted_hunter.storage.base import StateStore

MIGRATION_1 = """
CREATE TABLE listings (
    id INTEGER PRIMARY KEY, profile TEXT NOT NULL, seller_id INTEGER,
    body TEXT NOT NULL, tier TEXT, score INTEGER, trace TEXT, backfill INTEGER NOT NULL
);
CREATE TABLE sellers (id INTEGER PRIMARY KEY, captured TEXT NOT NULL, body TEXT NOT NULL);
CREATE TABLE photos (
    listing_id INTEGER NOT NULL, hash TEXT NOT NULL, is_primary INTEGER NOT NULL,
    PRIMARY KEY (listing_id, hash)
);
CREATE INDEX photos_hash ON photos(hash);
CREATE INDEX listings_seller ON listings(seller_id);
CREATE TABLE price_history (
    listing_id INTEGER NOT NULL, profile TEXT NOT NULL,
    captured TEXT NOT NULL, amount TEXT NOT NULL,
    PRIMARY KEY (listing_id, profile, captured)
);
CREATE TABLE run_log (id INTEGER PRIMARY KEY, body TEXT NOT NULL);
CREATE TABLE labels (listing_id INTEGER PRIMARY KEY, label TEXT NOT NULL, captured TEXT NOT NULL);
CREATE TABLE price_stats (profile TEXT PRIMARY KEY, body TEXT NOT NULL);
CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
PRAGMA user_version = 1;
"""
MIGRATION_2 = """
CREATE TABLE listing_events (
    id INTEGER PRIMARY KEY, listing_id INTEGER NOT NULL, captured TEXT NOT NULL,
    kind TEXT NOT NULL, body TEXT NOT NULL
);
CREATE INDEX listing_events_item ON listing_events(listing_id, captured);
PRAGMA user_version = 2;
"""


class SQLiteStore(StateStore):
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode = WAL")
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version == 0:
            self.db.executescript("BEGIN IMMEDIATE;\n" + MIGRATION_1 + "\nCOMMIT;")
            version = 1
        if version == 1:
            self.db.executescript("BEGIN IMMEDIATE;\n" + MIGRATION_2 + "\nCOMMIT;")
        elif version != 2:
            self.db.close()
            raise RuntimeError(f"Versión de base de datos no compatible: {version}")

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if kind is None:
                self.db.commit()
            else:
                self.db.rollback()
        finally:
            self.db.close()

    def listing(self, listing_id: int) -> Listing | None:
        row = self.db.execute("SELECT body FROM listings WHERE id=?", (listing_id,)).fetchone()
        return Listing.model_validate_json(row["body"]) if row else None

    def observe_price(self, listing: Listing, profile: str, at: str) -> Decimal | None:
        row = self.db.execute(
            "SELECT amount FROM price_history WHERE listing_id=? AND profile=? "
            "ORDER BY captured DESC LIMIT 1",
            (listing.id, profile),
        ).fetchone()
        self.db.execute(
            "INSERT OR REPLACE INTO price_history VALUES (?,?,?,?)",
            (listing.id, profile, at, str(listing.price)),
        )
        return Decimal(row["amount"]) if row else None

    def save(
        self,
        listing: Listing,
        profile: str,
        tier: str | None,
        score: int | None,
        trace: dict[str, Any],
        backfill: bool,
    ) -> None:
        old = self.listing(listing.id)
        if old and listing.availability == "unknown" and old.availability != "unknown":
            listing = listing.model_copy(update={
                key: getattr(old, key) for key in (
                    "availability", "availability_checked_at", "last_active_at",
                    "closed_observed_at", "observed_sale_price",
                )
            })
        if old and old.availability != listing.availability:
            self.db.execute(
                "INSERT INTO listing_events(listing_id,captured,kind,body) VALUES (?,?,?,?)",
                (listing.id, datetime.now(UTC).isoformat(), "availability", json.dumps({
                    "from": old.availability, "to": listing.availability,
                    "price": str(listing.price), "estimated_sale_time": True,
                })),
            )
        self.db.execute(
            "INSERT INTO listings VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
            "profile=excluded.profile,seller_id=excluded.seller_id,body=excluded.body,"
            "tier=excluded.tier,score=excluded.score,trace=excluded.trace,backfill=excluded.backfill",
            (
                listing.id,
                profile,
                listing.seller_id,
                listing.model_dump_json(),
                tier,
                score,
                json.dumps(trace, ensure_ascii=False),
                int(backfill),
            ),
        )

    @staticmethod
    def _record(row: sqlite3.Row) -> dict[str, Any]:
        return {**dict(row), "body": json.loads(row["body"]), "trace": json.loads(row["trace"])}

    def record(self, listing_id: int) -> dict[str, Any] | None:
        row = self.db.execute("SELECT * FROM listings WHERE id=?", (listing_id,)).fetchone()
        return self._record(row) if row else None

    def records(self, *, scored: bool = False) -> list[dict[str, Any]]:
        condition = "WHERE tier IN ('top','good','maybe','low')" if scored else ""
        rows = self.db.execute(f"SELECT * FROM listings {condition} ORDER BY id DESC")
        return [self._record(row) for row in rows]

    def plausible_prices(
        self, profile: str, score: float, categories: set[int], floor: Decimal
    ) -> list[Decimal]:
        if not categories:
            return []
        rows = self.db.execute(
            "SELECT body FROM listings LEFT JOIN labels ON labels.listing_id=listings.id "
            "WHERE profile=? AND score>=? AND tier IN ('top','good','maybe','low') "
            "AND COALESCE(labels.label, '') != 'fake' "
            "AND json_extract(trace, '$.enriched')=1",
            (profile, max(60, score)),
        )
        return [
            item.price
            for row in rows
            if (item := Listing.model_validate_json(row["body"])).category_id in categories
            and item.currency == "EUR"
            and item.price >= floor
        ]

    def save_market(self, profile: str, market: dict[str, Any]) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO price_stats VALUES (?, ?)",
            (profile, json.dumps(market, default=str)),
        )

    def flush(self) -> None:
        self.db.commit()

    def seller(self, seller_id: int, after: datetime) -> Seller | None:
        row = self.db.execute(
            "SELECT body FROM sellers WHERE id=? AND captured>=?",
            (seller_id, after.isoformat()),
        ).fetchone()
        return Seller.model_validate_json(row["body"]) if row else None

    def cache_seller(self, seller: Seller, now: datetime) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO sellers VALUES (?,?,?)",
            (seller.id, now.isoformat(), seller.model_dump_json()),
        )

    def save_photos(self, listing_id: int, hashes: list[str], primary: str | None) -> None:
        self.db.executemany(
            "INSERT OR REPLACE INTO photos VALUES (?,?,?)",
            [(listing_id, value, int(value == primary)) for value in hashes],
        )

    def matching_hashes(self, seller_id: int) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT photos.*, listings.body, listings.seller_id, labels.label FROM photos "
            "JOIN listings ON listings.id=photos.listing_id "
            "LEFT JOIN labels ON labels.listing_id=photos.listing_id "
            "WHERE listings.seller_id=? OR labels.label='fake'",
            (seller_id,),
        )
        return [dict(row) for row in rows]

    def shared_hash(self, value: str, seller_id: int) -> bool:
        return (
            self.db.execute(
                "SELECT 1 FROM photos JOIN listings ON listings.id=photos.listing_id "
                "WHERE hash=? AND seller_id!=? LIMIT 1",
                (value, seller_id),
            ).fetchone()
            is not None
        )

    def label(self, listing_id: int, label: str, captured: str) -> None:
        if self.listing(listing_id) is None:
            raise ValueError(f"Anuncio desconocido: {listing_id}")
        self.db.execute(
            "INSERT OR REPLACE INTO labels VALUES (?,?,?)", (listing_id, label, captured)
        )
        self.db.execute(
            "INSERT INTO listing_events(listing_id,captured,kind,body) VALUES (?,?,?,?)",
            (listing_id, captured, "label", json.dumps({"label": label})),
        )

    def seller_flags(self, seller_id: int) -> set[str]:
        return {row[0] for row in self.db.execute(
            "SELECT DISTINCT label FROM labels JOIN listings ON listings.id=labels.listing_id "
            "WHERE listings.seller_id=?", (seller_id,),
        )}

    def label_counts(self) -> dict[str, Any]:
        result: dict[str, Any] = {"total": {}, "by_profile": {}}
        for row in self.db.execute(
            "SELECT profile,label,count(*) AS n FROM labels "
            "JOIN listings ON listings.id=labels.listing_id GROUP BY profile,label"
        ):
            result["by_profile"].setdefault(row["profile"], {})[row["label"]] = row["n"]
            total = result["total"]
            total[row["label"]] = total.get(row["label"], 0) + row["n"]
        return result

    def update_listing(self, listing: Listing, at: datetime) -> None:
        old = self.listing(listing.id)
        if old is None:
            raise ValueError("Anuncio desconocido")
        if old.availability != listing.availability:
            self.db.execute(
                "INSERT INTO listing_events(listing_id,captured,kind,body) VALUES (?,?,?,?)",
                (listing.id, at.isoformat(), "availability", json.dumps({
                    "from": old.availability, "to": listing.availability,
                    "price": str(listing.price), "estimated_sale_time": True,
                    "last_active_at": old.last_active_at.isoformat()
                    if old.last_active_at else None,
                })),
            )
        self.db.execute("UPDATE listings SET body=?,seller_id=? WHERE id=?", (
            listing.model_dump_json(), listing.seller_id, listing.id,
        ))

    def setting(self, key: str, default: str = "") -> str:
        row = self.db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, value))

    def claim_setting(self, key: str, prior: str, value: str) -> bool:
        cursor = self.db.execute(
            "INSERT INTO settings(key,value) SELECT ?,? "
            "WHERE ?='' OR EXISTS (SELECT 1 FROM settings WHERE key=? AND value=?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value WHERE settings.value=?",
            (key, value, prior, key, prior, prior),
        )
        self.flush()
        return cursor.rowcount == 1

    def save_run(self, run: dict[str, Any]) -> None:
        self.db.execute("INSERT INTO run_log(body) VALUES (?)", (json.dumps(run),))

    def runs(self, limit: int) -> list[dict[str, Any]]:
        rows = self.db.execute("SELECT body FROM run_log ORDER BY id DESC LIMIT ?", (limit,))
        return [json.loads(row["body"]) for row in rows]

    def latest_backfill(self) -> dict[str, Any]:
        row = self.db.execute(
            "SELECT body FROM run_log WHERE json_type(body, '$.funnel') = 'object' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return json.loads(row["body"]) if row else {}
