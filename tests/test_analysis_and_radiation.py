from __future__ import annotations

from dataclasses import replace
import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from harmonica_model.analysis import analyze_audio
from harmonica_model.params import DEFAULT_PARAMS, RenderConfig
from harmonica_model.render import render_draw_note


def test_reference_analysis_estimates_harmonics() -> None:
    sample_rate_hz = 8_000
    time_s = np.arange(sample_rate_hz, dtype=float) / sample_rate_hz
    audio = np.sin(2.0 * np.pi * 440.0 * time_s) + 0.4 * np.sin(2.0 * np.pi * 880.0 * time_s)

    analysis = analyze_audio(audio, sample_rate_hz)

    assert abs(analysis.fundamental_hz - 440.0) < 5.0
    assert len(analysis.harmonic_amplitudes) == 12
    assert analysis.harmonic_amplitudes[1] > analysis.harmonic_amplitudes[2]
    assert analysis.harmonic_energy_ratio > 0.10
    assert analysis.spectral_centroid_hz > analysis.fundamental_hz


def test_flow_noise_path_remains_flow_driven_and_finite() -> None:
    params = replace(DEFAULT_PARAMS, flow_noise_amount=0.01)
    result = render_draw_note(
        params,
        RenderConfig(duration_s=0.25, sample_rate_hz=8_000, max_step_s=1.0 / 4_000.0),
    )

    assert np.all(np.isfinite(result.audio))
    assert float(np.max(np.abs(result.audio))) > 1.0e-4
    assert float(np.max(np.abs(result.q_b)) + np.max(np.abs(result.q_d))) > 1.0e-9
