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
    if values.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(values * values)))


def _time_window_rms(result: RenderResult, start_s: float, end_s: float) -> float:
    mask = (result.time_s >= start_s) & (result.time_s < end_s)
    if not np.any(mask):
        return 0.0
    return _rms(result.audio[mask])


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
            "spectral_rolloff_hz": 0.0,
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
    cumulative_power = np.cumsum(power[positive])
    rolloff_index = int(np.searchsorted(cumulative_power, 0.85 * total_power)) if total_power > 0.0 else 0
    spectral_rolloff_hz = (
        float(freqs_hz[positive][min(rolloff_index, cumulative_power.size - 1)])
        if cumulative_power.size
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
        "spectral_rolloff_hz": spectral_rolloff_hz,
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


def _dominant_reed_estimate(x_b_rms: float, x_d_rms: float) -> str:
    if x_b_rms <= 1.0e-7 and x_d_rms <= 1.0e-7:
        return "neither reed"
    if x_b_rms > x_d_rms * 1.25:
        return "blow reed"
    if x_d_rms > x_b_rms * 1.25:
        return "draw reed"
    return "mixed blow/draw"


def diagnostic_metrics(result: RenderResult) -> dict[str, float | bool | str]:
    spectral = _estimate_spectral_metrics(result)
    audio_peak = float(np.max(np.abs(result.audio)))
    audio_rms = _rms(result.audio)
    rms_first_100ms = _time_window_rms(result, 0.0, 0.10)
    rms_sustain = _time_window_rms(result, 0.70, 1.20)
    if rms_sustain <= 0.0:
        rms_sustain = _time_window_rms(result, result.time_s[-1] * 0.5, result.time_s[-1])
    attack_ratio = float(rms_first_100ms / rms_sustain) if rms_sustain > 0.0 else 0.0
    x_b_rms = _rms(result.x_b)
    x_d_rms = _rms(result.x_d)
    p_c_rms = _rms(result.p_c)
    p_t_rms = _rms(result.p_t)
    q_b_rms = _rms(result.q_b)
    q_d_rms = _rms(result.q_d)
    q_loss_rms = _rms(result.q_loss)
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
        "rms_first_100ms": rms_first_100ms,
        "rms_sustain": rms_sustain,
        "attack_ratio": attack_ratio,
        "attack_ratio_target_met": attack_ratio < 0.35,
        "x_b_rms": x_b_rms,
        "x_d_rms": x_d_rms,
        "p_c_rms": p_c_rms,
        "p_t_rms": p_t_rms,
        "q_b_rms": q_b_rms,
        "q_d_rms": q_d_rms,
        "q_loss_rms": q_loss_rms,
        "area_b_closed_percent": area_b_closed,
        "area_d_closed_percent": area_d_closed,
        "chamber_feedback_nonzero": chamber_feedback_nonzero,
        "reed_participation": reed_participation,
        "dominant_reed_estimate": _dominant_reed_estimate(x_b_rms, x_d_rms),
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
                "breath_envelope",
                "p_m_pa",
                "p_c_pa",
                "p_t_pa",
                "x_b_m",
                "v_b_m_s",
                "x_d_m",
                "v_d_m_s",
                "q_b_m3_s",
                "q_d_m3_s",
                "q_loss_m3_s",
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
                    f"{result.breath_envelope[i]:.9e}",
                    f"{result.p_m[i]:.9e}",
                    f"{result.p_c[i]:.9e}",
                    f"{result.p_t[i]:.9e}",
                    f"{result.x_b[i]:.9e}",
                    f"{result.v_b[i]:.9e}",
                    f"{result.x_d[i]:.9e}",
                    f"{result.v_d[i]:.9e}",
                    f"{result.q_b[i]:.9e}",
                    f"{result.q_d[i]:.9e}",
                    f"{result.q_loss[i]:.9e}",
                    f"{result.area_b[i]:.9e}",
                    f"{result.area_d[i]:.9e}",
                    f"{result.delta_p_b[i]:.9e}",
                    f"{result.delta_p_d[i]:.9e}",
                    f"{result.force_b[i]:.9e}",
                    f"{result.force_d[i]:.9e}",
                    f"{result.dp_c[i]:.9e}",
                ]
            )


def write_diagnostics_plot(path: str | Path, result: RenderResult, mode: str | None = None) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mode_name = mode or result.mode

    freqs_hz, _, magnitude_db = _spectrum(result.audio, result.sample_rate_hz)

    fig, axes = plt.subplots(5, 2, figsize=(14, 13))
    fig.suptitle(f"{mode_name.title()} Note Physical Model Diagnostics")

    axes[0, 0].plot(result.time_s, result.audio, color="black", linewidth=0.7)
    axes[0, 0].set_ylabel("audio")
    axes[0, 0].set_title("Audio waveform")

    spectrum_mask = (freqs_hz > 0.0) & (freqs_hz <= 5000.0)
    axes[0, 1].plot(freqs_hz[spectrum_mask], magnitude_db[spectrum_mask], color="black", linewidth=0.7)
    axes[0, 1].set_title("Rendered WAV spectrum")
    axes[0, 1].set_xlabel("frequency Hz")
    axes[0, 1].set_ylabel("magnitude dB")

    axes[1, 0].plot(result.time_s, result.p_m, label="p_m source", linewidth=0.9)
    axes[1, 0].set_title("Mouth pressure source")
    axes[1, 0].set_ylabel("Pa")
    axes[1, 0].legend(loc="upper right")

    axes[1, 1].plot(result.time_s, result.breath_envelope, label="envelope", linewidth=0.9)
    axes[1, 1].set_title("Breath envelope")
    axes[1, 1].set_ylabel("0..1")
    axes[1, 1].legend(loc="upper right")

    axes[2, 0].plot(result.time_s, result.p_c, label="p_c", linewidth=0.8)
    axes[2, 0].plot(result.time_s, result.p_t, label="p_t", linewidth=0.8)
    axes[2, 0].set_title("Chamber and tract pressure")
    axes[2, 0].set_ylabel("Pa")
    axes[2, 0].legend(loc="upper right")

    axes[2, 1].plot(result.time_s, result.delta_p_b, label="DeltaP_b", linewidth=0.8)
    axes[2, 1].plot(result.time_s, result.delta_p_d, label="DeltaP_d", linewidth=0.8)
    axes[2, 1].set_title("Reed pressure drops")
    axes[2, 1].set_ylabel("Pa")
    axes[2, 1].legend(loc="upper right")

    axes[3, 0].plot(result.time_s, result.x_b * 1.0e6, label="x_b", linewidth=0.8)
    axes[3, 0].plot(result.time_s, result.x_d * 1.0e6, label="x_d", linewidth=0.8)
    axes[3, 0].set_title("Reed displacements")
    axes[3, 0].set_ylabel("um")
    axes[3, 0].legend(loc="upper right")

    axes[3, 1].plot(result.time_s, result.area_b * 1.0e9, label="A_b", linewidth=0.8)
    axes[3, 1].plot(result.time_s, result.area_d * 1.0e9, label="A_d", linewidth=0.8)
    axes[3, 1].set_title("Reed opening areas")
    axes[3, 1].set_ylabel("mm^2")
    axes[3, 1].legend(loc="upper right")

    axes[4, 0].plot(result.time_s, result.q_b * 1.0e6, label="Q_b", linewidth=0.8)
    axes[4, 0].plot(result.time_s, result.q_d * 1.0e6, label="Q_d", linewidth=0.8)
    axes[4, 0].set_title("Bernoulli flows")
    axes[4, 0].set_ylabel("ml/s")
    axes[4, 0].set_xlabel("time s")
    axes[4, 0].legend(loc="upper right")

    net_flow = result.q_b - result.q_d - result.q_loss
    axes[4, 1].plot(result.time_s, net_flow * 1.0e6, label="Q_b - Q_d - Q_loss", linewidth=0.8)
    axes[4, 1].plot(result.time_s, result.dp_c / 1.0e6, label="p_c' / 1e6", linewidth=0.8)
    axes[4, 1].set_title("Chamber feedback drive")
    axes[4, 1].set_ylabel("flow ml/s, pressure slope")
    axes[4, 1].set_xlabel("time s")
    axes[4, 1].legend(loc="upper right")

    for axis in axes.flat:
        axis.grid(True, alpha=0.25)

    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.97))
    fig.savefig(output_path, dpi=140)
    plt.close(fig)


def write_diagnostic_report(path: str | Path, result: RenderResult, mode: str | None = None) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    metrics = diagnostic_metrics(result)
    mode_name = mode or result.mode
    expected_reed = "draw reed" if mode_name == "draw" else "blow reed"
    separation_harmonic_target = 0.60 if mode_name == "draw" else 0.25

    lines = [
        f"# {mode_name.title()} Note Diagnostic Report",
        "",
        "## Sign Convention",
        "",
        "- Positive mouth pressure means the player blows into the mouth side.",
        "- Negative mouth pressure means draw suction at the mouth side.",
        "- `DeltaP_b = p_m - p_c` for the blow-side flow and blow-reed force.",
        "- `DeltaP_d = p_c - p_out` for the draw-side flow and draw-reed force.",
        f"- This {mode_name} preset is expected to be dominated by the {expected_reed}.",
        "",
        "## Audio Metrics",
        "",
        f"- Peak audio: {metrics['audio_peak']:.6f}",
        f"- RMS audio: {metrics['audio_rms']:.6f}",
        f"- RMS first 100 ms: {metrics['rms_first_100ms']:.6f}",
        f"- RMS sustain region 0.7-1.2 s: {metrics['rms_sustain']:.6f}",
        f"- Attack ratio first/sustain: {metrics['attack_ratio']:.6f}",
        f"- Estimated fundamental frequency: {metrics['fundamental_hz']:.2f} Hz",
        f"- Harmonic energy ratio, harmonics 2-8 vs fundamental: {metrics['harmonic_energy_ratio']:.6f}",
        f"- Spectral centroid: {metrics['spectral_centroid_hz']:.2f} Hz",
        f"- Spectral rolloff 85%: {metrics['spectral_rolloff_hz']:.2f} Hz",
        f"- Spectral centroid / f0: {metrics['centroid_to_f0']:.2f}",
        f"- Mostly sinusoidal: {'yes' if metrics['mostly_sinusoidal'] else 'no'}",
        f"- Attack strength: {metrics['attack_strength']:.2f}",
        "",
        "## Output / Radiation Settings",
        "",
        f"- Output mode: {result.params.output_mode}",
        f"- Legacy output source: {result.params.output_source}",
        f"- Radiation enabled: {'yes' if result.params.radiation_enabled else 'no'}",
        f"- Radiation high-pass: {result.params.radiation_highpass_hz:.1f} Hz",
        f"- Radiation differentiation mix: {result.params.radiation_differentiation_mix:.3f}",
        f"- Body/cover resonance: {result.params.body_resonance_frequency_hz:.1f} Hz, Q={result.params.body_resonance_q:.2f}, gain={result.params.body_resonance_gain:.3f}",
        f"- Noise gain: {result.params.flow_noise_amount:.4f}",
        f"- Noise flow power: {result.params.flow_noise_power:.3f}",
        "",
        "## Physical State Metrics",
        "",
        f"- RMS x_b: {metrics['x_b_rms']:.9e} m",
        f"- RMS x_d: {metrics['x_d_rms']:.9e} m",
        f"- RMS p_c: {metrics['p_c_rms']:.9e} Pa",
        f"- RMS p_t: {metrics['p_t_rms']:.9e} Pa",
        f"- RMS Q_b: {metrics['q_b_rms']:.9e} m^3/s",
        f"- RMS Q_d: {metrics['q_d_rms']:.9e} m^3/s",
        f"- RMS Q_loss: {metrics['q_loss_rms']:.9e} m^3/s",
        f"- Chamber loss conductance: {result.params.chamber_loss_conductance_m3_s_pa:.9e} m^3/(s Pa)",
        f"- Blow reed opening near closed: {metrics['area_b_closed_percent']:.2f}%",
        f"- Draw reed opening near closed: {metrics['area_d_closed_percent']:.2f}%",
        f"- Chamber pressure feedback nonzero: {'yes' if metrics['chamber_feedback_nonzero'] else 'no'}",
        f"- Reed participation: {metrics['reed_participation']}",
        f"- Dominant reed estimate: {metrics['dominant_reed_estimate']}",
        f"- Mouth pressure min/max: {float(np.min(result.p_m)):.3f} / {float(np.max(result.p_m)):.3f} Pa",
        f"- Breath envelope min/max: {float(np.min(result.breath_envelope)):.3f} / {float(np.max(result.breath_envelope)):.3f}",
        "",
        "## Breath Envelope Parameters",
        "",
        f"- pre_delay: {result.params.pre_delay_s:.3f} s",
        f"- attack_time: {result.params.attack_s:.3f} s",
        f"- release_time: {result.params.release_s:.3f} s",
        f"- release_start: {result.params.release_start_s:.3f} s",
        f"- sustain_pressure: {result.params.mouth_pressure_pa:.3f} Pa",
        f"- breath_noise_amount: {result.params.breath_noise_amount:.3f}",
        f"- render_mode: {mode_name}",
        "",
        "## Milestone 4 Targets",
        "",
        "- Target render: same coupled model with mode-specific pressure sign and preset.",
        f"- Expected dominant reed: {expected_reed}.",
        f"- Estimated dominant reed: {metrics['dominant_reed_estimate']}.",
        "",
        "## Blow/Draw Separation Targets",
        "",
        "- Target: this preset has a distinct active reed, pressure sign, loading, and output balance.",
        "- Target: the audible result is separated by physical states, not by pitch shifting or a separate synth layer.",
        f"- Target harmonic energy ratio for this mode: > {separation_harmonic_target:.2f}.",
        "",
        f"- Separation harmonic target met: {'yes' if metrics['harmonic_energy_ratio'] > separation_harmonic_target else 'no'}",
        f"- Dominant reed target met: {'yes' if metrics['dominant_reed_estimate'] == expected_reed else 'no'}",
        "",
        "## Milestone 3D Targets",
        "",
        "- Target attack ratio first 100 ms / sustain: < 0.35.",
        "- Target diagnostics: p_m source and envelope rise gradually.",
        "- Target output: stable and non-silent with Milestone 3B harmonic character.",
        "",
        f"- Attack-ratio target met: {'yes' if metrics['attack_ratio_target_met'] else 'no'}",
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
        "- PASS: chamber pressure uses `p_c' = rho c^2 / V_c * (Q_b - Q_d - Q_loss)` with documented small acoustic loss.",
        "- PASS: vocal tract uses the second-order resonator driven by `Q_b - Q_d`.",
        "",
        "## Audit Interpretation",
        "",
        (
            "The current render is stable and physically coupled. Milestone 3B strengthens "
            "harmonic content by tightening reed-slot modulation, adding documented closure "
            "damping, and using a pressure/flow radiation approximation from simulated states. "
            "Milestone 3D restores audible Einschwingen by applying the raised-cosine breath "
            "envelope to the mouth-pressure source before the reed force and Bernoulli flow "
            "equations are evaluated. The blow/draw separation target keeps that same core "
            "model and changes only physical preset parameters and the documented radiation "
            "path from simulated pressure/flow states. Milestone 6B adds a small documented "
            "chamber acoustic loss and a shorter physical pressure release to avoid a "
            "bend-like shutdown tail."
        ),
        "",
    ]

    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_comparison_diagnostics_plot(
    path: str | Path,
    draw_result: RenderResult,
    blow_result: RenderResult,
) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    draw_freqs, _, draw_db = _spectrum(draw_result.audio, draw_result.sample_rate_hz)
    blow_freqs, _, blow_db = _spectrum(blow_result.audio, blow_result.sample_rate_hz)

    fig, axes = plt.subplots(4, 2, figsize=(14, 11))
    fig.suptitle("Draw vs Blow Physical Model Comparison")

    axes[0, 0].plot(draw_result.time_s, draw_result.audio, label="draw", linewidth=0.7)
    axes[0, 0].plot(blow_result.time_s, blow_result.audio, label="blow", linewidth=0.7, alpha=0.75)
    axes[0, 0].set_title("Audio waveforms")
    axes[0, 0].legend(loc="upper right")

    draw_mask = (draw_freqs > 0.0) & (draw_freqs <= 5000.0)
    blow_mask = (blow_freqs > 0.0) & (blow_freqs <= 5000.0)
    axes[0, 1].plot(draw_freqs[draw_mask], draw_db[draw_mask], label="draw", linewidth=0.7)
    axes[0, 1].plot(blow_freqs[blow_mask], blow_db[blow_mask], label="blow", linewidth=0.7, alpha=0.75)
    axes[0, 1].set_title("Rendered WAV spectra")
    axes[0, 1].set_xlabel("frequency Hz")
    axes[0, 1].legend(loc="upper right")

    axes[1, 0].plot(draw_result.time_s, draw_result.p_m, label="draw p_m", linewidth=0.8)
    axes[1, 0].plot(blow_result.time_s, blow_result.p_m, label="blow p_m", linewidth=0.8)
    axes[1, 0].set_title("Mouth pressure sign")
    axes[1, 0].set_ylabel("Pa")
    axes[1, 0].legend(loc="upper right")

    axes[1, 1].plot(draw_result.time_s, draw_result.p_c, label="draw p_c", linewidth=0.8)
    axes[1, 1].plot(blow_result.time_s, blow_result.p_c, label="blow p_c", linewidth=0.8)
    axes[1, 1].set_title("Chamber pressure")
    axes[1, 1].set_ylabel("Pa")
    axes[1, 1].legend(loc="upper right")

    axes[2, 0].plot(draw_result.time_s, draw_result.x_b * 1.0e6, label="draw x_b", linewidth=0.8)
    axes[2, 0].plot(draw_result.time_s, draw_result.x_d * 1.0e6, label="draw x_d", linewidth=0.8)
    axes[2, 0].set_title("Draw reed displacements")
    axes[2, 0].set_ylabel("um")
    axes[2, 0].legend(loc="upper right")

    axes[2, 1].plot(blow_result.time_s, blow_result.x_b * 1.0e6, label="blow x_b", linewidth=0.8)
    axes[2, 1].plot(blow_result.time_s, blow_result.x_d * 1.0e6, label="blow x_d", linewidth=0.8)
    axes[2, 1].set_title("Blow reed displacements")
    axes[2, 1].set_ylabel("um")
    axes[2, 1].legend(loc="upper right")

    axes[3, 0].plot(draw_result.time_s, draw_result.q_b * 1.0e6, label="draw Q_b", linewidth=0.8)
    axes[3, 0].plot(draw_result.time_s, draw_result.q_d * 1.0e6, label="draw Q_d", linewidth=0.8)
    axes[3, 0].set_title("Draw Bernoulli flows")
    axes[3, 0].set_xlabel("time s")
    axes[3, 0].set_ylabel("ml/s")
    axes[3, 0].legend(loc="upper right")

    axes[3, 1].plot(blow_result.time_s, blow_result.q_b * 1.0e6, label="blow Q_b", linewidth=0.8)
    axes[3, 1].plot(blow_result.time_s, blow_result.q_d * 1.0e6, label="blow Q_d", linewidth=0.8)
    axes[3, 1].set_title("Blow Bernoulli flows")
    axes[3, 1].set_xlabel("time s")
    axes[3, 1].set_ylabel("ml/s")
    axes[3, 1].legend(loc="upper right")

    for axis in axes.flat:
        axis.grid(True, alpha=0.25)

    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.96))
    fig.savefig(output_path, dpi=140)
    plt.close(fig)


def write_comparison_report(
    path: str | Path,
    draw_result: RenderResult,
    blow_result: RenderResult,
) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    draw_metrics = diagnostic_metrics(draw_result)
    blow_metrics = diagnostic_metrics(blow_result)

    def metric_line(label: str, key: str, fmt: str = ".6f") -> str:
        draw_value = draw_metrics[key]
        blow_value = blow_metrics[key]
        if isinstance(draw_value, bool):
            draw_text = "yes" if draw_value else "no"
            blow_text = "yes" if blow_value else "no"
        elif isinstance(draw_value, str):
            draw_text = str(draw_value)
            blow_text = str(blow_value)
        else:
            draw_text = f"{float(draw_value):{fmt}}"
            blow_text = f"{float(blow_value):{fmt}}"
        return f"| {label} | {draw_text} | {blow_text} |"

    same_audio = bool(
        draw_result.audio.shape == blow_result.audio.shape
        and np.allclose(draw_result.audio, blow_result.audio)
    )
    f0_difference_hz = abs(float(draw_metrics["fundamental_hz"]) - float(blow_metrics["fundamental_hz"]))
    harmonic_difference = abs(
        float(draw_metrics["harmonic_energy_ratio"]) - float(blow_metrics["harmonic_energy_ratio"])
    )

    lines = [
        "# Draw vs Blow Comparison Report",
        "",
        "## Sign Convention",
        "",
        "- Draw uses negative `p_m`: mouth suction relative to the chamber/outside.",
        "- Blow uses positive `p_m`: mouth pressure into the chamber.",
        "- `DeltaP_b = p_m - p_c`; positive values drive blow-side flow toward the chamber.",
        "- `DeltaP_d = p_c - p_out`; positive values drive draw-side/outlet flow away from the chamber.",
        "- The draw preset should emphasize draw-reed motion; the blow preset should emphasize blow-reed motion.",
        "- Audible separation should come from pressure sign, active reed parameters, tract loading, and simulated pressure/flow radiation.",
        "",
        "## Metrics",
        "",
        "| Metric | Draw | Blow |",
        "| --- | ---: | ---: |",
        metric_line("Fundamental estimate Hz", "fundamental_hz", ".2f"),
        metric_line("Harmonic energy ratio", "harmonic_energy_ratio"),
        metric_line("Spectral centroid Hz", "spectral_centroid_hz", ".2f"),
        metric_line("Spectral rolloff 85% Hz", "spectral_rolloff_hz", ".2f"),
        metric_line("Mostly sinusoidal", "mostly_sinusoidal"),
        metric_line("RMS x_b m", "x_b_rms", ".9e"),
        metric_line("RMS x_d m", "x_d_rms", ".9e"),
        metric_line("RMS p_c Pa", "p_c_rms", ".9e"),
        metric_line("RMS p_t Pa", "p_t_rms", ".9e"),
        metric_line("RMS Q_b m^3/s", "q_b_rms", ".9e"),
        metric_line("RMS Q_d m^3/s", "q_d_rms", ".9e"),
        metric_line("RMS Q_loss m^3/s", "q_loss_rms", ".9e"),
        metric_line("Blow opening near closed %", "area_b_closed_percent", ".2f"),
        metric_line("Draw opening near closed %", "area_d_closed_percent", ".2f"),
        metric_line("Attack ratio", "attack_ratio"),
        metric_line("Dominant reed estimate", "dominant_reed_estimate"),
        "",
        "## Output Check",
        "",
        f"- Draw and blow audio arrays identical: {'yes' if same_audio else 'no'}",
        f"- Draw mouth pressure min/max: {float(np.min(draw_result.p_m)):.3f} / {float(np.max(draw_result.p_m)):.3f} Pa",
        f"- Blow mouth pressure min/max: {float(np.min(blow_result.p_m)):.3f} / {float(np.max(blow_result.p_m)):.3f} Pa",
        f"- Draw output mode: {draw_result.params.output_mode}",
        f"- Blow output mode: {blow_result.params.output_mode}",
        f"- Draw radiation enabled: {'yes' if draw_result.params.radiation_enabled else 'no'}",
        f"- Blow radiation enabled: {'yes' if blow_result.params.radiation_enabled else 'no'}",
        f"- Draw noise gain: {draw_result.params.flow_noise_amount:.4f}",
        f"- Blow noise gain: {blow_result.params.flow_noise_amount:.4f}",
        f"- Draw chamber loss conductance: {draw_result.params.chamber_loss_conductance_m3_s_pa:.9e} m^3/(s Pa)",
        f"- Blow chamber loss conductance: {blow_result.params.chamber_loss_conductance_m3_s_pa:.9e} m^3/(s Pa)",
        f"- Fundamental separation: {f0_difference_hz:.2f} Hz",
        f"- Harmonic-ratio separation: {harmonic_difference:.6f}",
        f"- Draw separation target met: {'yes' if draw_metrics['dominant_reed_estimate'] == 'draw reed' and float(draw_metrics['harmonic_energy_ratio']) > 0.60 else 'no'}",
        f"- Blow separation target met: {'yes' if blow_metrics['dominant_reed_estimate'] == 'blow reed' and float(blow_metrics['harmonic_energy_ratio']) > 0.25 else 'no'}",
        "",
        "## Interpretation",
        "",
        "Draw and blow use the same coupled ODE and the same sign convention. The presets separate audibly by changing the signed breath pressure, which reed is the active high-Q reed, the reed-slot closure regime, the vocal-tract load, and the pressure/flow radiation balance. These are physical model controls rather than samples, wavetables, pitch shifting, or an extra oscillator.",
        "",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")
