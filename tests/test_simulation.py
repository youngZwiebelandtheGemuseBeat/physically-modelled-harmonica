from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from harmonica_minimal.parameters import SimulationConfig
from harmonica_minimal.simulate import simulate_note


def test_simulation_produces_finite_non_silent_chamber_pressure() -> None:
    config = SimulationConfig(duration_s=0.18, sample_rate_hz=8_000, max_step_s=1.0 / 8_000.0)

    result = simulate_note("draw", config=config)

    assert np.all(np.isfinite(result.p_c))
    assert float(np.max(np.abs(result.p_c))) > 1.0e-6


def test_trace_arrays_have_no_nan_or_inf() -> None:
    config = SimulationConfig(duration_s=0.12, sample_rate_hz=8_000, max_step_s=1.0 / 8_000.0)

    result = simulate_note("blow", config=config)

    arrays = [
        result.state,
        result.gap_b,
        result.gap_d,
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

