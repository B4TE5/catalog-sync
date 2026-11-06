"""Estado cifrado de una sola revisión y utilidades de publicación."""

import gzip
import json
import os
import re
import sqlite3
import subprocess
import sys
from base64 import b64encode
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import Request, urlopen

from cryptography.exceptions import InvalidTag

from vinted_hunter.board.build import build
from vinted_hunter.cloud_crypto import BOARD_CONTEXT, STATE_CONTEXT, seal, unseal
from vinted_hunter.secrets import local_secret
from vinted_hunter.storage.sqlite_store import SQLiteStore

STATE_REF = "refs/heads/state"


def git(*args: str, data: bytes | None = None, auth: bool = False) -> bytes:
    environment = {k: v for k, v in os.environ.items() if not k.startswith("GIT_TRACE")}
    environment.pop("GIT_CURL_VERBOSE", None)
    environment["GIT_TERMINAL_PROMPT"] = "0"
    environment.update(
        GIT_AUTHOR_NAME="Catalog Sync",
        GIT_COMMITTER_NAME="Catalog Sync",
        GIT_AUTHOR_EMAIL="catalog-sync@users.noreply.github.com",
        GIT_COMMITTER_EMAIL="catalog-sync@users.noreply.github.com",
    )
    if auth:
        token = environment["CATALOG_SYNC_TOKEN"]
        encoded = b64encode(f"x-access-token:{token}".encode()).decode("ascii")
        environment.update(
            GIT_CONFIG_COUNT="2",
            GIT_CONFIG_KEY_0="http.https://github.com/.extraheader",
            GIT_CONFIG_VALUE_0="Authorization: Basic " + encoded,
            GIT_CONFIG_KEY_1="credential.helper",
            GIT_CONFIG_VALUE_1="",
        )
    result = subprocess.run(
        ["git", *args],
        input=data,
        capture_output=True,
        check=False,
        env=environment,
    )
    if result.returncode:
        raise RuntimeError(f"Git {args[0]} salió con código {result.returncode}")
    return result.stdout


def require_key(root: Path) -> str:
    if key := local_secret(root, "BOARD_KEY"):
        return key
    raise ValueError("Falta la clave del tablero")


def render_pages(root: Path) -> Path:
    inner = build(root).read_text(encoding="utf-8").replace("Vinted Hunter", "Panel privado")
    data = seal(inner.encode(), require_key(root), BOARD_CONTEXT)
    template = Path(__file__).with_name("board") / "encrypted.html"
    target = root / "out" / "pages" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        template.read_text(encoding="utf-8").replace("__ENVELOPE__", data), encoding="utf-8"
    )
    return target


def archive_database(path: Path, key: str) -> str:
    with TemporaryDirectory(dir=path.parent) as temp:
        snapshot = Path(temp) / "snapshot.sqlite"
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as source:
            with closing(sqlite3.connect(snapshot)) as output:
                source.backup(output)
                output.execute("PRAGMA journal_mode=DELETE")
        return seal(gzip.compress(snapshot.read_bytes(), mtime=0), key, STATE_CONTEXT)


def restore_database(path: Path, envelope: str, key: str) -> None:
    raw = gzip.decompress(unseal(envelope, key, STATE_CONTEXT))
    path.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=path.parent) as temp:
        snapshot = Path(temp) / "snapshot.sqlite"
        snapshot.write_bytes(raw)
        with closing(sqlite3.connect(snapshot.as_uri() + "?mode=ro", uri=True)) as connection:
            if connection.execute("PRAGMA quick_check").fetchone() != ("ok",):
                raise ValueError("La copia SQLite no pasó su comprobación")
        snapshot.replace(path)


def restore(root: Path) -> str:
    raw = git("ls-remote", "origin", STATE_REF)
    if not raw.strip():
        print("Estado inicial vacío")
        return ""
    git("fetch", "--no-tags", "--depth=1", "origin", STATE_REF)
    version = git("rev-parse", "FETCH_HEAD").decode().strip()
    envelope = git("show", f"{version}:state.enc").decode()
    restore_database(root / "data" / "vh.sqlite", envelope, require_key(root))
    print("Estado cifrado restaurado")
    return version


def save(root: Path, version: str) -> None:
    archive = archive_database(root / "data" / "vh.sqlite", require_key(root))
    blob = git("hash-object", "-w", "--stdin", data=archive.encode()).strip()
    tree = git("mktree", data=b"100644 blob " + blob + b"\tstate.enc\n").decode().strip()
    commit = git("commit-tree", tree, "-m", "chore: replace encrypted state").decode().strip()
    git(
        "push",
        f"--force-with-lease={STATE_REF}:{version}",
        "origin",
        f"{commit}:{STATE_REF}",
        auth=True,
    )
    print("Estado cifrado guardado en una sola revisión")


def label_request(owner: str, sender: str, title: str) -> tuple[int, str] | None:
    if sender != owner:
        return None
    match = re.fullmatch(r"label:([1-9][0-9]{0,18}):(fake|good|meh)", title)
    if match and int(match[1]) <= 2**63 - 1:
        return int(match[1]), match[2]
    return None


def issue_update(path: str, method: str, payload: dict[str, str]) -> None:
    repo = os.environ["GITHUB_REPOSITORY"]
    request = Request(
        f"https://api.github.com/repos/{repo}/{path}",
        data=json.dumps(payload).encode(),
        method=method,
        headers={
            "Authorization": "Bearer " + os.environ["CATALOG_SYNC_TOKEN"],
            "User-Agent": "catalog-sync-feedback",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
        },
    )
    with urlopen(request, timeout=20):
        pass


def feedback(root: Path) -> None:
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    issue = event["issue"]
    number = int(issue["number"])
    command = label_request(
        os.environ["GITHUB_REPOSITORY_OWNER"], issue["user"]["login"], issue["title"]
    )
    message = "Solicitud rechazada por autor o formato."
    if command:
        listing_id, label = command
        version = restore(root)
        if version:
            with SQLiteStore(root / "data" / "vh.sqlite") as store:
                if store.listing(listing_id) is not None:
                    store.label(listing_id, label, datetime.now(UTC).isoformat())
                    message = "Etiqueta aplicada."
            if message == "Etiqueta aplicada.":
                save(root, version)
        if message != "Etiqueta aplicada.":
            message = "El anuncio no existe en el estado guardado."
    issue_update(f"issues/{number}/comments", "POST", {"body": message})
    issue_update(f"issues/{number}", "PATCH", {"state": "closed"})
    print(message)


def main() -> int:
    root = Path.cwd()
    operation = sys.argv[1] if len(sys.argv) > 1 else ""
    marker = root / "data" / "state-ref"
    try:
        if operation == "restore":
            version = restore(root)
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(version, encoding="ascii")
        elif operation == "save":
            save(root, marker.read_text(encoding="ascii"))
        elif operation == "render":
            render_pages(root)
            print("Artefacto del panel cifrado")
        elif operation == "feedback":
            feedback(root)
        elif operation == "keepalive":
            git("commit", "--allow-empty", "-m", "chore: record scheduled heartbeat")
            git("push", "origin", "HEAD:" + os.environ["GITHUB_REF"], auth=True)
        else:
            return 2
    except (OSError, ValueError, InvalidTag, RuntimeError, KeyError, sqlite3.Error) as error:
        print(f"Operación de nube fallida · {type(error).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
