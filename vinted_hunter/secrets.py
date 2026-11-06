"""Lee secretos de entorno y del archivo local sin incluir valores en errores."""

import os
from pathlib import Path


def local_secret(root: Path, name: str) -> str | None:
    if value := os.environ.get(name):
        return value
    path = root / ".env"
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() == name:
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            return value or None
    return None
