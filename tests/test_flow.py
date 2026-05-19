from __future__ import annotations

from math import isclose
import sys
from pathlib import Path
from dataclasses import replace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from harmonica_model.equations import bernoulli_flow, reed_opening_area
from harmonica_model.params import DEFAULT_PARAMS


def test_bernoulli_flow_sign_convention() -> None:
    params = DEFAULT_PARAMS
    area = 1.0e-8

    assert bernoulli_flow(100.0, area, params, 0.7) > 0.0
    assert bernoulli_flow(-100.0, area, params, 0.7) < 0.0
    assert bernoulli_flow(0.0, area, params, 0.7) == 0.0


def test_flow_is_zero_when_opening_is_closed() -> None:
    params = DEFAULT_PARAMS
    area = reed_opening_area(
        params.draw_reed.closing_displacement_m,
        params.draw_reed,
    )

    assert area == 0.0
    assert bernoulli_flow(-500.0, area, params, params.draw_reed.discharge_coefficient) == 0.0


def test_opening_area_uses_rest_gap_sigma_and_minimum_area() -> None:
    params = DEFAULT_PARAMS
    reed = replace(
        params.draw_reed,
        rest_opening_m=2.0e-6,
        displacement_to_gap=-3.0,
        slot_width_m=2.0e-3,
        min_opening_area_m2=1.0e-12,
    )

    open_area = reed_opening_area(-1.0e-6, reed)
    closed_area = reed_opening_area(2.0e-6, reed)

    assert isclose(open_area, 2.0e-3 * 5.0e-6)
    assert closed_area == 1.0e-12


def test_bernoulli_flow_uses_square_root_pressure_law() -> None:
    params = DEFAULT_PARAMS
    area = 1.0e-8

    low_pressure_flow = bernoulli_flow(100.0, area, params, 0.7)
    high_pressure_flow = bernoulli_flow(400.0, area, params, 0.7)

    assert isclose(high_pressure_flow / low_pressure_flow, 2.0)
