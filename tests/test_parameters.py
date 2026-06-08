from __future__ import annotations

from math import pi, sqrt
from pathlib import Path
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from harmonica_minimal.parameters import (
    MILLOT_BLOW_REED,
    MILLOT_CHANNEL4_4B,
    MILLOT_DRAW_REED,
    ParameterCategory,
)


def test_millot_si_unit_conversions() -> None:
    assert MILLOT_BLOW_REED.mass_kg == pytest.approx(11.98e-6)
    assert MILLOT_BLOW_REED.damping_kg_s == pytest.approx(172e-6)
    assert MILLOT_BLOW_REED.through_slot_rest_offset_m == pytest.approx(-1298e-6)
    assert MILLOT_DRAW_REED.mass_kg == pytest.approx(6.07e-6)
    assert MILLOT_DRAW_REED.damping_kg_s == pytest.approx(183e-6)
    assert MILLOT_DRAW_REED.through_slot_rest_offset_m == pytest.approx(286.5e-6)


def test_millot_oscillator_parameters_are_consistent() -> None:
    blow_frequency = sqrt(MILLOT_BLOW_REED.stiffness_n_m / MILLOT_BLOW_REED.mass_kg) / (2.0 * pi)
    draw_frequency = sqrt(MILLOT_DRAW_REED.stiffness_n_m / MILLOT_DRAW_REED.mass_kg) / (2.0 * pi)
    blow_q = sqrt(MILLOT_BLOW_REED.stiffness_n_m * MILLOT_BLOW_REED.mass_kg) / MILLOT_BLOW_REED.damping_kg_s
    draw_q = sqrt(MILLOT_DRAW_REED.stiffness_n_m * MILLOT_DRAW_REED.mass_kg) / MILLOT_DRAW_REED.damping_kg_s

    assert blow_frequency == pytest.approx(405.0, rel=1e-3)
    assert draw_frequency == pytest.approx(455.0, rel=1e-3)
    assert blow_q == pytest.approx(177.0, rel=2e-3)
    assert draw_q == pytest.approx(95.0, rel=2e-3)


def test_millot_preset_has_traceable_source_and_assumption_values() -> None:
    categories = {value.category for value in MILLOT_CHANNEL4_4B.provenance}
    names = {value.name for value in MILLOT_CHANNEL4_4B.provenance}

    assert ParameterCategory.SOURCE_DERIVED in categories
    assert ParameterCategory.PHYSICALLY_ESTIMATED in categories
    assert ParameterCategory.MODEL_ASSUMPTION in categories
    assert "blow_reed.stiffness_n_m" in names
    assert "draw_reed.through_slot_positive_gain" in names
