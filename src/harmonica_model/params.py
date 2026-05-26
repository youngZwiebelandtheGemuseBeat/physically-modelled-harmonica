"""Physical constants, reed presets, and numerical solver settings.

This file is the parameter sheet for the model, it only names the physical
values that the equations use.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi


@dataclass(frozen=True)
class ReedParams:
    """All physical constants for one reed and its slot.

    Each reed is represented as one lumped mass-spring-damper oscillator, plus
    a simple geometric slot-opening law for Bernoulli flow.
    """

    # Moving reed mass in kilograms.
    mass_kg: float
    # Viscous/mechanical damping coefficient `r_i` in the reed equation.
    damping_kg_s: float
    # Spring stiffness `k_i`; together with mass it sets the natural frequency.
    stiffness_n_m: float
    # Effective area that converts pressure difference into force on the reed.
    pressure_area_m2: float
    # Slot width used to turn a gap height into an opening area.
    slot_width_m: float
    # Reed-slot gap when the reed displacement is zero.
    rest_opening_m: float
    # Displacement where the simple gap law predicts geometric closure.
    closing_displacement_m: float
    # Sign/scale from reed displacement to slot gap: `gap = h0 + sigma*x`.
    displacement_to_gap: float
    # Optional minimum opening area; zero means a closed slot has zero flow.
    min_opening_area_m2: float
    # Gap range over which the near-closure damping approximation is active.
    closure_damping_gap_m: float
    # Extra damping amount at full near-closure.
    closure_damping_kg_s: float
    # Bernoulli discharge coefficient accounting for non-ideal slot flow.
    discharge_coefficient: float


@dataclass(frozen=True)
class ModelParams:
    """Complete parameter set for one rendered harmonica channel.

    These values control the air, chamber, both reeds, breath source, vocal
    tract load, and output/radiation approximation. Draw and blow presets use
    the same fields, but with different signed pressure and reed settings.
    """

    # Air density used by Bernoulli flow.
    rho_air_kg_m3: float
    # Speed of sound used by the chamber-compliance pressure equation.
    speed_of_sound_m_s: float
    # Effective chamber volume; smaller volume gives stronger pressure feedback.
    chamber_volume_m3: float
    # Outside/reference pressure, kept at 0 Pa gauge pressure.
    p_out_pa: float
    # Blow-side reed and slot parameters.
    blow_reed: ReedParams
    # Draw-side reed and slot parameters.
    draw_reed: ReedParams
    # Center frequency of the reduced vocal-tract acoustic load.
    vocal_tract_frequency_hz: float
    # Quality factor of the tract resonator; higher means narrower resonance.
    vocal_tract_q: float
    # Coupling strength from net flow into tract pressure.
    vocal_tract_impedance_pa_s_m3: float
    # Signed pressure supplied by the player: positive blow, negative draw.
    mouth_pressure_pa: float
    # Quiet time before the breath envelope starts.
    pre_delay_s: float
    # Time for the breath pressure to rise smoothly to full strength.
    attack_s: float
    # Time for the breath pressure to fall smoothly at note end.
    release_s: float
    # Time at which the pressure release starts.
    release_start_s: float
    # Optional deterministic mouth-pressure roughness; default is off.
    breath_noise_amount: float
    # Output gain for net flow when using mixed/flow radiation.
    acoustic_flow_gain_pa_s_m3: float
    # Output gain for vocal-tract pressure.
    pressure_output_gain: float
    # Output gain for chamber pressure.
    chamber_pressure_output_gain: float
    # Output gain for draw-side flow.
    draw_flow_output_gain_pa_s_m3: float
    # Output gain for blow-side flow.
    blow_flow_output_gain_pa_s_m3: float
    # Main output choice: pressure, flow, or mixed.
    output_mode: str
    # Legacy/source-level output selector used when output_mode is not direct.
    output_source: str
    # Loss inside the chamber ODE: `Q_loss = G_c p_c`.
    chamber_loss_conductance_m3_s_pa: float
    # Extra leakage used only in the output/radiation layer.
    chamber_leakage_conductance_m3_s_pa: float
    # Whether to apply the conservative radiation/body filtering stage.
    radiation_enabled: bool
    # High-pass cutoff for radiation from pressure/flow states.
    radiation_highpass_hz: float
    # Blend amount for differentiating flow/pressure radiation tendency.
    radiation_differentiation_mix: float
    # Broad body/cover-plate coloration frequency.
    body_resonance_frequency_hz: float
    # Quality factor for body coloration; deliberately low-Q.
    body_resonance_q: float
    # Gain of the body coloration filter mixed into the output.
    body_resonance_gain: float
    # Output-layer turbulent flow-noise gain; not fed back into the ODE.
    flow_noise_amount: float
    # Exponent controlling how strongly noise follows simulated flow magnitude.
    flow_noise_power: float
    # Seed for deterministic output noise so renders are repeatable.
    flow_noise_seed: int

    @property
    def vocal_tract_omega_rad_s(self) -> float:
        """Return tract angular frequency `omega_t = 2*pi*f_t`."""

        return 2.0 * pi * self.vocal_tract_frequency_hz


@dataclass(frozen=True)
class RenderConfig:
    """Numerical settings for one offline render.

    These are solver and sampling choices, not physical harmonica parameters.
    The ODE is evaluated on an integration grid and later interpolated to the
    audio sample rate.
    """

    # Total note length.
    duration_s: float = 2.5
    # Output WAV/trace sample rate.
    sample_rate_hz: int = 44_100
    # Dense reporting grid for the ODE solution before audio-rate interpolation.
    integration_rate_hz: int = 12_000
    # Maximum adaptive solver step; smaller is safer but slower.
    max_step_s: float = 1.0 / 6_000.0
    # Relative ODE solver tolerance.
    relative_tolerance: float = 1.0e-4
    # Absolute ODE solver tolerance.
    absolute_tolerance: float = 1.0e-7
    # SciPy ODE method used for stable offline integration.
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
    min_opening_area_m2: float,
    closure_damping_gap_m: float,
    closure_damping_kg_s: float,
    discharge_coefficient: float,
) -> ReedParams:
    """Build a reed from frequency and Q instead of raw stiffness/damping.

    This keeps the presets understandable: a reader can see "392 Hz, Q 18"
    while the code derives `k = m omega^2` and `r = m omega / Q` for the ODE.
    """

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
        min_opening_area_m2=min_opening_area_m2,
        closure_damping_gap_m=closure_damping_gap_m,
        closure_damping_kg_s=closure_damping_kg_s,
        discharge_coefficient=discharge_coefficient,
    )


# Default draw-note preset. It uses negative mouth pressure and makes the draw
# reed the more active, high-Q reed-slot oscillator.
DEFAULT_PARAMS = ModelParams(
    rho_air_kg_m3=1.204,
    speed_of_sound_m_s=343.0,
    chamber_volume_m3=8.0e-7,
    p_out_pa=0.0,
    blow_reed=_reed_from_frequency(
        frequency_hz=392.0,
        mass_kg=8.0e-6,
        quality_factor=18.0,
        pressure_area_m2=1.3e-6,
        slot_width_m=2.2e-3,
        rest_opening_m=30.0e-6,
        closing_displacement_m=-150.0e-6,
        displacement_to_gap=0.2,
        min_opening_area_m2=0.0,
        closure_damping_gap_m=8.0e-6,
        closure_damping_kg_s=4.0e-4,
        discharge_coefficient=0.62,
    ),
    draw_reed=_reed_from_frequency(
        frequency_hz=440.0,
        mass_kg=8.5e-6,
        quality_factor=42.0,
        pressure_area_m2=1.5e-6,
        slot_width_m=2.3e-3,
        rest_opening_m=2.0e-6,
        closing_displacement_m=0.6666666666666666e-6,
        displacement_to_gap=-3.0,
        min_opening_area_m2=0.0,
        closure_damping_gap_m=6.0e-6,
        closure_damping_kg_s=1.8e-3,
        discharge_coefficient=0.68,
    ),
    vocal_tract_frequency_hz=650.0,
    vocal_tract_q=5.0,
    vocal_tract_impedance_pa_s_m3=2.2e8,
    mouth_pressure_pa=-900.0,
    pre_delay_s=0.05,
    attack_s=0.35,
    release_s=0.05,
    release_start_s=2.45,
    breath_noise_amount=0.0,
    acoustic_flow_gain_pa_s_m3=0.0,
    pressure_output_gain=0.01,
    chamber_pressure_output_gain=0.0,
    draw_flow_output_gain_pa_s_m3=1.0e7,
    blow_flow_output_gain_pa_s_m3=0.0,
    output_mode="mixed",
    output_source="mix",
    chamber_loss_conductance_m3_s_pa=2.0e-11,
    chamber_leakage_conductance_m3_s_pa=0.0,
    radiation_enabled=True,
    radiation_highpass_hz=90.0,
    radiation_differentiation_mix=0.18,
    body_resonance_frequency_hz=1700.0,
    body_resonance_q=1.6,
    body_resonance_gain=0.10,
    flow_noise_amount=0.006,
    flow_noise_power=1.4,
    flow_noise_seed=17,
)


# Public alias used by the CLI/tests when the requested mode is draw.
DRAW_PARAMS = DEFAULT_PARAMS


# Blow uses the same ODE as draw, but a different physical playing preset:
# positive mouth pressure, the blow reed as the high-Q active reed, a slightly
# stronger breath drive, and a brighter physical radiation path from simulated
# net flow. These differences are intentionally parameter-level differences,
# not a separate synth voice or a post-render pitch/EQ trick.
BLOW_PARAMS = ModelParams(
    rho_air_kg_m3=1.204,
    speed_of_sound_m_s=343.0,
    chamber_volume_m3=8.0e-7,
    p_out_pa=0.0,
    blow_reed=_reed_from_frequency(
        frequency_hz=392.0,
        mass_kg=8.0e-6,
        quality_factor=42.0,
        pressure_area_m2=1.5e-6,
        slot_width_m=2.2e-3,
        rest_opening_m=2.0e-6,
        closing_displacement_m=-0.6666666666666666e-6,
        displacement_to_gap=3.0,
        min_opening_area_m2=0.0,
        closure_damping_gap_m=6.0e-6,
        closure_damping_kg_s=1.8e-3,
        discharge_coefficient=0.68,
    ),
    draw_reed=_reed_from_frequency(
        frequency_hz=440.0,
        mass_kg=8.5e-6,
        quality_factor=18.0,
        pressure_area_m2=1.2e-6,
        slot_width_m=2.3e-3,
        rest_opening_m=30.0e-6,
        closing_displacement_m=-150.0e-6,
        displacement_to_gap=0.2,
        min_opening_area_m2=0.0,
        closure_damping_gap_m=8.0e-6,
        closure_damping_kg_s=4.0e-4,
        discharge_coefficient=0.62,
    ),
    vocal_tract_frequency_hz=780.0,
    vocal_tract_q=4.5,
    vocal_tract_impedance_pa_s_m3=2.4e8,
    mouth_pressure_pa=800.0,
    pre_delay_s=0.05,
    attack_s=0.35,
    release_s=0.05,
    release_start_s=2.45,
    breath_noise_amount=0.0,
    acoustic_flow_gain_pa_s_m3=1.0e8,
    pressure_output_gain=0.01,
    chamber_pressure_output_gain=0.0,
    draw_flow_output_gain_pa_s_m3=0.0,
    blow_flow_output_gain_pa_s_m3=1.0e7,
    output_mode="mixed",
    output_source="mix",
    chamber_loss_conductance_m3_s_pa=2.0e-11,
    chamber_leakage_conductance_m3_s_pa=0.0,
    radiation_enabled=True,
    radiation_highpass_hz=150.0,
    radiation_differentiation_mix=0.40,
    body_resonance_frequency_hz=2100.0,
    body_resonance_q=1.5,
    body_resonance_gain=0.18,
    flow_noise_amount=0.006,
    flow_noise_power=1.4,
    flow_noise_seed=23,
)
