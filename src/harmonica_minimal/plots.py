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


def _spectrum_power_percent(signal: np.ndarray, sample_rate_hz: int) -> tuple[np.ndarray, np.ndarray]:
    floor = 1.0e-8
    centered = np.asarray(signal, dtype=float) - float(np.mean(signal))
    if centered.size < 8:
        return np.array([0.0]), np.array([floor])
    window = np.hanning(centered.size)
    power = np.abs(np.fft.rfft(centered * window)) ** 2
    freqs = np.fft.rfftfreq(centered.size, 1.0 / sample_rate_hz)
    peak = float(np.max(power))
    if peak <= 0.0:
        return freqs, np.full_like(freqs, floor, dtype=float)
    return freqs, np.maximum(100.0 * power / peak, floor)


def _mark_harmonics(ax: plt.Axes, f0_hz: float) -> None:
    if f0_hz <= 0.0:
        return
    for harmonic in range(1, 4):
        frequency = harmonic * f0_hz
        if frequency > ax.get_xlim()[1]:
            continue
        ax.axvline(frequency, color="#555555", linewidth=0.8, linestyle=":", alpha=0.75)
        ax.annotate(
            f"H{harmonic} {frequency:.1f} Hz",
            xy=(frequency, 0.96),
            xycoords=ax.get_xaxis_transform(),
            xytext=(6, 0),
            textcoords="offset points",
            ha="left",
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


def _presentation_f0(result: SimulationResult) -> float:
    active_motion, _ = _active_motion(result)
    analysis_start, analysis_stop = _analysis_window(result)
    return estimate_fundamental_hz(active_motion[analysis_start:analysis_stop], result.sample_rate_hz)


def _write_millot_style_spectrum_plot(path: Path, signal: np.ndarray, sample_rate_hz: int) -> None:
    freqs, power_percent = _spectrum_power_percent(signal, sample_rate_hz)
    band = freqs <= 8000.0

    with plt.rc_context(
        {
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "figure.dpi": 180,
            "savefig.dpi": 180,
        }
    ):
        fig, ax = plt.subplots(figsize=(7.2, 4.0), constrained_layout=True)
        ax.plot(freqs[band], power_percent[band], color="black", linewidth=0.75)
        ax.set_title("normalized power spectrum (% max.)")
        ax.set_xlabel("frequency (Hz)")
        ax.set_ylabel("power (% max.)")
        ax.set_xlim(0.0, 8000.0)
        ax.set_yscale("log")
        ax.set_ylim(1.0e-8, 1.0e2)
        ax.set_xticks(np.arange(0.0, 8001.0, 1000.0))
        ax.grid(axis="x", color="black", linestyle=":", linewidth=0.55, alpha=0.45)
        ax.grid(axis="y", color="#cfcfcf", linestyle=":", linewidth=0.45, alpha=0.6)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        fig.savefig(path)
        plt.close(fig)


def write_millot_style_spectra(output_dir: Path, result: SimulationResult) -> None:
    """Write Millot-style comparison spectra for active reed motion and chamber pressure."""

    output_dir.mkdir(parents=True, exist_ok=True)
    active_motion, _ = _active_motion(result)
    analysis_start, analysis_stop = _analysis_window(result)
    mode = result.mode

    _write_millot_style_spectrum_plot(
        output_dir / f"{mode}_millot_style_reed_spectrum.png",
        active_motion[analysis_start:analysis_stop],
        result.sample_rate_hz,
    )
    _write_millot_style_spectrum_plot(
        output_dir / f"{mode}_millot_style_pressure_spectrum.png",
        result.p_c[analysis_start:analysis_stop],
        result.sample_rate_hz,
    )


def plot_presentation_pressure_result(path: Path, result: SimulationResult) -> None:
    """Generate a two-panel pressure-only result figure for seminar slides."""

    path.parent.mkdir(parents=True, exist_ok=True)
    f0 = _presentation_f0(result)
    start, stop = _steady_window(result, f0)
    analysis_start, analysis_stop = _analysis_window(result)
    time_ms = 1000.0 * (result.time_s[start:stop] - result.time_s[start])

    freqs_p, spec_p = _spectrum_db(result.p_c[analysis_start:analysis_stop], result.sample_rate_hz)
    pressure_band = freqs_p <= 4000.0

    colors = {
        "pressure": "#27805d",
        "pressure_spectrum": "#4d4d4d",
    }
    mode_title = "Blow result" if result.mode == "blow" else "Draw result"
    subtitle = f"f0 {f0:.1f} Hz | mouth pressure {result.params.mouth_pressure_pa:.0f} Pa"

    with plt.rc_context(
        {
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "figure.dpi": 180,
            "savefig.dpi": 180,
        }
    ):
        fig, axes = plt.subplots(
            2,
            1,
            figsize=(8.8, 5.2),
            gridspec_kw={"height_ratios": [1.0, 1.15]},
            constrained_layout=True,
        )
        fig.suptitle(mode_title, fontweight="bold")
        axes[0].set_title(subtitle)

        axes[0].plot(time_ms, result.p_c[start:stop], color=colors["pressure"], linewidth=1.3)
        axes[0].set_ylabel("chamber pressure p_c (Pa)")
        axes[0].set_xlabel("time in steady-state window (ms)")
        _style_time_axis(axes[0])
        axes[0].set_xlim(float(time_ms[0]), float(time_ms[-1]) if time_ms.size > 1 else 1.0)

        axes[1].plot(freqs_p[pressure_band], spec_p[pressure_band], color=colors["pressure_spectrum"], linewidth=1.15)
        axes[1].set_title("chamber pressure spectrum")
        axes[1].set_ylabel("p_c (dB)")
        axes[1].set_xlabel("frequency (Hz)")
        _style_spectrum_axis(axes[1])
        _mark_harmonics(axes[1], f0)

        fig.savefig(path)
        plt.close(fig)


def write_tract_load_effect_plot(
    path: Path,
    loaded_results: list[SimulationResult],
    unloaded_results: list[SimulationResult],
) -> None:
    """Compare chamber pressure spectra with tract loading on and off."""

    pairs = []
    unloaded_by_mode = {result.mode: result for result in unloaded_results}
    for loaded in loaded_results:
        unloaded = unloaded_by_mode.get(loaded.mode)
        if unloaded is not None:
            pairs.append((loaded, unloaded))
    if not pairs:
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    colors = {
        "loaded": "#27805d",
        "unloaded": "#6b7280",
    }

    with plt.rc_context(
        {
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "figure.dpi": 180,
            "savefig.dpi": 180,
        }
    ):
        fig, axes = plt.subplots(
            len(pairs),
            1,
            figsize=(8.8, 3.2 * len(pairs)),
            squeeze=False,
            constrained_layout=True,
        )
        fig.suptitle("Tract-load effect", fontweight="bold")

        for ax, (loaded, unloaded) in zip(axes[:, 0], pairs):
            f0 = _presentation_f0(loaded)
            analysis_start, analysis_stop = _analysis_window(loaded)
            freqs_loaded, spec_loaded = _spectrum_db(
                loaded.p_c[analysis_start:analysis_stop],
                loaded.sample_rate_hz,
            )

            off_start, off_stop = _analysis_window(unloaded)
            freqs_unloaded, spec_unloaded = _spectrum_db(
                unloaded.p_c[off_start:off_stop],
                unloaded.sample_rate_hz,
            )
            loaded_band = freqs_loaded <= 4000.0
            unloaded_band = freqs_unloaded <= 4000.0

            ax.plot(
                freqs_unloaded[unloaded_band],
                spec_unloaded[unloaded_band],
                color=colors["unloaded"],
                linewidth=1.05,
                linestyle="--",
                label="tract-load off",
            )
            ax.plot(
                freqs_loaded[loaded_band],
                spec_loaded[loaded_band],
                color=colors["loaded"],
                linewidth=1.15,
                label="tract-load on",
            )
            ax.set_title(f"{loaded.mode} chamber pressure spectrum | f0 {f0:.1f} Hz")
            ax.set_ylabel("p_c (dB)")
            ax.set_xlabel("frequency (Hz)")
            _style_spectrum_axis(ax)
            _mark_harmonics(ax, f0)
            ax.legend(loc="upper right", frameon=False)

        fig.savefig(path)
        plt.close(fig)


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
    feedback_gain = result.params.vocal_tract_feedback_gain
    load_status = f"on eta_t={feedback_gain:.3g}" if feedback_gain != 0.0 else "off eta_t=0"
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
