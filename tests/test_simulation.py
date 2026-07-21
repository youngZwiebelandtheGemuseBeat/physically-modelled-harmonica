from __future__ import annotations

import csv
from dataclasses import replace
import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from harmonica_minimal.parameters import SimulationConfig
from harmonica_minimal.parameters import BLOW_PARAMETERS, DRAW_PARAMETERS, parameters_for_mode
from harmonica_minimal.output import (
    diagnostics_text,
    harmonic_ratios,
    low_frequency_measurements,
    oscillation_measurements,
    write_trace_csv,
)
from harmonica_minimal.plots import (
    DEFAULT_COMPARISON_PRESSURE_LIMIT_PA,
    _comparison_pressure_limit_pa,
    plot_presentation_pressure_result,
    write_millot_style_spectra,
    write_spectral_window_comparison_plot,
    write_validation_plot,
)
from harmonica_minimal.simulate import simulate_note


def test_simulation_produces_finite_non_silent_chamber_pressure() -> None:
    config = SimulationConfig(duration_s=0.18, sample_rate_hz=8_000, max_step_s=1.0 / 8_000.0)

    result = simulate_note("draw", config=config)

    assert np.all(np.isfinite(result.p_c))
    assert float(np.max(np.abs(result.p_c))) > 1.0e-6


def test_default_pressures_represent_normal_play_not_draw_bend() -> None:
    assert BLOW_PARAMETERS.mouth_pressure_pa == 250.0
    assert DRAW_PARAMETERS.mouth_pressure_pa == -250.0
    assert abs(DRAW_PARAMETERS.mouth_pressure_pa) < 635.0


def test_default_blow_and_draw_pressure_plots_use_the_same_symmetric_limit() -> None:
    config = SimulationConfig(duration_s=0.04, sample_rate_hz=4_000, max_step_s=1.0 / 4_000.0)

    for mode in ("blow", "draw"):
        result = simulate_note(mode, config=config)
        limit = _comparison_pressure_limit_pa(result, 0, len(result.time_s))

        assert limit == DEFAULT_COMPARISON_PRESSURE_LIMIT_PA == 260.0


def test_simulation_runs_with_symmetric_smooth_opening_model() -> None:
    config = SimulationConfig(duration_s=0.04, sample_rate_hz=4_000, max_step_s=1.0 / 4_000.0)

    result = simulate_note("draw", config=config, opening_model="symmetric_smooth")

    assert np.all(np.isfinite(result.p_c))


def test_simulation_runs_with_asymmetric_reopen_opening_model() -> None:
    config = SimulationConfig(duration_s=0.04, sample_rate_hz=4_000, max_step_s=1.0 / 4_000.0)

    result = simulate_note("draw", config=config, opening_model="asymmetric_reopen")

    assert np.all(np.isfinite(result.p_c))


def test_trace_arrays_have_no_nan_or_inf() -> None:
    config = SimulationConfig(duration_s=0.12, sample_rate_hz=8_000, max_step_s=1.0 / 8_000.0)

    result = simulate_note("blow", config=config)

    arrays = [
        result.state,
        result.gap_b,
        result.gap_d,
        result.area_b,
        result.area_d,
        result.delta_p_b,
        result.delta_p_d,
        result.q_b_gap,
        result.q_b_motion,
        result.q_b_total,
        result.q_d_gap,
        result.q_d_motion,
        result.q_d_total,
        result.force_b,
        result.force_d,
    ]
    for array in arrays:
        assert np.all(np.isfinite(array))


def test_effective_mouth_pressure_appears_in_trace_output(tmp_path: Path) -> None:
    config = SimulationConfig(duration_s=0.04, sample_rate_hz=4_000, max_step_s=1.0 / 4_000.0)
    result = simulate_note("draw", config=config, vocal_tract_feedback_gain=0.0)
    trace_path = tmp_path / "trace.csv"

    write_trace_csv(trace_path, result)

    with trace_path.open(newline="") as handle:
        header = next(csv.reader(handle))
    assert "p_m_static" in header
    assert "p_m_effective" in header
    assert "vocal_tract_feedback_gain" in header
    assert "area_b" in header
    assert "area_d" in header


def test_low_frequency_diagnostics_cover_required_signals() -> None:
    config = SimulationConfig(duration_s=0.18, sample_rate_hz=8_000, max_step_s=1.0 / 8_000.0)
    result = simulate_note("draw", config=config)

    measurements = low_frequency_measurements(result)
    names = {measurement.name for measurement in measurements}
    assert "raw chamber pressure p_c" in names
    assert "vocal-tract pressure p_t" in names
    assert "net flow q_b - q_d - q_loss" in names
    assert "raw selected output before normalization" in names
    assert "final normalized audio" in names

    report = diagnostics_text(result)
    assert "prescribed mouth-pressure boundary: -250 Pa" in report
    assert "Low-frequency/DC content, full note:" in report
    assert "Low-frequency/DC content, steady-state excluding attack/release:" in report
    assert "H1=f0" in report
    assert "0 Hz is the DC bin, not a harmonic" in report
    assert "opening model: clipped" in report
    assert "opening negative gain: 0.25" in report
    assert "opening closed band: 5 um" in report
    assert "active pressure-area scale: 1" in report
    assert "active damping scale: 1" in report
    assert "active discharge scale: 1" in report
    assert "passive pressure-area scale: 1" in report
    assert "passive damping scale: 1" in report
    assert "passive discharge scale: 1" in report
    assert "Steady-state oscillation measurements with explicit definitions:" in report


def test_oscillation_measurements_define_pressure_and_reed_amplitudes() -> None:
    config = SimulationConfig(duration_s=0.18, sample_rate_hz=8_000, max_step_s=1.0 / 8_000.0)
    result = simulate_note("blow", config=config)

    measurements = oscillation_measurements(result)

    assert {measurement.name for measurement in measurements} == {
        "chamber pressure p_c",
        "blow reed displacement x_b",
        "draw reed displacement x_d",
    }
    for measurement in measurements:
        assert np.isfinite(measurement.mean)
        assert np.isfinite(measurement.ac_rms)
        assert np.isfinite(measurement.half_peak_to_peak)
        assert measurement.ac_rms >= 0.0
        assert measurement.half_peak_to_peak >= 0.0


def test_harmonic_ratios_use_local_peaks_for_non_bin_centered_tones() -> None:
    sample_rate_hz = 8_000
    time_s = np.arange(sample_rate_hz) / sample_rate_hz
    f0_hz = 403.4
    signal = np.sin(2.0 * np.pi * f0_hz * time_s) + 0.25 * np.sin(4.0 * np.pi * f0_hz * time_s)

    ratios = harmonic_ratios(signal, sample_rate_hz, f0_hz, count=2)

    assert abs(ratios[0] - 1.0) < 1.0e-12
    assert abs(ratios[1] - 0.25) < 0.02


def test_default_calibration_scales_preserve_behavior() -> None:
    config = SimulationConfig(duration_s=0.04, sample_rate_hz=4_000, max_step_s=1.0 / 4_000.0)

    default_result = simulate_note("draw", config=config)
    explicit_result = simulate_note(
        "draw",
        config=config,
        active_pressure_area_scale=1.0,
        active_damping_scale=1.0,
        active_discharge_scale=1.0,
        passive_pressure_area_scale=1.0,
        passive_damping_scale=1.0,
        passive_discharge_scale=1.0,
    )

    assert default_result.active_pressure_area_scale == 1.0
    assert default_result.active_damping_scale == 1.0
    assert default_result.active_discharge_scale == 1.0
    assert default_result.passive_pressure_area_scale == 1.0
    assert default_result.passive_damping_scale == 1.0
    assert default_result.passive_discharge_scale == 1.0
    assert default_result.params == parameters_for_mode("draw")
    assert np.array_equal(default_result.state, explicit_result.state)


def test_calibration_scales_must_be_positive() -> None:
    for keyword in [
        "active_pressure_area_scale",
        "active_damping_scale",
        "active_discharge_scale",
        "passive_pressure_area_scale",
        "passive_damping_scale",
        "passive_discharge_scale",
    ]:
        with np.testing.assert_raises_regex(ValueError, keyword):
            simulate_note("draw", **{keyword: 0.0})
        with np.testing.assert_raises_regex(ValueError, keyword):
            simulate_note("draw", **{keyword: -0.1})


def test_blow_calibration_scales_only_requested_active_reed_fields() -> None:
    baseline = parameters_for_mode("blow")
    result = simulate_note(
        "blow",
        config=SimulationConfig(duration_s=0.01, sample_rate_hz=2_000),
        active_pressure_area_scale=1.25,
        active_damping_scale=0.8,
        active_discharge_scale=1.2,
    )

    assert result.params.blow_reed == replace(
        baseline.blow_reed,
        pressure_area_m2=baseline.blow_reed.pressure_area_m2 * 1.25,
        damping_kg_s=baseline.blow_reed.damping_kg_s * 0.8,
        discharge_coefficient=baseline.blow_reed.discharge_coefficient * 1.2,
    )
    assert result.params.draw_reed == baseline.draw_reed


def test_draw_calibration_scales_only_requested_active_reed_fields() -> None:
    baseline = parameters_for_mode("draw")
    result = simulate_note(
        "draw",
        config=SimulationConfig(duration_s=0.01, sample_rate_hz=2_000),
        active_pressure_area_scale=1.25,
        active_damping_scale=0.8,
        active_discharge_scale=1.2,
    )

    assert result.params.draw_reed == replace(
        baseline.draw_reed,
        pressure_area_m2=baseline.draw_reed.pressure_area_m2 * 1.25,
        damping_kg_s=baseline.draw_reed.damping_kg_s * 0.8,
        discharge_coefficient=baseline.draw_reed.discharge_coefficient * 1.2,
    )
    assert result.params.blow_reed == baseline.blow_reed


def test_blow_passive_calibration_scales_only_draw_reed_fields() -> None:
    baseline = parameters_for_mode("blow")
    result = simulate_note(
        "blow",
        config=SimulationConfig(duration_s=0.01, sample_rate_hz=2_000),
        passive_pressure_area_scale=1.25,
        passive_damping_scale=0.8,
        passive_discharge_scale=1.2,
    )

    assert result.params.draw_reed == replace(
        baseline.draw_reed,
        pressure_area_m2=baseline.draw_reed.pressure_area_m2 * 1.25,
        damping_kg_s=baseline.draw_reed.damping_kg_s * 0.8,
        discharge_coefficient=baseline.draw_reed.discharge_coefficient * 1.2,
    )
    assert result.params.blow_reed == baseline.blow_reed


def test_draw_passive_calibration_scales_only_blow_reed_fields() -> None:
    baseline = parameters_for_mode("draw")
    result = simulate_note(
        "draw",
        config=SimulationConfig(duration_s=0.01, sample_rate_hz=2_000),
        passive_pressure_area_scale=1.25,
        passive_damping_scale=0.8,
        passive_discharge_scale=1.2,
    )

    assert result.params.blow_reed == replace(
        baseline.blow_reed,
        pressure_area_m2=baseline.blow_reed.pressure_area_m2 * 1.25,
        damping_kg_s=baseline.blow_reed.damping_kg_s * 0.8,
        discharge_coefficient=baseline.blow_reed.discharge_coefficient * 1.2,
    )
    assert result.params.draw_reed == baseline.draw_reed


def test_passive_calibration_scales_change_only_requested_fields() -> None:
    baseline = parameters_for_mode("draw")
    config = SimulationConfig(duration_s=0.01, sample_rate_hz=2_000)
    cases = [
        (
            {"passive_pressure_area_scale": 1.25},
            replace(baseline.blow_reed, pressure_area_m2=baseline.blow_reed.pressure_area_m2 * 1.25),
        ),
        (
            {"passive_damping_scale": 0.8},
            replace(baseline.blow_reed, damping_kg_s=baseline.blow_reed.damping_kg_s * 0.8),
        ),
        (
            {"passive_discharge_scale": 1.2},
            replace(
                baseline.blow_reed,
                discharge_coefficient=baseline.blow_reed.discharge_coefficient * 1.2,
            ),
        ),
    ]

    for scales, expected_reed in cases:
        result = simulate_note("draw", config=config, **scales)
        assert result.params.blow_reed == expected_reed
        assert result.params.draw_reed == baseline.draw_reed


def test_presentation_plot_export_preserves_validation_plot(tmp_path: Path) -> None:
    config = SimulationConfig(duration_s=0.18, sample_rate_hz=8_000, max_step_s=1.0 / 8_000.0)
    result = simulate_note("blow", config=config)
    validation_path = tmp_path / "blow_validation.png"
    presentation_path = tmp_path / "blow_presentation_pressure.png"

    write_validation_plot(validation_path, result)
    plot_presentation_pressure_result(presentation_path, result)

    assert validation_path.exists()
    assert validation_path.stat().st_size > 0
    assert presentation_path.exists()
    assert presentation_path.stat().st_size > 0


def test_millot_style_spectra_are_additional_exports(tmp_path: Path) -> None:
    config = SimulationConfig(duration_s=0.18, sample_rate_hz=16_000, max_step_s=1.0 / 16_000.0)
    result = simulate_note("draw", config=config)
    validation_path = tmp_path / "draw_validation.png"
    presentation_path = tmp_path / "draw_presentation_pressure.png"

    write_validation_plot(validation_path, result)
    plot_presentation_pressure_result(presentation_path, result)
    write_millot_style_spectra(tmp_path, result)

    reed_path = tmp_path / "draw_millot_style_reed_spectrum.png"
    pressure_path = tmp_path / "draw_millot_style_pressure_spectrum.png"
    assert validation_path.exists()
    assert validation_path.stat().st_size > 0
    assert presentation_path.exists()
    assert presentation_path.stat().st_size > 0
    assert reed_path.exists()
    assert reed_path.stat().st_size > 0
    assert pressure_path.exists()
    assert pressure_path.stat().st_size > 0


def test_blow_draw_spectral_window_audit_is_written(tmp_path: Path) -> None:
    config = SimulationConfig(duration_s=0.08, sample_rate_hz=4_000, max_step_s=1.0 / 4_000.0)
    results = [simulate_note(mode, config=config) for mode in ("blow", "draw")]
    path = tmp_path / "blow_draw_spectral_window_audit.png"

    write_spectral_window_comparison_plot(path, results)

    assert path.exists()
    assert path.stat().st_size > 0
