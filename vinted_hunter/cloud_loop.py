"""Coordina pasadas independientes y el relevo del monitor en GitHub Actions."""

import json
import os
import random
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

LOOP_TITLE = "Monitor loop"
POLL_SECONDS = 15
ITERATION_TIMEOUT_SECONDS = 540
HANDOFF_MARGIN_SECONDS = 60


def emit(event: str, **details: Any) -> None:
    print(
        json.dumps({"event": event, "time": datetime.now(UTC).isoformat(), **details}),
        flush=True,
    )


def gh(*args: str, payload: dict[str, Any] | None = None) -> str:
    result = subprocess.run(
        ["gh", *args],
        input=json.dumps(payload) if payload is not None else None,
        text=True,
        capture_output=True,
        timeout=45,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"gh {args[0]} terminó con código {result.returncode}")
    return result.stdout


def api(path: str) -> dict[str, Any]:
    return json.loads(gh("api", f"repos/{os.environ['GITHUB_REPOSITORY']}/{path}"))


def allowed() -> bool:
    current = int(os.environ["GITHUB_RUN_ID"])
    predecessor = os.environ.get("LOOP_PREDECESSOR", "")
    for status in ("in_progress", "queued"):
        data = api(f"actions/workflows/hunt.yml/runs?status={status}&per_page=100")
        for run in data["workflow_runs"]:
            if (
                run["display_title"] == LOOP_TITLE
                and run["id"] < current
                and str(run["id"]) != predecessor
            ):
                emit("loop_already_active", run_id=run["id"])
                return False
    return True


def output(name: str, value: str) -> None:
    with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as stream:
        stream.write(f"{name}={value}\n")


def dispatch(fields: dict[str, str]) -> None:
    gh(
        "workflow", "run", "hunt.yml", "--ref", os.environ["GITHUB_REF_NAME"],
        "--json", payload=fields,
    )


def iteration(correlation: str, deadline: float) -> str:
    # Buscar también tras un error de transporte evita repetir un despacho aceptado.
    try:
        dispatch({"mode": "iteration", "correlation": correlation})
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        emit("iteration_dispatch_error", error=type(error).__name__)
    run_id = None
    while time.monotonic() < deadline:
        try:
            if run_id is None:
                data = api("actions/workflows/hunt.yml/runs?event=workflow_dispatch&per_page=100")
                run_id = next(
                    (row["id"] for row in data["workflow_runs"]
                     if row["display_title"] == f"Snapshot {correlation}"),
                    None,
                )
                if run_id is not None:
                    emit("iteration_run", run_id=run_id, correlation=correlation)
            if run_id is not None:
                run = api(f"actions/runs/{run_id}")
                if run["status"] == "completed":
                    return str(run["conclusion"])
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
            emit("iteration_poll_error", error=type(error).__name__)
        time.sleep(min(POLL_SECONDS, max(0, deadline - time.monotonic())))
    if run_id is not None:
        gh("run", "cancel", str(run_id))
    return "timed_out"


def loop() -> None:
    minutes = float(os.environ.get("LOOP_MAX_MINUTES", "340"))
    if not 10 <= minutes <= 340:
        raise ValueError("La duración debe estar entre 10 y 340 minutos")
    deadline = time.monotonic() + minutes * 60
    emit("loop_started", max_minutes=minutes, interval_seconds=600, jitter_seconds=120)
    not_before = float(os.environ.get("LOOP_NOT_BEFORE") or "0")
    wait = max(0, min(720, not_before - time.time()))
    time.sleep(wait)
    number = 0
    next_start = time.monotonic()
    while next_start + ITERATION_TIMEOUT_SECONDS + HANDOFF_MARGIN_SECONDS <= deadline:
        time.sleep(max(0, next_start - time.monotonic()))
        started = time.monotonic()
        if started + ITERATION_TIMEOUT_SECONDS + HANDOFF_MARGIN_SECONDS > deadline:
            break
        number += 1
        correlation = f"{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}-{number}"
        emit("loop_iteration_start", iteration=number, correlation=correlation)
        try:
            conclusion = iteration(correlation, min(deadline, started + ITERATION_TIMEOUT_SECONDS))
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
            conclusion = type(error).__name__
        next_start = started + random.uniform(480, 720)
        emit(
            "loop_iteration_end", iteration=number, conclusion=conclusion,
            duration_seconds=round(time.monotonic() - started, 2),
            next_start=datetime.fromtimestamp(
                time.time() + max(0, next_start - time.monotonic()), UTC
            ).isoformat(),
        )
    output("not_before", str(time.time() + max(0, next_start - time.monotonic())))
    emit("loop_handoff_ready", iterations=number)


def main() -> int:
    try:
        operation = sys.argv[1]
        if operation == "claim":
            output("proceed", "true" if allowed() else "false")
        elif operation == "loop":
            loop()
        elif operation == "relay":
            dispatch({
                "mode": "loop", "predecessor": os.environ["GITHUB_RUN_ID"],
                "not_before": os.environ.get("LOOP_NOT_BEFORE") or "0",
            })
            emit("loop_relay_dispatched")
        else:
            return 2
    except (OSError, ValueError, RuntimeError, KeyError, subprocess.TimeoutExpired) as error:
        emit("loop_error", error=type(error).__name__)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
