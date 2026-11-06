"""Interfaz para fuentes de anuncios públicos."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from vinted_hunter.pipeline.models import Listing

QueryParams = dict[str, str | list[str]]


@dataclass
class SearchResult:
    listings: list[Listing]
    raw_count: int
    invalid_count: int


class Source(ABC):
    @abstractmethod
    def search(self, params: QueryParams) -> SearchResult:
        """Obtiene y valida los anuncios de una búsqueda."""
