from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from harmonica_minimal.diagnostics import (
    analyze_cause_audit,
    detect_sideband_like_components,
    relative_spectrum,
    select_steady_state_window,
)
from harmonica_minimal.parameters import SimulationConfig
from harmonica_minimal.simulate import simulate_note


def test_cause_audit_spectra_are_finite_and_cover_requested_traces() -> None:
    config = SimulationConfig(duration_s=0.08, sample_rate_hz=4_000, max_step_s=1.0 / 4_000.0)
    result = simulate_note("blow", config=config)

    audit = analyze_cause_audit(result)

    assert {trace.name for trace in audit.traces} == {
        "audio",
        "p_c",
        "p_t",
        "q_b",
        "q_d",
        "net_flow",
        "x_b",
        "x_d",
    }
    for trace in audit.traces:
        for spectrum in (trace.full_spectrum, trace.steady_spectrum):
            assert np.all(np.isfinite(spectrum.frequencies_hz))
            assert np.all(np.isfinite(spectrum.relative_db))
            assert float(np.max(spectrum.relative_db)) <= 1.0e-12
    assert np.isfinite(audit.settling.pressure_early_db)
    assert np.isfinite(audit.settling.pressure_late_db)
    assert np.isfinite(audit.settling.passive_motion_early_db)
    assert np.isfinite(audit.settling.passive_motion_late_db)


def test_constant_and_dc_traces_have_finite_floor_values() -> None:
    for signal in (np.zeros(64), np.full(64, 3.25), np.array([8.0])):
        spectrum = relative_spectrum(signal, sample_rate_hz=8_000)

        assert np.all(np.isfinite(spectrum.relative_db))
        assert np.all(spectrum.relative_db == -120.0)


def test_sideband_detector_finds_significant_noncentral_peak() -> None:
    sample_rate_hz = 8_000
    time_s = np.arange(2 * sample_rate_hz) / sample_rate_hz
    signal = np.sin(2.0 * np.pi * 400.0 * time_s) + 0.02 * np.sin(2.0 * np.pi * 450.0 * time_s)

    spectrum = relative_spectrum(signal, sample_rate_hz)
    shoulders = detect_sideband_like_components(spectrum, f0_hz=400.0)

    assert shoulders[0].detected
    assert any(abs(frequency_hz - 450.0) < 1.0 for frequency_hz, _level_db in shoulders[0].components)


def test_steady_state_window_falls_back_safely_for_short_render() -> None:
    config = SimulationConfig(duration_s=0.01, sample_rate_hz=2_000, max_step_s=1.0 / 2_000.0)
    result = simulate_note("draw", config=config)

    window = select_steady_state_window(result)
    audit = analyze_cause_audit(result)

    assert window.used_fallback
    assert 0 <= window.start < window.stop <= len(result.time_s)
    assert len(audit.traces) == 8


def test_normal_steady_state_window_is_late_and_at_most_one_second() -> None:
    config = SimulationConfig(duration_s=1.5, sample_rate_hz=2_000, max_step_s=1.0 / 2_000.0)
    result = simulate_note("draw", config=config)

    window = select_steady_state_window(result)

    assert not window.used_fallback
    assert window.stop_s <= 1.5 - result.params.release_s - 0.10
    assert window.start_s >= result.params.attack_s + 0.10
    assert window.stop_s - window.start_s <= 1.0
