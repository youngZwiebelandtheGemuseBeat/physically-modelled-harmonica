from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import run as run_module
from run import parse_args, validate_active_scales, validate_opening_parameters, validate_passive_scales


def test_cli_passive_scales_default_to_one(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["run.py"])

    args = parse_args()

    assert args.passive_pressure_area_scale == 1.0
    assert args.passive_damping_scale == 1.0
    assert args.passive_discharge_scale == 1.0


def test_cli_opening_parameters_reject_negative_values() -> None:
    with np.testing.assert_raises_regex(ValueError, "--opening-negative-gain"):
        validate_opening_parameters(-0.1, 5.0)
    with np.testing.assert_raises_regex(ValueError, "--opening-closed-band-um"):
        validate_opening_parameters(0.25, -1.0)


def test_cli_active_scales_reject_nonpositive_values() -> None:
    cases = [
        ((0.0, 1.0, 1.0), "--active-pressure-area-scale"),
        ((1.0, 0.0, 1.0), "--active-damping-scale"),
        ((1.0, 1.0, 0.0), "--active-discharge-scale"),
        ((-0.1, 1.0, 1.0), "--active-pressure-area-scale"),
        ((1.0, -0.1, 1.0), "--active-damping-scale"),
        ((1.0, 1.0, -0.1), "--active-discharge-scale"),
    ]
    for values, message in cases:
        with np.testing.assert_raises_regex(ValueError, message):
            validate_active_scales(*values)


def test_cli_passive_scales_reject_nonpositive_values() -> None:
    cases = [
        ((0.0, 1.0, 1.0), "--passive-pressure-area-scale"),
        ((1.0, 0.0, 1.0), "--passive-damping-scale"),
        ((1.0, 1.0, 0.0), "--passive-discharge-scale"),
        ((-0.1, 1.0, 1.0), "--passive-pressure-area-scale"),
        ((1.0, -0.1, 1.0), "--passive-damping-scale"),
        ((1.0, 1.0, -0.1), "--passive-discharge-scale"),
    ]
    for values, message in cases:
        with np.testing.assert_raises_regex(ValueError, message):
            validate_passive_scales(*values)


def test_short_cli_run_writes_cause_audit_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(run_module, "OUTPUT_ROOT", tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run.py",
            "--mode",
            "draw",
            "--duration",
            "0.04",
            "--output-dir",
            "short-cause-audit",
        ],
    )

    run_module.main()

    output_dir = tmp_path / "short-cause-audit"
    for name in ("draw_note_cause_audit.png", "draw_note_cause_audit.md"):
        path = output_dir / name
        assert path.exists()
        assert path.stat().st_size > 0
