"""Interfaz mínima de estado persistente."""

from abc import ABC, abstractmethod
from decimal import Decimal

from vinted_hunter.pipeline.models import Listing


class StateStore(ABC):
    @abstractmethod
    def listing(self, listing_id: int) -> Listing | None:
        """Devuelve la última versión conocida del anuncio."""

    @abstractmethod
    def observe_price(self, listing: Listing, profile: str, at: str) -> Decimal | None:
        """Registra una observación y devuelve el precio previo."""
