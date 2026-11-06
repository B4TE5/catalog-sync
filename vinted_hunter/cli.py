"""Entrada de la herramienta local."""

import json
import random
import time
from datetime import UTC, datetime
from importlib.metadata import version as installed_version
from pathlib import Path
from typing import Annotated, Literal

import typer
from curl_cffi.requests import RequestsError
from rich import print as show

from vinted_hunter.board.build import build
from vinted_hunter.config import load_config
from vinted_hunter.diagnostics import check
from vinted_hunter.notify.console import ConsoleNotifier
from vinted_hunter.pipeline.funnel import funnel
from vinted_hunter.pipeline.run import market_for, run_pass
from vinted_hunter.sources.vinted.client import HttpFailure
from vinted_hunter.sources.vinted.parse import ParseError
from vinted_hunter.storage.sqlite_store import SQLiteStore

app = typer.Typer(help="Cazador local de sudaderas en Vinted.", no_args_is_help=True)
ROOT = Path.cwd()


def local_store() -> SQLiteStore:
    return SQLiteStore(ROOT / "data" / "vh.sqlite")


@app.command()
def version() -> None:
    """Muestra la versión instalada."""
    show(installed_version("vinted-hunter"))


@app.callback()
def main() -> None:
    """Captura y analiza anuncios públicos."""


@app.command()
def run() -> None:
    """Realiza una pasada de captura."""
    result = run_pass(ROOT)
    ConsoleNotifier().publish(result)
    if result["errors"]:
        raise typer.Exit(1)


@app.command()
def backfill(pages: Annotated[int, typer.Option(min=1, max=10)] = 10) -> None:
    """Explora varias páginas y registra los hallazgos sin avisos de novedad."""
    result = run_pass(ROOT, pages, backfill=True)
    ConsoleNotifier().publish(result)
    if result["errors"]:
        raise typer.Exit(1)


@app.command()
def explain(listing_id: int) -> None:
    """Muestra el rastro de decisión del anuncio."""
    with local_store() as store:
        row = store.db.execute("SELECT trace FROM listings WHERE id=?", (listing_id,)).fetchone()
    if row is None:
        raise typer.BadParameter("Anuncio desconocido")
    show(json.dumps(json.loads(row["trace"]), indent=2, ensure_ascii=False))


@app.command()
def label(listing_id: int, result: Literal["fake", "good", "meh"]) -> None:
    """Guarda una etiqueta manual. Fake activa la lista negra de fotos."""
    with local_store() as store:
        try:
            store.label(listing_id, result, datetime.now(UTC).isoformat())
        except ValueError as error:
            raise typer.BadParameter(str(error)) from error
    show(f"Etiqueta guardada: {result}")


@app.command()
def stats() -> None:
    """Resume precios y distribución de resultados por perfil."""
    config = load_config(ROOT)
    with local_store() as store:
        records = store.records()
        recent = store.latest_backfill().get("funnel", {})
        for profile in config.profiles:
            market = market_for(store, profile.id, config.scoring.thresholds["plausible"])
            samples = store.db.execute(
                "SELECT COUNT(*) FROM price_history WHERE profile=?", (profile.id,)
            ).fetchone()[0]
            inventory = funnel(row for row in records if row["profile"] == profile.id)
            show(
                f"{profile.brand} · {samples} precios · {market.count} plausibles · "
                f"mediana {market.median or '—'} · p25 {market.p25 or '—'} · "
                f"p10 {market.p10 or '—'}"
            )
            for label, counts in (
                ("Inventario", inventory),
                ("Último backfill", recent.get(profile.id)),
            ):
                if counts is None:
                    continue
                fetched = f" ({counts['fetched']} fichas nuevas)" if "fetched" in counts else ""
                show(
                    f"  {label} · {counts['seen']} vistos · descartes {counts['rejected']} · "
                    f"{counts['enriched']} enriquecidos{fetched} · tiers {counts['tiers']}"
                )


@app.command()
def board() -> None:
    """Genera el tablero HTML local."""
    show(str(build(ROOT)))


@app.command()
def serve(port: Annotated[int, typer.Option(min=1, max=65535)] = 8787) -> None:
    """Sirve el tablero en la interfaz local."""
    from functools import partial
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    path = build(ROOT)
    handler = partial(SimpleHTTPRequestHandler, directory=str(path.parent))
    with ThreadingHTTPServer(("127.0.0.1", port), handler) as server:
        show(f"http://localhost:{port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            return


@app.command()
def watch(
    interval: Annotated[float, typer.Option(min=0.15)] = 10,
    jitter: Annotated[float, typer.Option(min=0)] = 2,
    cycles: Annotated[int | None, typer.Option(min=1)] = None,
) -> None:
    """Repite la captura y regenera el tablero tras cada pasada."""
    completed = 0
    result = {"errors": []}
    try:
        while cycles is None or completed < cycles:
            result = run_pass(ROOT)
            ConsoleNotifier().publish(result)
            build(ROOT)
            if result.get("interrupted"):
                return
            completed += 1
            if cycles is None or completed < cycles:
                time.sleep(max(9, 60 * (interval + random.uniform(-jitter, jitter))))
    except KeyboardInterrupt:
        return
    if result["errors"]:
        raise typer.Exit(1)


@app.command()
def doctor() -> None:
    """Comprueba salud, conexión, parser y filtros."""
    try:
        checks = check(ROOT)
    except (HttpFailure, ParseError, RequestsError) as error:
        show(f"[red]✗[/red] {type(error).__name__}")
        raise typer.Exit(1) from error
    for name, ok, detail in checks:
        show(f"{'[green]✓[/green]' if ok else '[red]✗[/red]'} {name} · {detail}")
    if not all(ok for _, ok, _ in checks):
        raise typer.Exit(1)


@app.command()
def selftest(report: Annotated[bool, typer.Option("--report")] = False) -> None:
    """Ejecuta el embudo acotado y, opcionalmente, escribe TEST_REPORT.md."""
    from vinted_hunter.selftest import verify

    if not verify(ROOT, report):
        raise typer.Exit(1)
