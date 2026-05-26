"""CSV, WAV, and compact text export for simulated states."""

from __future__ import annotations

import csv
from pathlib import Path
import wave

import numpy as np

from .simulate import SimulationResult


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


def normalized_chamber_pressure(result: SimulationResult) -> np.ndarray:
    """Scale simulated chamber pressure to [-1, 1] without changing its source."""

    peak = float(np.max(np.abs(result.p_c)))
    if peak <= 0.0:
        return np.zeros_like(result.p_c)
    return result.p_c / peak


def write_pressure_wav(path: Path, result: SimulationResult) -> None:
    """Write normalized p_c(t) as 16-bit PCM."""

    path.parent.mkdir(parents=True, exist_ok=True)
    signal = normalized_chamber_pressure(result)
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


def diagnostics_text(result: SimulationResult) -> str:
    """Compute the minimal report requested for discussion."""

    if result.mode == "draw":
        active_name = "draw"
        active = result.x_d
        passive = result.x_b
    else:
        active_name = "blow"
        active = result.x_b
        passive = result.x_d

    start = min(max(0, int(0.35 * result.sample_rate_hz)), max(0, len(result.time_s) - 1))
    stop = min(len(result.time_s), max(start + 1, int(0.90 * len(result.time_s))))
    p_window = result.p_c[start:stop]
    p_t_window = result.p_t[start:stop]
    load_window = result.p_m_effective[start:stop] - result.p_m_static[start:stop]
    active_window = active[start:stop]
    passive_window = passive[start:stop]

    f0 = estimate_fundamental_hz(active_window, result.sample_rate_hz)
    active_rms = float(np.sqrt(np.mean(active_window * active_window)))
    passive_rms = float(np.sqrt(np.mean(passive_window * passive_window)))
    pressure_rms = float(np.sqrt(np.mean(p_window * p_window)))
    p_t_rms = float(np.sqrt(np.mean(p_t_window * p_t_window)))
    load_rms = float(np.sqrt(np.mean(load_window * load_window)))
    pressure_peak = float(np.max(np.abs(p_window))) if p_window.size else 0.0
    crest = pressure_peak / pressure_rms if pressure_rms > 0.0 else 0.0

    dp = np.diff(p_window) * result.sample_rate_hz
    dp_rms = float(np.sqrt(np.mean(dp * dp))) if dp.size else 0.0
    sharpness = float(np.max(np.abs(dp)) / dp_rms) if dp_rms > 0.0 else 0.0

    near_b = float(100.0 * np.mean(result.gap_b[start:stop] <= 1.0e-6))
    near_d = float(100.0 * np.mean(result.gap_d[start:stop] <= 1.0e-6))
    motion_total = float(np.sqrt(np.mean(result.q_b_motion[start:stop] ** 2 + result.q_d_motion[start:stop] ** 2)))
    flow_total = float(np.sqrt(np.mean(result.q_b_total[start:stop] ** 2 + result.q_d_total[start:stop] ** 2)))
    motion_ratio = motion_total / flow_total if flow_total > 0.0 else 0.0

    p_ratios = harmonic_ratios(p_window, result.sample_rate_hz, f0)
    reed_ratios = harmonic_ratios(active_window, result.sample_rate_hz, f0)

    lines = [
        f"mode: {result.mode}",
        f"estimated fundamental frequency: {f0:.2f} Hz",
        f"active reed estimate: {active_name}",
        f"tract load enabled: {'yes' if result.params.vocal_tract_feedback_gain != 0.0 else 'no'}",
        f"vocal_tract_feedback_gain: {result.params.vocal_tract_feedback_gain:.6g}",
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
    ]
    return "\n".join(lines) + "\n"


def write_diagnostics(path: Path, result: SimulationResult) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = diagnostics_text(result)
    path.write_text(text)
    return text
