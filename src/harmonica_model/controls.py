from __future__ import annotations

from math import cos, pi, sin

from .params import ModelParams


def raised_cosine_step(edge0: float, edge1: float, value: float) -> float:
    """Smooth 0..1 transition with zero slope at both endpoints."""

    if edge1 <= edge0:
        return 1.0 if value >= edge1 else 0.0
    x = min(1.0, max(0.0, (value - edge0) / (edge1 - edge0)))
    return 0.5 - 0.5 * cos(pi * x)


def breath_envelope(t_s: float, params: ModelParams) -> float:
    """Raised-cosine breath envelope used before the physical equations."""

    attack_start_s = params.pre_delay_s
    attack_end_s = attack_start_s + params.attack_s
    attack = raised_cosine_step(attack_start_s, attack_end_s, t_s)
    release = 1.0 - raised_cosine_step(
        params.release_start_s,
        params.release_start_s + params.release_s,
        t_s,
    )
    return max(0.0, min(1.0, attack * release))


def _breath_noise_multiplier(t_s: float, amount: float) -> float:
    if amount <= 0.0:
        return 1.0

    # Deterministic low-frequency breath-pressure roughness. This perturbs only
    # the mouth-pressure source and is disabled by default.
    noise = (
        0.55 * sin(2.0 * pi * 4.7 * t_s)
        + 0.30 * sin(2.0 * pi * 9.1 * t_s + 0.4)
        + 0.15 * sin(2.0 * pi * 16.3 * t_s + 1.1)
    )
    return max(0.0, 1.0 + amount * noise)


def mouth_pressure_source(t_s: float, params: ModelParams) -> float:
    """Signed mouth pressure source used before the physical equations."""

    envelope = breath_envelope(t_s, params)
    noise_multiplier = _breath_noise_multiplier(t_s, params.breath_noise_amount)
    return params.mouth_pressure_pa * envelope * noise_multiplier


def draw_mouth_pressure(t_s: float, params: ModelParams) -> float:
    """Backward-compatible alias for the signed mouth-pressure source."""

    return mouth_pressure_source(t_s, params)
