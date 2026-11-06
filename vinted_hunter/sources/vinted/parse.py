"""Lectura del transporte RSC observado en las páginas públicas."""

import json
import re
from collections.abc import Iterator
from typing import Any

FLIGHT_SCRIPT = re.compile(r"<script\b[^>]*>self\.__next_f\.push\((\[.*?\])\)</script>", re.DOTALL)
DECODER = json.JSONDecoder()


class ParseError(ValueError):
    """La respuesta carece de la estructura requerida."""


def flight_payload(html: str) -> str:
    chunks = []
    for match in FLIGHT_SCRIPT.finditer(html):
        try:
            chunk = json.loads(match[1])
        except json.JSONDecodeError:
            continue
        if len(chunk) > 1 and chunk[0] == 1 and isinstance(chunk[1], str):
            chunks.append(chunk[1])
    if not chunks:
        raise ParseError("Sin fragmentos RSC reconocibles")
    return "".join(chunks)


def values(payload: str, pattern: re.Pattern[str]) -> Iterator[Any]:
    for match in pattern.finditer(payload):
        try:
            value, _ = DECODER.raw_decode(payload, match.start(1))
        except json.JSONDecodeError:
            continue
        yield value
