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
from vinted_hunter.notify.ntfy import notifier_for
from vinted_hunter.pipeline.funnel import funnel
from vinted_hunter.pipeline.run import market_for, run_pass
from vinted_hunter.sources.vinted.client import HttpFailure
from vinted_hunter.sources.vinted.parse import ParseError
from vinted_hunter.storage.sqlite_store import SQLiteStore

app = typer.Typer(help="Cazador local de sudaderas en Vinted.", no_args_is_help=True,
                  pretty_exceptions_show_locals=False)
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


def publish_notifications(result: dict) -> None:
    with local_store() as store:
        try:
            notifier_for(ROOT, store).publish(result)
        except ValueError:
            typer.echo("Configuración local de ntfy no válida", err=True)


@app.command()
def run(
    pending_only: Annotated[bool, typer.Option("--pending-only")] = False,
    daily_only: Annotated[bool, typer.Option("--daily-backfill-only")] = False,
) -> None:
    """Realiza una pasada de captura."""
    result = run_pass(ROOT, pending_only=pending_only, notifications=True, daily_only=daily_only)
    ConsoleNotifier().publish(result)
    publish_notifications(result)
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


@app.command("replay")
def replay_item(
    url: str,
    save_fixture: Annotated[
        Literal["recall", "precision"] | None, typer.Option("--save-fixture")
    ] = None,
) -> None:
    """Analiza una ficha pública sin marcar el anuncio como visto."""
    from vinted_hunter.replay import replay

    try:
        record = replay(ROOT, url, save_fixture)
    except (ValueError, HttpFailure, ParseError) as error:
        raise typer.BadParameter(str(error)) from None
    trace = record["trace"]
    labels = {
        "garment": "Tipo de prenda", "price": "Precio y moneda", "replica": "Texto de réplica",
        "size": "Talla", "hood": "Capucha", "status": "Estado", "color": "Color",
        "photos": "Cantidad de fotos", "brand_rules": "Reglas de marca",
        "seller_feedback": "Valoraciones del vendedor", "seller_rating": "Nota del vendedor",
        "fake_certilogo_domain": "Dominio del QR", "catalog_photos_only": "Fotos propias",
        "too_cheap_for_brand": "Suelo de precio y Certilogo",
        "blacklisted_photo": "Lista negra de fotos", "shared_photo": "Foto compartida",
        "knitwear": "Prenda de punto o lana", "not_sweatshirt": "Tipo ajeno a sudaderas",
    }
    show(f"{record['body']['title']} · {record['body']['price']} EUR")
    show(f"Resultado {record['tier']} · {record['score']} puntos")
    notice = record.get("notification", {})
    typer.echo(
        f"Estado actual · {notice.get('actual_availability', 'unknown')} · "
        + ("generaría aviso como anuncio nuevo y activo"
           if notice.get("would_notify_as_new_active")
           else "no generaría aviso con la política del perfil")
    )
    for name in trace["gates_passed"]:
        typer.echo(f"✓ {labels.get(name, name)}")
    if trace["gate_rejected"]:
        reason = trace["gate_rejected"]
        typer.echo(f"✗ Descartado · {labels.get(reason, reason)}")
    if trace["seller"]:
        seller = trace["seller"]
        typer.echo(f"Vendedor · {seller['feedback_count']} valoraciones · nota {seller['rating']}")
    evidence = trace["evidence"]
    typer.echo(f"Visión · {evidence['qr']} · fotos de catálogo {evidence['catalog_photo_count']}")
    typer.echo(
        f"pHash · {len(evidence['hashes'])} fotos · "
        f"partes ORB · {', '.join(evidence['parts_present']) or 'sin coincidencias'}"
    )
    if trace.get("wardrobe"):
        wardrobe = trace["wardrobe"]
        typer.echo(
            f"Armario · {wardrobe['reviewed']} revisados · "
            f"{wardrobe['same_brand']} de la marca"
        )
    for key, label in (
        ("motivated", "Motivación"), ("replica", "Réplica"), ("wear", "Desgaste"),
        ("proof", "Prueba de compra"), ("authenticity_mentioned", "Autenticación"),
        ("hood_with", "Con capucha"), ("hood_without", "Sin capucha"),
    ):
        if phrases := trace["text"].get(key):
            typer.echo(f"Texto · {label} · {', '.join(phrases)}")
    for reason in trace["score"]["reasons"]:
        typer.echo(f"  {reason}")
    for query in record["query_coverage"]:
        label = "Compatible" if query["compatible"] else "Incompatible"
        typer.echo(f"{label} · {query['query']} · {query['reason']}")
    typer.echo(record["query_note"])
    if save_fixture:
        typer.echo(f"Captura guardada en tests/{save_fixture}/{record['id']}")


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
        from vinted_hunter.pipeline.availability import sale_statistics

        sales = sale_statistics(records)
        labels = store.label_counts()
        recent = store.latest_backfill().get("funnel", {})
        for profile in config.profiles:
            market = market_for(store, profile, config)
            samples = store.db.execute(
                "SELECT COUNT(*) FROM price_history WHERE profile=?", (profile.id,)
            ).fetchone()[0]
            inventory = funnel(row for row in records if row["profile"] == profile.id)
            show(
                f"{profile.brand} · {samples} precios · {market.count} plausibles · "
                f"mediana {market.median or '—'} · p25 {market.p25 or '—'} · "
                f"p10 {market.p10 or '—'}"
            )
            show(f"  Etiquetas · {labels['by_profile'].get(profile.id, {})}")
            if sale := sales.get(profile.id):
                duration = f"{sale['mean_minutes']} min" if sale['mean_minutes'] is not None \
                    else "sin intervalo observado"
                show(f"  Vendidos observados {sale['count']} · media estimada {duration} · "
                     f"{sale['timed_count']} transiciones medidas")
                for price, values in sale["by_price"].items():
                    show(f"    {price} EUR anunciados · {values['count']} vendidos · "
                         f"media estimada {values['mean_minutes'] or '—'} min")
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


@app.command("rescore")
def rescore_saved() -> None:
    """Reevalúa la base con las fichas y fotos que ya están guardadas."""
    from vinted_hunter.pipeline.rescore import rescore

    with local_store() as store:
        count = rescore(ROOT, store)
    path = build(ROOT)
    typer.echo(f"{count} anuncios reevaluados sin red · {path}")


@app.command()
def tune() -> None:
    """Propone pesos con 50 etiquetas; nunca modifica scoring.yaml."""
    from vinted_hunter.tune import propose

    typer.echo(json.dumps(propose(ROOT), ensure_ascii=False, indent=2))


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
            result = run_pass(ROOT, notifications=True)
            ConsoleNotifier().publish(result)
            publish_notifications(result)
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
def doctor(compact: Annotated[bool, typer.Option("--compact")] = False) -> None:
    """Comprueba salud, conexión, parser y filtros."""
    try:
        checks = check(ROOT)
    except (HttpFailure, ParseError, RequestsError) as error:
        detail = (
            str(error) if isinstance(error, (HttpFailure, ParseError)) else type(error).__name__
        )
        show(f"[red]✗[/red] {detail}")
        raise typer.Exit(1) from error
    for name, ok, detail in checks:
        suffix = f" · {detail}" if not compact or name in {"Portada y cookies", "Parser"} else ""
        show(f"{'[green]✓[/green]' if ok else '[red]✗[/red]'} {name}{suffix}")
    if not all(ok for _, ok, _ in checks):
        raise typer.Exit(1)


@app.command()
def selftest(report: Annotated[bool, typer.Option("--report")] = False) -> None:
    """Ejecuta el embudo acotado y, opcionalmente, escribe TEST_REPORT.md."""
    from vinted_hunter.selftest import verify

    if not verify(ROOT, report):
        raise typer.Exit(1)


@app.command("vision-check")
def check_vision(
    profile: Annotated[str, typer.Option()],
    limit: Annotated[int, typer.Option(min=1, max=30)] = 30,
) -> None:
    """Mide visión en anuncios públicos de un perfil sin aplicar sus gates."""
    from vinted_hunter.vision_check import vision_check

    try:
        output, report = vision_check(ROOT, profile, limit, typer.echo)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(f"QR {report['qr']} · {len(report['samples'])}/{limit} anuncios · {output}")
    for error in report["errors"]:
        typer.echo(error, err=True)
    if len(report["samples"]) != limit:
        raise typer.Exit(1)


@app.command("notify-test")
def notify_test(
    announcements_only: Annotated[bool, typer.Option("--announcements-only")] = False,
    configuration_only: Annotated[bool, typer.Option("--configuration-only")] = False,
) -> None:
    """Envía un ejemplo del formato final con un anuncio confirmado activo."""
    from vinted_hunter.pipeline.run import Pipeline
    from vinted_hunter.sources.vinted.client import VintedClient

    config = load_config(ROOT)
    with local_store() as store:
        if configuration_only:
            notifier = notifier_for(ROOT, store)
            typer.echo(f"NTFY_TOPIC presente: {bool(notifier.topic)} · "
                       f"NTFY_HEALTH_TOPIC presente: {bool(notifier.health_topic)} · "
                       f"shadow_mode={str(notifier.shadow_mode).lower()}")
            try:
                status = notifier.test_configuration()
            except ValueError as error:
                typer.echo(str(error), err=True)
                raise typer.Exit(1) from None
            typer.echo(f"ntfy prueba de configuración · HTTP {status}")
            if status != 200:
                raise typer.Exit(1)
            return
        active_profiles = {profile.id for profile in config.profiles if profile.notify_enabled}
        choices = [row for row in store.records(scored=True) if row["trace"].get("pricing")
                   and row["profile"] in active_profiles
                   and row["tier"] == "top"]
        if not choices:
            typer.echo("El tablero carece de anuncios puntuados para la prueba", err=True)
            raise typer.Exit(1)
        pipeline = Pipeline(ROOT, store, config, datetime.now(UTC))
        with VintedClient(enrich_limit=config.scoring.capture.enrich_limit,
                          wait=config.scoring.capture.wait) as client:
            client.home()
            notifier = notifier_for(ROOT, store, lambda row: pipeline.verify_active(client, row))
            chosen = next((
                row for row in sorted(choices, key=lambda r: r["score"], reverse=True)
                if client.remaining("enrich") and pipeline.verify_active(client, row)
            ), None)
            if chosen is None:
                typer.echo("Ningún anuncio confirmado activo para la prueba", err=True)
                raise typer.Exit(1)
            try:
                statuses = notifier.test(chosen, announcements_only=announcements_only)
            except ValueError as error:
                typer.echo(str(error), err=True)
                raise typer.Exit(1) from None
    typer.echo(f"ntfy anuncios · HTTP {statuses[0]}" + (
        f" · ntfy salud · HTTP {statuses[1]}" if statuses[1] is not None else ""
    ))
    if statuses[0] != 200 or not announcements_only and statuses[1] != 200:
        raise typer.Exit(1)


@app.command("board-url")
def board_url(qr: Annotated[bool, typer.Option("--qr")] = False) -> None:
    """Muestra en local el enlace privado del panel publicado."""
    from urllib.parse import quote

    from vinted_hunter.cloud import require_key
    from vinted_hunter.secrets import board_address

    address = board_address(ROOT)
    if address is None:
        raise typer.BadParameter("Repositorio no configurado para el tablero")
    try:
        key = require_key(ROOT)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from None
    private = address + "#k=" + quote(key, safe="")
    typer.echo(private)
    if qr:
        import qrcode

        target = ROOT / "out/board-url.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        qrcode.make(private).save(target)
        typer.echo(str(target))
