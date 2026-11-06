"""Detección multilingüe mediante palabras y frases completas."""

import re
from collections.abc import Iterable

from unidecode import unidecode


def normalize(text: str) -> str:
    return " ".join(unidecode(text).lower().replace("’", "'").split())


def matches(text: str, words: Iterable[str]) -> list[str]:
    normalized = normalize(text)
    return [
        word
        for word in words
        if re.search(r"(?<!\w)" + re.escape(normalize(word)) + r"(?!\w)", normalized)
    ]


def hood_signal(text: str, words: dict[str, list[str]]) -> str | None:
    if matches(text, words["hood_without"]):
        return "without"
    if matches(text, words["hood_with"]):
        return "with"
    return None


def stated_sizes(title: str, labels: list[str]) -> set[str]:
    if not labels:
        return set()
    prefixes = "|".join(re.escape(normalize(label)) for label in labels)
    size = r"(?:[2-6]xl|x{0,6}[sl]|m)"
    pattern = rf"(?<!\w)(?:{prefixes})(?:\s*[:=]\s*|\s+)({size})(?:\s*[/–-]\s*({size}))?(?!\w)"
    return {value for match in re.findall(pattern, normalize(title)) for value in match if value}
