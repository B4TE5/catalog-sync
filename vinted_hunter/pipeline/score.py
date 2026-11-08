"""Puntuación de candidatos y explicación en español."""

from vinted_hunter.config import Config, Profile
from vinted_hunter.pipeline.models import Evidence, Listing, ScoreResult, Seller
from vinted_hunter.pipeline.text import matches, normalize


def weights_for(profile: Profile, config: Config) -> dict[str, int]:
    return {**config.scoring.weights, **profile.scoring_weights}


def score(
    listing: Listing,
    profile: Profile,
    seller: Seller | None,
    evidence: Evidence,
    config: Config,
    passed: list[str],
    pricing: dict,
    rejected: str | None = None,
) -> ScoreResult:
    if rejected:
        return ScoreResult(tier="rejected", reasons=[rejected])
    scoring = config.scoring
    weights, limits = weights_for(profile, config), scoring.thresholds
    reasons = []
    points = {"base": weights["base"]}

    def add(key: str, reason: str, condition: bool = True) -> None:
        if condition and key in weights:
            points[key] = weights[key]
            reasons.append(reason)

    add(evidence.qr, "Certilogo ✓" if evidence.qr == "certilogo_ok" else "QR sin lectura")
    add("trusted_seller", "Vendedor de confianza por feedback", bool(seller and seller.trusted))
    if seller and seller.feedback_count is not None:
        feedback = seller.feedback_count
        reputation = seller.rating or 0
        add(
            "seller_high",
            f"{feedback} valoraciones · {reputation:.2f}",
            feedback >= limits["seller_high_count"] and reputation >= limits["seller_high_rating"],
        )
        add(
            "seller_medium",
            f"{feedback} valoraciones",
            limits["seller_medium_count"] <= feedback < limits["seller_high_count"],
        )
    if seller and seller.closet:
        target = normalize(profile.brand)
        tracked = {normalize(item.brand) for item in config.profiles}
        same = sum(normalize(item.brand or "") == target for item in seller.closet)
        new = sum(
            item.status == "new_with_tags" and normalize(item.brand or "") in tracked
            for item in seller.closet
        )
        add("diverse", "Armario variado", same / len(seller.closet) < limits["diverse_ratio"])
        add("same_brand", f"{same} artículos de la marca", same >= limits["same_brand_count"])
        add("many_new", f"{new} prendas con etiquetas", new >= limits["many_new_count"])
    conditions = {
        "very_good": "Muy buen estado",
        "new_without_tags": "Nuevo sin etiquetas",
        "satisfactory": "Estado satisfactorio",
    }
    if listing.status in conditions:
        add(listing.status, conditions[listing.status])
    add(
        "cheap_new",
        "Nuevo con etiquetas a precio bajo",
        listing.status == "new_with_tags"
        and float(listing.price / profile.price_max) < limits["cheap_new_ratio"],
    )
    text = f"{listing.title} {listing.description or ''}"
    for key, label in (
        ("motivated", "Vendedor motivado"),
        ("proof", "Prueba de compra"),
        ("authenticity_mentioned", "Autenticación mencionada"),
        ("wear", "Desgaste"),
    ):
        words = matches(text, scoring.words[key])
        add(key, f"{label} · {', '.join(words)}", bool(words))
    add(
        "short_description",
        "Descripción breve",
        len([line for line in (listing.description or "").splitlines() if line.strip()]) <= 1,
    )
    add("many_photos", f"{len(listing.photos)} fotos", len(listing.photos) >= limits["many_photos"])
    if evidence.parts_present:
        points["parts"] = min(
            weights["max_part_points"], weights["part"] * len(evidence.parts_present)
        )
        reasons.append("Partes visibles · " + ", ".join(evidence.parts_present))
    add("stock_photo", "Foto de catálogo", evidence.stock_photo)
    add("price_drop", "Ha bajado de precio", evidence.price_drop)
    add("bargain", "En el cuartil inferior", pricing["bargain"])
    add("hood_unconfirmed", "Capucha sin confirmar", "hood_unconfirmed" in passed)
    total = max(0, min(100, sum(points.values())))
    tier = next((tier for tier in ("top", "good", "maybe") if total >= limits[tier]), "low")
    flags = []
    if listing.price < profile.price_floor and evidence.qr == "certilogo_ok":
        tier = "maybe" if tier in ("top", "good") else tier
        flags.append("⚠️ Precio sospechoso: escanea el Certilogo antes de comprar")
    return ScoreResult(score=total, tier=tier, points=points, reasons=reasons, flags=flags)
