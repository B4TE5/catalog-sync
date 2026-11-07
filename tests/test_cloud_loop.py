from pathlib import Path

import pytest

from vinted_hunter import cloud_loop


@pytest.mark.parametrize(
    ("others", "predecessor", "expected"),
    [
        ([], "", True),
        ([(9, "Monitor loop")], "", False),
        ([(11, "Monitor loop")], "", True),
        ([(9, "Snapshot 8-1-1")], "", True),
        ([(9, "Monitor loop")], "9", True),
        ([(8, "Monitor loop"), (9, "Monitor loop")], "9", False),
    ],
)
def test_claim_handles_duplicate_races_and_handoff(
    monkeypatch: pytest.MonkeyPatch, others: list, predecessor: str, expected: bool
) -> None:
    monkeypatch.setenv("GITHUB_RUN_ID", "10")
    monkeypatch.setenv("LOOP_PREDECESSOR", predecessor)
    monkeypatch.setattr(cloud_loop, "api", lambda _: {
        "workflow_runs": [{"id": i, "display_title": title} for i, title in others]
    })
    assert cloud_loop.allowed() is expected


@pytest.mark.parametrize(
    ("minutes", "expected_starts", "finished", "next_at"),
    [(35, [0, 600, 1200], 1320, 101800),
     (340, list(range(0, 19801, 600)), 19920, 120400)],
)
def test_loop_keeps_cadence_after_failure_and_leaves_time_for_handoff(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    minutes: int, expected_starts: list[int], finished: int, next_at: int,
) -> None:
    clock = [0.0]
    starts = []
    marker = tmp_path / "output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(marker))
    monkeypatch.setenv("GITHUB_RUN_ID", "10")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv("LOOP_MAX_MINUTES", str(minutes))
    monkeypatch.setenv("LOOP_NOT_BEFORE", "0")
    monkeypatch.setattr(cloud_loop.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(cloud_loop.time, "time", lambda: clock[0] + 100000)
    monkeypatch.setattr(
        cloud_loop.time, "sleep", lambda wait: clock.__setitem__(0, clock[0] + wait)
    )
    monkeypatch.setattr(cloud_loop.random, "uniform", lambda low, high: 600)

    def iteration(correlation: str, deadline: float) -> str:
        starts.append(clock[0])
        assert deadline - clock[0] == 540
        clock[0] += 120
        return "failure" if len(starts) == 2 else "success"

    monkeypatch.setattr(cloud_loop, "iteration", iteration)
    cloud_loop.loop()
    assert starts == expected_starts
    assert clock[0] == finished
    assert marker.read_text().strip() == f"not_before={next_at}.0"


def test_iteration_observes_dispatch_after_uncertain_transport_and_retries_poll(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = [0.0]
    attempts = [RuntimeError("transport"), {"status": "completed", "conclusion": "success"}]

    def dispatch(fields: dict) -> None:
        raise RuntimeError("uncertain response")

    def api(path: str) -> dict:
        if "runs?" in path:
            return {"workflow_runs": [{"id": 17, "display_title": "Snapshot test"}]}
        response = attempts.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(cloud_loop, "dispatch", dispatch)
    monkeypatch.setattr(cloud_loop, "api", api)
    monkeypatch.setattr(cloud_loop.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(
        cloud_loop.time, "sleep", lambda wait: clock.__setitem__(0, clock[0] + wait)
    )
    assert cloud_loop.iteration("test", 120) == "success"
    assert attempts == [] and clock[0] == 15


def test_iteration_cancels_timed_out_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = [0.0]
    cancelled = []
    monkeypatch.setattr(cloud_loop, "dispatch", lambda _: None)
    monkeypatch.setattr(cloud_loop, "gh", lambda *args: cancelled.append(args))
    monkeypatch.setattr(cloud_loop, "api", lambda path: {
        "workflow_runs": [{"id": 19, "display_title": "Snapshot test"}]
    } if "runs?" in path else {"status": "in_progress"})
    monkeypatch.setattr(cloud_loop.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(
        cloud_loop.time, "sleep", lambda wait: clock.__setitem__(0, clock[0] + wait)
    )
    assert cloud_loop.iteration("test", 31) == "timed_out"
    assert cancelled == [("run", "cancel", "19")]
    assert clock[0] == 31


def test_relay_uses_workflow_dispatch_with_default_full_duration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands = []
    monkeypatch.setenv("GITHUB_RUN_ID", "17")
    monkeypatch.setenv("GITHUB_REF_NAME", "main")
    monkeypatch.setenv("LOOP_NOT_BEFORE", "2000")
    monkeypatch.setattr(cloud_loop, "gh", lambda *args, **kwargs: commands.append((args, kwargs)))
    monkeypatch.setattr(cloud_loop.sys, "argv", ["cloud_loop", "relay"])
    assert cloud_loop.main() == 0
    args, kwargs = commands[0]
    assert args == ("workflow", "run", "hunt.yml", "--ref", "main", "--json")
    assert kwargs["payload"] == {
        "mode": "loop", "predecessor": "17", "not_before": "2000"
    }
