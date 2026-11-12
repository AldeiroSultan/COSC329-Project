"""Integration coverage for report generation in a headless subprocess."""
import os
import subprocess
import sys

from PIL import Image

from study_planner import config as cfg


def test_figures_cli_writes_three_valid_images_to_custom_directory(tmp_path):
    output = tmp_path / "nested" / "figures"
    env = dict(os.environ, MPLBACKEND="Agg", MPLCONFIGDIR=str(tmp_path / "mpl"))
    result = subprocess.run(
        [sys.executable, "-m", "study_planner.cli", "figures", "--out", str(output)],
        cwd=cfg.ROOT, env=env, capture_output=True, text=True, timeout=90,
    )
    assert result.returncode == 0, result.stderr
    assert {path.name for path in output.iterdir()} == {
        "network.png", "cpt_comparison.png", "expected_utility.png",
    }
    assert result.stdout.count("Saved:") == 3
    for path in output.iterdir():
        with Image.open(path) as image:
            assert image.format == "PNG"
            assert image.width >= 1000 and image.height >= 600
            image.verify()
