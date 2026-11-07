"""Verificación de extremo a extremo y reporte de los tres niveles."""

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from rich import print as show

from vinted_hunter.board.build import build
from vinted_hunter.notify.console import ConsoleNotifier
from vinted_hunter.pipeline.models import Listing
from vinted_hunter.pipeline.run import run_pass
from vinted_hunter.replay import evaluate_fixture
from vinted_hunter.storage.sqlite_store import SQLiteStore


def verify(root: Path, report: bool) -> bool:
    database = f"selftest-{uuid4().hex}.sqlite"
    result = run_pass(root, selftest=True, database=database)
    ConsoleNotifier().publish(result)
    recall = None
    if result["scored"] == 0:
        for manifest in sorted((root / "tests" / "recall").glob("*/capture.json")):
            candidate = evaluate_fixture(root, manifest.parent)
            if candidate["tier"] in {"good", "top"}:
                recall = candidate
                with SQLiteStore(root / "data" / database) as store:
                    store.save(
                        Listing.model_validate(recall["body"]), recall["profile"],
                        recall["tier"], recall["score"], recall["trace"], False,
                    )
                break
    vision = result["vision"] > 0 or bool(recall and recall["trace"]["evidence"]["hashes"])
    scoring = result["scored"] > 0 or bool(recall)
    recall_detail = (
        f"Caso real capturado {recall['id']} · {recall['tier']} · {recall['score']} puntos"
        if recall else ""
    )
    start = time.monotonic()
    board = build(root, database, "selftest")
    board_seconds = round(time.monotonic() - start, 2)
    checks = [
        ("Home y cookies", result.get("cookies", False), "sesión pública"),
        ("Catálogo", result["seen"] >= 10, f"{result['phases'].get('catalog', 0):.2f} s"),
        ("Gates", bool(result["rejected"]) or bool(result["candidates"]), "embudo"),
        ("Ficha", result["enriched"] > 0, f"{result['enriched']} enriquecidos"),
        ("Visión", vision, recall_detail or f"{result['vision']} evaluados"),
        ("Score", scoring, recall_detail or f"{result['scored']} puntuados"),
        ("Tablero", board.is_file(), f"{board_seconds:.2f} s"),
        (
            "Pasada sin incidentes",
            not result["errors"],
            f"{result['phases'].get('pipeline', 0):.2f} s de procesamiento",
        ),
    ]
    for name, ok, duration in checks:
        show(f"{'[green]✓[/green]' if ok else '[red]✗[/red]'} {name} · {duration}")
    passed = sum(ok for _, ok, _ in checks)
    success = passed == len(checks)
    if report:
        lines = ["# Informe de pruebas", "", datetime.now().astimezone().isoformat(), ""]
        lines.append(
            f"- `vh selftest --report` · {passed}/{len(checks)} etapas · "
            f"{result['duration']} s · {result['requests']} peticiones.",
        )
        lines.extend(f"  - {'✅' if ok else '❌'} {name} · {detail}" for name, ok, detail in checks)
        if result["errors"]:
            lines.extend(f"  - {error}" for error in result["errors"])
        for markers in ([], ["-m", "live"]):
            command = [sys.executable, "-m", "pytest", "-q", *markers]
            test = subprocess.run(
                command,
                cwd=root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            success &= test.returncode == 0
            lines.extend(
                [
                    "",
                    f"## pytest {' '.join(markers) or 'offline'}",
                    "",
                    f"Salida {test.returncode}.",
                    "",
                    "```text",
                    test.stdout.strip(),
                    test.stderr.strip(),
                    "```",
                ]
            )
        (root / "TEST_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return success
