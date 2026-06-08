"""Physical parameters, provenance, presets, and numerical settings."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from math import pi


class ParameterCategory(str, Enum):
    """Required source-traceability categories."""

    SOURCE_DERIVED = "SOURCE_DERIVED"
    PHYSICALLY_ESTIMATED = "PHYSICALLY_ESTIMATED"
    MODEL_ASSUMPTION = "MODEL_ASSUMPTION"


@dataclass(frozen=True)
class ParameterValue:
    """One numerical value with its source and original representation."""

    name: str
    value_si: float
    si_unit: str
    original_value: str
    original_unit: str
    source_label: str
    category: ParameterCategory
    note: str


@dataclass(frozen=True)
class SourceValidationTargets:
    """Published values used for comparison, not solver constraints."""

    name: str
    applicable_mode: str
    played_frequency_hz: float
    active_peak_amplitude_m: float
    passive_peak_amplitude_m: float
    active_passive_ratio: float
    active_mean_opening_m: float
    passive_mean_opening_m: float
    mean_chamber_pressure_pa: float
    equivalent_acoustic_amplitude_pa: float
    source_label: str


@dataclass(frozen=True)
class ReedParameters:
    """One lumped reed oscillator and its reduced slot-opening constants."""

    mass_kg: float
    damping_kg_s: float
    stiffness_n_m: float
    pressure_area_m2: float
    slot_width_m: float
    rest_gap_m: float
    gap_displacement_scale: float
    through_slot_rest_offset_m: float
    through_slot_positive_threshold_m: float
    through_slot_negative_threshold_m: float
    through_slot_positive_gain: float
    through_slot_negative_gain: float
    leakage_area_m2: float
    threshold_smoothing_m: float
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
    opening_model: str = "clipped"
    parameter_preset: str = "generic_default"
    source_validation: str | None = None
    provenance: tuple[ParameterValue, ...] = ()

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


def _value(
    name: str,
    value_si: float,
    si_unit: str,
    original_value: str,
    original_unit: str,
    source_label: str,
    category: ParameterCategory,
    note: str,
) -> ParameterValue:
    return ParameterValue(
        name=name,
        value_si=value_si,
        si_unit=si_unit,
        original_value=original_value,
        original_unit=original_unit,
        source_label=source_label,
        category=category,
        note=note,
    )


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
    through_slot_rest_offset_m: float | None = None,
    through_slot_positive_threshold_m: float = 1.0e-6,
    through_slot_negative_threshold_m: float = 1.0e-6,
    through_slot_positive_gain: float = 1.0,
    through_slot_negative_gain: float = 1.0,
    leakage_area_m2: float = 0.0,
    threshold_smoothing_m: float = 0.0,
) -> ReedParameters:
    """Derive oscillator stiffness and damping from frequency and Q."""

    omega = 2.0 * pi * frequency_hz
    return ReedParameters(
        mass_kg=mass_kg,
        damping_kg_s=mass_kg * omega / quality_factor,
        stiffness_n_m=mass_kg * omega**2,
        pressure_area_m2=pressure_area_m2,
        slot_width_m=slot_width_m,
        rest_gap_m=rest_gap_m,
        gap_displacement_scale=gap_displacement_scale,
        through_slot_rest_offset_m=(
            rest_gap_m + through_slot_positive_threshold_m
            if through_slot_rest_offset_m is None
            else through_slot_rest_offset_m
        ),
        through_slot_positive_threshold_m=through_slot_positive_threshold_m,
        through_slot_negative_threshold_m=through_slot_negative_threshold_m,
        through_slot_positive_gain=through_slot_positive_gain,
        through_slot_negative_gain=through_slot_negative_gain,
        leakage_area_m2=leakage_area_m2,
        threshold_smoothing_m=threshold_smoothing_m,
        discharge_coefficient=discharge_coefficient,
        motion_area_m2=motion_area_m2,
    )


def _generic_provenance(params: ModelParameters) -> tuple[ParameterValue, ...]:
    values = [
        _value("rho_air_kg_m3", params.rho_air_kg_m3, "kg/m^3", "1.204", "kg/m^3", "standard room-air constant", ParameterCategory.PHYSICALLY_ESTIMATED, "Room-temperature air density."),
        _value("speed_of_sound_m_s", params.speed_of_sound_m_s, "m/s", "343", "m/s", "standard room-air constant", ParameterCategory.PHYSICALLY_ESTIMATED, "Room-temperature speed of sound."),
        _value("chamber_volume_m3", params.chamber_volume_m3, "m^3", "8.0e-7", "m^3", "seminar-core reduced model", ParameterCategory.MODEL_ASSUMPTION, "Effective channel chamber volume; not taken from Millot, Bahnson, or Bilbao."),
        _value("p_out_pa", params.p_out_pa, "Pa", "0", "Pa gauge", "gauge-pressure reference", ParameterCategory.MODEL_ASSUMPTION, "Outside pressure is the gauge reference."),
        _value("mouth_pressure_pa", params.mouth_pressure_pa, "Pa", f"{params.mouth_pressure_pa:g}", "Pa", "seminar-core reduced model", ParameterCategory.MODEL_ASSUMPTION, "Static breath-pressure level."),
        _value("attack_s", params.attack_s, "s", f"{params.attack_s:g}", "s", "seminar-core reduced model", ParameterCategory.MODEL_ASSUMPTION, "Smooth breath-envelope attack."),
        _value("release_s", params.release_s, "s", f"{params.release_s:g}", "s", "seminar-core reduced model", ParameterCategory.MODEL_ASSUMPTION, "Smooth breath-envelope release."),
        _value("vocal_tract_frequency_hz", params.vocal_tract_frequency_hz, "Hz", f"{params.vocal_tract_frequency_hz:g}", "Hz", "reduced tract closure", ParameterCategory.MODEL_ASSUMPTION, "One-mode tract resonance, motivated but not parameterized by Bahnson."),
        _value("vocal_tract_q", params.vocal_tract_q, "1", f"{params.vocal_tract_q:g}", "1", "reduced tract closure", ParameterCategory.MODEL_ASSUMPTION, "Reduced tract quality factor."),
        _value("vocal_tract_impedance_pa_s_m3", params.vocal_tract_impedance_pa_s_m3, "Pa s/m^3", f"{params.vocal_tract_impedance_pa_s_m3:g}", "Pa s/m^3", "reduced tract closure", ParameterCategory.MODEL_ASSUMPTION, "Reduced tract drive impedance."),
        _value("vocal_tract_feedback_gain", params.vocal_tract_feedback_gain, "1", f"{params.vocal_tract_feedback_gain:g}", "1", "reduced tract closure", ParameterCategory.MODEL_ASSUMPTION, "Feedback from tract pressure to effective mouth pressure."),
    ]
    for prefix, reed, frequency, quality in (
        ("blow_reed", params.blow_reed, 405.0, 177.0),
        ("draw_reed", params.draw_reed, 455.0, 95.0),
    ):
        values.extend(
            [
                _value(f"{prefix}.frequency_hz", frequency, "Hz", f"{frequency:g}", "Hz", "Millot et al. (2001), Table 3, Harmonica 4b", ParameterCategory.SOURCE_DERIVED, "Equivalent reed resonance used to derive k and r in the generic preset."),
                _value(f"{prefix}.quality_factor", quality, "1", f"{quality:g}", "1", "Millot et al. (2001), Table 3, Harmonica 4b", ParameterCategory.SOURCE_DERIVED, "Equivalent reed Q used to derive damping in the generic preset."),
                _value(f"{prefix}.mass_kg", reed.mass_kg, "kg", f"{reed.mass_kg * 1e6:g}", "mg", "Millot et al. (2001), Table 3, Harmonica 4b", ParameterCategory.SOURCE_DERIVED, "Equivalent oscillator mass."),
                _value(f"{prefix}.stiffness_n_m", reed.stiffness_n_m, "N/m", "m(2 pi f)^2", "derived", "Millot frequency and mass", ParameterCategory.PHYSICALLY_ESTIMATED, "Derived oscillator stiffness in the retained generic preset."),
                _value(f"{prefix}.damping_kg_s", reed.damping_kg_s, "kg/s", "m(2 pi f)/Q", "derived", "Millot frequency, mass, and Q", ParameterCategory.PHYSICALLY_ESTIMATED, "Derived viscous damping in the retained generic preset."),
            ]
        )
        assumption_fields = (
            ("pressure_area_m2", reed.pressure_area_m2, "m^2", "Effective pressure-loaded surface."),
            ("slot_width_m", reed.slot_width_m, "m", "Effective slot width."),
            ("rest_gap_m", reed.rest_gap_m, "m", "One-sided effective rest gap."),
            ("gap_displacement_scale", reed.gap_displacement_scale, "1", "Displacement-to-gap sign and gain."),
            ("through_slot_rest_offset_m", reed.through_slot_rest_offset_m, "m", "Signed rest position for the reduced crossing law."),
            ("through_slot_positive_threshold_m", reed.through_slot_positive_threshold_m, "m", "Positive-side crossing threshold."),
            ("through_slot_negative_threshold_m", reed.through_slot_negative_threshold_m, "m", "Negative-side crossing threshold."),
            ("through_slot_positive_gain", reed.through_slot_positive_gain, "1", "Positive-side area gain."),
            ("through_slot_negative_gain", reed.through_slot_negative_gain, "1", "Negative-side area gain."),
            ("leakage_area_m2", reed.leakage_area_m2, "m^2", "Residual leakage area."),
            ("threshold_smoothing_m", reed.threshold_smoothing_m, "m", "Threshold smoothing half-width."),
            ("discharge_coefficient", reed.discharge_coefficient, "1", "Bernoulli/orifice discharge coefficient."),
            ("motion_area_m2", reed.motion_area_m2, "m^2", "Optional moving-reed flow area."),
        )
        values.extend(
            _value(f"{prefix}.{name}", float(value), unit, f"{value:g}", unit, "seminar-core reduced model", ParameterCategory.MODEL_ASSUMPTION, note)
            for name, value, unit, note in assumption_fields
        )
    return tuple(values)


GENERIC_DRAW_PARAMETERS = ModelParameters(
    rho_air_kg_m3=1.204,
    speed_of_sound_m_s=343.0,
    chamber_volume_m3=8.0e-7,
    p_out_pa=0.0,
    blow_reed=reed_from_frequency(
        frequency_hz=405.0,
        mass_kg=11.98e-6,
        quality_factor=177.0,
        pressure_area_m2=8.0e-6,
        slot_width_m=2.2e-3,
        rest_gap_m=60.0e-6,
        gap_displacement_scale=0.20,
        discharge_coefficient=0.62,
        motion_area_m2=0.0,
    ),
    draw_reed=reed_from_frequency(
        frequency_hz=455.0,
        mass_kg=6.07e-6,
        quality_factor=95.0,
        pressure_area_m2=5.0e-6,
        slot_width_m=2.3e-3,
        rest_gap_m=2.0e-6,
        gap_displacement_scale=-3.5,
        discharge_coefficient=0.35,
        motion_area_m2=1.1e-6,
    ),
    mouth_pressure_pa=-700.0,
    attack_s=0.18,
    release_s=0.05,
    vocal_tract_frequency_hz=680.0,
    vocal_tract_q=5.0,
    vocal_tract_impedance_pa_s_m3=2.0e8,
    vocal_tract_feedback_gain=0.0,
    motion_flow_enabled=False,
)
GENERIC_DRAW_PARAMETERS = replace(GENERIC_DRAW_PARAMETERS, provenance=_generic_provenance(GENERIC_DRAW_PARAMETERS))

GENERIC_BLOW_PARAMETERS = replace(
    GENERIC_DRAW_PARAMETERS,
    blow_reed=reed_from_frequency(
        frequency_hz=405.0,
        mass_kg=11.98e-6,
        quality_factor=177.0,
        pressure_area_m2=12.0e-6,
        slot_width_m=2.2e-3,
        rest_gap_m=2.0e-6,
        gap_displacement_scale=3.5,
        discharge_coefficient=0.72,
        motion_area_m2=1.1e-6,
    ),
    draw_reed=reed_from_frequency(
        frequency_hz=455.0,
        mass_kg=6.07e-6,
        quality_factor=95.0,
        pressure_area_m2=2.5e-6,
        slot_width_m=2.3e-3,
        rest_gap_m=22.0e-6,
        gap_displacement_scale=0.20,
        discharge_coefficient=0.62,
        motion_area_m2=0.0,
    ),
    mouth_pressure_pa=250.0,
    vocal_tract_frequency_hz=800.0,
)
GENERIC_BLOW_PARAMETERS = replace(GENERIC_BLOW_PARAMETERS, provenance=_generic_provenance(GENERIC_BLOW_PARAMETERS))

# Backwards-compatible names used by existing tests and callers.
DRAW_PARAMETERS = GENERIC_DRAW_PARAMETERS
BLOW_PARAMETERS = GENERIC_BLOW_PARAMETERS


def _millot_reed(
    *,
    mass_kg: float,
    damping_kg_s: float,
    stiffness_n_m: float,
    h00_m: float,
    pressure_area_m2: float,
    slot_width_m: float,
    gap_displacement_scale: float,
    positive_threshold_m: float,
    negative_threshold_m: float,
    positive_gain: float,
    negative_gain: float,
    discharge_coefficient: float,
) -> ReedParameters:
    return ReedParameters(
        mass_kg=mass_kg,
        damping_kg_s=damping_kg_s,
        stiffness_n_m=stiffness_n_m,
        pressure_area_m2=pressure_area_m2,
        slot_width_m=slot_width_m,
        rest_gap_m=abs(h00_m),
        gap_displacement_scale=gap_displacement_scale,
        through_slot_rest_offset_m=h00_m,
        through_slot_positive_threshold_m=positive_threshold_m,
        through_slot_negative_threshold_m=negative_threshold_m,
        through_slot_positive_gain=positive_gain,
        through_slot_negative_gain=negative_gain,
        leakage_area_m2=5.0e-10,
        threshold_smoothing_m=20.0e-6,
        discharge_coefficient=discharge_coefficient,
        motion_area_m2=0.0,
    )


# Millot upper reed maps to the blow reed and Millot lower reed maps to the
# draw reed for the normal-blow channel-4 configuration.
MILLOT_BLOW_REED = _millot_reed(
    mass_kg=11.98e-6,
    damping_kg_s=172.0e-6,
    stiffness_n_m=77.5,
    h00_m=-1298.0e-6,
    pressure_area_m2=220.0e-6,
    slot_width_m=2.2e-3,
    gap_displacement_scale=-1.0,
    positive_threshold_m=120.0e-6,
    negative_threshold_m=1100.0e-6,
    positive_gain=0.35,
    negative_gain=0.70,
    discharge_coefficient=0.72,
)
MILLOT_DRAW_REED = _millot_reed(
    mass_kg=6.07e-6,
    damping_kg_s=183.0e-6,
    stiffness_n_m=49.6,
    h00_m=286.5e-6,
    pressure_area_m2=0.9e-6,
    slot_width_m=2.3e-3,
    gap_displacement_scale=1.0,
    positive_threshold_m=220.0e-6,
    negative_threshold_m=80.0e-6,
    positive_gain=0.35,
    negative_gain=0.12,
    discharge_coefficient=0.62,
)


def _millot_provenance(params: ModelParameters) -> tuple[ParameterValue, ...]:
    source = "Millot et al. (2001), Table 3, Harmonica 4b"
    values = list(_generic_provenance(params))
    replacements = {
        "blow_reed.frequency_hz": _value("blow_reed.frequency_hz", 405.0, "Hz", "405", "Hz", source, ParameterCategory.SOURCE_DERIVED, "Upper reed 4b resonance; upper maps to blow for normal blow."),
        "blow_reed.quality_factor": _value("blow_reed.quality_factor", 177.0, "1", "177", "1", source, ParameterCategory.SOURCE_DERIVED, "Upper reed 4b quality factor."),
        "blow_reed.mass_kg": _value("blow_reed.mass_kg", 11.98e-6, "kg", "11.98", "mg", source, ParameterCategory.SOURCE_DERIVED, "Upper reed 4b equivalent mass."),
        "blow_reed.stiffness_n_m": _value("blow_reed.stiffness_n_m", 77.5, "N/m", "77.5", "N/m", source, ParameterCategory.SOURCE_DERIVED, "Upper reed 4b equivalent stiffness."),
        "blow_reed.damping_kg_s": _value("blow_reed.damping_kg_s", 172.0e-6, "kg/s", "172", "micro N s/m", source, ParameterCategory.SOURCE_DERIVED, "Upper reed 4b equivalent viscous damping."),
        "blow_reed.rest_gap_m": _value("blow_reed.rest_gap_m", 1298.0e-6, "m", "|-1298.0|", "micrometer", source, ParameterCategory.PHYSICALLY_ESTIMATED, "Magnitude of Millot h00 used by the one-sided clipped area law."),
        "blow_reed.through_slot_rest_offset_m": _value("blow_reed.through_slot_rest_offset_m", -1298.0e-6, "m", "-1298.0", "micrometer", source, ParameterCategory.SOURCE_DERIVED, "Signed upper-reed h00."),
        "blow_reed.pressure_area_m2": _value("blow_reed.pressure_area_m2", params.blow_reed.pressure_area_m2, "m^2", f"{params.blow_reed.pressure_area_m2:g}", "m^2", "target-informed reduced-model closure", ParameterCategory.MODEL_ASSUMPTION, "Effective generalized pressure-force coefficient selected against the Millot normal-blow limit cycle; it is not a measured geometric reed area."),
        "blow_reed.through_slot_negative_gain": _value("blow_reed.through_slot_negative_gain", params.blow_reed.through_slot_negative_gain, "1", f"{params.blow_reed.through_slot_negative_gain:g}", "1", "target-informed reduced-model closure", ParameterCategory.MODEL_ASSUMPTION, "Inside-side area gain selected by numerical comparison with the published normal-blow targets, not by listening."),
        "draw_reed.frequency_hz": _value("draw_reed.frequency_hz", 455.0, "Hz", "455", "Hz", source, ParameterCategory.SOURCE_DERIVED, "Lower reed 4b resonance; lower maps to draw for normal blow."),
        "draw_reed.quality_factor": _value("draw_reed.quality_factor", 95.0, "1", "95", "1", source, ParameterCategory.SOURCE_DERIVED, "Lower reed 4b quality factor."),
        "draw_reed.mass_kg": _value("draw_reed.mass_kg", 6.07e-6, "kg", "6.07", "mg", source, ParameterCategory.SOURCE_DERIVED, "Lower reed 4b equivalent mass."),
        "draw_reed.stiffness_n_m": _value("draw_reed.stiffness_n_m", 49.6, "N/m", "49.6", "N/m", source, ParameterCategory.SOURCE_DERIVED, "Lower reed 4b equivalent stiffness."),
        "draw_reed.damping_kg_s": _value("draw_reed.damping_kg_s", 183.0e-6, "kg/s", "183", "micro N s/m", source, ParameterCategory.SOURCE_DERIVED, "Lower reed 4b equivalent viscous damping."),
        "draw_reed.rest_gap_m": _value("draw_reed.rest_gap_m", 286.5e-6, "m", "286.5", "micrometer", source, ParameterCategory.PHYSICALLY_ESTIMATED, "Magnitude of Millot h00 used by the one-sided clipped area law."),
        "draw_reed.through_slot_rest_offset_m": _value("draw_reed.through_slot_rest_offset_m", 286.5e-6, "m", "+286.5", "micrometer", source, ParameterCategory.SOURCE_DERIVED, "Signed lower-reed h00."),
        "draw_reed.pressure_area_m2": _value("draw_reed.pressure_area_m2", params.draw_reed.pressure_area_m2, "m^2", f"{params.draw_reed.pressure_area_m2:g}", "m^2", "target-informed reduced-model closure", ParameterCategory.MODEL_ASSUMPTION, "Effective generalized pressure-force coefficient selected against passive-reed amplitude; it is not source-derived."),
        "mouth_pressure_pa": _value("mouth_pressure_pa", params.mouth_pressure_pa, "Pa", f"{params.mouth_pressure_pa:g}", "Pa", "target-informed reduced-model closure", ParameterCategory.MODEL_ASSUMPTION, "Static source pressure used to sustain the reduced closing-reed model; Millot reports inner pressure, not mouth pressure."),
        "chamber_volume_m3": _value("chamber_volume_m3", params.chamber_volume_m3, "m^3", f"{params.chamber_volume_m3:g}", "m^3", "target-informed reduced-model closure", ParameterCategory.MODEL_ASSUMPTION, "Effective chamber compliance volume selected by numerical comparison with pressure and reed-motion targets; not measured from the cited harmonica."),
    }
    return tuple(replacements.get(value.name, value) for value in values)


MILLOT_CHANNEL4_4B = ModelParameters(
    rho_air_kg_m3=1.204,
    speed_of_sound_m_s=343.0,
    chamber_volume_m3=1.4e-6,
    p_out_pa=0.0,
    blow_reed=MILLOT_BLOW_REED,
    draw_reed=MILLOT_DRAW_REED,
    mouth_pressure_pa=500.0,
    attack_s=0.18,
    release_s=0.05,
    vocal_tract_frequency_hz=800.0,
    vocal_tract_q=5.0,
    vocal_tract_impedance_pa_s_m3=2.0e8,
    vocal_tract_feedback_gain=0.0,
    motion_flow_enabled=False,
    opening_model="through_slot_calibrated",
    parameter_preset="millot_channel4_4b",
)
MILLOT_CHANNEL4_4B = replace(MILLOT_CHANNEL4_4B, provenance=_millot_provenance(MILLOT_CHANNEL4_4B))


MILLOT_NORMAL_BLOW_4B = SourceValidationTargets(
    name="millot_normal_blow_4b",
    applicable_mode="blow",
    played_frequency_hz=401.0,
    active_peak_amplitude_m=1493.0e-6,
    passive_peak_amplitude_m=67.0e-6,
    active_passive_ratio=1493.0 / 67.0,
    active_mean_opening_m=-1171.0e-6,
    passive_mean_opening_m=320.0e-6,
    mean_chamber_pressure_pa=219.0,
    equivalent_acoustic_amplitude_pa=128.0,
    source_label="Millot et al. (2001), Table 4 and normal-blow pressure discussion",
)

SOURCE_VALIDATIONS = {MILLOT_NORMAL_BLOW_4B.name: MILLOT_NORMAL_BLOW_4B}
PARAMETER_PRESETS = ("generic_default", "millot_channel4_4b")
OPENING_MODELS = ("clipped", "through_slot_simple", "through_slot_calibrated")


SIMULATION_PARAMETER_PROVENANCE = (
    _value("simulation.duration_s", 2.0, "s", "2.0", "s", "seminar-core numerical setup", ParameterCategory.MODEL_ASSUMPTION, "Default offline render duration."),
    _value("simulation.sample_rate_hz", 22_050.0, "Hz", "22050", "Hz", "seminar-core numerical setup", ParameterCategory.MODEL_ASSUMPTION, "Default exported trace and WAV sample rate."),
    _value("simulation.max_step_s", 1.0 / 12_000.0, "s", "1/12000", "s", "seminar-core numerical setup", ParameterCategory.MODEL_ASSUMPTION, "Maximum adaptive solver step selected for temporal resolution."),
    _value("simulation.relative_tolerance", 2.0e-5, "1", "2e-5", "1", "seminar-core numerical setup", ParameterCategory.MODEL_ASSUMPTION, "Adaptive solver relative tolerance."),
    _value("simulation.absolute_tolerance", 1.0e-8, "state-dependent", "1e-8", "state-dependent", "seminar-core numerical setup", ParameterCategory.MODEL_ASSUMPTION, "Adaptive solver absolute tolerance."),
)


def parameters_for_mode(mode: str, parameter_preset: str = "generic_default") -> ModelParameters:
    """Return a reproducible mode/preset combination."""

    if parameter_preset == "generic_default":
        if mode == "draw":
            return GENERIC_DRAW_PARAMETERS
        if mode == "blow":
            return GENERIC_BLOW_PARAMETERS
    elif parameter_preset == "millot_channel4_4b":
        if mode in {"draw", "blow"}:
            pressure = -700.0 if mode == "draw" else MILLOT_CHANNEL4_4B.mouth_pressure_pa
            tract_frequency = 680.0 if mode == "draw" else 800.0
            params = replace(MILLOT_CHANNEL4_4B, mouth_pressure_pa=pressure, vocal_tract_frequency_hz=tract_frequency)
            return replace(params, provenance=_millot_provenance(params))
    else:
        raise ValueError(f"unknown parameter preset: {parameter_preset}")
    raise ValueError(f"unknown mode: {mode}")


def source_validation_targets(name: str | None) -> SourceValidationTargets | None:
    if name is None:
        return None
    try:
        return SOURCE_VALIDATIONS[name]
    except KeyError as exc:
        raise ValueError(f"unknown source validation: {name}") from exc
