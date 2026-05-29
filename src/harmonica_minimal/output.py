"""CSV, WAV, and compact text export for simulated states."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
import wave

import numpy as np

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
    band = (freqs >= 60.0) & (freqs <= 2000.0)
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

    f0 = estimate_fundamental_hz(active_window, result.sample_rate_hz)
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
        f"estimated fundamental frequency: {f0:.2f} Hz",
        "harmonic labels: H1=f0, H2=2*f0, etc.; 0 Hz is the DC bin, not a harmonic.",
        f"active reed estimate: {active_name}",
        f"tract load enabled: {'yes' if result.params.vocal_tract_feedback_gain != 0.0 else 'no'}",
        f"vocal_tract_feedback_gain: {result.params.vocal_tract_feedback_gain:.6g}",
        f"WAV rendering: {wav_processing}",
        f"RMS p_t: {p_t_rms:.6g} Pa",
        f"RMS p_m_effective - p_m_static: {load_rms:.6g} Pa",
        f"active/passive RMS displacement ratio: {active_rms / passive_rms if passive_rms > 0.0 else 0.0:.3f}",
        f"chamber pressure RMS: {pressure_rms:.6g} Pa",
        f"chamber pressure crest factor: {crest:.3f}",
        "p_c harmonic ratios H1-H10: " + ", ".join(f"{value:.3f}" for value in p_ratios),
        "active reed harmonic ratios H1-H10: " + ", ".join(f"{value:.3f}" for value in reed_ratios),
        f"pressure peak sharpness: {sharpness:.3f}",
        f"near-closed percentage blow reed: {near_b:.2f}%",
        f"near-closed percentage draw reed: {near_d:.2f}%",
        f"motion-flow contribution ratio: {motion_ratio:.6f}",
        "q_loss in net-flow diagnosis: 0 (no separate loss flow is implemented in this model).",
        f"steady-state diagnosis window: {steady_start_s:.6g} s to {steady_stop_s:.6g} s",
        "",
        "Low-frequency/DC content, full note:",
    ]
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
