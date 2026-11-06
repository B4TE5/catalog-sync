"""Datos normalizados y resultados del embudo."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

Tier = Literal["top", "good", "maybe", "low", "rejected"]
QR = Literal["certilogo_ok", "qr_detected_unreadable", "qr_foreign_domain", "none"]


class Listing(BaseModel):
    id: int = Field(gt=0)
    title: str = Field(min_length=1)
    price: Decimal = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    url: HttpUrl
    photos: list[HttpUrl] = Field(min_length=1)
    seller_id: int | None = None
    brand: str | None = None
    size: str | None = None
    status: str | None = None
    category_id: int | None = None
    color: str | None = None
    description: str | None = None
    uploaded_at: datetime | None = None
    first_seen: datetime | None = None
    favourites: int | None = None
    views: int | None = None
    protected_total: Decimal | None = None
    shipping: Decimal | None = None


class Seller(BaseModel):
    id: int
    feedback_count: int | None = None
    rating: float | None = None
    country: str | None = None
    city: str | None = None
    joined_at: datetime | None = None
    last_seen: datetime | None = None
    active_count: int | None = None
    professional: bool | None = None
    closet: list[Listing] | None = None


class Evidence(BaseModel):
    qr: QR = "none"
    qr_decoded: bool = False
    hashes: list[str] = Field(default_factory=list)
    primary_hash: str | None = None
    parts_present: list[str] = Field(default_factory=list)
    stock_photo: bool = False
    shared_photo: bool = False
    blacklisted_photo: bool = False
    price_drop: bool = False


class ScoreResult(BaseModel):
    score: int = 0
    tier: Tier
    reasons: list[str] = Field(default_factory=list)
    points: dict[str, int] = Field(default_factory=dict)
