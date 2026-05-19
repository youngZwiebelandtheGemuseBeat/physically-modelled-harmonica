from __future__ import annotations

from dataclasses import dataclass
from math import pi


@dataclass(frozen=True)
class ReedParams:
    """Lumped mass-spring-damper reed parameters."""

    mass_kg: float
    damping_kg_s: float
    stiffness_n_m: float
    pressure_area_m2: float
    slot_width_m: float
    rest_opening_m: float
    closing_displacement_m: float
    displacement_to_gap: float
    discharge_coefficient: float


@dataclass(frozen=True)
class ModelParams:
    """Physical and numerical parameters for one harmonica channel."""

    rho_air_kg_m3: float
    speed_of_sound_m_s: float
    chamber_volume_m3: float
    p_out_pa: float
    blow_reed: ReedParams
    draw_reed: ReedParams
    vocal_tract_frequency_hz: float
    vocal_tract_q: float
    vocal_tract_impedance_pa_s_m3: float
    mouth_pressure_pa: float
    attack_s: float
    release_s: float
    release_start_s: float
    acoustic_flow_gain_pa_s_m3: float
    pressure_output_gain: float

    @property
    def vocal_tract_omega_rad_s(self) -> float:
        return 2.0 * pi * self.vocal_tract_frequency_hz


@dataclass(frozen=True)
class RenderConfig:
    duration_s: float = 2.0
    sample_rate_hz: int = 44_100
    integration_rate_hz: int = 12_000
    max_step_s: float = 1.0 / 6_000.0
    relative_tolerance: float = 1.0e-4
    absolute_tolerance: float = 1.0e-7
    solve_method: str = "DOP853"


def _reed_from_frequency(
    *,
    frequency_hz: float,
    mass_kg: float,
    quality_factor: float,
    pressure_area_m2: float,
    slot_width_m: float,
    rest_opening_m: float,
    closing_displacement_m: float,
    displacement_to_gap: float,
    discharge_coefficient: float,
) -> ReedParams:
    omega = 2.0 * pi * frequency_hz
    stiffness = mass_kg * omega * omega
    damping = mass_kg * omega / quality_factor
    return ReedParams(
        mass_kg=mass_kg,
        damping_kg_s=damping,
        stiffness_n_m=stiffness,
        pressure_area_m2=pressure_area_m2,
        slot_width_m=slot_width_m,
        rest_opening_m=rest_opening_m,
        closing_displacement_m=closing_displacement_m,
        displacement_to_gap=displacement_to_gap,
        discharge_coefficient=discharge_coefficient,
    )


DEFAULT_PARAMS = ModelParams(
    rho_air_kg_m3=1.204,
    speed_of_sound_m_s=343.0,
    chamber_volume_m3=1.2e-6,
    p_out_pa=0.0,
    blow_reed=_reed_from_frequency(
        frequency_hz=392.0,
        mass_kg=8.0e-6,
        quality_factor=18.0,
        pressure_area_m2=1.3e-6,
        slot_width_m=2.2e-3,
        rest_opening_m=30.0e-6,
        closing_displacement_m=-8.0e-6,
        displacement_to_gap=0.1,
        discharge_coefficient=0.62,
    ),
    draw_reed=_reed_from_frequency(
        frequency_hz=440.0,
        mass_kg=8.5e-6,
        quality_factor=30.0,
        pressure_area_m2=1.5e-6,
        slot_width_m=2.3e-3,
        rest_opening_m=8.0e-6,
        closing_displacement_m=8.0e-6,
        displacement_to_gap=-1.0,
        discharge_coefficient=0.68,
    ),
    vocal_tract_frequency_hz=520.0,
    vocal_tract_q=4.0,
    vocal_tract_impedance_pa_s_m3=1.8e8,
    mouth_pressure_pa=-780.0,
    attack_s=0.055,
    release_s=0.12,
    release_start_s=2.10,
    acoustic_flow_gain_pa_s_m3=2.4e7,
    pressure_output_gain=0.08,
)
