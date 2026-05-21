from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

import numpy as np

from .controls import breath_envelope, mouth_pressure_source
from .params import ModelParams, ReedParams


X_B = 0
V_B = 1
X_D = 2
V_D = 3
P_C = 4
P_T = 5
V_T = 6
STATE_SIZE = 7


@dataclass(frozen=True)
class DerivedValues:
    p_m: float
    breath_envelope: float
    delta_p_b: float
    delta_p_d: float
    area_b: float
    area_d: float
    q_b: float
    q_d: float
    q_loss: float
    force_b: float
    force_d: float
    dp_c: float
    audio_pressure: float


def reed_opening_area(displacement_m: float, reed: ReedParams) -> float:
    """A_i = max(A_min, W_i * max(0, h_i0 + sigma_i x_i))."""

    gap_m = reed_gap(displacement_m, reed)
    geometric_area_m2 = reed.slot_width_m * max(0.0, gap_m)
    return max(reed.min_opening_area_m2, geometric_area_m2)


def reed_gap(displacement_m: float, reed: ReedParams) -> float:
    """Physical reed-slot gap h_i0 + sigma_i x_i."""

    return reed.rest_opening_m + reed.displacement_to_gap * displacement_m


def reed_closure_damping(gap_m: float, reed: ReedParams) -> float:
    """Extra damping used only as a smooth reed-slot closure approximation."""

    if reed.closure_damping_gap_m <= 0.0 or reed.closure_damping_kg_s <= 0.0:
        return 0.0
    closure = 1.0 - np.clip(gap_m / reed.closure_damping_gap_m, 0.0, 1.0)
    smooth_closure = closure * closure * (3.0 - 2.0 * closure)
    return reed.closure_damping_kg_s * float(smooth_closure)


def bernoulli_flow(delta_p_pa: float, area_m2: float, params: ModelParams, discharge_coefficient: float) -> float:
    """C A sgn(delta_p) sqrt(2 |delta_p| / rho)."""

    if area_m2 <= 0.0 or delta_p_pa == 0.0:
        return 0.0
    sign = 1.0 if delta_p_pa > 0.0 else -1.0
    speed_m_s = sqrt(2.0 * abs(delta_p_pa) / params.rho_air_kg_m3)
    return discharge_coefficient * area_m2 * sign * speed_m_s


def blow_reed_force(p_m_pa: float, p_c_pa: float, params: ModelParams) -> float:
    """F_b = S_b (p_m - p_c)."""

    return params.blow_reed.pressure_area_m2 * (p_m_pa - p_c_pa)


def draw_reed_force(p_c_pa: float, params: ModelParams) -> float:
    """F_d = S_d (p_c - p_out)."""

    return params.draw_reed.pressure_area_m2 * (p_c_pa - params.p_out_pa)


def chamber_loss_flow(p_c_pa: float, params: ModelParams) -> float:
    """Small pressure-proportional acoustic loss flow from the chamber."""

    return params.chamber_loss_conductance_m3_s_pa * p_c_pa


def chamber_pressure_derivative(
    q_b_m3_s: float,
    q_d_m3_s: float,
    params: ModelParams,
    p_c_pa: float = 0.0,
) -> float:
    """p_c' = rho c^2 / V_c * (Q_b - Q_d - Q_loss).

    With zero chamber loss this is exactly the proposal equation. The default
    presets use a small pressure-proportional loss so chamber pressure energy
    can decay physically during release instead of ringing as an ideal sealed
    compliance.
    """

    stiffness = params.rho_air_kg_m3 * params.speed_of_sound_m_s**2 / params.chamber_volume_m3
    return stiffness * (q_b_m3_s - q_d_m3_s - chamber_loss_flow(p_c_pa, params))


def state_derivatives(t_s: float, state: np.ndarray, params: ModelParams) -> np.ndarray:
    x_b, v_b, x_d, v_d, p_c, p_t, v_t = state

    # This is the player's signed breath pressure before any acoustic state is
    # computed. It shapes the physical drive terms below; the rendered audio is
    # not faded afterward to fake an attack.
    p_m = mouth_pressure_source(t_s, params)

    area_b = reed_opening_area(x_b, params.blow_reed)
    area_d = reed_opening_area(x_d, params.draw_reed)
    gap_b = reed_gap(x_b, params.blow_reed)
    gap_d = reed_gap(x_d, params.draw_reed)
    damping_b = params.blow_reed.damping_kg_s + reed_closure_damping(gap_b, params.blow_reed)
    damping_d = params.draw_reed.damping_kg_s + reed_closure_damping(gap_d, params.draw_reed)

    force_b = blow_reed_force(p_m, p_c, params)
    force_d = draw_reed_force(p_c, params)

    # Keep the two pressure drops explicit because this is where blow/draw
    # direction enters the proposal equations. Draw uses negative p_m; blow
    # uses positive p_m. The signs here also determine the Bernoulli flow signs.
    delta_p_b = p_m - p_c
    delta_p_d = p_c - params.p_out_pa

    q_b = bernoulli_flow(
        delta_p_b,
        area_b,
        params,
        params.blow_reed.discharge_coefficient,
    )
    q_d = bernoulli_flow(
        delta_p_d,
        area_d,
        params,
        params.draw_reed.discharge_coefficient,
    )

    dx_b = v_b
    dv_b = (
        force_b
        - damping_b * v_b
        - params.blow_reed.stiffness_n_m * x_b
    ) / params.blow_reed.mass_kg
    dx_d = v_d
    dv_d = (
        force_d
        - damping_d * v_d
        - params.draw_reed.stiffness_n_m * x_d
    ) / params.draw_reed.mass_kg
    dp_c = chamber_pressure_derivative(q_b, q_d, params, p_c)

    omega_t = params.vocal_tract_omega_rad_s

    # The tract is a reduced acoustic load driven by net simulated flow. It is
    # not an independent oscillator layered onto the audio.
    flow_drive = q_b - q_d
    dp_t = v_t
    dv_t = (
        omega_t * omega_t * params.vocal_tract_impedance_pa_s_m3 * flow_drive
        - (omega_t / params.vocal_tract_q) * v_t
        - omega_t * omega_t * p_t
    )

    return np.array([dx_b, dv_b, dx_d, dv_d, dp_c, dp_t, dv_t], dtype=float)


def derived_values(t_s: float, state: np.ndarray, params: ModelParams) -> DerivedValues:
    x_b, _, x_d, _, p_c, p_t, _ = state
    p_m = mouth_pressure_source(t_s, params)
    envelope = breath_envelope(t_s, params)
    area_b = reed_opening_area(x_b, params.blow_reed)
    area_d = reed_opening_area(x_d, params.draw_reed)
    force_b = blow_reed_force(p_m, p_c, params)
    force_d = draw_reed_force(p_c, params)
    delta_p_b = p_m - p_c
    delta_p_d = p_c - params.p_out_pa
    q_b = bernoulli_flow(
        delta_p_b,
        area_b,
        params,
        params.blow_reed.discharge_coefficient,
    )
    q_d = bernoulli_flow(
        delta_p_d,
        area_d,
        params,
        params.draw_reed.discharge_coefficient,
    )
    q_loss = chamber_loss_flow(p_c, params)
    dp_c = chamber_pressure_derivative(q_b, q_d, params, p_c)
    audio_pressure = (
        params.chamber_pressure_output_gain * p_c
        + params.pressure_output_gain * p_t
        + params.acoustic_flow_gain_pa_s_m3 * (q_b - q_d - q_loss)
        + params.draw_flow_output_gain_pa_s_m3 * q_d
        + params.blow_flow_output_gain_pa_s_m3 * q_b
    )
    return DerivedValues(
        p_m=p_m,
        breath_envelope=envelope,
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
        audio_pressure=audio_pressure,
    )
