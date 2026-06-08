"""CSV, WAV, and compact text export for simulated states."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import json
from math import sqrt
from pathlib import Path
import wave

import numpy as np

from .parameters import ParameterCategory, source_validation_targets
from .simulate import SimulationResult


DEFAULT_DC_BLOCK_CUTOFF_HZ = 20.0


TRACE_COLUMNS = [
    "time",
    "x_b",
    "v_b",
    "x_d",
    "v_d",
    "p_c",
    "p_m_static",
    "p_t",
    "p_m_effective",
    "vocal_tract_feedback_gain",
    "v_t",
    "gap_b",
    "gap_d",
    "z_b",
    "z_d",
    "area_b",
    "area_d",
    "area_b_pos",
    "area_b_neg",
    "area_d_pos",
    "area_d_neg",
    "opening_side_b",
    "opening_side_d",
    "opening_model",
    "parameter_preset",
    "source_validation",
    "delta_p_b",
    "delta_p_d",
    "q_b_gap",
    "q_b_motion",
    "q_b_total",
    "q_d_gap",
    "q_d_motion",
    "q_d_total",
    "force_b",
    "force_d",
]


@dataclass(frozen=True)
class LowFrequencyStats:
    mean: float
    minimum: float
    maximum: float
    rms: float
    ac_rms: float
    spectral_energy_below_20_hz: float
    spectral_energy_below_50_hz: float
    spectral_energy_total: float


@dataclass(frozen=True)
class SignalMeasurement:
    name: str
    unit: str
    full: LowFrequencyStats
    steady: LowFrequencyStats


@dataclass(frozen=True)
class ValidationMetrics:
    """Source-comparison measurements derived only from simulated states."""

    fundamental_hz: float
    mean_chamber_pressure_pa: float
    ac_pressure_rms_pa: float
    equivalent_acoustic_amplitude_pa: float
    active_peak_amplitude_m: float
    passive_peak_amplitude_m: float
    active_passive_ratio: float
    active_mean_position_m: float
    passive_mean_position_m: float
    blow_positive_open_percent: float
    blow_negative_open_percent: float
    blow_closed_percent: float
    draw_positive_open_percent: float
    draw_negative_open_percent: float
    draw_closed_percent: float
    blow_crosses_slot_plane: bool
    draw_crosses_slot_plane: bool
    pressure_harmonic_ratios: tuple[float, ...]
    fundamental_is_strongest: bool
    passive_reed_dominates: bool
    through_slot_almost_always_open: bool


def selected_output_signal(result: SimulationResult) -> np.ndarray:
    """Return the physical signal selected for WAV rendering before normalization."""

    return result.p_c


def _peak_normalize(signal: np.ndarray) -> np.ndarray:
    peak = float(np.max(np.abs(signal))) if signal.size else 0.0
    if peak <= 0.0:
        return np.zeros_like(signal)
    return signal / peak


def dc_block_signal(
    signal: np.ndarray,
    sample_rate_hz: int,
    cutoff_hz: float = DEFAULT_DC_BLOCK_CUTOFF_HZ,
) -> np.ndarray:
    """Apply a first-order DC blocker for optional WAV-only listening output."""

    source = np.asarray(signal, dtype=float)
    if source.size == 0:
        return source.copy()
    if cutoff_hz <= 0.0:
        return source.copy()

    radius = float(np.exp(-2.0 * np.pi * cutoff_hz / float(sample_rate_hz)))
    blocked = np.empty_like(source)
    previous_x = 0.0
    previous_y = 0.0
    for index, value in enumerate(source):
        y = value - previous_x + radius * previous_y
        blocked[index] = y
        previous_x = float(value)
        previous_y = float(y)
    return blocked


def rendered_audio_signal(result: SimulationResult, dc_block_cutoff_hz: float | None = None) -> np.ndarray:
    """Return the normalized signal written to WAV, with optional WAV-only postprocessing."""

    signal = selected_output_signal(result)
    if dc_block_cutoff_hz is not None:
        signal = dc_block_signal(signal, result.sample_rate_hz, dc_block_cutoff_hz)
    return _peak_normalize(signal)


def normalized_chamber_pressure(result: SimulationResult) -> np.ndarray:
    """Scale simulated chamber pressure to [-1, 1] without changing its source."""

    return rendered_audio_signal(result)


def write_pressure_wav(path: Path, result: SimulationResult, dc_block_cutoff_hz: float | None = None) -> None:
    """Write normalized p_c(t) as 16-bit PCM."""

    path.parent.mkdir(parents=True, exist_ok=True)
    signal = rendered_audio_signal(result, dc_block_cutoff_hz)
    pcm = np.clip(signal, -1.0, 1.0)
    pcm_i16 = np.asarray(np.round(pcm * 32767.0), dtype="<i2")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(result.sample_rate_hz)
        handle.writeframes(pcm_i16.tobytes())


def write_trace_csv(path: Path, result: SimulationResult) -> None:
    """Write the required state and derived-flow trace."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if result.params.opening_model.startswith("through_slot"):
        opening_side_b = np.where(result.area_b_pos > 0.0, 1, np.where(result.area_b_neg > 0.0, -1, 0))
        opening_side_d = np.where(result.area_d_pos > 0.0, 1, np.where(result.area_d_neg > 0.0, -1, 0))
    else:
        opening_side_b = np.where(result.area_b > 0.0, 1, 0)
        opening_side_d = np.where(result.area_d > 0.0, 1, 0)
    rows = zip(
        result.time_s,
        result.x_b,
        result.v_b,
        result.x_d,
        result.v_d,
        result.p_c,
        result.p_m_static,
        result.p_t,
        result.p_m_effective,
        np.full_like(result.time_s, result.params.vocal_tract_feedback_gain, dtype=float),
        result.v_t,
        result.gap_b,
        result.gap_d,
        result.z_b,
        result.z_d,
        result.area_b,
        result.area_d,
        result.area_b_pos,
        result.area_b_neg,
        result.area_d_pos,
        result.area_d_neg,
        opening_side_b,
        opening_side_d,
        [result.params.opening_model] * len(result.time_s),
        [result.params.parameter_preset] * len(result.time_s),
        [result.params.source_validation or "none"] * len(result.time_s),
        result.delta_p_b,
        result.delta_p_d,
        result.q_b_gap,
        result.q_b_motion,
        result.q_b_total,
        result.q_d_gap,
        result.q_d_motion,
        result.q_d_total,
        result.force_b,
        result.force_d,
    )
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(TRACE_COLUMNS)
        writer.writerows(rows)


def estimate_fundamental_hz(signal: np.ndarray, sample_rate_hz: int) -> float:
    """Estimate f0 from the strongest low-frequency spectral peak."""

    centered = np.asarray(signal, dtype=float) - float(np.mean(signal))
    if centered.size < 8 or float(np.max(np.abs(centered))) == 0.0:
        return 0.0
    window = np.hanning(centered.size)
    magnitudes = np.abs(np.fft.rfft(centered * window))
    freqs = np.fft.rfftfreq(centered.size, 1.0 / sample_rate_hz)
    # This prototype models channel-4 reeds near 400 Hz. Excluding sub-150 Hz
    # envelope and slow-equilibrium components prevents them being mislabeled
    # as the played fundamental.
    band = (freqs >= 150.0) & (freqs <= 2000.0)
    if not np.any(band):
        return 0.0
    index = int(np.argmax(magnitudes[band]))
    return float(freqs[band][index])


def harmonic_ratios(signal: np.ndarray, sample_rate_hz: int, f0_hz: float, count: int = 10) -> list[float]:
    """Return H1-H10 magnitude ratios relative to H1."""

    centered = np.asarray(signal, dtype=float) - float(np.mean(signal))
    if f0_hz <= 0.0 or centered.size < 8:
        return [0.0] * count
    window = np.hanning(centered.size)
    magnitudes = np.abs(np.fft.rfft(centered * window))
    freqs = np.fft.rfftfreq(centered.size, 1.0 / sample_rate_hz)
    values = []
    for harmonic in range(1, count + 1):
        target = harmonic * f0_hz
        if target > freqs[-1]:
            values.append(0.0)
            continue
        idx = int(np.argmin(np.abs(freqs - target)))
        values.append(float(magnitudes[idx]))
    h1 = values[0] if values and values[0] > 0.0 else 1.0
    return [value / h1 for value in values]


def _crosses_zero(values: np.ndarray) -> bool:
    return bool(values.size and np.min(values) <= 0.0 <= np.max(values))


def _side_percentages(area_pos: np.ndarray, area_neg: np.ndarray) -> tuple[float, float, float]:
    positive = area_pos > 0.0
    negative = area_neg > 0.0
    closed = ~(positive | negative)
    return (
        float(100.0 * np.mean(positive)),
        float(100.0 * np.mean(negative)),
        float(100.0 * np.mean(closed)),
    )


def validation_metrics(result: SimulationResult) -> ValidationMetrics:
    """Measure source-comparison quantities in the steady-state window."""

    start, stop = _steady_region(result)
    if result.mode == "draw":
        active = result.x_d[start:stop]
        passive = result.x_b[start:stop]
        active_position = result.z_d[start:stop]
        passive_position = result.z_b[start:stop]
    else:
        active = result.x_b[start:stop]
        passive = result.x_d[start:stop]
        active_position = result.z_b[start:stop]
        passive_position = result.z_d[start:stop]

    pressure = result.p_c[start:stop]
    f0 = estimate_fundamental_hz(active, result.sample_rate_hz)
    pressure_ratios = tuple(harmonic_ratios(pressure, result.sample_rate_hz, f0))
    active_amplitude = 0.5 * float(np.ptp(active)) if active.size else 0.0
    passive_amplitude = 0.5 * float(np.ptp(passive)) if passive.size else 0.0
    pressure_mean = float(np.mean(pressure)) if pressure.size else 0.0
    pressure_ac_rms = (
        float(np.sqrt(np.mean((pressure - pressure_mean) ** 2)))
        if pressure.size
        else 0.0
    )

    blow_pos, blow_neg, blow_closed = _side_percentages(
        result.area_b_pos[start:stop],
        result.area_b_neg[start:stop],
    )
    draw_pos, draw_neg, draw_closed = _side_percentages(
        result.area_d_pos[start:stop],
        result.area_d_neg[start:stop],
    )
    if result.params.opening_model == "clipped":
        blow_pos, blow_neg, blow_closed = _side_percentages(
            result.area_b[start:stop],
            np.zeros_like(result.area_b[start:stop]),
        )
        draw_pos, draw_neg, draw_closed = _side_percentages(
            result.area_d[start:stop],
            np.zeros_like(result.area_d[start:stop]),
        )

    active_passive_ratio = active_amplitude / passive_amplitude if passive_amplitude > 0.0 else 0.0
    return ValidationMetrics(
        fundamental_hz=f0,
        mean_chamber_pressure_pa=pressure_mean,
        ac_pressure_rms_pa=pressure_ac_rms,
        equivalent_acoustic_amplitude_pa=sqrt(2.0) * pressure_ac_rms,
        active_peak_amplitude_m=active_amplitude,
        passive_peak_amplitude_m=passive_amplitude,
        active_passive_ratio=active_passive_ratio,
        active_mean_position_m=float(np.mean(active_position)) if active_position.size else 0.0,
        passive_mean_position_m=float(np.mean(passive_position)) if passive_position.size else 0.0,
        blow_positive_open_percent=blow_pos,
        blow_negative_open_percent=blow_neg,
        blow_closed_percent=blow_closed,
        draw_positive_open_percent=draw_pos,
        draw_negative_open_percent=draw_neg,
        draw_closed_percent=draw_closed,
        blow_crosses_slot_plane=_crosses_zero(result.z_b[start:stop]),
        draw_crosses_slot_plane=_crosses_zero(result.z_d[start:stop]),
        pressure_harmonic_ratios=pressure_ratios,
        fundamental_is_strongest=bool(
            pressure_ratios
            and pressure_ratios[0] > 0.0
            and max(pressure_ratios[1:], default=0.0) <= pressure_ratios[0]
        ),
        passive_reed_dominates=passive_amplitude > active_amplitude,
        through_slot_almost_always_open=bool(
            result.params.opening_model.startswith("through_slot")
            and (blow_closed < 1.0 or draw_closed < 1.0)
        ),
    )


def _steady_region(result: SimulationResult) -> tuple[int, int]:
    sample_count = len(result.time_s)
    if sample_count <= 1:
        return 0, sample_count

    duration_s = float(result.time_s[-1]) + 1.0 / float(result.sample_rate_hz)
    start_s = max(result.params.attack_s + 0.10, 0.35)
    stop_s = min(duration_s - result.params.release_s - 0.10, 0.90 * duration_s)
    start = min(max(0, int(round(start_s * result.sample_rate_hz))), sample_count - 1)
    stop = min(sample_count, max(start + 1, int(round(stop_s * result.sample_rate_hz))))
    if stop <= start + 8:
        start = min(max(0, int(0.35 * sample_count)), sample_count - 1)
        stop = min(sample_count, max(start + 1, int(0.90 * sample_count)))
    if stop <= start + 8:
        start = 0
        stop = sample_count
    return start, stop


def _spectral_energies(signal: np.ndarray, sample_rate_hz: int) -> tuple[float, float, float]:
    source = np.asarray(signal, dtype=float)
    if source.size == 0:
        return 0.0, 0.0, 0.0

    spectrum = np.fft.rfft(source)
    power = np.abs(spectrum) ** 2 / float(source.size ** 2)
    if power.size > 1:
        if source.size % 2 == 0:
            power[1:-1] *= 2.0
        else:
            power[1:] *= 2.0

    freqs = np.fft.rfftfreq(source.size, 1.0 / sample_rate_hz)
    below_20 = float(np.sum(power[freqs < 20.0]))
    below_50 = float(np.sum(power[freqs < 50.0]))
    total = float(np.sum(power))
    return below_20, below_50, total


def _low_frequency_stats(signal: np.ndarray, sample_rate_hz: int) -> LowFrequencyStats:
    source = np.asarray(signal, dtype=float)
    if source.size == 0:
        return LowFrequencyStats(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    mean = float(np.mean(source))
    below_20, below_50, total = _spectral_energies(source, sample_rate_hz)
    return LowFrequencyStats(
        mean=mean,
        minimum=float(np.min(source)),
        maximum=float(np.max(source)),
        rms=float(np.sqrt(np.mean(source ** 2))),
        ac_rms=float(np.sqrt(np.mean((source - mean) ** 2))),
        spectral_energy_below_20_hz=below_20,
        spectral_energy_below_50_hz=below_50,
        spectral_energy_total=total,
    )


def low_frequency_measurements(
    result: SimulationResult,
    final_audio: np.ndarray | None = None,
) -> list[SignalMeasurement]:
    """Measure low-frequency and DC content for physical and rendered signals."""

    start, stop = _steady_region(result)
    selected = selected_output_signal(result)
    rendered = normalized_chamber_pressure(result) if final_audio is None else np.asarray(final_audio, dtype=float)
    q_loss = np.zeros_like(result.q_b_total)
    net_flow = result.q_b_total - result.q_d_total - q_loss
    signals = [
        ("raw chamber pressure p_c", "Pa", result.p_c),
        ("vocal-tract pressure p_t", "Pa", result.p_t),
        ("net flow q_b - q_d - q_loss", "m^3/s", net_flow),
        ("raw selected output before normalization", "Pa", selected),
        ("final normalized audio", "normalized", rendered),
    ]
    return [
        SignalMeasurement(
            name=name,
            unit=unit,
            full=_low_frequency_stats(values, result.sample_rate_hz),
            steady=_low_frequency_stats(values[start:stop], result.sample_rate_hz),
        )
        for name, unit, values in signals
    ]


def _format_stats(stats: LowFrequencyStats) -> str:
    def percent(energy: float) -> float:
        return 100.0 * energy / stats.spectral_energy_total if stats.spectral_energy_total > 0.0 else 0.0

    return (
        f"mean={stats.mean:.6g}, min={stats.minimum:.6g}, max={stats.maximum:.6g}, "
        f"RMS={stats.rms:.6g}, AC RMS={stats.ac_rms:.6g}, "
        f"E<20Hz={stats.spectral_energy_below_20_hz:.6g} ({percent(stats.spectral_energy_below_20_hz):.2f}%), "
        f"E<50Hz={stats.spectral_energy_below_50_hz:.6g} ({percent(stats.spectral_energy_below_50_hz):.2f}%)"
    )


def _artifact_assessment(measurements: list[SignalMeasurement], wav_processing: str) -> list[str]:
    by_name = {measurement.name: measurement for measurement in measurements}
    p_c = by_name["raw chamber pressure p_c"].steady
    p_t = by_name["vocal-tract pressure p_t"].steady
    net_flow = by_name["net flow q_b - q_d - q_loss"].steady
    audio = by_name["final normalized audio"].steady

    p_c_dc_ratio = abs(p_c.mean) / p_c.ac_rms if p_c.ac_rms > 0.0 else 0.0
    p_t_dc_ratio = abs(p_t.mean) / p_t.ac_rms if p_t.ac_rms > 0.0 else 0.0
    flow_dc_ratio = abs(net_flow.mean) / net_flow.ac_rms if net_flow.ac_rms > 0.0 else 0.0
    audio_dc_ratio = abs(audio.mean) / audio.ac_rms if audio.ac_rms > 0.0 else 0.0

    if p_c_dc_ratio >= 0.5:
        chamber = (
            "yes: steady-state p_c has a large DC/equilibrium component "
            f"(abs(mean)/AC RMS={p_c_dc_ratio:.3g})."
        )
    else:
        chamber = (
            "not dominant: steady-state p_c DC is smaller than its AC motion "
            f"(abs(mean)/AC RMS={p_c_dc_ratio:.3g})."
        )

    if audio_dc_ratio >= 0.5:
        normalization = (
            "yes: normalized audio preserves the selected signal bias "
            f"(steady abs(mean)/AC RMS={audio_dc_ratio:.3g})."
        )
    else:
        normalization = (
            "not dominant in the measured final audio "
            f"(steady abs(mean)/AC RMS={audio_dc_ratio:.3g})."
        )

    return [
        f"physical chamber pressure drift/bias: {chamber}",
        (
            "breath attack/release envelope: secondary if full-note low-frequency energy exceeds "
            "steady-state energy; the steady-state table shows whether the artifact persists without attack/release."
        ),
        "output source selection: yes when WAV source is raw p_c, because the selected output contains the p_c bias.",
        f"normalization of a biased signal: {normalization}",
        (
            "final rendering layer: no separate acoustic output model is implemented; "
            f"the WAV path is {wav_processing}."
        ),
        f"vocal-tract DC contribution check: steady abs(mean)/AC RMS={p_t_dc_ratio:.3g}.",
        f"net-flow DC contribution check with q_loss=0: steady abs(mean)/AC RMS={flow_dc_ratio:.3g}.",
    ]


def diagnostics_text(
    result: SimulationResult,
    final_audio: np.ndarray | None = None,
    wav_processing: str = "peak normalization only",
) -> str:
    """Compute the minimal report requested for discussion."""

    if result.mode == "draw":
        active_name = "draw"
        active = result.x_d
        passive = result.x_b
    else:
        active_name = "blow"
        active = result.x_b
        passive = result.x_d

    start, stop = _steady_region(result)
    p_window = result.p_c[start:stop]
    p_t_window = result.p_t[start:stop]
    load_window = result.p_m_effective[start:stop] - result.p_m_static[start:stop]
    active_window = active[start:stop]
    passive_window = passive[start:stop]

    metrics = validation_metrics(result)
    targets = source_validation_targets(result.params.source_validation)
    f0 = metrics.fundamental_hz
    active_rms = float(np.sqrt(np.mean(active_window ** 2)))
    passive_rms = float(np.sqrt(np.mean(passive_window ** 2)))
    pressure_rms = float(np.sqrt(np.mean(p_window ** 2)))
    p_t_rms = float(np.sqrt(np.mean(p_t_window ** 2)))
    load_rms = float(np.sqrt(np.mean(load_window ** 2)))
    pressure_peak = float(np.max(np.abs(p_window))) if p_window.size else 0.0
    crest = pressure_peak / pressure_rms if pressure_rms > 0.0 else 0.0

    dp = np.diff(p_window) * result.sample_rate_hz
    dp_rms = float(np.sqrt(np.mean(dp ** 2))) if dp.size else 0.0
    sharpness = float(np.max(np.abs(dp)) / dp_rms) if dp_rms > 0.0 else 0.0

    near_b = float(100.0 * np.mean(result.gap_b[start:stop] <= 1.0e-6))
    near_d = float(100.0 * np.mean(result.gap_d[start:stop] <= 1.0e-6))
    motion_total = float(np.sqrt(np.mean(result.q_b_motion[start:stop] ** 2 + result.q_d_motion[start:stop] ** 2)))
    flow_total = float(np.sqrt(np.mean(result.q_b_total[start:stop] ** 2 + result.q_d_total[start:stop] ** 2)))
    motion_ratio = motion_total / flow_total if flow_total > 0.0 else 0.0

    p_ratios = harmonic_ratios(p_window, result.sample_rate_hz, f0)
    reed_ratios = harmonic_ratios(active_window, result.sample_rate_hz, f0)
    final_audio_signal = normalized_chamber_pressure(result) if final_audio is None else np.asarray(final_audio, dtype=float)
    measurements = low_frequency_measurements(result, final_audio_signal)
    steady_start_s = result.time_s[start] if len(result.time_s) else 0.0
    steady_stop_s = result.time_s[stop - 1] if stop > start and len(result.time_s) else steady_start_s

    lines = [
        f"mode: {result.mode}",
        f"parameter preset: {result.params.parameter_preset}",
        f"opening model: {result.params.opening_model}",
        f"source validation: {result.params.source_validation or 'none'}",
        f"estimated fundamental frequency: {f0:.2f} Hz",
        "harmonic labels: H1=f0, H2=2*f0, etc.; 0 Hz is the DC bin, not a harmonic.",
        f"active reed estimate: {active_name}",
        f"tract load enabled: {'yes' if result.params.vocal_tract_feedback_gain != 0.0 else 'no'}",
        f"vocal_tract_feedback_gain: {result.params.vocal_tract_feedback_gain:.6g}",
        f"WAV rendering: {wav_processing}",
        f"RMS p_t: {p_t_rms:.6g} Pa",
        f"RMS p_m_effective - p_m_static: {load_rms:.6g} Pa",
        f"active/passive RMS displacement ratio: {active_rms / passive_rms if passive_rms > 0.0 else 0.0:.3f}",
        f"active reed peak amplitude: {metrics.active_peak_amplitude_m * 1.0e6:.3f} micrometer",
        f"passive reed peak amplitude: {metrics.passive_peak_amplitude_m * 1.0e6:.3f} micrometer",
        f"active/passive peak amplitude ratio: {metrics.active_passive_ratio:.3f}",
        f"mean chamber pressure: {metrics.mean_chamber_pressure_pa:.6g} Pa",
        f"AC chamber pressure RMS: {metrics.ac_pressure_rms_pa:.6g} Pa",
        f"equivalent acoustic pressure amplitude sqrt(2)*AC_RMS: {metrics.equivalent_acoustic_amplitude_pa:.6g} Pa",
        f"chamber pressure RMS: {pressure_rms:.6g} Pa",
        f"chamber pressure peak: {pressure_peak:.6g} Pa",
        f"chamber pressure crest factor: {crest:.3f}",
        f"blow signed position crosses zero: {'yes' if metrics.blow_crosses_slot_plane else 'no'}",
        f"draw signed position crosses zero: {'yes' if metrics.draw_crosses_slot_plane else 'no'}",
        f"blow positive-side open percentage: {metrics.blow_positive_open_percent:.2f}%",
        f"blow negative-side open percentage: {metrics.blow_negative_open_percent:.2f}%",
        f"blow closed percentage: {metrics.blow_closed_percent:.2f}%",
        f"draw positive-side open percentage: {metrics.draw_positive_open_percent:.2f}%",
        f"draw negative-side open percentage: {metrics.draw_negative_open_percent:.2f}%",
        f"draw closed percentage: {metrics.draw_closed_percent:.2f}%",
        "p_c harmonic ratios H1-H10: " + ", ".join(f"{value:.3f}" for value in p_ratios),
        f"pressure H2/H1: {p_ratios[1] if len(p_ratios) > 1 else 0.0:.3f}",
        f"pressure H3/H1: {p_ratios[2] if len(p_ratios) > 2 else 0.0:.3f}",
        f"pressure H4/H1: {p_ratios[3] if len(p_ratios) > 3 else 0.0:.3f}",
        f"pressure fundamental is strongest harmonic: {'yes' if metrics.fundamental_is_strongest else 'no'}",
        "active reed harmonic ratios H1-H10: " + ", ".join(f"{value:.3f}" for value in reed_ratios),
        f"pressure peak sharpness: {sharpness:.3f}",
        f"near-closed percentage blow reed: {near_b:.2f}%",
        f"near-closed percentage draw reed: {near_d:.2f}%",
        f"motion-flow contribution ratio: {motion_ratio:.6f}",
        "q_loss in net-flow diagnosis: 0 (no separate loss flow is implemented in this model).",
        f"steady-state diagnosis window: {steady_start_s:.6g} s to {steady_stop_s:.6g} s",
        "",
    ]
    if targets is not None:
        def error(value: float, target: float) -> tuple[float, float]:
            absolute = value - target
            percent = 100.0 * absolute / target if target != 0.0 else 0.0
            return absolute, percent

        frequency_error = error(metrics.fundamental_hz, targets.played_frequency_hz)
        mean_pressure_error = error(metrics.mean_chamber_pressure_pa, targets.mean_chamber_pressure_pa)
        acoustic_error = error(
            metrics.equivalent_acoustic_amplitude_pa,
            targets.equivalent_acoustic_amplitude_pa,
        )
        ratio_error = error(metrics.active_passive_ratio, targets.active_passive_ratio)
        lines.extend(
            [
                "Source validation targets and errors:",
                f"- played frequency target: {targets.played_frequency_hz:.3f} Hz; error {frequency_error[0]:+.3f} Hz ({frequency_error[1]:+.2f}%)",
                f"- mean chamber pressure target: {targets.mean_chamber_pressure_pa:.3f} Pa; error {mean_pressure_error[0]:+.3f} Pa ({mean_pressure_error[1]:+.2f}%)",
                f"- equivalent acoustic amplitude target: {targets.equivalent_acoustic_amplitude_pa:.3f} Pa; error {acoustic_error[0]:+.3f} Pa ({acoustic_error[1]:+.2f}%)",
                f"- active reed H1 target: {targets.active_peak_amplitude_m * 1.0e6:.3f} micrometer",
                f"- passive reed H2 target: {targets.passive_peak_amplitude_m * 1.0e6:.3f} micrometer",
                f"- active/passive target: {targets.active_passive_ratio:.3f}; error {ratio_error[0]:+.3f} ({ratio_error[1]:+.2f}%)",
                f"- active mean playing opening target: {targets.active_mean_opening_m * 1.0e6:.3f} micrometer",
                f"- passive mean playing opening target: {targets.passive_mean_opening_m * 1.0e6:.3f} micrometer",
                "- qualitative target: fundamental strongest; reed motion near sinusoidal; pressure richer in harmonics.",
                "- mechanism target: sharp pressure features are associated with reed crossing and nonlinear valve flow.",
            ]
        )
        if metrics.passive_reed_dominates:
            lines.append("WARNING: passive reed dominates the source-targeted normal-blow run.")
        if len(p_ratios) > 1 and p_ratios[1] > 1.0:
            lines.append("WARNING: pressure second harmonic is stronger than the fundamental.")
        if metrics.through_slot_almost_always_open:
            lines.append("WARNING: at least one through-slot reed path is open for more than 99% of the steady window.")
        lines.append("")
    lines.append("Low-frequency/DC content, full note:")
    for measurement in measurements:
        lines.append(f"- {measurement.name} [{measurement.unit}]: {_format_stats(measurement.full)}")
    lines.append("")
    lines.append("Low-frequency/DC content, steady-state excluding attack/release:")
    for measurement in measurements:
        lines.append(f"- {measurement.name} [{measurement.unit}]: {_format_stats(measurement.steady)}")
    lines.append("")
    lines.append("Low-frequency artifact source assessment:")
    lines.extend(f"- {line}" for line in _artifact_assessment(measurements, wav_processing))
    return "\n".join(lines) + "\n"


def write_diagnostics(
    path: Path,
    result: SimulationResult,
    final_audio: np.ndarray | None = None,
    wav_processing: str = "peak normalization only",
) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = diagnostics_text(result, final_audio, wav_processing)
    path.write_text(text)
    return text


def _relative_error_percent(value: float, target: float) -> float:
    return 100.0 * abs(value - target) / abs(target) if target != 0.0 else 0.0


def _numeric_status(value: float, target: float, pass_percent: float, warn_percent: float) -> str:
    error = _relative_error_percent(value, target)
    if error <= pass_percent:
        return "PASS"
    if error <= warn_percent:
        return "WARN"
    return "FAIL"


def _parameter_table(values: list, heading: str) -> list[str]:
    lines = [
        f"## {heading}",
        "",
        "| Parameter | SI value | Original value | Source | Note |",
        "|---|---:|---|---|---|",
    ]
    for value in values:
        note = value.note.replace("|", "/")
        source = value.source_label.replace("|", "/")
        lines.append(
            f"| `{value.name}` | {value.value_si:.8g} {value.si_unit} | "
            f"{value.original_value} {value.original_unit} | {source} | {note} |"
        )
    lines.append("")
    return lines


def source_validation_report_text(result: SimulationResult) -> str:
    """Build a source-to-code calibration report for one targeted run."""

    targets = source_validation_targets(result.params.source_validation)
    if targets is None:
        raise ValueError("a source validation target is required for this report")
    metrics = validation_metrics(result)
    source_values = [
        value
        for value in result.params.provenance
        if value.category == ParameterCategory.SOURCE_DERIVED
    ]
    estimated_values = [
        value
        for value in result.params.provenance
        if value.category == ParameterCategory.PHYSICALLY_ESTIMATED
    ]
    assumptions = [
        value
        for value in result.params.provenance
        if value.category == ParameterCategory.MODEL_ASSUMPTION
    ]

    rows = [
        (
            "Played frequency",
            f"{targets.played_frequency_hz:.3f} Hz",
            f"{metrics.fundamental_hz:.3f} Hz",
            _numeric_status(metrics.fundamental_hz, targets.played_frequency_hz, 2.0, 5.0),
        ),
        (
            "Mean chamber pressure",
            f"{targets.mean_chamber_pressure_pa:.3f} Pa",
            f"{metrics.mean_chamber_pressure_pa:.3f} Pa",
            _numeric_status(metrics.mean_chamber_pressure_pa, targets.mean_chamber_pressure_pa, 20.0, 50.0),
        ),
        (
            "Equivalent acoustic amplitude",
            f"{targets.equivalent_acoustic_amplitude_pa:.3f} Pa",
            f"{metrics.equivalent_acoustic_amplitude_pa:.3f} Pa",
            _numeric_status(
                metrics.equivalent_acoustic_amplitude_pa,
                targets.equivalent_acoustic_amplitude_pa,
                20.0,
                50.0,
            ),
        ),
        (
            "Active reed peak amplitude",
            f"{targets.active_peak_amplitude_m * 1e6:.3f} micrometer",
            f"{metrics.active_peak_amplitude_m * 1e6:.3f} micrometer",
            _numeric_status(metrics.active_peak_amplitude_m, targets.active_peak_amplitude_m, 25.0, 60.0),
        ),
        (
            "Passive reed peak amplitude",
            f"{targets.passive_peak_amplitude_m * 1e6:.3f} micrometer",
            f"{metrics.passive_peak_amplitude_m * 1e6:.3f} micrometer",
            _numeric_status(metrics.passive_peak_amplitude_m, targets.passive_peak_amplitude_m, 25.0, 60.0),
        ),
        (
            "Active/passive amplitude ratio",
            f"{targets.active_passive_ratio:.3f}",
            f"{metrics.active_passive_ratio:.3f}",
            _numeric_status(metrics.active_passive_ratio, targets.active_passive_ratio, 25.0, 60.0),
        ),
        (
            "Active mean playing opening",
            f"{targets.active_mean_opening_m * 1e6:.3f} micrometer",
            f"{metrics.active_mean_position_m * 1e6:.3f} micrometer",
            _numeric_status(metrics.active_mean_position_m, targets.active_mean_opening_m, 10.0, 25.0),
        ),
        (
            "Passive mean playing opening",
            f"{targets.passive_mean_opening_m * 1e6:.3f} micrometer",
            f"{metrics.passive_mean_position_m * 1e6:.3f} micrometer",
            _numeric_status(metrics.passive_mean_position_m, targets.passive_mean_opening_m, 10.0, 25.0),
        ),
        (
            "Fundamental strongest",
            "yes",
            "yes" if metrics.fundamental_is_strongest else "no",
            "PASS" if metrics.fundamental_is_strongest else "FAIL",
        ),
        (
            "Closing/speaking reed is primary",
            "yes (Bahnson qualitative constraint)",
            "yes" if not metrics.passive_reed_dominates else "no",
            "PASS" if not metrics.passive_reed_dominates else "FAIL",
        ),
        (
            "Through-slot path not open >99%",
            "yes (model plausibility criterion)",
            "yes" if not metrics.through_slot_almost_always_open else "no",
            "PASS" if not metrics.through_slot_almost_always_open else "WARN",
        ),
    ]

    lines = [
        "# Source Validation Report",
        "",
        f"- Parameter preset: `{result.params.parameter_preset}`",
        f"- Opening model: `{result.params.opening_model}`",
        f"- Validation target: `{targets.name}`",
        f"- Target source: {targets.source_label}",
        "",
    ]
    lines.extend(_parameter_table(source_values, "SOURCE_DERIVED Parameters"))
    lines.extend(_parameter_table(estimated_values, "PHYSICALLY_ESTIMATED Parameters"))
    lines.extend(_parameter_table(assumptions, "MODEL_ASSUMPTION Parameters"))
    lines.extend(
        [
            "## Target Versus Achieved",
            "",
            "| Criterion | Target | Achieved | Status |",
            "|---|---:|---:|---|",
        ]
    )
    lines.extend(f"| {name} | {target} | {achieved} | **{status}** |" for name, target, achieved, status in rows)
    ratios = metrics.pressure_harmonic_ratios
    lines.extend(
        [
            "",
            "## Additional Achieved Metrics",
            "",
            f"- Pressure H2/H1: {ratios[1] if len(ratios) > 1 else 0.0:.4f}",
            f"- Pressure H3/H1: {ratios[2] if len(ratios) > 2 else 0.0:.4f}",
            f"- Pressure H4/H1: {ratios[3] if len(ratios) > 3 else 0.0:.4f}",
            f"- Blow opening percentages (positive/negative/closed): {metrics.blow_positive_open_percent:.2f}% / {metrics.blow_negative_open_percent:.2f}% / {metrics.blow_closed_percent:.2f}%",
            f"- Draw opening percentages (positive/negative/closed): {metrics.draw_positive_open_percent:.2f}% / {metrics.draw_negative_open_percent:.2f}% / {metrics.draw_closed_percent:.2f}%",
            f"- Blow reed crosses slot plane: {'yes' if metrics.blow_crosses_slot_plane else 'no'}",
            f"- Draw reed crosses slot plane: {'yes' if metrics.draw_crosses_slot_plane else 'no'}",
            "",
            "## Remaining Mismatch and Scope",
            "",
            "The report compares a reduced seven-state model with published normal-blow measurements; it is not a claim of full instrument realism. Millot directly supplies the reed oscillator values and selected validation targets. The chamber volume, effective pressure areas, slot widths, discharge coefficients, breath envelope, tract parameters, and calibrated through-slot thresholds/gains/leakage/smoothing remain assumptions unless independently measured.",
            "",
            "Bahnson is used for mounting, closing/opening direction, and speaking-reed plausibility, not for unsupported numerical constants. Bilbao motivates explicit states, units, stable direct integration, reproducible presets, and validation from physical states; it is not used as a harmonica-parameter source.",
            "",
        ]
    )
    return "\n".join(lines)


def write_source_validation_report(path: Path, result: SimulationResult) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = source_validation_report_text(result)
    path.write_text(text)
    return text


def validation_metrics_dict(result: SimulationResult) -> dict[str, object]:
    metrics = validation_metrics(result)
    ratios = metrics.pressure_harmonic_ratios
    return {
        "mode": result.mode,
        "parameter_preset": result.params.parameter_preset,
        "opening_model": result.params.opening_model,
        "source_validation": result.params.source_validation,
        "fundamental_hz": metrics.fundamental_hz,
        "mean_chamber_pressure_pa": metrics.mean_chamber_pressure_pa,
        "ac_pressure_rms_pa": metrics.ac_pressure_rms_pa,
        "equivalent_acoustic_amplitude_pa": metrics.equivalent_acoustic_amplitude_pa,
        "active_peak_amplitude_um": metrics.active_peak_amplitude_m * 1e6,
        "passive_peak_amplitude_um": metrics.passive_peak_amplitude_m * 1e6,
        "active_passive_ratio": metrics.active_passive_ratio,
        "pressure_h2_h1": ratios[1] if len(ratios) > 1 else 0.0,
        "pressure_h3_h1": ratios[2] if len(ratios) > 2 else 0.0,
        "pressure_h4_h1": ratios[3] if len(ratios) > 3 else 0.0,
        "fundamental_is_strongest": metrics.fundamental_is_strongest,
        "blow_positive_open_percent": metrics.blow_positive_open_percent,
        "blow_negative_open_percent": metrics.blow_negative_open_percent,
        "blow_closed_percent": metrics.blow_closed_percent,
        "draw_positive_open_percent": metrics.draw_positive_open_percent,
        "draw_negative_open_percent": metrics.draw_negative_open_percent,
        "draw_closed_percent": metrics.draw_closed_percent,
    }


def write_validation_metrics_json(path: Path, result: SimulationResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(validation_metrics_dict(result), indent=2) + "\n")
