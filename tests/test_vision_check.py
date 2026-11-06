from io import BytesIO
from pathlib import Path

import qrcode
from typer.testing import CliRunner

from vinted_hunter.cli import app
from vinted_hunter.config import load_config
from vinted_hunter.pipeline.vision import inspect_photos

ROOT = Path(__file__).parents[1]


def test_vision_command_is_registered() -> None:
    result = CliRunner().invoke(app, ["vision-check", "--help"])
    assert result.exit_code == 0
    assert "--profile" in result.stdout and "--limit" in result.stdout


def test_plaintext_qr_is_legible_in_visual_sample(tmp_path: Path) -> None:
    image = BytesIO()
    qrcode.make("Stone Island").save(image)
    evidence = inspect_photos(
        [image.getvalue()], tmp_path, tmp_path, load_config(ROOT).scoring.thresholds, True,
    )
    assert evidence.qr_decoded
    assert evidence.qr == "qr_detected_unreadable"
    assert len(evidence.hashes) == 1
    assert evidence.parts_present == []
