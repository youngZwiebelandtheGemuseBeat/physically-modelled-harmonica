"""Offline numerical integration for the minimal harmonica model."""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
from scipy.integrate import solve_ivp

from .equations import P_C, P_T, STATE_SIZE, V_B, V_D, V_T, X_B, X_D, derived_state, state_derivative
from .parameters import ModelParameters, SimulationConfig, parameters_for_mode


@dataclass(frozen=True)
class SimulationResult:
    mode: str
    sample_rate_hz: int
    time_s: np.ndarray
    params: ModelParameters
    state: np.ndarray
    p_m_static: np.ndarray
    p_m_effective: np.ndarray
    gap_b: np.ndarray
    gap_d: np.ndarray
    delta_p_b: np.ndarray
    delta_p_d: np.ndarray
    q_b_gap: np.ndarray
    q_b_motion: np.ndarray
    q_b_total: np.ndarray
    q_d_gap: np.ndarray
    q_d_motion: np.ndarray
    q_d_total: np.ndarray
    force_b: np.ndarray
    force_d: np.ndarray

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


def simulate_note(
    mode: str,
    config: SimulationConfig = SimulationConfig(),
    pressure_pa: float | None = None,
    attack_s: float | None = None,
    motion_flow_enabled: bool | None = None,
    vocal_tract_feedback_gain: float | None = None,
) -> SimulationResult:
    """Solve the proposal ODE for one blow or draw note."""

    params = parameters_for_mode(mode)
    """Check if any parameters have been set at call"""
    if pressure_pa is not None:
        sign = -1.0 if mode == "draw" else 1.0
        params = replace(params, mouth_pressure_pa=sign * abs(pressure_pa))
    if attack_s is not None:
        params = replace(params, attack_s=attack_s)
    if motion_flow_enabled is not None:
        params = replace(params, motion_flow_enabled=motion_flow_enabled)
    if vocal_tract_feedback_gain is not None:
        params = replace(params, vocal_tract_feedback_gain=vocal_tract_feedback_gain)

    sample_count = int(round(config.duration_s * config.sample_rate_hz))
    time_s = np.arange(sample_count, dtype=float) / float(config.sample_rate_hz)
    initial_state = np.zeros(STATE_SIZE, dtype=float)

    solution = solve_ivp(
        fun=lambda t, y: state_derivative(t, y, config.duration_s, params), # loops
        t_span=(0.0, config.duration_s),
        y0=initial_state,
        t_eval=time_s,
        method=config.solve_method,
        max_step=config.max_step_s,
        rtol=config.relative_tolerance,
        atol=config.absolute_tolerance,
    )
    if not solution.success:
        raise RuntimeError(f"ODE solver failed: {solution.message}")

    state = np.asarray(solution.y, dtype=float)
    derived = [derived_state(float(t), config.duration_s, state[:, i], params) for i, t in enumerate(time_s)]

    return SimulationResult(
        mode=mode,
        sample_rate_hz=config.sample_rate_hz,
        time_s=time_s,
        params=params,
        state=state,
        p_m_static=np.array([value.p_m_static for value in derived], dtype=float),
        p_m_effective=np.array([value.p_m_effective for value in derived], dtype=float),
        gap_b=np.array([value.gap_b for value in derived], dtype=float),
        gap_d=np.array([value.gap_d for value in derived], dtype=float),
        delta_p_b=np.array([value.delta_p_b for value in derived], dtype=float),
        delta_p_d=np.array([value.delta_p_d for value in derived], dtype=float),
        q_b_gap=np.array([value.q_b_gap for value in derived], dtype=float),
        q_b_motion=np.array([value.q_b_motion for value in derived], dtype=float),
        q_b_total=np.array([value.q_b_total for value in derived], dtype=float),
        q_d_gap=np.array([value.q_d_gap for value in derived], dtype=float),
        q_d_motion=np.array([value.q_d_motion for value in derived], dtype=float),
        q_d_total=np.array([value.q_d_total for value in derived], dtype=float),
        force_b=np.array([value.force_b for value in derived], dtype=float),
        force_d=np.array([value.force_d for value in derived], dtype=float),
    )
