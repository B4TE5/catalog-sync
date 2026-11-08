"""Revisión local de decisiones guardadas a partir de la evidencia disponible."""

from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from vinted_hunter.config import load_config
from vinted_hunter.pipeline.enrich import image_path
from vinted_hunter.pipeline.gates import gate
from vinted_hunter.pipeline.models import Evidence, Listing, Seller
from vinted_hunter.pipeline.pricing import Market
from vinted_hunter.pipeline.run import Pipeline, market_for
from vinted_hunter.pipeline.vision import inspect_photos
from vinted_hunter.storage.sqlite_store import SQLiteStore


def rescore(root: Path, store: SQLiteStore) -> int:
    config = load_config(root)
    now = datetime.now(UTC)
    pipeline = Pipeline(root, store, config, now)
    pipeline.markets = {profile.id: Market() for profile in config.profiles}
    profiles = {profile.id: profile for profile in config.profiles}
    fake_ids = {
        row[0] for row in store.db.execute("SELECT listing_id FROM labels WHERE label='fake'")
    }
    cache = root / "data" / "images"
    count = 0
    for row in store.records():
        profile = profiles.get(row["profile"])
        if profile is None:
            if row["tier"] != "rejected":
                trace = {**row["trace"], "pending": False, "gate_rejected": "profile_disabled"}
                trace["score"] = {
                    "tier": "rejected", "score": 0, "points": {},
                    "reasons": ["Perfil desactivado"], "flags": [],
                }
                store.save(
                    Listing.model_validate(row["body"]), row["profile"], "rejected", 0,
                    trace, bool(row["backfill"]),
                )
                count += 1
            continue
        count += 1
        listing = Listing.model_validate(row["body"])
        trace = row["trace"]
        enriched = trace.get("enriched", listing.category_id is not None)
        if (
            listing.category_id in profile.categories.conditional
            and listing.material is None and trace.get("gate_rejected") == "not_sweatshirt"
        ):
            enriched = False
        seller = Seller.model_validate(trace["seller"]) if trace.get("seller") else None
        if listing.seller_id:
            flags = store.seller_flags(listing.seller_id)
            if "fake" in flags and seller is None:
                seller = Seller(id=listing.seller_id, blacklisted=True)
            if seller:
                seller = seller.model_copy(update={
                    "blacklisted": "fake" in flags, "trusted": "good" in flags,
                })
        if seller is not None:
            cached = store.seller(seller.id, datetime.min.replace(tzinfo=UTC))
            if cached:
                seller.closet = cached.closet
        evidence = Evidence.model_validate(trace.get("evidence", {}))
        paths = [
            image_path(cache, str(url))
            for url in listing.photos[: config.scoring.capture.max_photos]
        ]
        images = [path.read_bytes() if path.is_file() else None for path in paths]
        if enriched and any(images):
            refs = root / (profile.refs_dir or Path("refs") / profile.id)
            scan = inspect_photos(
                images, refs, root / "refs" / "stock", config.scoring.thresholds, True
            )
            evidence = scan.model_copy(
                update={
                    "price_drop": evidence.price_drop,
                    "shared_photo": evidence.shared_photo,
                    "blacklisted_photo": evidence.blacklisted_photo,
                    "qr": evidence.qr
                    if scan.qr == "none"
                    or (evidence.qr == "certilogo_ok" and scan.qr != "qr_foreign_domain")
                    else scan.qr,
                    "qr_decoded": evidence.qr_decoded or scan.qr_decoded,
                }
            )
        reason, passed = gate(
            listing,
            profile,
            config,
            seller,
            evidence if evidence.hashes else None,
            detailed=enriched,
        )
        if not reason and listing.price < profile.price_floor and evidence.qr != "certilogo_ok":
            reason = "too_cheap_for_brand"
        if not reason and trace.get("gate_rejected") == "relisted":
            reason = "relisted"
        if row["id"] in fake_ids:
            reason = "labelled_fake"
        pending = reason is None and not (enriched and seller and evidence.hashes)
        pipeline.record(
            listing,
            profile,
            passed,
            evidence,
            bool(row["backfill"]),
            seller,
            reason,
            pending=pending,
            enriched=enriched,
        )
    for profile in config.profiles:
        store.save_market(profile.id, asdict(market_for(store, profile, config)))
    return count
