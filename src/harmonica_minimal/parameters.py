"""Physical parameters and numerical settings for the minimal model."""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import pi


@dataclass(frozen=True)
class ReedParameters:
    """One lumped reed oscillator and its slot-opening constants."""

    mass_kg: float
    damping_kg_s: float
    stiffness_n_m: float
    pressure_area_m2: float
    slot_width_m: float
    rest_gap_m: float
    gap_displacement_scale: float
    discharge_coefficient: float
    motion_area_m2: float


@dataclass(frozen=True)
class ModelParameters:
    """Complete parameter set used by the proposal equations."""

    rho_air_kg_m3: float
    speed_of_sound_m_s: float
    chamber_volume_m3: float
    p_out_pa: float
    blow_reed: ReedParameters
    draw_reed: ReedParameters
    mouth_pressure_pa: float
    attack_s: float
    release_s: float
    vocal_tract_frequency_hz: float
    vocal_tract_q: float
    vocal_tract_impedance_pa_s_m3: float
    vocal_tract_feedback_gain: float
    motion_flow_enabled: bool

    @property
    def vocal_tract_omega_rad_s(self) -> float:
        return 2.0 * pi * self.vocal_tract_frequency_hz


@dataclass(frozen=True)
class SimulationConfig:
    """Numerical integration and export settings."""

    duration_s: float = 2.0
    sample_rate_hz: int = 22_050
    max_step_s: float = 1.0 / 12_000.0
    relative_tolerance: float = 2.0e-5
    absolute_tolerance: float = 1.0e-8
    solve_method: str = "DOP853"


def reed_from_frequency(
    *,
    frequency_hz: float,
    mass_kg: float,
    quality_factor: float,
    pressure_area_m2: float,
    slot_width_m: float,
    rest_gap_m: float,
    gap_displacement_scale: float,
    discharge_coefficient: float,
    motion_area_m2: float,
) -> ReedParameters:
    """Derive oscillator stiffness and damping from frequency and Q."""

    omega = 2.0 * pi * frequency_hz
    return ReedParameters(
        mass_kg=mass_kg,
        damping_kg_s=mass_kg * omega / quality_factor,
        stiffness_n_m=mass_kg * omega * omega,
        pressure_area_m2=pressure_area_m2,
        slot_width_m=slot_width_m,
        rest_gap_m=rest_gap_m,
        gap_displacement_scale=gap_displacement_scale,
        discharge_coefficient=discharge_coefficient,
        motion_area_m2=motion_area_m2,
    )


DRAW_PARAMETERS = ModelParameters(
    rho_air_kg_m3=1.204,
    speed_of_sound_m_s=343.0,
    chamber_volume_m3=8.0e-7,
    p_out_pa=0.0,
    blow_reed=reed_from_frequency(
        frequency_hz=392.0,
        mass_kg=8.0e-6,
        quality_factor=20.0,
        pressure_area_m2=1.25e-6,
        slot_width_m=2.2e-3,
        rest_gap_m=22.0e-6,
        gap_displacement_scale=0.20,
        discharge_coefficient=0.62,
        motion_area_m2=0.0,
    ),
    draw_reed=reed_from_frequency(
        frequency_hz=440.0,
        mass_kg=8.5e-6,
        quality_factor=38.0,
        pressure_area_m2=1.55e-6,
        slot_width_m=2.3e-3,
        rest_gap_m=2.0e-6,
        gap_displacement_scale=-3.0,
        discharge_coefficient=0.68,
        motion_area_m2=1.1e-6,
    ),
    mouth_pressure_pa=-850.0,
    attack_s=0.28,
    release_s=0.06,
    vocal_tract_frequency_hz=650.0,
    vocal_tract_q=5.0,
    vocal_tract_impedance_pa_s_m3=2.0e8,
    vocal_tract_feedback_gain=0.05,
    motion_flow_enabled=False,
)


BLOW_PARAMETERS = replace(
    DRAW_PARAMETERS,
    blow_reed=reed_from_frequency(
        frequency_hz=392.0,
        mass_kg=8.0e-6,
        quality_factor=38.0,
        pressure_area_m2=1.55e-6,
        slot_width_m=2.2e-3,
        rest_gap_m=2.0e-6,
        gap_displacement_scale=3.0,
        discharge_coefficient=0.68,
        motion_area_m2=1.1e-6,
    ),
    draw_reed=reed_from_frequency(
        frequency_hz=440.0,
        mass_kg=8.5e-6,
        quality_factor=20.0,
        pressure_area_m2=1.20e-6,
        slot_width_m=2.3e-3,
        rest_gap_m=22.0e-6,
        gap_displacement_scale=0.20,
        discharge_coefficient=0.62,
        motion_area_m2=0.0,
    ),
    mouth_pressure_pa=800.0,
    vocal_tract_frequency_hz=780.0,
)


def parameters_for_mode(mode: str) -> ModelParameters:
    if mode == "draw":
        return DRAW_PARAMETERS
    if mode == "blow":
        return BLOW_PARAMETERS
    raise ValueError(f"unknown mode: {mode}")
