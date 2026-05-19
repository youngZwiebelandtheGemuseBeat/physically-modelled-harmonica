from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from harmonica_model.equations import chamber_pressure_derivative
from harmonica_model.params import DEFAULT_PARAMS


def test_chamber_pressure_derivative_signs() -> None:
    params = DEFAULT_PARAMS

    assert chamber_pressure_derivative(1.0e-7, 0.0, params) > 0.0
    assert chamber_pressure_derivative(0.0, 1.0e-7, params) < 0.0
    assert chamber_pressure_derivative(-1.0e-7, -2.0e-7, params) > 0.0
