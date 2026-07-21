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
    opening_area_asymmetric_reopen,
    opening_area_clipped,
    opening_area_symmetric_smooth,
    P_C,
    P_T,
    reed_gap,
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


def displacement_for_gap(gap_m: float) -> float:
    reed = DRAW_PARAMETERS.draw_reed
    return (gap_m - reed.rest_gap_m) / reed.gap_displacement_scale


def test_opening_area_clipped_reproduces_previous_law() -> None:
    reed = DRAW_PARAMETERS.draw_reed

    for gap_m, expected_area_m2 in [
        (2.0e-5, reed.slot_width_m * 2.0e-5),
        (0.0, 0.0),
        (-2.0e-5, 0.0),
    ]:
        displacement_m = displacement_for_gap(gap_m)
        assert reed_gap(displacement_m, reed) == gap_m
        assert opening_area_clipped(displacement_m, reed) == expected_area_m2


def test_opening_area_symmetric_smooth_reopens_on_both_sides() -> None:
    reed = DRAW_PARAMETERS.draw_reed
    zero_area = opening_area_symmetric_smooth(displacement_for_gap(0.0), reed)
    positive_area = opening_area_symmetric_smooth(displacement_for_gap(2.0e-5), reed)
    negative_area = opening_area_symmetric_smooth(displacement_for_gap(-2.0e-5), reed)

    assert zero_area >= 0.0
    assert zero_area < 1.0e-18
    assert positive_area > 0.0
    assert negative_area > 0.0


def test_opening_area_asymmetric_reopen_behavior() -> None:
    reed = DRAW_PARAMETERS.draw_reed
    positive_gap_m = 2.0e-5
    negative_gap_m = -2.0e-5
    positive_displacement_m = displacement_for_gap(positive_gap_m)
    negative_displacement_m = displacement_for_gap(negative_gap_m)

    positive_area = opening_area_asymmetric_reopen(positive_displacement_m, reed)
    inward_area = opening_area_asymmetric_reopen(negative_displacement_m, reed)

    assert positive_area >= 0.0
    assert inward_area >= 0.0
    assert positive_area == opening_area_clipped(positive_displacement_m, reed)
    assert opening_area_asymmetric_reopen(
        negative_displacement_m,
        reed,
        negative_gain=0.0,
    ) == 0.0
    assert opening_area_asymmetric_reopen(
        negative_displacement_m,
        reed,
        negative_gain=1.0,
        closed_band_m=0.0,
    ) == reed.slot_width_m * abs(negative_gap_m)
    assert inward_area < positive_area


def test_opening_area_asymmetric_reopen_closed_band_delays_reopening() -> None:
    reed = DRAW_PARAMETERS.draw_reed
    displacement_m = displacement_for_gap(-2.0e-6)

    assert opening_area_asymmetric_reopen(
        displacement_m,
        reed,
        closed_band_m=5.0e-6,
    ) == 0.0


def test_opening_area_asymmetric_reopen_rejects_negative_parameters() -> None:
    reed = DRAW_PARAMETERS.draw_reed

    with np.testing.assert_raises_regex(ValueError, "negative_gain"):
        opening_area_asymmetric_reopen(0.0, reed, negative_gain=-0.1)
    with np.testing.assert_raises_regex(ValueError, "closed_band_m"):
        opening_area_asymmetric_reopen(0.0, reed, closed_band_m=-1.0e-6)


def test_opening_area_defaults_to_clipped() -> None:
    reed = DRAW_PARAMETERS.draw_reed
    displacement_m = displacement_for_gap(-2.0e-5)

    assert opening_area(displacement_m, reed) == opening_area_clipped(displacement_m, reed)


def test_existing_opening_models_ignore_asymmetric_tuning() -> None:
    reed = DRAW_PARAMETERS.draw_reed
    displacement_m = displacement_for_gap(-2.0e-5)

    for opening_model in ["clipped", "symmetric_smooth"]:
        default_area = opening_area(displacement_m, reed, opening_model)
        tuned_area = opening_area(
            displacement_m,
            reed,
            opening_model,
            negative_gain=10.0,
            closed_band_m=1.0,
        )
        assert tuned_area == default_area


def test_opening_area_rejects_unknown_model() -> None:
    reed = DRAW_PARAMETERS.draw_reed

    with np.testing.assert_raises_regex(ValueError, "unknown opening model"):
        opening_area(0.0, reed, "invalid")


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
