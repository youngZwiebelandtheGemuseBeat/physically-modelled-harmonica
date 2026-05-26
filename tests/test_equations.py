from __future__ import annotations

from dataclasses import replace
import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from harmonica_minimal.equations import (
    bernoulli_gap_flow,
    blow_pressure_drop,
    blow_reed_force,
    chamber_pressure_derivative,
    derived_state,
    effective_mouth_pressure,
    motion_flow,
    opening_area,
    P_C,
    P_T,
    total_reed_flow,
)
from harmonica_minimal.parameters import DRAW_PARAMETERS


def test_bernoulli_flow_sign() -> None:
    area = 1.0e-8
    rho = DRAW_PARAMETERS.rho_air_kg_m3

    assert bernoulli_gap_flow(100.0, area, 0.7, rho) > 0.0
    assert bernoulli_gap_flow(-100.0, area, 0.7, rho) < 0.0


def test_bernoulli_flow_zero_cases() -> None:
    rho = DRAW_PARAMETERS.rho_air_kg_m3

    assert bernoulli_gap_flow(0.0, 1.0e-8, 0.7, rho) == 0.0
    assert bernoulli_gap_flow(100.0, 0.0, 0.7, rho) == 0.0
    assert bernoulli_gap_flow(-100.0, -1.0e-8, 0.7, rho) == 0.0


def test_opening_area_nonnegative() -> None:
    reed = DRAW_PARAMETERS.draw_reed

    assert opening_area(0.0, reed) >= 0.0
    assert opening_area(1.0, reed) == 0.0


def test_chamber_derivative_sign() -> None:
    params = DRAW_PARAMETERS

    assert chamber_pressure_derivative(1.0e-7, 0.0, params) > 0.0
    assert chamber_pressure_derivative(0.0, 1.0e-7, params) < 0.0
    assert chamber_pressure_derivative(-1.0e-7, -2.0e-7, params) > 0.0


def test_motion_flow_disabled_gives_zero() -> None:
    reed = DRAW_PARAMETERS.draw_reed

    assert motion_flow(0.25, reed, enabled=False) == 0.0


def test_motion_flow_enabled_uses_hdot() -> None:
    reed = replace(DRAW_PARAMETERS.draw_reed, motion_area_m2=2.0e-6, gap_displacement_scale=-3.0)

    assert motion_flow(0.25, reed, enabled=True) == -1.5e-6


def test_total_flow_is_gap_plus_motion() -> None:
    assert total_reed_flow(1.2e-7, -0.2e-7) == 1.0e-7


def test_zero_tract_feedback_recovers_static_mouth_pressure() -> None:
    params = replace(DRAW_PARAMETERS, vocal_tract_feedback_gain=0.0)

    assert effective_mouth_pressure(-850.0, 123.0, params) == -850.0


def test_positive_tract_feedback_changes_effective_mouth_pressure() -> None:
    params = replace(DRAW_PARAMETERS, vocal_tract_feedback_gain=0.05)

    assert effective_mouth_pressure(-850.0, 100.0, params) == -855.0


def test_blow_pressure_drop_uses_effective_mouth_pressure() -> None:
    params = replace(DRAW_PARAMETERS, vocal_tract_feedback_gain=0.1)
    state = np.zeros(7, dtype=float)
    state[P_C] = 20.0
    state[P_T] = 50.0

    values = derived_state(1.0, 2.0, state, params)

    assert values.p_m_static == DRAW_PARAMETERS.mouth_pressure_pa
    assert values.p_m_effective == DRAW_PARAMETERS.mouth_pressure_pa - 5.0
    assert values.delta_p_b == blow_pressure_drop(values.p_m_effective, 20.0)
    assert values.delta_p_b != blow_pressure_drop(values.p_m_static, 20.0)


def test_blow_reed_force_uses_effective_mouth_pressure() -> None:
    params = replace(DRAW_PARAMETERS, vocal_tract_feedback_gain=0.1)
    state = np.zeros(7, dtype=float)
    state[P_C] = 20.0
    state[P_T] = 50.0

    values = derived_state(1.0, 2.0, state, params)

    assert values.force_b == blow_reed_force(values.p_m_effective, 20.0, params)
    assert values.force_b != blow_reed_force(values.p_m_static, 20.0, params)
