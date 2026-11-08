"""Perfiles y parámetros del embudo."""

from decimal import Decimal
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class Query(BaseModel):
    q: str
    priority: Literal["high", "normal"]


class BrandRule(BaseModel):
    if_text_any: list[str] = Field(default_factory=list)
    if_condition: str | None = None
    and_price_below: Decimal
    then: Literal["reject"]
    reason: str


class Categories(BaseModel):
    search: list[int]
    accept: list[int]
    conditional: list[int] = Field(default_factory=list)
    exclude: list[int] = Field(default_factory=list)
    exclude_reason: str = "knitwear"


class Profile(BaseModel):
    id: str
    enabled: bool
    priority: int = 10
    brand: str
    size: str | None = None
    hood: Literal["with", "without"] | None = None
    categories: Categories
    type_keywords_include: list[str] = Field(default_factory=list)
    type_keywords_exclude: list[str] = Field(default_factory=list)
    type_keywords_explicit: list[str] = Field(default_factory=list)
    material_keywords_include: list[str] = Field(default_factory=list)
    material_keywords_exclude: list[str] = Field(default_factory=list)
    material_keywords_exclude_exact: list[str] = Field(default_factory=list)
    notify_min_tier: Literal["good", "top"] = "top"
    notify_enabled: bool = False
    scoring_weights: dict[str, int] = Field(default_factory=dict)
    price_floor: Decimal
    price_max: Decimal
    allowed_status: list[str]
    seller_min_feedback: int
    seller_min_rating: float
    min_photos: int
    domain: Literal["vinted.es"]
    color: str | None = None
    certilogo: bool = False
    text_queries: list[Query]
    brand_rules: list[BrandRule]
    refs_dir: Path | None = None

    @model_validator(mode="after")
    def valid_price_range(self) -> "Profile":
        if not 0 <= self.price_floor <= self.price_max:
            raise ValueError("Rango de precio inválido")
        return self


class IDs(BaseModel):
    brand_ids: dict[str, list[int]] = Field(default_factory=dict)
    brand_names: dict[str, list[str]] = Field(default_factory=dict)
    size_ids: dict[str, int] = Field(default_factory=dict)
    detail_attribute_ids: dict[str, int] = Field(default_factory=dict)
    catalog_ids: dict[str, int] = Field(default_factory=dict)
    status_ids: dict[str, int] = Field(default_factory=dict)
    color_ids: dict[str, int] = Field(default_factory=dict)


class Capture(BaseModel):
    catalog_limit: int = Field(12, ge=1, le=12)
    enrich_limit: int = Field(12, ge=1, le=120)
    cloud_enrich_limit: int = Field(72, ge=1, le=120)
    max_pass_seconds: float = Field(270, gt=0, le=300)
    wait: tuple[float, float] = (3, 8)
    max_photos: int = Field(12, ge=1, le=12)
    cdn_workers: int = Field(4, ge=1, le=4)
    cdn_timeout: float = Field(10, gt=0, le=30)
    seller_hours: int = 24
    unhealthy_after: int = 3
    availability_limit: int = Field(15, ge=0, le=15)
    availability_stale_minutes: int = Field(60, ge=10)
    availability_reserve_seconds: float = Field(85, ge=0, le=150)
    preflight_valid_seconds: float = Field(2, ge=0, le=5)
    size_repair_limit: int = Field(10, ge=0, le=30)
    backoff_seconds: int = 60
    max_backoff_seconds: int = 3600

    @model_validator(mode="after")
    def human_wait(self) -> "Capture":
        low, high = self.wait
        if not 3 <= low <= high <= 8:
            raise ValueError("La pausa entre peticiones debe quedar entre 3 y 8 segundos")
        return self


class Tuning(BaseModel):
    min_labels: int = Field(50, ge=50)
    validation_fraction: float = Field(0.2, gt=0, lt=0.5)
    learning_rate: float = Field(0.1, gt=0)
    iterations: int = Field(1000, ge=1)
    l2: float = Field(0.01, ge=0)


class DailyBackfill(BaseModel):
    enabled: bool = True
    timezone: str = "Europe/Madrid"
    hour: int = Field(3, ge=0, le=23)
    start_window_minutes: int = Field(120, ge=10, le=360)
    interval_hours: int = Field(24, ge=24)
    pages: int = Field(10, ge=1, le=10)
    catalog_share: int = Field(6, ge=1, le=11)
    stop_on_empty: bool = True


class Scoring(BaseModel):
    shadow_mode: bool = True
    revision: str = "1"
    capture: Capture = Field(default_factory=Capture)
    words: dict[str, list[str]] = Field(default_factory=dict)
    weights: dict[str, int] = Field(default_factory=dict)
    thresholds: dict[str, float] = Field(default_factory=dict)
    pricing: dict[str, Decimal] = Field(default_factory=dict)
    tuning: Tuning = Field(default_factory=Tuning)
    daily_backfill: DailyBackfill = Field(default_factory=DailyBackfill)


class Config(BaseModel):
    profiles: list[Profile]
    ids: IDs
    scoring: Scoring


def read_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as source:
        return yaml.safe_load(source) or {}


def load_config(root: Path, *, include_disabled: bool = False) -> Config:
    folder = root / "config"
    profiles = read_yaml(folder / "profiles.yaml")
    ids = folder / "vinted_ids.yaml"
    scoring = folder / "scoring.yaml"
    return Config(
        profiles=[
            Profile.model_validate({**profiles["defaults"], **p})
            for p in profiles["profiles"]
            if p["enabled"] or include_disabled
        ],
        ids=IDs.model_validate(read_yaml(ids) if ids.exists() else {}),
        scoring=Scoring.model_validate(read_yaml(scoring) if scoring.exists() else {}),
    )
