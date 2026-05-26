"""Offline integration pipeline for the harmonica model.

`equations.py` defines the physics. This file decides how to solve those
equations over time, interpolate the result to audio rate, and collect all
diagnostic traces needed to explain the simulation afterward.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from .audio import physical_output_signal
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
    """Complete result of one rendered note.

    The object stores both the minimal ODE state and the derived physical
    quantities that a professor or reviewer would want to inspect: pressure
    drops, flows, forces, opening areas, and chamber pressure derivative.
    """

    # Mode label used for file names and reports: "draw" or "blow".
    mode: str
    # Output sample rate for audio and all trace arrays.
    sample_rate_hz: int
    # Time axis in seconds at output sample rate.
    time_s: np.ndarray
    # Exact parameters used for this render.
    params: ModelParams
    # Solved ODE state as rows `[x_b, v_b, x_d, v_d, p_c, p_t, v_t]`.
    state: np.ndarray
    # Final normalized audio waveform derived from physical pressure/flow.
    audio: np.ndarray
    # Signed mouth pressure actually applied to the equations.
    p_m: np.ndarray
    # 0..1 breath envelope that shaped `p_m`.
    breath_envelope: np.ndarray
    # Blow-side pressure drop `p_m - p_c`.
    delta_p_b: np.ndarray
    # Draw/outlet-side pressure drop `p_c - p_out`.
    delta_p_d: np.ndarray
    # Blow reed opening area over time.
    area_b: np.ndarray
    # Draw reed opening area over time.
    area_d: np.ndarray
    # Blow-side Bernoulli flow over time.
    q_b: np.ndarray
    # Draw-side Bernoulli flow over time.
    q_d: np.ndarray
    # Pressure-proportional chamber loss flow over time.
    q_loss: np.ndarray
    # Pressure force on blow reed.
    force_b: np.ndarray
    # Pressure force on draw reed.
    force_d: np.ndarray
    # Chamber pressure derivative.
    dp_c: np.ndarray

    @property
    def x_b(self) -> np.ndarray:
        """Blow reed displacement trace in meters."""

        return self.state[X_B]

    @property
    def v_b(self) -> np.ndarray:
        """Blow reed velocity trace in meters per second."""

        return self.state[V_B]

    @property
    def x_d(self) -> np.ndarray:
        """Draw reed displacement trace in meters."""

        return self.state[X_D]

    @property
    def v_d(self) -> np.ndarray:
        """Draw reed velocity trace in meters per second."""

        return self.state[V_D]

    @property
    def p_c(self) -> np.ndarray:
        """Chamber pressure trace in pascals."""

        return self.state[P_C]

    @property
    def p_t(self) -> np.ndarray:
        """Reduced vocal-tract pressure trace in pascals."""

        return self.state[P_T]

    @property
    def v_t(self) -> np.ndarray:
        """Vocal-tract pressure velocity `p_t'` trace."""

        return self.state[V_T]


def render_note(
    mode: str,
    params: ModelParams = DEFAULT_PARAMS,
    config: RenderConfig = RenderConfig(),
) -> RenderResult:
    """Render one note by solving the coupled physical ODE.

    Workflow:
    1. create output and integration time grids,
    2. integrate `state_derivatives()` from a silent zero state,
    3. interpolate the solved state to audio sample rate,
    4. recompute diagnostic physical values at each audio sample, and
    5. build final audio from simulated pressure/flow states.
    """

    # The audio grid is the final timeline used by WAVs, CSV traces, and plots.
    sample_count = int(round(config.duration_s * config.sample_rate_hz))
    time_s = np.arange(sample_count, dtype=float) / float(config.sample_rate_hz)

    # The ODE can be solved on a lower reporting grid while `solve_ivp` still
    # takes adaptive internal steps no larger than `max_step_s`.
    integration_rate_hz = min(config.integration_rate_hz, config.sample_rate_hz)
    integration_count = int(round(config.duration_s * integration_rate_hz)) + 1
    integration_time_s = np.arange(integration_count, dtype=float) / float(integration_rate_hz)
    integration_time_s[-1] = config.duration_s
    initial_state = np.zeros(STATE_SIZE, dtype=float)

    # This is the only place the time-domain physics is integrated.
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

    # Interpolate every ODE state row onto the audio-rate timeline so all output
    # arrays line up sample-for-sample with the WAV.
    integrated_state = np.asarray(solution.y, dtype=float)
    state = np.vstack(
        [np.interp(time_s, integration_time_s, integrated_state[row]) for row in range(STATE_SIZE)]
    )

    # These derived traces make the render explainable: each CSV row can show
    # which pressures, areas, flows, and forces existed at that instant.
    derived = [derived_values(float(t), state[:, i], params) for i, t in enumerate(time_s)]
    p_m = np.array([value.p_m for value in derived], dtype=float)
    breath = np.array([value.breath_envelope for value in derived], dtype=float)
    delta_p_b = np.array([value.delta_p_b for value in derived], dtype=float)
    delta_p_d = np.array([value.delta_p_d for value in derived], dtype=float)
    area_b = np.array([value.area_b for value in derived], dtype=float)
    area_d = np.array([value.area_d for value in derived], dtype=float)
    q_b = np.array([value.q_b for value in derived], dtype=float)
    q_d = np.array([value.q_d for value in derived], dtype=float)
    q_loss = np.array([value.q_loss for value in derived], dtype=float)
    force_b = np.array([value.force_b for value in derived], dtype=float)
    force_d = np.array([value.force_d for value in derived], dtype=float)
    dp_c = np.array([value.dp_c for value in derived], dtype=float)

    # The audible signal is formed only after the physical state is solved.
    # This keeps the ODE model separate from the output/radiation approximation.
    audio = physical_output_signal(
        params=params,
        sample_rate_hz=config.sample_rate_hz,
        p_c=state[P_C],
        p_t=state[P_T],
        q_b=q_b,
        q_d=q_d,
        delta_p_b=delta_p_b,
        delta_p_d=delta_p_d,
    )

    return RenderResult(
        mode=mode,
        sample_rate_hz=config.sample_rate_hz,
        time_s=time_s,
        params=params,
        state=state,
        audio=audio,
        p_m=p_m,
        breath_envelope=breath,
        delta_p_b=delta_p_b,
        delta_p_d=delta_p_d,
        area_b=area_b,
        area_d=area_d,
        q_b=q_b,
        q_d=q_d,
        q_loss=q_loss,
        force_b=force_b,
        force_d=force_d,
        dp_c=dp_c,
    )


def render_draw_note(
    params: ModelParams = DEFAULT_PARAMS,
    config: RenderConfig = RenderConfig(),
) -> RenderResult:
    """Convenience wrapper for the default draw-note render path."""

    return render_note("draw", params, config)
