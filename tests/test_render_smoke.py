from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from harmonica_model.diagnostics import write_diagnostic_report
from harmonica_model.params import DEFAULT_PARAMS, RenderConfig
from harmonica_model.render import render_draw_note


def test_render_smoke_produces_non_silent_audio() -> None:
    result = render_draw_note(
        DEFAULT_PARAMS,
        RenderConfig(duration_s=0.25, sample_rate_hz=8_000, max_step_s=1.0 / 4_000.0),
    )

    assert result.audio.shape == (2_000,)
    assert np.all(np.isfinite(result.audio))
    assert float(np.max(np.abs(result.audio))) > 1.0e-4
    assert float(np.sqrt(np.mean(result.audio**2))) > 1.0e-5


def test_render_exposes_full_coupled_state_and_feedback() -> None:
    result = render_draw_note(
        DEFAULT_PARAMS,
        RenderConfig(duration_s=0.25, sample_rate_hz=8_000, max_step_s=1.0 / 4_000.0),
    )

    assert result.state.shape == (7, 2_000)
    for trace in (
        result.x_b,
        result.x_d,
        result.p_c,
        result.p_t,
        result.q_b,
        result.q_d,
        result.area_b,
        result.area_d,
        result.delta_p_b,
        result.delta_p_d,
    ):
        assert np.all(np.isfinite(trace))

    assert float(np.max(np.abs(result.x_b))) > 0.0
    assert float(np.max(np.abs(result.x_d))) > 0.0
    assert float(np.max(np.abs(result.p_c))) > 1.0
    assert float(np.max(np.abs(result.p_t))) > 1.0
    assert float(np.max(np.abs(result.q_b))) > 1.0e-9
    assert float(np.max(np.abs(result.q_d))) > 1.0e-9
    assert float(np.max(np.abs(result.delta_p_b))) > 1.0
    assert float(np.max(np.abs(result.delta_p_d))) > 1.0


def test_diagnostic_report_contains_audit_metrics(tmp_path: Path) -> None:
    result = render_draw_note(
        DEFAULT_PARAMS,
        RenderConfig(duration_s=0.25, sample_rate_hz=8_000, max_step_s=1.0 / 4_000.0),
    )
    report_path = tmp_path / "draw_note_report.md"

    write_diagnostic_report(report_path, result)

    report = report_path.read_text(encoding="utf-8")
    assert "Peak audio" in report
    assert "Estimated fundamental frequency" in report
    assert "Harmonic energy ratio" in report
    assert "Chamber pressure feedback nonzero" in report
    assert "Equation Audit" in report
