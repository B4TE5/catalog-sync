"""Contrato de estado que usa el embudo."""

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Any

from vinted_hunter.pipeline.models import Listing, Seller


class StateStore(ABC):
    @abstractmethod
    def listing(self, listing_id: int) -> Listing | None:
        """Devuelve la última versión conocida del anuncio."""

    @abstractmethod
    def record(self, listing_id: int) -> dict[str, Any] | None:
        """Devuelve el anuncio persistido y su rastro."""

    @abstractmethod
    def records(self, *, scored: bool = False) -> list[dict[str, Any]]:
        """Devuelve los anuncios y sus rastros de decisión."""

    @abstractmethod
    def observe_price(self, listing: Listing, profile: str, at: str) -> Decimal | None:
        """Registra una observación y devuelve el precio previo."""

    @abstractmethod
    def plausible_prices(self, profile: str, score: float) -> list[Decimal]:
        """Devuelve el precio vigente de los anuncios que superan el umbral."""

    @abstractmethod
    def save_market(self, profile: str, market: dict[str, Any]) -> None:
        """Guarda la última instantánea de precios calculada."""

    @abstractmethod
    def save(
        self,
        listing: Listing,
        profile: str,
        tier: str | None,
        score: int | None,
        trace: dict[str, Any],
        backfill: bool,
    ) -> None:
        """Conserva la última decisión para un anuncio."""

    @abstractmethod
    def seller(self, seller_id: int, after: datetime) -> Seller | None:
        """Recupera la información de vendedor vigente."""

    @abstractmethod
    def cache_seller(self, seller: Seller, now: datetime) -> None:
        """Conserva una captura del vendedor."""

    @abstractmethod
    def save_photos(self, listing_id: int, hashes: list[str], primary: str | None) -> None:
        """Indexa las huellas de las fotografías."""

    @abstractmethod
    def matching_hashes(self, seller_id: int) -> list[dict[str, Any]]:
        """Devuelve huellas propias y de la lista negra."""

    @abstractmethod
    def shared_hash(self, value: str, seller_id: int) -> bool:
        """Indica si otro vendedor publicó una foto con la misma huella."""

    @abstractmethod
    def setting(self, key: str, default: str = "") -> str:
        """Devuelve un ajuste operativo persistido."""

    @abstractmethod
    def set_setting(self, key: str, value: str) -> None:
        """Actualiza un ajuste operativo."""

    @abstractmethod
    def save_run(self, run: dict[str, Any]) -> None:
        """Registra el resultado de una pasada."""

    @abstractmethod
    def runs(self, limit: int) -> list[dict[str, Any]]:
        """Devuelve las últimas pasadas, empezando por la más reciente."""

    @abstractmethod
    def flush(self) -> None:
        """Confirma los cambios antes de una etapa de red."""
