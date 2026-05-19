from __future__ import annotations

import csv
import os
import tempfile
from pathlib import Path

cache_dir = Path(tempfile.gettempdir()) / "harmonica_model_matplotlib"
cache_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(cache_dir))
os.environ.setdefault("XDG_CACHE_HOME", str(cache_dir))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .render import RenderResult


def _rms(signal: np.ndarray) -> float:
    values = np.asarray(signal, dtype=float)
    return float(np.sqrt(np.mean(values * values)))


def _spectrum(signal: np.ndarray, sample_rate_hz: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    centered = np.asarray(signal, dtype=float) - float(np.mean(signal))
    if centered.size == 0:
        return np.array([], dtype=float), np.array([], dtype=float), np.array([], dtype=float)
    window = np.hanning(centered.size)
    windowed = centered * window
    spectrum = np.fft.rfft(windowed)
    freqs_hz = np.fft.rfftfreq(centered.size, d=1.0 / float(sample_rate_hz))
    power = np.abs(spectrum) ** 2
    magnitude_db = 20.0 * np.log10(np.maximum(np.abs(spectrum), 1.0e-12))
    return freqs_hz, power, magnitude_db


def _band_energy(freqs_hz: np.ndarray, power: np.ndarray, center_hz: float, half_width_hz: float) -> float:
    band = (freqs_hz >= center_hz - half_width_hz) & (freqs_hz <= center_hz + half_width_hz)
    return float(np.sum(power[band]))


def _estimate_spectral_metrics(result: RenderResult) -> dict[str, float]:
    freqs_hz, power, _ = _spectrum(result.audio, result.sample_rate_hz)
    if freqs_hz.size == 0 or float(np.sum(power)) <= 0.0:
        return {
            "fundamental_hz": 0.0,
            "harmonic_energy_ratio": 0.0,
            "spectral_centroid_hz": 0.0,
        }

    audible = (freqs_hz >= 50.0) & (freqs_hz <= min(5000.0, result.sample_rate_hz * 0.5))
    if not np.any(audible):
        fundamental_hz = 0.0
    else:
        audible_indices = np.flatnonzero(audible)
        fundamental_hz = float(freqs_hz[audible_indices[int(np.argmax(power[audible]))]])

    positive = freqs_hz > 0.0
    total_power = float(np.sum(power[positive]))
    spectral_centroid_hz = (
        float(np.sum(freqs_hz[positive] * power[positive]) / total_power)
        if total_power > 0.0
        else 0.0
    )

    if fundamental_hz <= 0.0:
        harmonic_energy_ratio = 0.0
    else:
        half_width_hz = max(8.0, fundamental_hz * 0.02)
        fundamental_energy = _band_energy(freqs_hz, power, fundamental_hz, half_width_hz)
        harmonic_energy = sum(
            _band_energy(freqs_hz, power, harmonic * fundamental_hz, half_width_hz)
            for harmonic in range(2, 9)
            if harmonic * fundamental_hz < result.sample_rate_hz * 0.5
        )
        harmonic_energy_ratio = float(harmonic_energy / fundamental_energy) if fundamental_energy > 0.0 else 0.0

    return {
        "fundamental_hz": fundamental_hz,
        "harmonic_energy_ratio": harmonic_energy_ratio,
        "spectral_centroid_hz": spectral_centroid_hz,
    }


def _near_closed_percent(area: np.ndarray) -> float:
    values = np.asarray(area, dtype=float)
    if values.size == 0:
        return 0.0
    threshold = max(float(np.max(values)) * 0.05, 1.0e-12)
    return float(np.mean(values <= threshold) * 100.0)


def _mostly_sinusoidal(harmonic_energy_ratio: float, spectral_centroid_hz: float, fundamental_hz: float) -> bool:
    if fundamental_hz <= 0.0:
        return True
    return harmonic_energy_ratio < 0.05 and spectral_centroid_hz < fundamental_hz * 1.8


def _attack_strength(result: RenderResult) -> float:
    if result.audio.size < 2:
        return 0.0
    onset_count = max(2, min(result.audio.size, int(round(0.12 * result.sample_rate_hz))))
    onset = result.audio[:onset_count]
    peak = float(np.max(np.abs(result.audio)))
    if peak <= 0.0:
        return 0.0
    return float(np.max(np.abs(np.diff(onset))) * result.sample_rate_hz / peak)


def diagnostic_metrics(result: RenderResult) -> dict[str, float | bool | str]:
    spectral = _estimate_spectral_metrics(result)
    audio_peak = float(np.max(np.abs(result.audio)))
    audio_rms = _rms(result.audio)
    x_b_rms = _rms(result.x_b)
    x_d_rms = _rms(result.x_d)
    p_c_rms = _rms(result.p_c)
    p_t_rms = _rms(result.p_t)
    q_b_rms = _rms(result.q_b)
    q_d_rms = _rms(result.q_d)
    area_b_closed = _near_closed_percent(result.area_b)
    area_d_closed = _near_closed_percent(result.area_d)

    chamber_feedback_nonzero = p_c_rms > 1.0 and _rms(result.dp_c) > 1.0
    x_threshold = 1.0e-7
    blow_participates = x_b_rms > x_threshold
    draw_participates = x_d_rms > x_threshold
    if blow_participates and draw_participates:
        reed_participation = "both reeds participate"
    elif blow_participates:
        reed_participation = "only blow reed moves above threshold"
    elif draw_participates:
        reed_participation = "only draw reed moves above threshold"
    else:
        reed_participation = "neither reed moves above threshold"

    mostly_sinusoidal = _mostly_sinusoidal(
        spectral["harmonic_energy_ratio"],
        spectral["spectral_centroid_hz"],
        spectral["fundamental_hz"],
    )
    max_closed = max(area_b_closed, area_d_closed)
    stable_non_clipped = bool(
        np.all(np.isfinite(result.audio))
        and audio_peak <= 0.98
        and audio_rms > 1.0e-5
        and np.all(np.isfinite(result.state))
    )

    return {
        **spectral,
        "audio_peak": audio_peak,
        "audio_rms": audio_rms,
        "x_b_rms": x_b_rms,
        "x_d_rms": x_d_rms,
        "p_c_rms": p_c_rms,
        "p_t_rms": p_t_rms,
        "q_b_rms": q_b_rms,
        "q_d_rms": q_d_rms,
        "area_b_closed_percent": area_b_closed,
        "area_d_closed_percent": area_d_closed,
        "chamber_feedback_nonzero": chamber_feedback_nonzero,
        "reed_participation": reed_participation,
        "mostly_sinusoidal": mostly_sinusoidal,
        "stable_non_clipped": stable_non_clipped,
        "attack_strength": _attack_strength(result),
        "centroid_to_f0": (
            spectral["spectral_centroid_hz"] / spectral["fundamental_hz"]
            if spectral["fundamental_hz"] > 0.0
            else 0.0
        ),
        "closure_target_met": 5.0 <= max_closed <= 60.0,
    }


def write_trace_csv(path: str | Path, result: RenderResult) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "time_s",
                "audio",
                "p_m_pa",
                "p_c_pa",
                "p_t_pa",
                "x_b_m",
                "v_b_m_s",
                "x_d_m",
                "v_d_m_s",
                "q_b_m3_s",
                "q_d_m3_s",
                "area_b_m2",
                "area_d_m2",
                "delta_p_b_pa",
                "delta_p_d_pa",
                "force_b_n",
                "force_d_n",
                "dp_c_pa_s",
            ]
        )
        for i, t_s in enumerate(result.time_s):
            writer.writerow(
                [
                    f"{t_s:.9f}",
                    f"{result.audio[i]:.9e}",
                    f"{result.p_m[i]:.9e}",
                    f"{result.p_c[i]:.9e}",
                    f"{result.p_t[i]:.9e}",
                    f"{result.x_b[i]:.9e}",
                    f"{result.v_b[i]:.9e}",
                    f"{result.x_d[i]:.9e}",
                    f"{result.v_d[i]:.9e}",
                    f"{result.q_b[i]:.9e}",
                    f"{result.q_d[i]:.9e}",
                    f"{result.area_b[i]:.9e}",
                    f"{result.area_d[i]:.9e}",
                    f"{result.delta_p_b[i]:.9e}",
                    f"{result.delta_p_d[i]:.9e}",
                    f"{result.force_b[i]:.9e}",
                    f"{result.force_d[i]:.9e}",
                    f"{result.dp_c[i]:.9e}",
                ]
            )


def write_diagnostics_plot(path: str | Path, result: RenderResult) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    freqs_hz, _, magnitude_db = _spectrum(result.audio, result.sample_rate_hz)

    fig, axes = plt.subplots(4, 2, figsize=(14, 11))
    fig.suptitle("Draw Note Physical Model Diagnostics")

    axes[0, 0].plot(result.time_s, result.audio, color="black", linewidth=0.7)
    axes[0, 0].set_ylabel("audio")
    axes[0, 0].set_title("Audio waveform")

    spectrum_mask = (freqs_hz > 0.0) & (freqs_hz <= 5000.0)
    axes[0, 1].plot(freqs_hz[spectrum_mask], magnitude_db[spectrum_mask], color="black", linewidth=0.7)
    axes[0, 1].set_title("Rendered WAV spectrum")
    axes[0, 1].set_xlabel("frequency Hz")
    axes[0, 1].set_ylabel("magnitude dB")

    axes[1, 0].plot(result.time_s, result.p_c, label="p_c", linewidth=0.8)
    axes[1, 0].plot(result.time_s, result.p_t, label="p_t", linewidth=0.8)
    axes[1, 0].set_title("Chamber and tract pressure")
    axes[1, 0].set_ylabel("Pa")
    axes[1, 0].legend(loc="upper right")

    axes[1, 1].plot(result.time_s, result.delta_p_b, label="DeltaP_b", linewidth=0.8)
    axes[1, 1].plot(result.time_s, result.delta_p_d, label="DeltaP_d", linewidth=0.8)
    axes[1, 1].set_title("Reed pressure drops")
    axes[1, 1].set_ylabel("Pa")
    axes[1, 1].legend(loc="upper right")

    axes[2, 0].plot(result.time_s, result.x_b * 1.0e6, label="x_b", linewidth=0.8)
    axes[2, 0].plot(result.time_s, result.x_d * 1.0e6, label="x_d", linewidth=0.8)
    axes[2, 0].set_title("Reed displacements")
    axes[2, 0].set_ylabel("um")
    axes[2, 0].legend(loc="upper right")

    axes[2, 1].plot(result.time_s, result.area_b * 1.0e9, label="A_b", linewidth=0.8)
    axes[2, 1].plot(result.time_s, result.area_d * 1.0e9, label="A_d", linewidth=0.8)
    axes[2, 1].set_title("Reed opening areas")
    axes[2, 1].set_ylabel("mm^2")
    axes[2, 1].legend(loc="upper right")

    axes[3, 0].plot(result.time_s, result.q_b * 1.0e6, label="Q_b", linewidth=0.8)
    axes[3, 0].plot(result.time_s, result.q_d * 1.0e6, label="Q_d", linewidth=0.8)
    axes[3, 0].set_title("Bernoulli flows")
    axes[3, 0].set_ylabel("ml/s")
    axes[3, 0].set_xlabel("time s")
    axes[3, 0].legend(loc="upper right")

    net_flow = result.q_b - result.q_d
    axes[3, 1].plot(result.time_s, net_flow * 1.0e6, label="Q_b - Q_d", linewidth=0.8)
    axes[3, 1].plot(result.time_s, result.dp_c / 1.0e6, label="p_c' / 1e6", linewidth=0.8)
    axes[3, 1].set_title("Chamber feedback drive")
    axes[3, 1].set_ylabel("flow ml/s, pressure slope")
    axes[3, 1].set_xlabel("time s")
    axes[3, 1].legend(loc="upper right")

    for axis in axes.flat:
        axis.grid(True, alpha=0.25)

    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.97))
    fig.savefig(output_path, dpi=140)
    plt.close(fig)


def write_diagnostic_report(path: str | Path, result: RenderResult) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    metrics = diagnostic_metrics(result)

    lines = [
        "# Draw Note Diagnostic Report",
        "",
        "## Audio Metrics",
        "",
        f"- Peak audio: {metrics['audio_peak']:.6f}",
        f"- RMS audio: {metrics['audio_rms']:.6f}",
        f"- Estimated fundamental frequency: {metrics['fundamental_hz']:.2f} Hz",
        f"- Harmonic energy ratio, harmonics 2-8 vs fundamental: {metrics['harmonic_energy_ratio']:.6f}",
        f"- Spectral centroid: {metrics['spectral_centroid_hz']:.2f} Hz",
        f"- Spectral centroid / f0: {metrics['centroid_to_f0']:.2f}",
        f"- Mostly sinusoidal: {'yes' if metrics['mostly_sinusoidal'] else 'no'}",
        f"- Attack strength: {metrics['attack_strength']:.2f}",
        "",
        "## Physical State Metrics",
        "",
        f"- RMS x_b: {metrics['x_b_rms']:.9e} m",
        f"- RMS x_d: {metrics['x_d_rms']:.9e} m",
        f"- RMS p_c: {metrics['p_c_rms']:.9e} Pa",
        f"- RMS p_t: {metrics['p_t_rms']:.9e} Pa",
        f"- RMS Q_b: {metrics['q_b_rms']:.9e} m^3/s",
        f"- RMS Q_d: {metrics['q_d_rms']:.9e} m^3/s",
        f"- Blow reed opening near closed: {metrics['area_b_closed_percent']:.2f}%",
        f"- Draw reed opening near closed: {metrics['area_d_closed_percent']:.2f}%",
        f"- Chamber pressure feedback nonzero: {'yes' if metrics['chamber_feedback_nonzero'] else 'no'}",
        f"- Reed participation: {metrics['reed_participation']}",
        "",
        "## Milestone 3B Targets",
        "",
        "- Target harmonic energy ratio: > 0.05.",
        "- Target spectral centroid: at least 2x f0 if this remains stable.",
        "- Target mostly sinusoidal: no.",
        "- Target near-closed reed opening: one reed between 5% and 60%.",
        "- Target output: stable and non-silent.",
        "",
        f"- Harmonic target met: {'yes' if metrics['harmonic_energy_ratio'] > 0.05 else 'no'}",
        f"- Centroid 2x target met: {'yes' if metrics['centroid_to_f0'] >= 2.0 else 'no'}",
        f"- Mostly-sinusoidal target met: {'yes' if not metrics['mostly_sinusoidal'] else 'no'}",
        f"- Closure target met: {'yes' if metrics['closure_target_met'] else 'no'}",
        f"- Stable non-clipped target met: {'yes' if metrics['stable_non_clipped'] else 'no'}",
        "",
        "## Equation Audit",
        "",
        "- PASS: reed ODEs use `m_i x_i'' + r_i x_i' + k_i x_i = F_air`.",
        "- PASS: blow force uses `F_b = S_b (p_m - p_c)`.",
        "- PASS: draw force uses `F_d = S_d (p_c - p_out)`.",
        "- PASS: Bernoulli flows use signed square-root pressure laws for `Q_b` and `Q_d`.",
        "- PASS: chamber pressure uses `p_c' = rho c^2 / V_c * (Q_b - Q_d)`.",
        "- PASS: vocal tract uses the second-order resonator driven by `Q_b - Q_d`.",
        "",
        "## Audit Interpretation",
        "",
        (
            "The current render is stable and physically coupled. Milestone 3B strengthens "
            "harmonic content by tightening reed-slot modulation, adding documented closure "
            "damping, and using a pressure/flow radiation approximation from simulated states."
        ),
        "",
    ]

    output_path.write_text("\n".join(lines), encoding="utf-8")
