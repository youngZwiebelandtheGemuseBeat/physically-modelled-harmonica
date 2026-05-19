from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from .equations import (
    P_C,
    P_T,
    STATE_SIZE,
    V_B,
    V_D,
    V_T,
    X_B,
    X_D,
    derived_values,
    state_derivatives,
)
from .params import DEFAULT_PARAMS, ModelParams, RenderConfig


@dataclass(frozen=True)
class RenderResult:
    sample_rate_hz: int
    time_s: np.ndarray
    state: np.ndarray
    audio: np.ndarray
    p_m: np.ndarray
    area_b: np.ndarray
    area_d: np.ndarray
    q_b: np.ndarray
    q_d: np.ndarray
    force_b: np.ndarray
    force_d: np.ndarray
    dp_c: np.ndarray

    @property
    def x_b(self) -> np.ndarray:
        return self.state[X_B]

    @property
    def v_b(self) -> np.ndarray:
        return self.state[V_B]

    @property
    def x_d(self) -> np.ndarray:
        return self.state[X_D]

    @property
    def v_d(self) -> np.ndarray:
        return self.state[V_D]

    @property
    def p_c(self) -> np.ndarray:
        return self.state[P_C]

    @property
    def p_t(self) -> np.ndarray:
        return self.state[P_T]

    @property
    def v_t(self) -> np.ndarray:
        return self.state[V_T]


def _dc_block(signal: np.ndarray) -> np.ndarray:
    return signal - float(np.mean(signal))


def _normalize_audio(signal: np.ndarray, peak: float = 0.85) -> np.ndarray:
    centered = _dc_block(np.asarray(signal, dtype=float))
    max_abs = float(np.max(np.abs(centered)))
    if max_abs <= 0.0:
        return centered
    return centered * (peak / max_abs)


def render_draw_note(
    params: ModelParams = DEFAULT_PARAMS,
    config: RenderConfig = RenderConfig(),
) -> RenderResult:
    sample_count = int(round(config.duration_s * config.sample_rate_hz))
    time_s = np.arange(sample_count, dtype=float) / float(config.sample_rate_hz)
    integration_rate_hz = min(config.integration_rate_hz, config.sample_rate_hz)
    integration_count = int(round(config.duration_s * integration_rate_hz)) + 1
    integration_time_s = np.arange(integration_count, dtype=float) / float(integration_rate_hz)
    integration_time_s[-1] = config.duration_s
    initial_state = np.zeros(STATE_SIZE, dtype=float)

    solution = solve_ivp(
        fun=lambda t, y: state_derivatives(t, y, params),
        t_span=(0.0, config.duration_s),
        y0=initial_state,
        method=config.solve_method,
        t_eval=integration_time_s,
        max_step=config.max_step_s,
        rtol=config.relative_tolerance,
        atol=config.absolute_tolerance,
    )
    if not solution.success:
        raise RuntimeError(f"solve_ivp failed: {solution.message}")

    integrated_state = np.asarray(solution.y, dtype=float)
    state = np.vstack(
        [np.interp(time_s, integration_time_s, integrated_state[row]) for row in range(STATE_SIZE)]
    )
    derived = [derived_values(float(t), state[:, i], params) for i, t in enumerate(time_s)]
    raw_audio = np.array([value.audio_pressure for value in derived], dtype=float)

    return RenderResult(
        sample_rate_hz=config.sample_rate_hz,
        time_s=time_s,
        state=state,
        audio=_normalize_audio(raw_audio),
        p_m=np.array([value.p_m for value in derived], dtype=float),
        area_b=np.array([value.area_b for value in derived], dtype=float),
        area_d=np.array([value.area_d for value in derived], dtype=float),
        q_b=np.array([value.q_b for value in derived], dtype=float),
        q_d=np.array([value.q_d for value in derived], dtype=float),
        force_b=np.array([value.force_b for value in derived], dtype=float),
        force_d=np.array([value.force_d for value in derived], dtype=float),
        dp_c=np.array([value.dp_c for value in derived], dtype=float),
    )
