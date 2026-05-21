from __future__ import annotations

import sys
from pathlib import Path
from dataclasses import replace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from harmonica_model.equations import chamber_pressure_derivative
from harmonica_model.equations import derived_values
from harmonica_model.params import BLOW_PARAMS, DEFAULT_PARAMS, DRAW_PARAMS


def test_chamber_pressure_derivative_signs() -> None:
    params = DEFAULT_PARAMS

    assert chamber_pressure_derivative(1.0e-7, 0.0, params) > 0.0
    assert chamber_pressure_derivative(0.0, 1.0e-7, params) < 0.0
    assert chamber_pressure_derivative(-1.0e-7, -2.0e-7, params) > 0.0


def test_chamber_loss_opposes_existing_pressure() -> None:
    params = replace(DEFAULT_PARAMS, chamber_loss_conductance_m3_s_pa=2.0e-11)

    assert chamber_pressure_derivative(0.0, 0.0, params, p_c_pa=100.0) < 0.0
    assert chamber_pressure_derivative(0.0, 0.0, params, p_c_pa=-100.0) > 0.0


def test_draw_and_blow_pressure_sign_convention() -> None:
    zero_state = [0.0] * 7

    draw_values = derived_values(0.70, zero_state, DRAW_PARAMS)
    blow_values = derived_values(0.70, zero_state, BLOW_PARAMS)

    assert draw_values.p_m < 0.0
    assert draw_values.delta_p_b < 0.0
    assert blow_values.p_m > 0.0
    assert blow_values.delta_p_b > 0.0
    assert draw_values.delta_p_d == 0.0
    assert blow_values.delta_p_d == 0.0
