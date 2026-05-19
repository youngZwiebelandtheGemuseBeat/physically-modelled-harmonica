from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from harmonica_model.params import DEFAULT_PARAMS, RenderConfig
from harmonica_model.render import render_draw_note


def test_render_smoke_produces_non_silent_audio() -> None:
    result = render_draw_note(
        DEFAULT_PARAMS,
        RenderConfig(duration_s=0.25, sample_rate_hz=8_000, max_step_s=1.0 / 4_000.0),
    )

    assert result.audio.shape == (2_000,)
    assert np.all(np.isfinite(result.audio))
    assert float(np.max(np.abs(result.audio))) > 1.0e-4
    assert float(np.sqrt(np.mean(result.audio**2))) > 1.0e-5
