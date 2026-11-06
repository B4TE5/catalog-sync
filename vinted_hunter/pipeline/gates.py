"""Filtros duros, con motivos persistibles."""

from vinted_hunter.config import Config, Profile
from vinted_hunter.pipeline.models import Evidence, Listing, Seller
from vinted_hunter.pipeline.text import hood_signal, matches, normalize, stated_sizes

ATTRIBUTE_GATES = frozenset({"size", "hood", "status", "color"})


def gate(
    listing: Listing,
    profile: Profile,
    config: Config,
    seller: Seller | None = None,
    evidence: Evidence | None = None,
    *,
    detailed: bool = False,
) -> tuple[str | None, list[str]]:
    passed = []
    text = " ".join(filter(None, (listing.title, listing.description)))
    words = config.scoring.words
    category_hood = next(
        (
            hood
            for hood in ("with", "without")
            if listing.category_id and config.ids.catalog_ids.get(hood) == listing.category_id
        ),
        None,
    )
    hood = category_hood or hood_signal(text, words)
    categories = set(config.ids.catalog_ids.values())
    expected_size = normalize(profile.size)
    explicit_sizes = stated_sizes(listing.title, words.get("size_labels", []))
    size = normalize((listing.size or "").split(" / ")[0])
    tests = {
        "category": not categories
        or listing.category_id is None
        or listing.category_id in categories,
        "price": listing.currency == "EUR"
        and profile.price_floor <= listing.price <= profile.price_max,
        "replica": not matches(text, words["replica"]),
    }
    for reason, valid in tests.items():
        if not valid:
            return reason, passed
        passed.append(reason)
    if detailed:
        attributes = {
            "size": (not size or size == expected_size)
            and (not explicit_sizes or expected_size in explicit_sizes)
            if size or explicit_sizes
            else None,
            "hood": hood == profile.hood if hood is not None else None,
            "status": listing.status in profile.allowed_status if listing.status else None,
            "color": bool(matches(listing.color, words.get(profile.color, [profile.color])))
            if profile.color and listing.color and listing.color.strip()
            else None,
        }
        for reason, valid in attributes.items():
            if valid is False:
                return reason, passed
            if reason != "color" or profile.color:
                passed.append(reason if valid else f"{reason}_unconfirmed")
    elif hood is None:
        passed.append("hood_unconfirmed")
    if detailed and len(listing.photos) < profile.min_photos:
        return "photos", passed
    if detailed:
        passed.append("photos")
    for rule in profile.brand_rules:
        text_pass = not rule.if_text_any or bool(matches(text, rule.if_text_any))
        status_pass = not rule.if_condition or (detailed and listing.status == rule.if_condition)
        if text_pass and status_pass and listing.price < rule.and_price_below:
            return rule.reason, passed
    passed.append("brand_rules")
    if seller:
        if (
            seller.feedback_count is not None
            and seller.feedback_count < profile.seller_min_feedback
        ):
            return "seller_feedback", passed
        if seller.rating is not None and seller.rating < profile.seller_min_rating:
            return "seller_rating", passed
        passed.extend(["seller_feedback", "seller_rating"])
    if evidence:
        for rejected, reason in (
            (evidence.qr == "qr_foreign_domain", "fake_certilogo_domain"),
            (evidence.blacklisted_photo, "blacklisted_photo"),
            (evidence.shared_photo, "shared_photo"),
        ):
            if rejected:
                return reason, passed
            passed.append(reason)
    return None, passed
