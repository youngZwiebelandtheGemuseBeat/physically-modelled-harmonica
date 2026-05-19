from __future__ import annotations

from .params import ModelParams


def smoothstep(edge0: float, edge1: float, value: float) -> float:
    if edge1 <= edge0:
        return 1.0 if value >= edge1 else 0.0
    x = min(1.0, max(0.0, (value - edge0) / (edge1 - edge0)))
    return x * x * (3.0 - 2.0 * x)


def draw_mouth_pressure(t_s: float, params: ModelParams) -> float:
    """Negative mouth pressure envelope for one offline draw note."""

    attack = smoothstep(0.0, params.attack_s, t_s)
    release = 1.0 - smoothstep(
        params.release_start_s,
        params.release_start_s + params.release_s,
        t_s,
    )
    return params.mouth_pressure_pa * attack * release
