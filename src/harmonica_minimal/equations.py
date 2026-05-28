"""Explicit equations for the seven-state harmonica channel model."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

import numpy as np

from .parameters import ModelParameters, ReedParameters


X_B = 0
V_B = 1
X_D = 2
V_D = 3
P_C = 4
P_T = 5
V_T = 6
STATE_SIZE = 7


@dataclass(frozen=True)
class DerivedState:
    p_m_static: float
    p_m_effective: float
    gap_b: float
    gap_d: float
    area_b: float
    area_d: float
    delta_p_b: float
    delta_p_d: float
    q_b_gap: float
    q_b_motion: float
    q_b_total: float
    q_d_gap: float
    q_d_motion: float
    q_d_total: float
    force_b: float
    force_d: float
    dp_c: float


def smooth_breath_pressure(t_s: float, duration_s: float, params: ModelParameters) -> float:
    """Simple player pressure p_m(t) with smooth attack and release."""

    attack = max(params.attack_s, 1.0e-9)
    release = max(params.release_s, 1.0e-9)
    if t_s < attack:
        u = max(0.0, min(1.0, t_s / attack))
        envelope = u ** 2 * (3.0 - 2.0 * u)
    elif t_s > duration_s - release:
        u = max(0.0, min(1.0, (duration_s - t_s) / release))
        envelope = u ** 2 * (3.0 - 2.0 * u)
    else:
        envelope = 1.0
    return params.mouth_pressure_pa * envelope


def effective_mouth_pressure(p_m_static_pa: float, p_t_pa: float, params: ModelParameters) -> float:
    """Mouth-side pressure after reduced vocal-tract loading."""

    return p_m_static_pa - params.vocal_tract_feedback_gain * p_t_pa


def blow_pressure_drop(p_m_effective_pa: float, p_c_pa: float) -> float:
    """Blow-side pressure drop using the loaded mouth-side pressure."""

    return p_m_effective_pa - p_c_pa


def reed_gap(displacement_m: float, reed: ReedParameters) -> float:
    """Opening height h_i0 + alpha_i x_i."""

    return reed.rest_gap_m + reed.gap_displacement_scale * displacement_m


def opening_area(displacement_m: float, reed: ReedParameters) -> float:
    """Opening area A_i(x_i) = W_i max(0, h_i0 + alpha_i x_i)."""

    return reed.slot_width_m * max(0.0, reed_gap(displacement_m, reed))


def bernoulli_gap_flow(
    delta_p_pa: float,
    area_m2: float,
    discharge_coefficient: float,
    rho_air_kg_m3: float,
) -> float:
    """Gap flow Q_gap,i = C_i A_i sign(Delta p_i) sqrt(2 abs(Delta p_i) / rho)."""

    if area_m2 <= 0.0 or delta_p_pa == 0.0:
        return 0.0
    sign = 1.0 if delta_p_pa > 0.0 else -1.0
    return discharge_coefficient * area_m2 * sign * sqrt(2.0 * abs(delta_p_pa) / rho_air_kg_m3)


def motion_flow(velocity_m_s: float, reed: ReedParameters, enabled: bool) -> float:
    """Optional moving-reed flow Q_motion,i = S_motion,i hdot_i."""

    if not enabled:
        return 0.0
    hdot_m_s = reed.gap_displacement_scale * velocity_m_s
    return reed.motion_area_m2 * hdot_m_s


def total_reed_flow(q_gap_m3_s: float, q_motion_m3_s: float) -> float:
    """Total reed flow Q_i = Q_gap,i + Q_motion,i."""

    return q_gap_m3_s + q_motion_m3_s


def blow_reed_force(p_m_effective_pa: float, p_c_pa: float, params: ModelParameters) -> float:
    """Blow reed force F_b = S_b (p_m_effective - p_c)."""

    return params.blow_reed.pressure_area_m2 * blow_pressure_drop(p_m_effective_pa, p_c_pa)


def draw_reed_force(p_c_pa: float, params: ModelParameters) -> float:
    """Draw reed force F_d = S_d (p_c - p_out)."""

    return params.draw_reed.pressure_area_m2 * (p_c_pa - params.p_out_pa)


def chamber_pressure_derivative(q_b_total_m3_s: float, q_d_total_m3_s: float, params: ModelParameters) -> float:
    """Chamber equation p_c' = rho c^2 / V_c (Q_b - Q_d)."""

    return (
        params.rho_air_kg_m3
        * params.speed_of_sound_m_s ** 2
        / params.chamber_volume_m3
        * (q_b_total_m3_s - q_d_total_m3_s)
    )


def derived_state(t_s: float, duration_s: float, state: np.ndarray, params: ModelParameters) -> DerivedState:
    """Compute pressures, gaps, flows, and forces from one ODE state."""

    x_b, v_b, x_d, v_d, p_c, p_t, _v_t = state
    p_m_static = smooth_breath_pressure(t_s, duration_s, params)
    p_m_effective = effective_mouth_pressure(p_m_static, float(p_t), params)

    gap_b = reed_gap(float(x_b), params.blow_reed)
    gap_d = reed_gap(float(x_d), params.draw_reed)
    area_b = opening_area(float(x_b), params.blow_reed)
    area_d = opening_area(float(x_d), params.draw_reed)

    delta_p_b = blow_pressure_drop(p_m_effective, float(p_c))
    delta_p_d = float(p_c) - params.p_out_pa

    q_b_gap = bernoulli_gap_flow(
        delta_p_b,
        area_b,
        params.blow_reed.discharge_coefficient,
        params.rho_air_kg_m3,
    )
    q_d_gap = bernoulli_gap_flow(
        delta_p_d,
        area_d,
        params.draw_reed.discharge_coefficient,
        params.rho_air_kg_m3,
    )
    q_b_motion = motion_flow(float(v_b), params.blow_reed, params.motion_flow_enabled) # currently neglected (default: 0)
    q_d_motion = motion_flow(float(v_d), params.draw_reed, params.motion_flow_enabled) # currently neglected (default: 0)
    q_b_total = total_reed_flow(q_b_gap, q_b_motion)
    q_d_total = total_reed_flow(q_d_gap, q_d_motion)

    force_b = blow_reed_force(p_m_effective, float(p_c), params)
    force_d = draw_reed_force(float(p_c), params)
    dp_c = chamber_pressure_derivative(q_b_total, q_d_total, params)

    return DerivedState(
        p_m_static=p_m_static,
        p_m_effective=p_m_effective,
        gap_b=gap_b,
        gap_d=gap_d,
        area_b=area_b,
        area_d=area_d,
        delta_p_b=delta_p_b,
        delta_p_d=delta_p_d,
        q_b_gap=q_b_gap,
        q_b_motion=q_b_motion,
        q_b_total=q_b_total,
        q_d_gap=q_d_gap,
        q_d_motion=q_d_motion,
        q_d_total=q_d_total,
        force_b=force_b,
        force_d=force_d,
        dp_c=dp_c,
    )


def state_derivative(t_s: float, state: np.ndarray, duration_s: float, params: ModelParameters) -> np.ndarray:
    """ODE right-hand side for [x_b, v_b, x_d, v_d, p_c, p_t, v_t]."""

    x_b, v_b, x_d, v_d, _p_c, _p_t, v_t = state
    values = derived_state(t_s, duration_s, state, params)

    dx_b = v_b
    dv_b = (
        values.force_b
        - params.blow_reed.damping_kg_s * v_b
        - params.blow_reed.stiffness_n_m * x_b
    ) / params.blow_reed.mass_kg

    dx_d = v_d
    dv_d = (
        values.force_d
        - params.draw_reed.damping_kg_s * v_d
        - params.draw_reed.stiffness_n_m * x_d
    ) / params.draw_reed.mass_kg

    omega_t = params.vocal_tract_omega_rad_s
    dp_t = v_t
    dv_t = (
        omega_t ** 2 * params.vocal_tract_impedance_pa_s_m3 * (values.q_b_total - values.q_d_total)
        - (omega_t / params.vocal_tract_q) * v_t
        - omega_t ** 2 * state[P_T]
    )

    return np.array([dx_b, dv_b, dx_d, dv_d, values.dp_c, dp_t, dv_t], dtype=float)
