from __future__ import annotations

import sys
from pathlib import Path


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
