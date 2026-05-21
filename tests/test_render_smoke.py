from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from harmonica_model.diagnostics import diagnostic_metrics, write_diagnostic_report
from harmonica_model.params import BLOW_PARAMS, DEFAULT_PARAMS, DRAW_PARAMS, RenderConfig
from harmonica_model.render import render_draw_note, render_note
from run import render_both, render_mode_outputs, render_output_compare


def test_render_smoke_produces_non_silent_audio() -> None:
    result = render_draw_note(
        DEFAULT_PARAMS,
        RenderConfig(duration_s=0.25, sample_rate_hz=8_000, max_step_s=1.0 / 4_000.0),
    )

    assert result.audio.shape == (2_000,)
    assert np.all(np.isfinite(result.audio))
    assert float(np.max(np.abs(result.audio))) > 1.0e-4
    assert float(np.sqrt(np.mean(result.audio**2))) > 1.0e-5


def test_draw_mode_runs_and_writes_outputs(tmp_path: Path) -> None:
    config = RenderConfig(duration_s=0.12, sample_rate_hz=8_000, max_step_s=1.0 / 4_000.0)

    result = render_mode_outputs(tmp_path, "draw", DRAW_PARAMS, config)

    assert result.mode == "draw"
    assert (tmp_path / "draw_note.wav").exists()
    assert (tmp_path / "draw_note_trace.csv").exists()
    assert (tmp_path / "draw_note_diagnostics.png").exists()
    assert (tmp_path / "draw_note_report.md").exists()


def test_blow_mode_runs_and_writes_outputs(tmp_path: Path) -> None:
    config = RenderConfig(duration_s=0.12, sample_rate_hz=8_000, max_step_s=1.0 / 4_000.0)

    result = render_mode_outputs(tmp_path, "blow", BLOW_PARAMS, config)

    assert result.mode == "blow"
    assert (tmp_path / "blow_note.wav").exists()
    assert (tmp_path / "blow_note_trace.csv").exists()
    assert (tmp_path / "blow_note_diagnostics.png").exists()
    assert (tmp_path / "blow_note_report.md").exists()


def test_both_mode_runs_and_writes_comparison_outputs(tmp_path: Path) -> None:
    config = RenderConfig(duration_s=0.12, sample_rate_hz=8_000, max_step_s=1.0 / 4_000.0)

    render_both(tmp_path, DRAW_PARAMS, BLOW_PARAMS, config)

    assert (tmp_path / "draw_note.wav").exists()
    assert (tmp_path / "blow_note.wav").exists()
    assert (tmp_path / "comparison_report.md").exists()
    assert (tmp_path / "comparison_diagnostics.png").exists()


def test_output_compare_writes_pressure_flow_and_mixed_outputs(tmp_path: Path) -> None:
    config = RenderConfig(duration_s=0.12, sample_rate_hz=8_000, max_step_s=1.0 / 4_000.0)

    render_output_compare(tmp_path, "draw", DRAW_PARAMS, BLOW_PARAMS, config)

    compare_dir = tmp_path / "output_compare"
    assert (compare_dir / "draw_pressure.wav").exists()
    assert (compare_dir / "draw_flow.wav").exists()
    assert (compare_dir / "draw_mixed.wav").exists()
    assert (compare_dir / "summary.md").exists()


def test_draw_and_blow_outputs_are_not_identical() -> None:
    config = RenderConfig(duration_s=0.50, sample_rate_hz=8_000, max_step_s=1.0 / 4_000.0)

    draw_result = render_note("draw", DRAW_PARAMS, config)
    blow_result = render_note("blow", BLOW_PARAMS, config)
    blow_sustain = (blow_result.time_s >= 0.25) & (blow_result.time_s < 0.45)

    assert draw_result.audio.shape == blow_result.audio.shape
    assert not np.allclose(draw_result.audio, blow_result.audio)
    assert float(np.sqrt(np.mean(draw_result.audio**2))) > 1.0e-5
    assert float(np.sqrt(np.mean(blow_result.audio**2))) > 1.0e-5
    assert float(np.std(blow_result.audio[blow_sustain])) > 0.05
    assert float(np.std(blow_result.x_b[blow_sustain])) > 1.0e-6


def test_draw_and_blow_have_audible_physical_separation() -> None:
    config = RenderConfig(duration_s=0.50, sample_rate_hz=8_000, max_step_s=1.0 / 4_000.0)

    draw_result = render_note("draw", DRAW_PARAMS, config)
    blow_result = render_note("blow", BLOW_PARAMS, config)
    draw_metrics = diagnostic_metrics(draw_result)
    blow_metrics = diagnostic_metrics(blow_result)

    assert draw_metrics["dominant_reed_estimate"] == "draw reed"
    assert blow_metrics["dominant_reed_estimate"] == "blow reed"
    assert float(draw_metrics["harmonic_energy_ratio"]) > 0.60
    assert float(blow_metrics["harmonic_energy_ratio"]) > 0.25
    assert abs(float(draw_metrics["fundamental_hz"]) - float(blow_metrics["fundamental_hz"])) > 25.0
    assert float(draw_metrics["area_d_closed_percent"]) > 5.0
    assert float(blow_metrics["area_b_closed_percent"]) > 5.0
    assert draw_result.params.mouth_pressure_pa < 0.0
    assert blow_result.params.mouth_pressure_pa > 0.0


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
        result.q_loss,
        result.area_b,
        result.area_d,
        result.breath_envelope,
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
    assert result.p_m[0] == 0.0
    assert result.breath_envelope[0] == 0.0


def test_physical_breath_attack_is_audible_in_render_metrics() -> None:
    result = render_draw_note(
        DEFAULT_PARAMS,
        RenderConfig(duration_s=1.25, sample_rate_hz=8_000, max_step_s=1.0 / 4_000.0),
    )
    metrics = diagnostic_metrics(result)

    assert metrics["rms_first_100ms"] < metrics["rms_sustain"]
    assert metrics["attack_ratio"] < 0.35
    assert float(result.breath_envelope[0]) == 0.0
    assert float(result.breath_envelope[int(0.70 * result.sample_rate_hz)]) > 0.99


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
    assert "Attack ratio first/sustain" in report
    assert "Breath Envelope Parameters" in report
    assert "Chamber pressure feedback nonzero" in report
    assert "Dominant reed estimate" in report
    assert "Sign Convention" in report
    assert "Equation Audit" in report
