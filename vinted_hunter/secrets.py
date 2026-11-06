"""Lee secretos de entorno y del archivo local sin incluir valores en errores."""

import os
import re
from pathlib import Path
from urllib.parse import quote


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


def repository_name(root: Path) -> str | None:
    value = local_secret(root, "GITHUB_REPO") or os.environ.get("GITHUB_REPOSITORY", "")
    slug = (
        value.removeprefix("https://github.com/")
        .removeprefix("git@github.com:")
        .removesuffix(".git")
    )
    return slug if re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+", slug) else None


def board_address(root: Path) -> str | None:
    if slug := repository_name(root):
        owner, project = slug.split("/")
        return f"https://{owner.lower()}.github.io/{quote(project)}/"
    return None
