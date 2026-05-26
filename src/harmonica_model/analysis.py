"""Audio-analysis helpers for validating and comparing rendered notes.

These routines do not create the harmonica sound. They measure an existing
WAV/audio array so the project can report pitch, harmonic content, spectral
centroid, attack time, and similarity to an optional reference recording.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tempfile

import numpy as np
import soundfile as sf
from scipy import signal

cache_dir = Path(tempfile.gettempdir()) / "harmonica_model_matplotlib"
cache_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(cache_dir))
os.environ.setdefault("XDG_CACHE_HOME", str(cache_dir))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


@dataclass(frozen=True)
class SignalAnalysis:
    """Summary measurements for one audio signal.

    The fields are intentionally explicit because reports and comparison plots
    use them directly when judging whether a render is stable, harmonic, and
    recognizably different from a pure sine-like tone.
    """

    sample_rate_hz: int
    duration_s: float
    fundamental_hz: float
    harmonic_amplitudes: list[float]
    harmonic_energy_ratio: float
    spectral_centroid_hz: float
    spectral_rolloff_hz: float
    attack_time_s: float
    rms_envelope_time_s: np.ndarray
    rms_envelope: np.ndarray
    spectrum_freqs_hz: np.ndarray
    spectrum_db: np.ndarray
    spectral_envelope_freqs_hz: np.ndarray
    spectral_envelope_db: np.ndarray


def read_wav_mono(path: str | Path) -> tuple[np.ndarray, int]:
    """Read any WAV as mono floating-point audio plus sample rate."""

    audio, sample_rate_hz = sf.read(Path(path), always_2d=True)
    mono = np.mean(np.asarray(audio, dtype=float), axis=1)
    return mono, int(sample_rate_hz)


def _spectrum(audio: np.ndarray, sample_rate_hz: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return frequency bins, power, and dB magnitude for an audio signal."""

    values = np.asarray(audio, dtype=float)
    if values.size == 0:
        return np.array([]), np.array([]), np.array([])
    centered = values - float(np.mean(values))
    window = np.hanning(centered.size)
    spec = np.fft.rfft(centered * window)
    freqs = np.fft.rfftfreq(centered.size, d=1.0 / float(sample_rate_hz))
    magnitude = np.abs(spec)
    power = magnitude * magnitude
    db = 20.0 * np.log10(np.maximum(magnitude, 1.0e-12))
    return freqs, power, db


def _rms_envelope(audio: np.ndarray, sample_rate_hz: int) -> tuple[np.ndarray, np.ndarray]:
    """Measure short-time RMS level so the attack can be estimated."""

    frame = max(256, int(round(0.025 * sample_rate_hz)))
    hop = max(64, int(round(0.005 * sample_rate_hz)))
    values = np.asarray(audio, dtype=float)
    if values.size < frame:
        rms = float(np.sqrt(np.mean(values * values))) if values.size else 0.0
        return np.array([0.0]), np.array([rms])
    times: list[float] = []
    envelope: list[float] = []
    for start in range(0, values.size - frame + 1, hop):
        frame_values = values[start : start + frame]
        envelope.append(float(np.sqrt(np.mean(frame_values * frame_values))))
        times.append((start + 0.5 * frame) / float(sample_rate_hz))
    return np.asarray(times), np.asarray(envelope)


def _fundamental_from_spectrum(freqs: np.ndarray, power: np.ndarray, sample_rate_hz: int) -> float:
    """Estimate fundamental as the strongest audible spectral peak."""

    if freqs.size == 0 or float(np.sum(power)) <= 0.0:
        return 0.0
    mask = (freqs >= 70.0) & (freqs <= min(1600.0, sample_rate_hz * 0.45))
    if not np.any(mask):
        return 0.0
    indices = np.flatnonzero(mask)
    return float(freqs[indices[int(np.argmax(power[mask]))]])


def _band_amplitude(freqs: np.ndarray, power: np.ndarray, center_hz: float) -> float:
    """Return total amplitude around one expected harmonic frequency."""

    half_width_hz = max(8.0, center_hz * 0.018)
    mask = (freqs >= center_hz - half_width_hz) & (freqs <= center_hz + half_width_hz)
    return float(np.sqrt(np.sum(power[mask]))) if np.any(mask) else 0.0


def _attack_time(times: np.ndarray, envelope: np.ndarray) -> float:
    """Estimate time between 10% and 90% of peak RMS envelope."""

    if envelope.size == 0:
        return 0.0
    peak = float(np.max(envelope))
    if peak <= 0.0:
        return 0.0
    start_candidates = np.flatnonzero(envelope >= 0.1 * peak)
    end_candidates = np.flatnonzero(envelope >= 0.9 * peak)
    if start_candidates.size == 0 or end_candidates.size == 0:
        return 0.0
    start = int(start_candidates[0])
    end = int(end_candidates[end_candidates >= start][0]) if np.any(end_candidates >= start) else start
    return max(0.0, float(times[end] - times[start]))


def _spectral_rolloff(freqs: np.ndarray, power: np.ndarray, percentile: float = 0.85) -> float:
    """Return frequency below which `percentile` of spectral power lies."""

    positive = freqs > 0.0
    if not np.any(positive):
        return 0.0
    cumulative = np.cumsum(power[positive])
    total = float(cumulative[-1]) if cumulative.size else 0.0
    if total <= 0.0:
        return 0.0
    index = int(np.searchsorted(cumulative, percentile * total))
    return float(freqs[positive][min(index, cumulative.size - 1)])


def _spectral_envelope(freqs: np.ndarray, db: np.ndarray, sample_rate_hz: int) -> tuple[np.ndarray, np.ndarray]:
    """Build a smoothed high-level spectral envelope for plotting."""

    max_hz = min(8000.0, sample_rate_hz * 0.45)
    mask = (freqs > 0.0) & (freqs <= max_hz)
    if not np.any(mask):
        return np.array([]), np.array([])
    selected_freqs = freqs[mask]
    selected_db = db[mask]
    bin_count = 96
    edges = np.linspace(0.0, max_hz, bin_count + 1)
    envelope_freqs: list[float] = []
    envelope_db: list[float] = []
    for low, high in zip(edges[:-1], edges[1:]):
        band = (selected_freqs >= low) & (selected_freqs < high)
        if np.any(band):
            envelope_freqs.append(float(0.5 * (low + high)))
            envelope_db.append(float(np.max(selected_db[band])))
    if len(envelope_db) >= 7:
        smoothed = signal.savgol_filter(np.asarray(envelope_db), 7, 2)
    else:
        smoothed = np.asarray(envelope_db)
    return np.asarray(envelope_freqs), np.asarray(smoothed)


def analyze_audio(audio: np.ndarray, sample_rate_hz: int) -> SignalAnalysis:
    """Measure pitch, harmonics, spectrum, and attack for an audio array."""

    values = np.asarray(audio, dtype=float)
    freqs, power, db = _spectrum(values, sample_rate_hz)
    f0 = _fundamental_from_spectrum(freqs, power, sample_rate_hz)
    harmonic_amplitudes = [
        _band_amplitude(freqs, power, harmonic * f0) if f0 > 0.0 else 0.0
        for harmonic in range(1, 13)
    ]
    fundamental_energy = harmonic_amplitudes[0] ** 2
    harmonic_energy = sum(amplitude * amplitude for amplitude in harmonic_amplitudes[1:])
    harmonic_ratio = harmonic_energy / fundamental_energy if fundamental_energy > 0.0 else 0.0
    positive = freqs > 0.0
    total_power = float(np.sum(power[positive])) if np.any(positive) else 0.0
    centroid = (
        float(np.sum(freqs[positive] * power[positive]) / total_power)
        if total_power > 0.0
        else 0.0
    )
    envelope_times, envelope = _rms_envelope(values, sample_rate_hz)
    spectral_env_freqs, spectral_env_db = _spectral_envelope(freqs, db, sample_rate_hz)
    return SignalAnalysis(
        sample_rate_hz=sample_rate_hz,
        duration_s=values.size / float(sample_rate_hz) if sample_rate_hz > 0 else 0.0,
        fundamental_hz=f0,
        harmonic_amplitudes=harmonic_amplitudes,
        harmonic_energy_ratio=float(harmonic_ratio),
        spectral_centroid_hz=centroid,
        spectral_rolloff_hz=_spectral_rolloff(freqs, power),
        attack_time_s=_attack_time(envelope_times, envelope),
        rms_envelope_time_s=envelope_times,
        rms_envelope=envelope,
        spectrum_freqs_hz=freqs,
        spectrum_db=db,
        spectral_envelope_freqs_hz=spectral_env_freqs,
        spectral_envelope_db=spectral_env_db,
    )


def analyze_wav(path: str | Path) -> SignalAnalysis:
    """Read a WAV from disk and run `analyze_audio()` on it."""

    audio, sample_rate_hz = read_wav_mono(path)
    return analyze_audio(audio, sample_rate_hz)


def write_analysis_report(path: str | Path, title: str, analysis: SignalAnalysis) -> None:
    """Write a Markdown report containing the analysis numbers."""

    lines = [
        f"# {title}",
        "",
        f"- Duration: {analysis.duration_s:.3f} s",
        f"- Sample rate: {analysis.sample_rate_hz} Hz",
        f"- Fundamental estimate: {analysis.fundamental_hz:.2f} Hz",
        f"- Harmonic energy ratio, harmonics 2-12 vs fundamental: {analysis.harmonic_energy_ratio:.6f}",
        f"- Spectral centroid: {analysis.spectral_centroid_hz:.2f} Hz",
        f"- Spectral rolloff 85%: {analysis.spectral_rolloff_hz:.2f} Hz",
        f"- Attack time, 10% to 90% RMS envelope: {analysis.attack_time_s:.3f} s",
        "",
        "## Harmonic Amplitudes",
        "",
        "| Harmonic | Frequency Hz | Relative amplitude |",
        "| ---: | ---: | ---: |",
    ]
    fundamental = analysis.harmonic_amplitudes[0] if analysis.harmonic_amplitudes else 0.0
    for index, amplitude in enumerate(analysis.harmonic_amplitudes, start=1):
        relative = amplitude / fundamental if fundamental > 0.0 else 0.0
        lines.append(f"| {index} | {index * analysis.fundamental_hz:.2f} | {relative:.6f} |")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_analysis_plot(path: str | Path, title: str, analysis: SignalAnalysis) -> None:
    """Write a four-panel PNG showing envelope, spectrum, and harmonics."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle(title)

    axes[0, 0].plot(analysis.rms_envelope_time_s, analysis.rms_envelope, linewidth=0.9)
    axes[0, 0].set_title("RMS envelope")
    axes[0, 0].set_xlabel("time s")

    mask = (analysis.spectrum_freqs_hz > 0.0) & (analysis.spectrum_freqs_hz <= 5000.0)
    axes[0, 1].plot(analysis.spectrum_freqs_hz[mask], analysis.spectrum_db[mask], linewidth=0.7)
    axes[0, 1].set_title("Spectrum")
    axes[0, 1].set_xlabel("frequency Hz")
    axes[0, 1].set_ylabel("dB")

    harmonics = np.arange(1, 13)
    fundamental = analysis.harmonic_amplitudes[0] if analysis.harmonic_amplitudes else 0.0
    relative = [
        amplitude / fundamental if fundamental > 0.0 else 0.0
        for amplitude in analysis.harmonic_amplitudes
    ]
    axes[1, 0].bar(harmonics, relative)
    axes[1, 0].set_title("Harmonic amplitudes 1-12")
    axes[1, 0].set_xlabel("harmonic")

    axes[1, 1].plot(analysis.spectral_envelope_freqs_hz, analysis.spectral_envelope_db, linewidth=0.9)
    axes[1, 1].set_title("Spectral envelope")
    axes[1, 1].set_xlabel("frequency Hz")
    axes[1, 1].set_ylabel("dB")

    for axis in axes.flat:
        axis.grid(True, alpha=0.25)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.95))
    fig.savefig(output_path, dpi=140)
    plt.close(fig)


def comparison_score(synthetic: SignalAnalysis, reference: SignalAnalysis) -> float:
    """Return a bounded similarity score between synthetic and reference audio.

    The score compares analysis features only. Reference audio is never used
    as a source for rendering.
    """

    if reference.fundamental_hz <= 0.0 or synthetic.fundamental_hz <= 0.0:
        return 0.0
    centroid_error = abs(synthetic.spectral_centroid_hz - reference.spectral_centroid_hz) / max(reference.spectral_centroid_hz, 1.0)
    harmonic_error = abs(synthetic.harmonic_energy_ratio - reference.harmonic_energy_ratio) / max(reference.harmonic_energy_ratio, 0.05)
    rolloff_error = abs(synthetic.spectral_rolloff_hz - reference.spectral_rolloff_hz) / max(reference.spectral_rolloff_hz, 1.0)
    synthetic_base = synthetic.harmonic_amplitudes[0] if synthetic.harmonic_amplitudes else 0.0
    reference_base = reference.harmonic_amplitudes[0] if reference.harmonic_amplitudes else 0.0
    synthetic_harmonics = np.asarray(
        [value / synthetic_base if synthetic_base > 0.0 else 0.0 for value in synthetic.harmonic_amplitudes]
    )
    reference_harmonics = np.asarray(
        [value / reference_base if reference_base > 0.0 else 0.0 for value in reference.harmonic_amplitudes]
    )
    harmonic_vectors = synthetic_harmonics - reference_harmonics
    harmonic_norm = float(np.linalg.norm(harmonic_vectors)) / max(float(np.linalg.norm(reference_harmonics)), 1.0e-9)
    return float(1.0 / (1.0 + centroid_error + harmonic_error + 0.5 * rolloff_error + 0.5 * harmonic_norm))


def write_reference_comparison(
    report_path: str | Path,
    plot_path: str | Path,
    synthetic: SignalAnalysis,
    reference: SignalAnalysis,
) -> None:
    """Write Markdown and PNG comparison between rendered and reference audio."""

    score = comparison_score(synthetic, reference)
    lines = [
        "# Synthetic vs Reference Comparison",
        "",
        f"- Similarity score: {score:.6f}",
        f"- Synthetic f0: {synthetic.fundamental_hz:.2f} Hz",
        f"- Reference f0: {reference.fundamental_hz:.2f} Hz",
        f"- Synthetic harmonic energy ratio: {synthetic.harmonic_energy_ratio:.6f}",
        f"- Reference harmonic energy ratio: {reference.harmonic_energy_ratio:.6f}",
        f"- Synthetic spectral centroid: {synthetic.spectral_centroid_hz:.2f} Hz",
        f"- Reference spectral centroid: {reference.spectral_centroid_hz:.2f} Hz",
        f"- Synthetic rolloff 85%: {synthetic.spectral_rolloff_hz:.2f} Hz",
        f"- Reference rolloff 85%: {reference.spectral_rolloff_hz:.2f} Hz",
        f"- Synthetic attack time: {synthetic.attack_time_s:.3f} s",
        f"- Reference attack time: {reference.attack_time_s:.3f} s",
        "",
        "Reference WAVs are used only for analysis and comparison. They are not used as a synthesis source.",
        "",
    ]
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text("\n".join(lines), encoding="utf-8")

    output_path = Path(plot_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle("Synthetic vs Reference")

    axes[0, 0].plot(reference.rms_envelope_time_s, reference.rms_envelope, label="reference", linewidth=0.9)
    axes[0, 0].plot(synthetic.rms_envelope_time_s, synthetic.rms_envelope, label="synthetic", linewidth=0.9)
    axes[0, 0].set_title("RMS envelope")
    axes[0, 0].legend(loc="upper right")

    ref_mask = (reference.spectrum_freqs_hz > 0.0) & (reference.spectrum_freqs_hz <= 5000.0)
    syn_mask = (synthetic.spectrum_freqs_hz > 0.0) & (synthetic.spectrum_freqs_hz <= 5000.0)
    axes[0, 1].plot(reference.spectrum_freqs_hz[ref_mask], reference.spectrum_db[ref_mask], label="reference", linewidth=0.7)
    axes[0, 1].plot(synthetic.spectrum_freqs_hz[syn_mask], synthetic.spectrum_db[syn_mask], label="synthetic", linewidth=0.7)
    axes[0, 1].set_title("Spectrum")
    axes[0, 1].legend(loc="upper right")

    harmonics = np.arange(1, 13)
    ref_base = reference.harmonic_amplitudes[0] if reference.harmonic_amplitudes else 0.0
    syn_base = synthetic.harmonic_amplitudes[0] if synthetic.harmonic_amplitudes else 0.0
    ref_rel = [v / ref_base if ref_base > 0.0 else 0.0 for v in reference.harmonic_amplitudes]
    syn_rel = [v / syn_base if syn_base > 0.0 else 0.0 for v in synthetic.harmonic_amplitudes]
    axes[1, 0].bar(harmonics - 0.18, ref_rel, width=0.36, label="reference")
    axes[1, 0].bar(harmonics + 0.18, syn_rel, width=0.36, label="synthetic")
    axes[1, 0].set_title("Harmonic amplitudes 1-12")
    axes[1, 0].legend(loc="upper right")

    axes[1, 1].plot(reference.spectral_envelope_freqs_hz, reference.spectral_envelope_db, label="reference", linewidth=0.9)
    axes[1, 1].plot(synthetic.spectral_envelope_freqs_hz, synthetic.spectral_envelope_db, label="synthetic", linewidth=0.9)
    axes[1, 1].set_title("Spectral envelope")
    axes[1, 1].legend(loc="upper right")

    for axis in axes.flat:
        axis.grid(True, alpha=0.25)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.95))
    fig.savefig(output_path, dpi=140)
    plt.close(fig)
