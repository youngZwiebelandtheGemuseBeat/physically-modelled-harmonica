"""Compact validation plots for simulated state variables."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile

import numpy as np

_MPL_CACHE = Path(tempfile.gettempdir()) / "harmonica_minimal_matplotlib"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CACHE))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .output import estimate_fundamental_hz
from .simulate import SimulationResult


def _active_motion(result: SimulationResult) -> tuple[np.ndarray, str]:
    if result.mode == "draw":
        return result.x_d, "draw reed"
    return result.x_b, "blow reed"


def _analysis_window(result: SimulationResult) -> tuple[int, int]:
    start = min(max(0, int(0.35 * result.sample_rate_hz)), max(0, len(result.time_s) - 1))
    stop = min(len(result.time_s), max(start + 1, int(0.90 * len(result.time_s))))
    return start, stop


def _steady_window(result: SimulationResult, f0_hz: float) -> tuple[int, int]:
    if f0_hz > 0.0:
        length = int(round(3.0 * result.sample_rate_hz / f0_hz))
        length = min(max(length, 128), int(0.12 * result.sample_rate_hz))
    else:
        length = int(0.08 * result.sample_rate_hz)
    length = max(8, min(length, len(result.time_s)))

    preferred_start = int(0.60 * len(result.time_s))
    latest_start = max(0, len(result.time_s) - length)
    start = min(preferred_start, latest_start)
    stop = min(len(result.time_s), start + length)
    return start, max(start + 1, stop)


def _spectrum_db(signal: np.ndarray, sample_rate_hz: int) -> tuple[np.ndarray, np.ndarray]:
    centered = np.asarray(signal, dtype=float) - float(np.mean(signal))
    if centered.size < 8:
        return np.array([0.0]), np.array([-120.0])
    window = np.hanning(centered.size)
    magnitudes = np.abs(np.fft.rfft(centered * window))
    freqs = np.fft.rfftfreq(centered.size, 1.0 / sample_rate_hz)
    peak = float(np.max(magnitudes))
    if peak <= 0.0:
        return freqs, np.full_like(freqs, -120.0, dtype=float)
    normalized = np.maximum(magnitudes / peak, 1.0e-6)
    return freqs, 20.0 * np.log10(normalized)


def _mark_harmonics(ax: plt.Axes, f0_hz: float) -> None:
    if f0_hz <= 0.0:
        return
    ymin, ymax = ax.get_ylim()
    for harmonic in range(1, 4):
        frequency = harmonic * f0_hz
        if frequency > ax.get_xlim()[1]:
            continue
        ax.axvline(frequency, color="#555555", linewidth=0.8, linestyle=":", alpha=0.75)
        ax.text(
            frequency,
            ymax - 0.08 * (ymax - ymin),
            f"H{harmonic}",
            ha="center",
            va="top",
            fontsize=8,
            color="#333333",
        )


def _style_time_axis(ax: plt.Axes) -> None:
    ax.axhline(0.0, color="#333333", linewidth=0.8, alpha=0.75)
    ax.grid(True, color="#d8d8d8", linewidth=0.7, alpha=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def _style_spectrum_axis(ax: plt.Axes) -> None:
    ax.grid(True, color="#d8d8d8", linewidth=0.7, alpha=0.8)
    ax.set_xlim(0.0, 4000.0)
    ax.set_ylim(-80.0, 3.0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def write_validation_plot(path: Path, result: SimulationResult) -> None:
    """Generate the required compact validation figure."""

    path.parent.mkdir(parents=True, exist_ok=True)
    active_motion, active_label = _active_motion(result)
    analysis_start, analysis_stop = _analysis_window(result)
    f0 = estimate_fundamental_hz(active_motion[analysis_start:analysis_stop], result.sample_rate_hz)
    start, stop = _steady_window(result, f0)
    time_ms = 1000.0 * (result.time_s[start:stop] - result.time_s[start])

    freqs_reed, spec_reed = _spectrum_db(active_motion[analysis_start:analysis_stop], result.sample_rate_hz)
    freqs_p, spec_p = _spectrum_db(result.p_c[analysis_start:analysis_stop], result.sample_rate_hz)
    reed_band = freqs_reed <= 4000.0
    pressure_band = freqs_p <= 4000.0

    motion_status = "on" if result.params.motion_flow_enabled else "off"
    load_status = "on" if result.params.vocal_tract_feedback_gain != 0.0 else "off"
    pressure = result.params.mouth_pressure_pa
    title = (
        f"{result.mode} validation | f0 {f0:.1f} Hz | "
        f"tract-load {load_status} | motion-flow {motion_status} | mouth pressure {pressure:.0f} Pa"
    )

    colors = {
        "blow": "#2563a6",
        "draw": "#b24a3b",
        "pressure": "#27805d",
        "mouth_static": "#6b7280",
        "mouth_effective": "#0f766e",
        "reed_spectrum": "#7654a6",
        "pressure_spectrum": "#4d4d4d",
    }

    with plt.rc_context(
        {
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "figure.dpi": 160,
            "savefig.dpi": 160,
        }
    ):
        fig, axes = plt.subplots(
            6,
            1,
            figsize=(8.8, 10.0),
            gridspec_kw={"height_ratios": [1.0, 1.0, 1.0, 1.0, 1.15, 1.15]},
            constrained_layout=True,
        )
        fig.suptitle(title, fontweight="bold")

        axes[0].plot(time_ms, result.gap_b[start:stop] * 1.0e6, color=colors["blow"], linewidth=1.25)
        axes[0].set_ylabel("blow gap\n(um)")

        axes[1].plot(time_ms, result.gap_d[start:stop] * 1.0e6, color=colors["draw"], linewidth=1.25)
        axes[1].set_ylabel("draw gap\n(um)")

        axes[2].plot(time_ms, result.p_c[start:stop], color=colors["pressure"], linewidth=1.25)
        axes[2].set_ylabel("p_c\n(Pa)")

        axes[3].plot(
            time_ms,
            result.p_m_effective[start:stop],
            color=colors["mouth_effective"],
            linewidth=1.25,
            label="p_m_effective",
        )
        axes[3].plot(
            time_ms,
            result.p_m_static[start:stop],
            color=colors["mouth_static"],
            linewidth=1.0,
            linestyle="--",
            label="p_m_static",
        )
        axes[3].set_ylabel("mouth pressure\n(Pa)")
        axes[3].set_xlabel("time in steady-state window (ms)")
        axes[3].legend(loc="upper right", frameon=False, fontsize=8)

        for ax in axes[:4]:
            _style_time_axis(ax)
            ax.set_xlim(float(time_ms[0]), float(time_ms[-1]) if time_ms.size > 1 else 1.0)
        axes[0].tick_params(labelbottom=False)
        axes[1].tick_params(labelbottom=False)
        axes[2].tick_params(labelbottom=False)

        axes[4].plot(freqs_p[pressure_band], spec_p[pressure_band], color=colors["pressure_spectrum"], linewidth=1.1)
        axes[4].set_ylabel("p_c\n(dB)")
        axes[4].set_title("chamber pressure spectrum")
        _style_spectrum_axis(axes[4])
        _mark_harmonics(axes[4], f0)

        axes[5].plot(freqs_reed[reed_band], spec_reed[reed_band], color=colors["reed_spectrum"], linewidth=1.1)
        axes[5].set_ylabel("active reed\n(dB)")
        axes[5].set_xlabel("frequency (Hz)")
        axes[5].set_title(f"{active_label} spectrum")
        _style_spectrum_axis(axes[5])
        _mark_harmonics(axes[5], f0)

        fig.savefig(path)
        plt.close(fig)
