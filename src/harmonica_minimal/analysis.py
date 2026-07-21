"""Shared time-window and spectrum helpers for model diagnostics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .simulate import SimulationResult


SPECTRUM_FLOOR_DB = -120.0
STEADY_SAFETY_MARGIN_S = 0.10
MAX_STEADY_WINDOW_S = 1.0


@dataclass(frozen=True)
class RelativeSpectrum:
    """A Hann-windowed magnitude spectrum normalized to its largest bin."""

    frequencies_hz: np.ndarray
    relative_db: np.ndarray


@dataclass(frozen=True)
class SteadyStateWindow:
    """Indices and provenance for a late window away from note boundaries."""

    start: int
    stop: int
    start_s: float
    stop_s: float
    pre_delay_s: float
    attack_end_s: float
    release_start_s: float
    safety_margin_s: float
    used_fallback: bool


def relative_spectrum(
    signal: np.ndarray,
    sample_rate_hz: int,
    floor_db: float = SPECTRUM_FLOOR_DB,
) -> RelativeSpectrum:
    """Return a finite mean-removed Hann/rFFT magnitude spectrum in relative dB."""

    source = np.asarray(signal, dtype=float).reshape(-1)
    if source.size == 0:
        return RelativeSpectrum(np.array([0.0]), np.array([floor_db]))

    source = np.nan_to_num(source, nan=0.0, posinf=0.0, neginf=0.0)
    if np.all(source == source[0]):
        centered = np.zeros_like(source)
    else:
        centered = source - float(np.mean(source))
    window = np.hanning(centered.size) if centered.size > 1 else np.ones(1)
    magnitude = np.abs(np.fft.rfft(centered * window))
    frequencies = np.fft.rfftfreq(centered.size, 1.0 / float(sample_rate_hz))
    peak = float(np.max(magnitude)) if magnitude.size else 0.0

    if not np.isfinite(peak) or peak <= np.finfo(float).tiny:
        relative_db = np.full(frequencies.shape, floor_db, dtype=float)
    else:
        floor_ratio = 10.0 ** (floor_db / 20.0)
        normalized = magnitude / peak
        relative_db = 20.0 * np.log10(np.maximum(normalized, floor_ratio))
        relative_db = np.nan_to_num(relative_db, nan=floor_db, posinf=0.0, neginf=floor_db)
    return RelativeSpectrum(frequencies, relative_db)


def select_steady_state_window(
    result: SimulationResult,
    safety_margin_s: float = STEADY_SAFETY_MARGIN_S,
    maximum_duration_s: float = MAX_STEADY_WINDOW_S,
) -> SteadyStateWindow:
    """Select a late analysis window after attack and before release."""

    sample_count = len(result.time_s)
    sample_rate_hz = max(1, int(result.sample_rate_hz))
    duration_s = sample_count / float(sample_rate_hz)
    pre_delay_s = 0.0
    attack_end_s = pre_delay_s + max(0.0, float(result.params.attack_s))
    release_start_s = max(0.0, duration_s - max(0.0, float(result.params.release_s)))
    margin_s = max(0.0, float(safety_margin_s))
    window_duration_s = max(0.02, float(maximum_duration_s))

    earliest_start_s = attack_end_s + margin_s
    requested_stop_s = release_start_s - margin_s
    requested_start_s = max(earliest_start_s, requested_stop_s - window_duration_s)
    start = int(np.ceil(requested_start_s * sample_rate_hz))
    stop = int(np.floor(requested_stop_s * sample_rate_hz))
    minimum_samples = min(sample_count, max(8, int(round(0.02 * sample_rate_hz))))
    used_fallback = start < 0 or stop > sample_count or stop - start < minimum_samples

    if used_fallback:
        start = int(np.floor(0.35 * sample_count))
        stop = int(np.ceil(0.80 * sample_count))
        if stop - start < minimum_samples:
            start = 0
            stop = sample_count

    start = min(max(0, start), sample_count)
    stop = min(max(start, stop), sample_count)
    if sample_count and stop <= start:
        start = 0
        stop = sample_count

    return SteadyStateWindow(
        start=start,
        stop=stop,
        start_s=start / float(sample_rate_hz),
        stop_s=stop / float(sample_rate_hz),
        pre_delay_s=pre_delay_s,
        attack_end_s=attack_end_s,
        release_start_s=release_start_s,
        safety_margin_s=margin_s,
        used_fallback=used_fallback,
    )
