"""Eventos JSONL, rotación y ejecución de una pasada."""

import json
import os
import time
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any

from curl_cffi.requests import RequestsError

from vinted_hunter.config import Config, Profile, load_config
from vinted_hunter.pipeline.availability import check_listing
from vinted_hunter.pipeline.daily import advance, prepare
from vinted_hunter.pipeline.daily import summary as daily_summary
from vinted_hunter.pipeline.dedupe import is_drop, photo_dedupe
from vinted_hunter.pipeline.enrich import get_item, get_seller, image_bytes
from vinted_hunter.pipeline.funnel import funnel
from vinted_hunter.pipeline.gates import (
    ATTRIBUTE_GATES,
    gate,
    needs_confirmed_detail,
    sweatshirt_categories,
)
from vinted_hunter.pipeline.models import Evidence, Listing, Seller
from vinted_hunter.pipeline.pricing import Market, price_signals, summarize, timing
from vinted_hunter.pipeline.score import score
from vinted_hunter.pipeline.text import hood_signal, matches, normalize
from vinted_hunter.pipeline.vision import inspect_photos
from vinted_hunter.sources.vinted.catalog import VintedCatalog
from vinted_hunter.sources.vinted.client import (
    BudgetExhausted,
    CircuitOpen,
    HttpFailure,
    VintedClient,
)
from vinted_hunter.sources.vinted.parse import ParseError
from vinted_hunter.sources.vinted.search import Search, plan_searches
from vinted_hunter.storage.base import StateStore
from vinted_hunter.storage.sqlite_store import SQLiteStore

LOG_RETENTION_DAYS = 14
REMOTE_ERRORS = (RequestsError, HttpFailure, ParseError)


class EventLog:
    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.lock = Lock()
        folder.mkdir(parents=True, exist_ok=True)
        cutoff = (datetime.now(UTC) - timedelta(days=LOG_RETENTION_DAYS)).strftime("%Y%m%d")
        for file in folder.glob("run-????????.jsonl"):
            if file.stem[4:] < cutoff:
                file.unlink()

    def __call__(self, event: str, **data: Any) -> None:
        now = datetime.now(UTC)
        path = self.folder / f"run-{now:%Y%m%d}.jsonl"
        with self.lock, path.open("a", encoding="utf-8") as target:
            row = {"event": event, "at": now.isoformat(), **data}
            target.write(json.dumps(row, ensure_ascii=False) + "\n")


def market_for(store: StateStore, profile: Profile, config: Config) -> Market:
    return summarize(
        store.plausible_prices(
            profile.id,
            config.scoring.thresholds["plausible"],
            sweatshirt_categories(config, profile)
            | set(profile.categories.conditional),
            profile.price_floor,
        )
    )


def health(store: StateStore, config: Config) -> str:
    failures = int(store.setting("failures", "0"))
    if failures >= config.scoring.capture.unhealthy_after:
        return "unhealthy"
    if failures:
        return "degraded"
    return "healthy" if store.runs(1) else "unknown"


def select_profiles(
    listing: Listing,
    profiles: list[Profile],
    config: Config,
) -> list[Profile]:
    brand = normalize(listing.brand or "")
    exact = [
        p
        for p in profiles
        if brand
        in {normalize(name) for name in [p.brand, *config.ids.brand_names.get(p.brand, [])]}
    ]
    if exact:
        return exact
    if len(profiles) == 1:
        profile = profiles[0]
        names = [profile.brand, *config.ids.brand_names.get(profile.brand, [])]
        if matches(listing.title, names + [name.replace(" ", "") for name in names]):
            return profiles
    return []


def enrichment_priority(
    listing: Listing,
    profile: Profile,
    fresh: bool,
    now: datetime,
) -> tuple[bool, int, bool, float, float]:
    age = listing.uploaded_at or listing.first_seen or now
    return (
        not fresh,
        profile.priority,
        listing.price < profile.price_floor,
        float(listing.price / profile.price_max),
        -age.timestamp(),
    )


class Pipeline:
    def __init__(self, root: Path, store: StateStore, config: Config, now: datetime) -> None:
        self.root = root
        self.store = store
        self.config = config
        self.now = now
        self.emit = EventLog(root / "data" / "logs")
        self.reasons: Counter[str] = Counter()
        self.fetched_details: set[int] = set()
        self.deadline: float | None = None
        self.notifications = False
        self.availability_ids: set[int] = set()
        self.backfill_ids: set[int] = set()
        self.markets = {
            profile.id: market_for(store, profile, config) for profile in config.profiles
        }
        self.baseline = not store.runs(1)
        self.run: dict[str, Any] = dict(
            start=now.isoformat(),
            discovered=0,
            seen=0,
            new=0,
            candidates=0,
            scored=0,
            scored_ids=[],
            enriched=0,
            vision=0,
            errors=[],
            tiers=Counter(),
            qr=Counter(),
            vision_by_profile={},
            candidate_seconds=[],
            phases={},
        )

    def error(self, error: Exception | str, phase: str) -> None:
        message = (
            str(error)
            if isinstance(error, (HttpFailure, ParseError, str))
            else (type(error).__name__)
        )
        self.run["errors"].append(f"{phase}: {message}")
        self.emit("error", phase=phase, message=message)

    def feedback_seller(self, listing: Listing) -> Seller | None:
        if listing.seller_id and "fake" in self.store.seller_flags(listing.seller_id):
            return Seller(id=listing.seller_id, blacklisted=True)
        return None

    def verify_active(self, client: VintedClient, row: dict) -> bool:
        item = Listing.model_validate(row["body"])
        capture = self.config.scoring.capture
        if item.id not in self.availability_ids:
            if len(self.availability_ids) >= capture.availability_limit:
                return False
            self.availability_ids.add(item.id)
            self.run["availability_checks"] = len(self.availability_ids)
        fresh = item.availability_checked_at is not None and (
            datetime.now(UTC) - item.availability_checked_at
        ).total_seconds() <= capture.preflight_valid_seconds
        if not fresh:
            if not client.remaining("enrich"):
                return False
            try:
                previous = item.availability
                item = check_listing(client, self.store, item, datetime.now(UTC))
                if item.availability != previous:
                    self.run.setdefault("availability_detected", Counter())[item.availability] += 1
            except CircuitOpen:
                raise
            except REMOTE_ERRORS as error:
                self.error(error, "notify_preflight")
                return False
        profile = next(p for p in self.config.profiles if p.id == row["profile"])
        seller = (
            Seller.model_validate(row["trace"]["seller"]) if row["trace"].get("seller") else None
        )
        if seller:
            flags = self.store.seller_flags(seller.id)
            seller = seller.model_copy(update={
                "blacklisted": "fake" in flags, "trusted": "good" in flags,
            })
            cached = self.store.seller(seller.id, datetime.min.replace(tzinfo=UTC))
            if cached:
                seller.closet = cached.closet
        evidence = Evidence.model_validate(row["trace"].get("evidence", {}))
        reason, passed = gate(item, profile, self.config, seller, evidence, detailed=True)
        if reason or item.availability == "active":
            self.record(item, profile, passed, evidence, bool(row["backfill"]),
                        seller, reason, enriched=True, count_event=False)
        return item.availability == "active" and reason is None

    def maybe_notify(self, listing_id: int, client: VintedClient) -> None:
        if not self.notifications:
            return
        from vinted_hunter.notify.ntfy import notifier_for

        row = self.store.record(listing_id)
        if row is None:
            return
        notifier = notifier_for(self.root, self.store, lambda row: self.verify_active(client, row))
        status = notifier.publish_listing(row)
        if status is not None:
            counts = self.run.setdefault("notifications", {"sent": 0, "failed": 0})
            counts["sent" if status == 200 else "failed"] += 1
            self.emit("notification", id=listing_id, status=status)
            if status != 200:
                self.error(f"ntfy HTTP {status}", "notify")

    def refresh_states(self, client: VintedClient, *, repair_sizes: bool = False) -> None:
        profiles = {p.id: p for p in self.config.profiles}
        rows = self.store.records()
        if repair_sizes:
            rows = [r for r in rows if not r["body"].get("size")
                    and r["body"].get("size_source", "unknown") == "unknown"]
            cap = self.config.scoring.capture.size_repair_limit
        else:
            rows = [r for r in rows if r["profile"] in profiles
                    and r["tier"] in {"top", "good", "maybe"}
                    and r["id"] not in self.availability_ids
                    and r["body"].get("availability") not in {"sold", "gone"}]
            def state_priority(row: dict) -> tuple:
                checked = row["body"].get("availability_checked_at")
                stale = not checked or (datetime.now(UTC)-datetime.fromisoformat(checked)
                    ).total_seconds() >= self.config.scoring.capture.availability_stale_minutes*60
                return (-profiles[row["profile"]].priority, stale, row["score"] or 0,
                        row["body"].get("uploaded_at") or "")
            rows.sort(key=state_priority, reverse=True)
            cap = max(0, self.config.scoring.capture.availability_limit-len(self.availability_ids))
        counter = "size_repaired" if repair_sizes else "availability_checks"
        self.run.setdefault(counter, 0)
        self.run.setdefault("availability_detected", Counter())
        for row in rows[:cap]:
            if not client.remaining("enrich") or (
                self.deadline is not None and time.monotonic() >= self.deadline
            ):
                break
            item = Listing.model_validate(row["body"])
            try:
                current = check_listing(client, self.store, item, datetime.now(UTC))
            except CircuitOpen:
                raise
            except REMOTE_ERRORS as error:
                self.error(error, "availability")
                continue
            if repair_sizes:
                self.run[counter] += 1
            else:
                self.availability_ids.add(current.id)
                self.run[counter] = len(self.availability_ids)
            if current.availability != item.availability:
                self.run["availability_detected"][current.availability] += 1
            if not repair_sizes and current.availability == "active":
                trace = row["trace"]
                seller = Seller.model_validate(trace["seller"]) if trace.get("seller") else None
                if seller:
                    flags = self.store.seller_flags(seller.id)
                    seller = seller.model_copy(update={
                        "blacklisted": "fake" in flags, "trusted": "good" in flags,
                    })
                    cached = self.store.seller(seller.id, datetime.min.replace(tzinfo=UTC))
                    if cached:
                        seller.closet = cached.closet
                evidence = Evidence.model_validate(trace.get("evidence", {}))
                reason, passed = gate(current, profiles[row["profile"]], self.config,
                                      seller, evidence, detailed=True)
                self.record(current, profiles[row["profile"]], passed, evidence,
                            bool(row["backfill"]), seller, reason, enriched=True)
                if reason is None:
                    self.maybe_notify(current.id, client)
            self.store.flush()

    def record(
        self,
        listing: Listing,
        profile: Profile,
        passed: list[str],
        evidence: Evidence,
        backfill: bool,
        seller: Seller | None = None,
        rejection: str | None = None,
        pending: bool = False,
        enriched: bool = False,
        count_event: bool = True,
    ) -> None:
        clock = timing(listing, self.now, self.config.scoring)
        market = self.markets[profile.id]
        seller_verified = bool(
            seller
            and seller.feedback_count is not None
            and seller.rating is not None
            and {"seller_feedback", "seller_rating"} <= set(passed)
            and not rejection
        )
        prices = None
        result = None
        if not pending:
            prices = (
                price_signals(
                    listing,
                    profile,
                    market,
                    clock["age_minutes"],
                    evidence.price_drop,
                    self.config.scoring,
                    seller_verified=seller_verified,
                )
                if not rejection
                else None
            )
            result = score(
                listing,
                profile,
                seller,
                evidence,
                self.config,
                passed,
                prices or {},
                rejection,
            )
        trace = {
            "rules_revision": self.config.scoring.revision,
            "gates_passed": passed,
            "gate_rejected": rejection,
            "evidence": evidence.model_dump(mode="json"),
            "text": {
                key: matches(
                    f"{listing.title} {listing.description or ''}", keywords,
                    accent_sensitive=key == "knitwear_exact",
                )
                for key, keywords in self.config.scoring.words.items()
                if key != profile.color
            },
            "timing": clock,
            "pricing": prices,
            "score": result.model_dump() if result else None,
            "seller": seller.model_dump(
                mode="json",
                exclude={"closet"},
            )
            if seller
            else None,
            "wardrobe": (
                {
                    "reviewed": len(seller.closet),
                    "same_brand": sum(
                        normalize(item.brand or "") == normalize(profile.brand)
                        for item in seller.closet
                    ),
                    "new_with_tags": sum(item.status == "new_with_tags" for item in seller.closet),
                }
                if seller and seller.closet is not None
                else None
            ),
            "pending": pending,
            "enriched": enriched,
        }
        latent = result if result and not rejection else score(
            listing, profile, seller, evidence, self.config, passed, {"bargain": False}
        )
        trace["signals"] = {
            key: value / self.config.scoring.weights.get(
                "part" if key == "parts" else key, 1
            ) if self.config.scoring.weights.get("part" if key == "parts" else key) else 1
            for key, value in latent.points.items() if key not in {"base", "trusted_seller"}
        }
        self.store.save(
            listing,
            profile.id,
            result.tier if result else None,
            result.score if result else None,
            trace,
            backfill,
        )
        self.store.save_photos(listing.id, evidence.hashes, evidence.primary_hash)
        if result is None or not count_event:
            return
        self.run["tiers"][result.tier] += 1
        if rejection:
            self.reasons[rejection] += 1
            self.emit("gate_reject", id=listing.id, profile=profile.id, reason=rejection)
        else:
            self.run["scored"] += 1
            self.run["scored_ids"].append(listing.id)
            self.emit("score", id=listing.id, score=result.score, tier=result.tier)

    def catalog(
        self,
        client: VintedClient,
        pages: int,
        selftest: bool,
        daily_only: bool = False,
    ) -> dict[int, tuple[Listing, Profile, bool]]:
        source = VintedCatalog(client)
        cursor = int(self.store.setting("search_cursor", "0"))
        state = prepare(self.store, self.config, self.now, manual=daily_only) if (
            not selftest and os.environ.get("GITHUB_ACTIONS") == "true"
        ) else {}
        share = min(client.limits["catalog"], self.config.scoring.daily_backfill.catalog_share)
        searches, cursor = plan_searches(
            self.config, cursor, selftest,
            catalog_limit=max(1, client.limits["catalog"]-share) if state else None,
        )
        if state:
            searches = [] if daily_only else searches[:max(1, client.limits["catalog"]-share)]
        elif daily_only:
            return {}
        if not selftest:
            self.store.set_setting("search_cursor", str(cursor))
            self.store.flush()
        jobs = [(search, page) for page in range(1, pages + 1) for search in searches]
        if pages > 1 and searches:
            # Da profundidad a la primera búsqueda conocida dentro de la cuota de la pasada.
            primary = next((search for search in searches if search.expects_items), searches[0])
            jobs = [(primary, page) for page in range(1, pages + 1)]
            jobs += [(search, 1) for search in searches if search is not primary]
        found: dict[int, tuple[Listing, Profile, bool]] = {}
        ids_seen = set()
        cache: dict[str, Any] = {}

        def consume(search: Search, page: int, *, deep: bool = False) -> bool:
            key = json.dumps(search.query(page), sort_keys=True)
            try:
                reused = key in cache
                result = cache[key] if reused else source.search(search.query(page))
                cache[key] = result
                if page == 1 and search.expects_items and not result.listings:
                    raise ParseError("parser_suspect: 200 sin anuncios en una búsqueda habitual")
            except CircuitOpen:
                raise
            except REMOTE_ERRORS as error:
                if isinstance(error, ParseError) and "parser_suspect" not in str(error):
                    error = ParseError(f"parser_suspect: {error}")
                self.error(error, "catalog")
                return False
            query_key = "query:" + json.dumps(search.params, sort_keys=True)
            known_search = self.baseline or bool(self.store.setting(query_key))
            if page == 1:
                self.store.set_setting(query_key, self.now.isoformat())
                self.store.flush()
            ids_seen.update(listing.id for listing in result.listings)
            self.run["seen"] = len(ids_seen)
            self.emit(
                "parse_result",
                count=len(result.listings),
                invalid=result.invalid_count,
                raw=result.raw_count,
                page=page,
                profiles=[p.id for p in search.profiles],
            )
            for listing in result.listings:
                profiles = select_profiles(listing, search.profiles, self.config)
                if profiles:
                    previous = found.get(listing.id)
                    if previous is None or known_search and not previous[2]:
                        found[listing.id] = (listing, profiles[0], known_search)
                    if deep and previous is None:
                        self.backfill_ids.add(listing.id)
            if deep:
                advance(self.store, state, empty=not result.listings,
                        stop_on_empty=self.config.scoring.daily_backfill.stop_on_empty,
                        now=datetime.now(UTC), reused=reused)
                self.run["daily_backfill"] = daily_summary(state)
            return True

        for search, page in jobs[:client.limits["catalog"]]:
            consume(search, page)
        profiles = {profile.id: profile for profile in self.config.profiles}
        deep_start = client.counts["catalog"]
        deep_limit = client.limits["catalog"] if daily_only else share
        while state and state["cursor"] < len(state["jobs"]) and (
            client.remaining("catalog") > 0 and client.counts["catalog"]-deep_start < deep_limit
        ):
            job = state["jobs"][state["cursor"]]
            related = [profiles[key] for key in job["profiles"] if key in profiles]
            if not related:
                state["cursor"] += 1
                continue
            params = {key: value for key, value in job["params"].items()
                      if key not in {"page", "order"}}
            if not consume(Search(related, params, job["expects_items"]), job["page"], deep=True):
                break
        if state:
            self.run["daily_backfill"] = daily_summary(state)
        return found

    def candidate(
        self,
        client: VintedClient,
        listing: Listing,
        profile: Profile,
        backfill: bool,
        evidence: Evidence,
        is_new: bool,
        *,
        detail_loaded: bool = False,
    ) -> None:
        settings = self.config.scoring.capture
        seller = None
        enriched = False
        if blocked := self.feedback_seller(listing):
            self.record(listing, profile, [], evidence, backfill, blocked,
                        "seller_blacklisted")
            return
        try:
            if not detail_loaded:
                listing = get_item(client, listing, self.now)
            enriched = True
            self.run["enriched"] += 1
            self.fetched_details.add(listing.id)
            reason, passed = gate(listing, profile, self.config, detailed=True)
            if not reason and listing.seller_id is None:
                raise ParseError("Ficha sin ID de vendedor")
            if not reason and listing.seller_id:
                seller = get_seller(client, self.store, listing.seller_id, self.now, settings)
                reason, passed = gate(listing, profile, self.config, seller, detailed=True)
            if not reason:
                images = image_bytes(client, listing, self.root / "data" / "images", settings)
                if not any(images):
                    raise BudgetExhausted("Sin fotos descargadas para el candidato")
                refs = profile.refs_dir or Path("refs") / profile.id
                vision = inspect_photos(
                    images,
                    self.root / refs,
                    self.root / "refs" / "stock",
                    self.config.scoring.thresholds,
                    True,
                )
                if not vision.hashes:
                    raise ParseError("Las fotos del anuncio no se pudieron analizar")
                vision.price_drop = evidence.price_drop
                evidence = vision
                self.run["vision"] += 1
                self.run["vision_by_profile"].setdefault(profile.id, Counter())[evidence.qr] += 1
                self.run["qr"][evidence.qr] += 1
                relisted = photo_dedupe(
                    self.store,
                    listing,
                    evidence,
                    int(
                        self.config.scoring.thresholds["relist_distance"],
                    ),
                )
                if relisted and is_new:
                    self.run["new"] -= 1
                reason, passed = gate(
                    listing, profile, self.config, seller, evidence, detailed=True
                )
                reason = reason or ("relisted" if relisted else None)
        except BudgetExhausted:
            self.record(
                listing, profile, [], evidence, backfill, seller, pending=True, enriched=enriched
            )
            return
        except CircuitOpen:
            self.record(
                listing, profile, [], evidence, backfill, seller, pending=True, enriched=enriched
            )
            raise
        except REMOTE_ERRORS as error:
            if not enriched and isinstance(error, HttpFailure) and error.status == 404:
                self.record(
                    listing, profile, [], evidence, backfill,
                    rejection="listing_unavailable",
                )
                return
            self.error(error, "enrich")
            self.record(
                listing, profile, [], evidence, backfill, seller, pending=True, enriched=enriched
            )
            return
        self.record(listing, profile, passed, evidence, backfill, seller, reason, enriched=enriched)
        if reason is None:
            self.maybe_notify(listing.id, client)

    def process(
        self,
        client: VintedClient,
        found: dict[int, tuple[Listing, Profile, bool]],
        backfill: bool,
        candidate_cap: int | None,
    ) -> None:
        work = []
        for listing, profile, known_search in found.values():
            item_backfill = backfill or listing.id in self.backfill_ids
            row = self.store.record(listing.id)
            previous = Listing.model_validate(row["body"]) if row else None
            listing.first_seen = (previous.first_seen if previous else None) or self.now
            previous_price = self.store.observe_price(listing, profile.id, self.now.isoformat())
            dropped = is_drop(listing, previous_price)
            needs_detail = (
                row
                and "enriched" not in row["trace"]
                and needs_confirmed_detail(row["trace"].get("gate_rejected"), profile)
            )
            if (
                row
                and row["tier"] is not None
                and previous_price == listing.price
                and not needs_detail
            ):
                continue
            if not row:
                self.run["discovered"] += 1
            is_new = not item_backfill and (not row and known_search or dropped)
            if is_new:
                self.run["new"] += 1
            reason, passed = gate(
                listing, profile, self.config, self.feedback_seller(listing)
            )
            pending_drop = (
                row is not None
                and row["tier"] is None
                and row["trace"].get("evidence", {}).get("price_drop", False)
            )
            evidence = Evidence(price_drop=dropped or pending_drop)
            self.record(
                listing,
                profile,
                passed,
                evidence,
                item_backfill,
                rejection=reason,
                pending=reason is None,
            )
            if reason is None:
                work.append((listing, profile, evidence, is_new,
                             (not row or dropped) and not item_backfill, item_backfill))
        self.run["candidates"] = len(work)
        self.store.flush()
        words = self.config.scoring.words

        def priority(job: tuple[Listing, Profile, Evidence, bool, bool, bool]) -> tuple:
            listing, profile, _, _, fresh, _ = job
            primary = enrichment_priority(listing, profile, fresh, self.now)
            if candidate_cap is None:
                return primary
            stated = hood_signal(listing.title, words)
            color_match = profile.color and matches(
                listing.title,
                words.get(profile.color, [profile.color]),
            )
            return (
                primary[0],
                primary[1],
                gate(listing, profile, self.config, detailed=True)[0] in ATTRIBUTE_GATES,
                listing.size is not None and listing.size != profile.size,
                not (stated == profile.hood or color_match),
                *primary[2:],
            )

        profiles = {profile.id: profile for profile in self.config.profiles}
        for row in self.store.records():
            if row["tier"] is not None or row["id"] in found or row["profile"] not in profiles:
                continue
            listing = Listing.model_validate(row["body"])
            profile = profiles[row["profile"]]
            work.append((listing, profile, Evidence.model_validate(
                row["trace"].get("evidence", {})
            ), False, False, bool(row["backfill"])))
        self.run["candidates"] = len(work)
        work.sort(key=priority)
        ordered = work
        if candidate_cap is not None:
            first_per_profile: dict[str, tuple] = {}
            remaining = []
            for job in work:
                profile_id = job[1].id
                if profile_id in first_per_profile:
                    remaining.append(job)
                else:
                    first_per_profile[profile_id] = job
            ordered = sorted([*first_per_profile.values(), *remaining], key=lambda job: not job[4])
        for listing, profile, evidence, is_new, _, job_backfill in ordered[:candidate_cap]:
            if not client.remaining("enrich") or (
                self.deadline is not None and time.monotonic() >= self.deadline
            ):
                break
            self.emit("candidate", id=listing.id, profile=profile.id)
            started = time.monotonic()
            self.candidate(client, listing, profile, job_backfill, evidence, is_new)
            duration = round(time.monotonic() - started, 2)
            self.run["candidate_seconds"].append(duration)
            self.store.flush()

    def backfill_funnel(self, found: dict[int, tuple[Listing, Profile, bool]]) -> dict:
        cohorts: dict[str, list[dict]] = {}
        fetched: Counter[str] = Counter()
        for listing, profile, _ in found.values():
            row = self.store.record(listing.id)
            if row is None:
                row = {"id": listing.id, "body": {}, "trace": {}, "tier": None}
            cohorts.setdefault(profile.id, []).append(row)
            fetched[profile.id] += int(listing.id in self.fetched_details)
        return {
            profile: {**funnel(rows), "fetched": fetched[profile]}
            for profile, rows in cohorts.items()
        }

    def revalidate(self) -> int:
        """Aplica los gates actuales a las tarjetas enriquecidas guardadas."""
        profiles = {profile.id: profile for profile in self.config.profiles}
        rows = [row for row in self.store.records() if row["tier"] != "rejected"]
        changed = 0
        for row in rows:
            profile = profiles.get(row["profile"])
            if profile is None:
                continue
            listing = Listing.model_validate(row["body"])
            trace = row["trace"]
            seller = Seller.model_validate(trace["seller"]) if trace.get("seller") else None
            if seller:
                flags = self.store.seller_flags(seller.id)
                seller = seller.model_copy(update={
                    "blacklisted": "fake" in flags, "trusted": "good" in flags,
                })
            seller = self.feedback_seller(listing) or seller
            evidence = Evidence.model_validate(trace.get("evidence", {}))
            enriched = trace.get("enriched", listing.category_id is not None)
            reason, passed = gate(
                listing, profile, self.config, seller,
                evidence if evidence.hashes else None, detailed=enriched,
            )
            if not reason and listing.price < profile.price_floor and evidence.qr != "certilogo_ok":
                reason = "too_cheap_for_brand"
            if needs_confirmed_detail(reason, profile) and not trace.get("enriched"):
                continue
            if reason:
                self.record(
                    listing,
                    profile,
                    passed,
                    evidence,
                    bool(row["backfill"]),
                    seller,
                    reason,
                    enriched=enriched,
                )
                changed += 1
        self.store.flush()
        return changed

    def execute(
        self, pages: int, backfill: bool, selftest: bool, pending_only: bool = False,
        notifications: bool = False,
        daily_only: bool = False,
    ) -> dict[str, Any]:
        capture = self.config.scoring.capture
        self.notifications = notifications
        self.run["notifications_handled"] = notifications
        self.run.update(
            pages=pages, backfill=backfill, selftest=selftest, pending_only=pending_only,
            rules_revision=self.config.scoring.revision, daily_backfill_only=daily_only,
        )
        self.emit("run_start", pages=pages, backfill=backfill, selftest=selftest)
        started = time.monotonic()
        self.deadline = started + capture.max_pass_seconds - 45
        if self.store.setting("rules_revision") != self.config.scoring.revision:
            from vinted_hunter.pipeline.rescore import rescore

            self.run["rescored"] = rescore(self.root, self.store)
            self.store.set_setting("rules_revision", self.config.scoring.revision)
            self.store.flush()
        base = (
            f"https://www.{self.config.profiles[0].domain}"
            if self.config.profiles
            else ("https://www.vinted.es")
        )
        with VintedClient(
            base, capture.catalog_limit,
            capture.cloud_enrich_limit if os.environ.get("GITHUB_ACTIONS") == "true"
            else capture.enrich_limit,
            capture.wait, self.emit,
        ) as client:
            try:
                retry_at = self.store.setting("retry_at")
                if retry_at and self.now < datetime.fromisoformat(retry_at):
                    self.run["deferred"] = True
                    self.error("Circuito en espera hasta " + retry_at, "capture")
                else:
                    self.run["revalidated"] = self.revalidate()
                    client.home()
                    self.run["cookies"] = bool(client.session.cookies)
                    catalog_start = time.monotonic()
                    found = {} if pending_only else self.catalog(
                        client, pages, selftest, daily_only=daily_only
                    )
                    self.run["phases"]["catalog"] = round(time.monotonic() - catalog_start, 2)
                    pipeline_start = time.monotonic()
                    try:
                        full_deadline = self.deadline
                        if not selftest and self.deadline is not None:
                            self.deadline -= capture.availability_reserve_seconds
                        if pending_only:
                            self.refresh_states(client, repair_sizes=True)
                        self.process(client, found, backfill,
                                     0 if daily_only else 3 if selftest else None)
                        self.deadline = full_deadline
                        if not selftest:
                            self.refresh_states(client)
                            self.refresh_states(client, repair_sizes=True)
                    finally:
                        if backfill:
                            self.run["funnel"] = self.backfill_funnel(found)
                    self.run["phases"]["pipeline"] = round(time.monotonic() - pipeline_start, 2)
            except CircuitOpen as error:
                self.error(error, "capture")
                failures = int(self.store.setting("failures", "0")) + 1
                wait = min(
                    capture.max_backoff_seconds,
                    capture.backoff_seconds * 2 ** min(failures - 1, 20),
                )
                self.store.set_setting(
                    "retry_at", (datetime.now(UTC) + timedelta(seconds=wait)).isoformat()
                )
            except REMOTE_ERRORS as error:
                self.error(error, "capture")
            except Exception as error:
                self.error(type(error).__name__, "capture")
            except KeyboardInterrupt:
                self.error("Interrumpido", "capture")
                self.run["interrupted"] = True
            self.run["requests"] = client.requests
            self.run["budget"] = client.counts
        if not self.run.get("deferred"):
            failures = int(self.store.setting("failures", "0"))
            self.store.set_setting("failures", str(failures + 1 if self.run["errors"] else 0))
            if not self.run["errors"]:
                self.store.set_setting("retry_at", "")
        self.run["rejected"] = dict(self.reasons)
        rows = self.store.records()
        self.run["pending"] = sum(row["tier"] is None for row in rows)
        self.run["pending_unconfirmed"] = sum(
            row["tier"] is None and not row["trace"].get("enriched") for row in rows
        )
        self.run["pending_by_profile"] = {
            profile.id: sum(row["tier"] is None and row["profile"] == profile.id for row in rows)
            for profile in self.config.profiles
        }
        self.run["duration"] = round(time.monotonic() - started, 2)
        self.run["end"] = datetime.now(UTC).isoformat()
        for profile in self.config.profiles:
            market = market_for(self.store, profile, self.config)
            self.store.save_market(profile.id, asdict(market))
        self.store.save_run(self.run)
        self.emit("run_end", **self.run)
        return self.run


def run_pass(
    root: Path,
    pages: int = 1,
    *,
    backfill: bool = False,
    selftest: bool = False,
    database: str = "vh.sqlite",
    pending_only: bool = False,
    notifications: bool = False,
    daily_only: bool = False,
) -> dict[str, Any]:
    config = load_config(root)
    with SQLiteStore(root / "data" / database) as store:
        return Pipeline(root, store, config, datetime.now(UTC)).execute(
            pages, backfill, selftest, pending_only, notifications, daily_only
        )
