"""Salida desacoplada de los resultados de la pasada."""

from abc import ABC, abstractmethod
from typing import Any


class Notifier(ABC):
    @abstractmethod
    def publish(self, summary: dict[str, Any]) -> None:
        """Presenta el resumen de una pasada."""
