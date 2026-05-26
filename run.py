"""Command-line workflow for rendering and auditing the harmonica model.

This script wires together the package modules:

1. choose draw/blow parameters,
2. optionally adjust breath and output controls from CLI arguments,
3. run the offline ODE renderer,
4. write WAV/CSV/diagnostic files, and
5. optionally run sweeps, calibration, or reference analysis.

The physical formulas are not defined here. They live in
`src/harmonica_model/equations.py`; this file is the operator interface.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from math import sqrt
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from harmonica_model.audio import write_wav
from harmonica_model.analysis import (
    analyze_audio,
    analyze_wav,
    comparison_score,
    write_analysis_plot,
    write_analysis_report,
    write_reference_comparison,
)
from harmonica_model.diagnostics import (
    diagnostic_metrics,
    write_comparison_diagnostics_plot,
    write_comparison_report,
    write_diagnostic_report,
    write_diagnostics_plot,
    write_trace_csv,
)
from harmonica_model.params import BLOW_PARAMS, DEFAULT_PARAMS, DRAW_PARAMS, ModelParams, ReedParams, RenderConfig
from harmonica_model.render import RenderResult, render_draw_note, render_note


def _reed_with_q(reed: ReedParams, quality_factor: float) -> ReedParams:
    """Return a reed with damping recalculated from a requested Q factor."""

    omega = sqrt(reed.stiffness_n_m / reed.mass_kg)
    return replace(reed, damping_kg_s=reed.mass_kg * omega / quality_factor)


def _draw_reed_variant(
    params: ModelParams,
    *,
    rest_opening_m: float,
    displacement_to_gap: float,
    quality_factor: float,
    closure_damping_kg_s: float | None = None,
) -> ModelParams:
    """Return draw-note parameters with a modified draw reed opening regime."""

    draw_reed = _reed_with_q(params.draw_reed, quality_factor)
    closing_displacement_m = -rest_opening_m / displacement_to_gap
    if closure_damping_kg_s is None:
        closure_damping_kg_s = draw_reed.closure_damping_kg_s
    draw_reed = replace(
        draw_reed,
        rest_opening_m=rest_opening_m,
        displacement_to_gap=displacement_to_gap,
        closing_displacement_m=closing_displacement_m,
        closure_damping_kg_s=closure_damping_kg_s,
    )
    return replace(params, draw_reed=draw_reed)


def _reed_opening_variant(
    reed: ReedParams,
    *,
    rest_opening_m: float | None = None,
    displacement_to_gap: float | None = None,
    quality_factor: float | None = None,
    discharge_coefficient: float | None = None,
) -> ReedParams:
    """Return a reed with optional changes to opening, Q, and discharge."""

    next_reed = _reed_with_q(reed, quality_factor) if quality_factor is not None else reed
    next_rest = next_reed.rest_opening_m if rest_opening_m is None else rest_opening_m
    next_scale = next_reed.displacement_to_gap if displacement_to_gap is None else displacement_to_gap
    next_reed = replace(
        next_reed,
        rest_opening_m=next_rest,
        displacement_to_gap=next_scale,
        closing_displacement_m=(-next_rest / next_scale if next_scale != 0.0 else next_reed.closing_displacement_m),
    )
    if discharge_coefficient is not None:
        next_reed = replace(next_reed, discharge_coefficient=discharge_coefficient)
    return next_reed


def _sweep_candidates() -> list[tuple[str, ModelParams]]:
    """Return hand-picked draw-mode candidates for exploratory rendering."""

    base = DEFAULT_PARAMS
    return [
        ("3b_default_tract_plus_draw_flow", base),
        (
            "draw_flow_only",
            replace(base, pressure_output_gain=0.0, draw_flow_output_gain_pa_s_m3=1.0e7),
        ),
        (
            "slightly_looser_draw_gap",
            _draw_reed_variant(
                base,
                rest_opening_m=3.0e-6,
                displacement_to_gap=-2.5,
                quality_factor=40.0,
                closure_damping_kg_s=1.5e-3,
            ),
        ),
        (
            "warmer_draw_gap",
            _draw_reed_variant(
                base,
                rest_opening_m=5.0e-6,
                displacement_to_gap=-2.0,
                quality_factor=36.0,
                closure_damping_kg_s=1.2e-3,
            ),
        ),
        (
            "moderate_draw_pressure_reference",
            replace(base, mouth_pressure_pa=-780.0, attack_s=0.30),
        ),
        (
            "larger_chamber_reference",
            replace(base, chamber_volume_m3=1.2e-6),
        ),
        (
            "lower_tract_reference",
            replace(base, vocal_tract_frequency_hz=520.0, vocal_tract_q=4.0, vocal_tract_impedance_pa_s_m3=1.8e8),
        ),
    ]


def _candidate_score(metrics: dict[str, float | bool | str]) -> float:
    """Score sweep candidates using stability, harmonics, closure, and attack."""

    if not metrics["stable_non_clipped"]:
        return -1.0e6
    closure_values = [
        float(metrics["area_b_closed_percent"]),
        float(metrics["area_d_closed_percent"]),
    ]
    best_closure = max(closure_values)
    closure_score = 1.0 if 5.0 <= best_closure <= 60.0 else -abs(best_closure - 30.0) / 30.0
    centroid_ratio = float(metrics["centroid_to_f0"])
    return (
        100.0 * float(metrics["harmonic_energy_ratio"])
        + 8.0 * min(centroid_ratio, 3.0)
        + 8.0 * closure_score
        + 0.02 * min(float(metrics["attack_strength"]), 500.0)
    )


def _calibration_score(
    metrics: dict[str, float | bool | str],
    analysis,
    reference_analysis=None,
) -> float:
    """Score calibration candidates, optionally including reference similarity."""

    if not metrics["stable_non_clipped"]:
        return -1.0e6
    centroid_ratio = float(metrics["centroid_to_f0"])
    harmonic_ratio = float(analysis.harmonic_energy_ratio)
    non_sinusoidal = 1.0 if not bool(metrics["mostly_sinusoidal"]) else -1.0
    attack_ratio = float(metrics["attack_ratio"])
    attack_score = 1.0 - min(abs(attack_ratio - 0.05) / 0.30, 1.5)
    waveform_score = min(float(metrics["audio_rms"]) / 0.20, 2.0)
    score = (
        80.0 * min(harmonic_ratio, 2.0)
        + 12.0 * min(centroid_ratio, 3.5)
        + 12.0 * non_sinusoidal
        + 10.0 * attack_score
        + 5.0 * waveform_score
    )
    if reference_analysis is not None:
        score += 80.0 * comparison_score(analysis, reference_analysis)
    return float(score)


def _calibration_candidates(mode: str) -> list[tuple[str, ModelParams]]:
    """Return bounded physical parameter candidates for draw or blow mode."""

    base = _preset_for_mode(mode)

    if mode == "draw":
        active_reed_name = "draw_reed"
        passive_reed_name = "blow_reed"
        active_scale = -3.2
    else:
        active_reed_name = "blow_reed"
        passive_reed_name = "draw_reed"
        active_scale = 3.2

    def with_reeds(
        params: ModelParams,
        *,
        active_q: float | None = None,
        passive_q: float | None = None,
        active_rest: float | None = None,
        active_gap_scale: float | None = None,
        active_discharge: float | None = None,
        passive_discharge: float | None = None,
    ) -> ModelParams:
        """Modify active/passive reed settings without changing the ODE path."""

        active = _reed_opening_variant(
            getattr(params, active_reed_name),
            rest_opening_m=active_rest,
            displacement_to_gap=active_gap_scale,
            quality_factor=active_q,
            discharge_coefficient=active_discharge,
        )
        passive = _reed_opening_variant(
            getattr(params, passive_reed_name),
            quality_factor=passive_q,
            discharge_coefficient=passive_discharge,
        )
        return replace(params, **{active_reed_name: active, passive_reed_name: passive})

    return [
        ("baseline_radiated_mix", base),
        (
            "brighter_flow_radiation",
            replace(
                base,
                radiation_highpass_hz=150.0,
                radiation_differentiation_mix=0.36,
                body_resonance_frequency_hz=2100.0,
                body_resonance_q=1.8,
                body_resonance_gain=0.18,
            ),
        ),
        (
            "net_flow_radiator",
            replace(
                base,
                output_mode="flow",
                output_source="net_flow",
                acoustic_flow_gain_pa_s_m3=1.4e8,
                radiation_highpass_hz=120.0,
                radiation_differentiation_mix=0.45,
                body_resonance_frequency_hz=1900.0,
                body_resonance_gain=0.16,
            ),
        ),
        (
            "active_reed_higher_q",
            with_reeds(base, active_q=50.0, passive_q=16.0),
        ),
        (
            "tighter_active_opening",
            with_reeds(base, active_rest=1.5e-6, active_gap_scale=active_scale * 1.10),
        ),
        (
            "looser_active_opening",
            with_reeds(base, active_rest=3.2e-6, active_gap_scale=active_scale * 0.85),
        ),
        (
            "higher_discharge",
            with_reeds(base, active_discharge=0.76, passive_discharge=0.68),
        ),
        (
            "smaller_chamber_stronger_feedback",
            replace(base, chamber_volume_m3=6.5e-7, vocal_tract_impedance_pa_s_m3=2.6e8),
        ),
        (
            "larger_chamber_small_leak_radiation",
            replace(base, chamber_volume_m3=1.1e-6, chamber_leakage_conductance_m3_s_pa=1.5e-10),
        ),
        (
            "tract_near_second_harmonic",
            replace(base, vocal_tract_frequency_hz=780.0, vocal_tract_q=4.5, vocal_tract_impedance_pa_s_m3=2.4e8),
        ),
        (
            "low_q_body_coloration",
            replace(base, body_resonance_frequency_hz=1450.0, body_resonance_q=1.1, body_resonance_gain=0.22),
        ),
        (
            "low_flow_noise",
            replace(base, flow_noise_amount=0.018, radiation_differentiation_mix=0.25),
        ),
    ]


def _write_sweep_report(path: Path, name: str, metrics: dict[str, float | bool | str], score: float) -> None:
    """Write one Markdown report for a sweep candidate."""

    path.write_text(
        "\n".join(
            [
                f"# Sweep Candidate: {name}",
                "",
                f"- Rank score: {score:.3f}",
                f"- Stable non-clipped output: {'yes' if metrics['stable_non_clipped'] else 'no'}",
                f"- Peak audio: {metrics['audio_peak']:.6f}",
                f"- RMS audio: {metrics['audio_rms']:.6f}",
                f"- RMS first 100 ms: {metrics['rms_first_100ms']:.6f}",
                f"- RMS sustain region 0.7-1.2 s: {metrics['rms_sustain']:.6f}",
                f"- Attack ratio first/sustain: {metrics['attack_ratio']:.6f}",
                f"- Estimated fundamental frequency: {metrics['fundamental_hz']:.2f} Hz",
                f"- Harmonic energy ratio: {metrics['harmonic_energy_ratio']:.6f}",
                f"- Spectral centroid: {metrics['spectral_centroid_hz']:.2f} Hz",
                f"- Spectral centroid / f0: {metrics['centroid_to_f0']:.2f}",
                f"- Mostly sinusoidal: {'yes' if metrics['mostly_sinusoidal'] else 'no'}",
                f"- Attack strength: {metrics['attack_strength']:.2f}",
                f"- Blow reed opening near closed: {metrics['area_b_closed_percent']:.2f}%",
                f"- Draw reed opening near closed: {metrics['area_d_closed_percent']:.2f}%",
                f"- Closure target met: {'yes' if metrics['closure_target_met'] else 'no'}",
                f"- Chamber pressure feedback nonzero: {'yes' if metrics['chamber_feedback_nonzero'] else 'no'}",
                f"- Reed participation: {metrics['reed_participation']}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _signed_mode_pressure(value_pa: float, mode: str) -> float:
    """Force CLI pressure magnitude to the correct sign for draw or blow."""

    if mode == "draw":
        return -abs(value_pa)
    if mode == "blow":
        return abs(value_pa)
    raise ValueError(f"unsupported mode: {mode}")


def _preset_for_mode(mode: str) -> ModelParams:
    """Return the default physical preset for a render mode."""

    if mode == "draw":
        return DRAW_PARAMS
    if mode == "blow":
        return BLOW_PARAMS
    raise ValueError(f"unsupported mode: {mode}")


def _params_with_breath_controls(
    params: ModelParams,
    *,
    mode: str,
    duration_s: float,
    pre_delay_s: float | None,
    attack_s: float | None,
    release_s: float | None,
    pressure_pa: float | None,
) -> ModelParams:
    """Apply CLI breath controls while preserving draw/blow pressure sign."""

    next_params = params
    if pre_delay_s is not None:
        next_params = replace(next_params, pre_delay_s=pre_delay_s)
    if attack_s is not None:
        next_params = replace(next_params, attack_s=attack_s)
    if release_s is not None:
        next_params = replace(next_params, release_s=release_s)
    if pressure_pa is not None:
        next_params = replace(next_params, mouth_pressure_pa=_signed_mode_pressure(pressure_pa, mode))

    release_start_s = max(
        next_params.pre_delay_s + next_params.attack_s,
        duration_s - next_params.release_s,
    )
    return replace(next_params, release_start_s=release_start_s)


def _params_with_output_controls(
    params: ModelParams,
    *,
    output_mode: str,
    noise_gain: float | None,
    radiation: str | None,
) -> ModelParams:
    """Apply CLI output-layer controls to a parameter set."""

    next_params = replace(params, output_mode=output_mode)
    if noise_gain is not None:
        next_params = replace(next_params, flow_noise_amount=max(0.0, noise_gain))
    if radiation is not None:
        next_params = replace(next_params, radiation_enabled=(radiation == "on"))
    return next_params


def render_mode_outputs(output_dir: Path, mode: str, params: ModelParams, config: RenderConfig) -> RenderResult:
    """Render one mode and write all normal output artifacts."""

    output_dir.mkdir(parents=True, exist_ok=True)

    result = render_note(mode, params, config)

    stem = f"{mode}_note"
    wav_path = output_dir / f"{stem}.wav"
    csv_path = output_dir / f"{stem}_trace.csv"
    png_path = output_dir / f"{stem}_diagnostics.png"
    report_path = output_dir / f"{stem}_report.md"

    write_wav(wav_path, result.audio, result.sample_rate_hz)
    write_trace_csv(csv_path, result)
    write_diagnostics_plot(png_path, result, mode)
    write_diagnostic_report(report_path, result, mode)

    peak = float(abs(result.audio).max())
    rms = float((result.audio**2).mean() ** 0.5)
    print(f"Wrote {wav_path}")
    print(f"Wrote {csv_path}")
    print(f"Wrote {png_path}")
    print(f"Wrote {report_path}")
    print(f"{mode.title()} audio peak={peak:.6f}, rms={rms:.6f}")
    print(
        "Breath "
        f"pre_delay={params.pre_delay_s:.3f}s, "
        f"attack={params.attack_s:.3f}s, "
        f"release={params.release_s:.3f}s, "
        f"pressure={params.mouth_pressure_pa:.1f}Pa"
    )
    print(
        "Output "
        f"mode={params.output_mode}, "
        f"radiation={'on' if params.radiation_enabled else 'off'}, "
        f"noise={params.flow_noise_amount:.4f}"
    )
    return result


def render_default(output_dir: Path, params: ModelParams, config: RenderConfig) -> None:
    """Render the historical default draw note."""

    render_mode_outputs(output_dir, "draw", params, config)


def render_both(output_dir: Path, draw_params: ModelParams, blow_params: ModelParams, config: RenderConfig) -> None:
    """Render draw and blow notes, then write comparison artifacts."""

    draw_result = render_mode_outputs(output_dir, "draw", draw_params, config)
    blow_result = render_mode_outputs(output_dir, "blow", blow_params, config)

    comparison_report_path = output_dir / "comparison_report.md"
    comparison_plot_path = output_dir / "comparison_diagnostics.png"
    write_comparison_report(comparison_report_path, draw_result, blow_result)
    write_comparison_diagnostics_plot(comparison_plot_path, draw_result, blow_result)
    print(f"Wrote {comparison_report_path}")
    print(f"Wrote {comparison_plot_path}")


def render_output_compare(
    output_dir: Path,
    mode: str,
    draw_params: ModelParams,
    blow_params: ModelParams,
    config: RenderConfig,
) -> None:
    """Render pressure, flow, and mixed output modes for comparison."""

    compare_dir = output_dir / "output_compare"
    compare_dir.mkdir(parents=True, exist_ok=True)
    modes_to_render = ("draw", "blow") if mode == "both" else (mode,)
    summary_lines = [
        "# Output Mode Comparison",
        "",
        "- Core ODE state is unchanged across pressure, flow, and mixed renders.",
        "- Only the radiation/output layer is changed.",
        "",
        "| Render | Output mode | Radiation | Noise gain | Harmonic ratio | Centroid Hz | Rolloff Hz | Attack ratio | WAV |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    for note_mode in modes_to_render:
        base_params = draw_params if note_mode == "draw" else blow_params
        for output_mode in ("pressure", "flow", "mixed"):
            params = replace(base_params, output_mode=output_mode)
            result = render_note(note_mode, params, config)
            metrics = diagnostic_metrics(result)
            stem = f"{note_mode}_{output_mode}"
            wav_path = compare_dir / f"{stem}.wav"
            report_path = compare_dir / f"{stem}_report.md"
            write_wav(wav_path, result.audio, result.sample_rate_hz)
            write_diagnostic_report(report_path, result, note_mode)
            summary_lines.append(
                (
                    f"| {note_mode} | {output_mode} | {'on' if params.radiation_enabled else 'off'} | "
                    f"{params.flow_noise_amount:.4f} | {metrics['harmonic_energy_ratio']:.6f} | "
                    f"{metrics['spectral_centroid_hz']:.2f} | {metrics['spectral_rolloff_hz']:.2f} | "
                    f"{metrics['attack_ratio']:.6f} | `{wav_path.name}` |"
                )
            )
            print(f"Wrote {wav_path}")
            print(f"Wrote {report_path}")

    summary_path = compare_dir / "summary.md"
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    print(f"Wrote {summary_path}")


def render_sweep(output_dir: Path) -> None:
    """Render the draw-mode sweep candidates and rank them."""

    sweep_dir = output_dir / "sweep"
    sweep_dir.mkdir(parents=True, exist_ok=True)
    config = RenderConfig(duration_s=2.5, sample_rate_hz=44_100)
    scored: list[tuple[float, str, dict[str, float | bool | str]]] = []

    for index, (name, params) in enumerate(_sweep_candidates(), start=1):
        result = render_draw_note(params, config)
        metrics = diagnostic_metrics(result)
        score = _candidate_score(metrics)
        stem = f"{index:02d}_{name}"
        wav_path = sweep_dir / f"{stem}.wav"
        report_path = sweep_dir / f"{stem}_report.md"
        write_wav(wav_path, result.audio, result.sample_rate_hz)
        _write_sweep_report(report_path, name, metrics, score)
        scored.append((score, stem, metrics))
        print(f"Wrote {wav_path}")
        print(f"Wrote {report_path}")

    ranked = sorted(scored, key=lambda item: item[0], reverse=True)
    summary_lines = ["# Sweep Summary", ""]
    for rank, (score, stem, metrics) in enumerate(ranked, start=1):
        summary_lines.append(
            (
                f"{rank}. {stem}: score={score:.3f}, "
                f"harmonic={metrics['harmonic_energy_ratio']:.6f}, "
                f"centroid/f0={metrics['centroid_to_f0']:.2f}, "
                f"attack={metrics['attack_strength']:.2f}, "
                f"attack_ratio={metrics['attack_ratio']:.3f}, "
                f"closed=({metrics['area_b_closed_percent']:.2f}%, "
                f"{metrics['area_d_closed_percent']:.2f}%), "
                f"stable={'yes' if metrics['stable_non_clipped'] else 'no'}"
            )
        )
    summary_path = sweep_dir / "summary.md"
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    print(f"Wrote {summary_path}")


def analyze_reference(output_dir: Path, reference_path: Path) -> None:
    """Analyze an external reference WAV without using it for synthesis."""

    analysis = analyze_wav(reference_path)
    report_path = output_dir / "reference_analysis.md"
    plot_path = output_dir / "reference_analysis.png"
    write_analysis_report(report_path, "Reference Analysis", analysis)
    write_analysis_plot(plot_path, "Reference Analysis", analysis)
    print(f"Wrote {report_path}")
    print(f"Wrote {plot_path}")


def compare_render_to_reference(output_dir: Path, result: RenderResult, reference_path: Path) -> None:
    """Compare one rendered result to a reference WAV by analysis metrics."""

    synthetic = analyze_audio(result.audio, result.sample_rate_hz)
    reference = analyze_wav(reference_path)
    report_path = output_dir / "reference_comparison.md"
    plot_path = output_dir / "reference_comparison.png"
    write_reference_comparison(report_path, plot_path, synthetic, reference)
    print(f"Wrote {report_path}")
    print(f"Wrote {plot_path}")


def render_calibration(output_dir: Path, mode: str, reference_path: Path | None = None) -> None:
    """Run a bounded calibration search and write ranked candidates.

    Calibration changes physical parameters and output-layer settings, renders
    each candidate, analyzes the result, and ranks candidates. Reference audio,
    if provided, is used only for scoring, never as an audio source.
    """

    calibration_mode = "draw" if mode == "both" else mode
    calibration_dir = output_dir / "calibration"
    calibration_dir.mkdir(parents=True, exist_ok=True)
    config = RenderConfig(duration_s=1.8, sample_rate_hz=44_100)
    reference_analysis = analyze_wav(reference_path) if reference_path is not None else None
    scored = []

    for index, (name, params) in enumerate(_calibration_candidates(calibration_mode), start=1):
        result = render_note(calibration_mode, params, config)
        metrics = diagnostic_metrics(result)
        analysis = analyze_audio(result.audio, result.sample_rate_hz)
        score = _calibration_score(metrics, analysis, reference_analysis)
        stem = f"{index:02d}_{name}"
        report_path = calibration_dir / f"{stem}_report.md"
        report_lines = [
            f"# Calibration Candidate: {name}",
            "",
            f"- Mode: {calibration_mode}",
            f"- Score: {score:.6f}",
            f"- Stable non-clipped: {'yes' if metrics['stable_non_clipped'] else 'no'}",
            f"- Fundamental estimate: {analysis.fundamental_hz:.2f} Hz",
            f"- Harmonic energy ratio, harmonics 2-12 vs fundamental: {analysis.harmonic_energy_ratio:.6f}",
            f"- Spectral centroid: {analysis.spectral_centroid_hz:.2f} Hz",
            f"- Spectral rolloff 85%: {analysis.spectral_rolloff_hz:.2f} Hz",
            f"- Attack time: {analysis.attack_time_s:.3f} s",
            f"- Attack ratio first/sustain: {metrics['attack_ratio']:.6f}",
            f"- Mostly sinusoidal: {'yes' if metrics['mostly_sinusoidal'] else 'no'}",
            f"- Output mode: {params.output_mode}",
            f"- Output source: {params.output_source}",
            f"- Radiation enabled: {'yes' if params.radiation_enabled else 'no'}",
            f"- Radiation high-pass: {params.radiation_highpass_hz:.1f} Hz",
            f"- Radiation differentiation mix: {params.radiation_differentiation_mix:.3f}",
            f"- Body resonance: {params.body_resonance_frequency_hz:.1f} Hz, Q={params.body_resonance_q:.2f}, gain={params.body_resonance_gain:.3f}",
            f"- Noise gain: {params.flow_noise_amount:.4f}",
            f"- Noise flow power: {params.flow_noise_power:.3f}",
            f"- Chamber volume: {params.chamber_volume_m3:.9e} m^3",
            f"- Chamber leakage conductance for radiation: {params.chamber_leakage_conductance_m3_s_pa:.9e} m^3/(s Pa)",
            f"- Vocal tract: {params.vocal_tract_frequency_hz:.1f} Hz, Q={params.vocal_tract_q:.2f}, coupling={params.vocal_tract_impedance_pa_s_m3:.3e}",
            "",
        ]
        if reference_analysis is not None:
            report_lines.append(f"- Reference similarity score: {comparison_score(analysis, reference_analysis):.6f}")
            report_lines.append("")
        report_path.write_text("\n".join(report_lines), encoding="utf-8")
        scored.append((score, stem, name, params, result, metrics, analysis))
        print(f"Scored {stem}: {score:.3f}")

    ranked = sorted(scored, key=lambda item: item[0], reverse=True)
    summary_lines = [
        "# Calibration Summary",
        "",
        f"- Mode: {calibration_mode}",
        "- Search dimensions: reed Q/damping, rest opening, opening scale, discharge coefficients, chamber volume, leakage-radiation conductance, tract resonance/Q/coupling, output source, radiation settings, flow-noise amount.",
        "- Reference audio is used only for analysis and ranking when provided.",
        "",
    ]
    for rank, (score, stem, name, params, result, metrics, analysis) in enumerate(ranked, start=1):
        summary_lines.append(
            (
                f"{rank}. {stem}: score={score:.3f}, "
                f"f0={analysis.fundamental_hz:.2f}Hz, "
                f"harmonic={analysis.harmonic_energy_ratio:.3f}, "
                f"centroid={analysis.spectral_centroid_hz:.1f}Hz, "
                f"rolloff={analysis.spectral_rolloff_hz:.1f}Hz, "
                f"attack={analysis.attack_time_s:.3f}s, "
                f"stable={'yes' if metrics['stable_non_clipped'] else 'no'}"
            )
        )
        if rank <= 3:
            wav_path = calibration_dir / f"best_{rank:02d}_{name}.wav"
            plot_path = calibration_dir / f"best_{rank:02d}_{name}_analysis.png"
            write_wav(wav_path, result.audio, result.sample_rate_hz)
            write_analysis_plot(plot_path, f"Calibration Best {rank}: {name}", analysis)
            summary_lines.append(f"   WAV: `{wav_path.relative_to(output_dir.parent)}`")
            summary_lines.append(f"   Plot: `{plot_path.relative_to(output_dir.parent)}`")

    best_score, _, best_name, _, best_result, _, best_analysis = ranked[0]
    best_report = calibration_dir / "best_candidate_report.md"
    write_analysis_report(best_report, f"Best Calibration Candidate: {best_name}", best_analysis)
    if reference_analysis is not None:
        write_reference_comparison(
            calibration_dir / "best_reference_comparison.md",
            calibration_dir / "best_reference_comparison.png",
            best_analysis,
            reference_analysis,
        )
    summary_path = calibration_dir / "summary.md"
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    print(f"Wrote {summary_path}")
    print(f"Wrote {best_report}")
    print(f"Best candidate: {best_name} score={best_score:.3f}")


def main(argv: list[str] | None = None, output_dir: Path | None = None) -> None:
    """Parse CLI arguments and dispatch to the requested workflow."""

    parser = argparse.ArgumentParser(description="Render the offline harmonica physical model.")
    parser.add_argument(
        "--mode",
        choices=("draw", "blow", "both"),
        default="draw",
        help="render draw note, blow note, or both",
    )
    parser.add_argument("--sweep", action="store_true", help="render Milestone 3D parameter candidates")
    parser.add_argument("--calibrate", action="store_true", help="run Milestone 5 physical calibration search")
    parser.add_argument("--output-compare", action="store_true", help="render pressure, flow, and mixed output-layer variants")
    parser.add_argument("--analyze-reference", type=Path, default=None, help="analyze a reference WAV without using it as a synthesis source")
    parser.add_argument("--compare-reference", type=Path, default=None, help="compare rendered output or calibration candidates against a reference WAV")
    parser.add_argument(
        "--output",
        choices=("pressure", "flow", "mixed"),
        default="mixed",
        help="select the physical output/radiation source",
    )
    parser.add_argument("--noise", type=float, default=None, help="flow-driven output noise gain")
    parser.add_argument("--radiation", choices=("on", "off"), default=None, help="enable or bypass radiation high-pass/body filtering")
    parser.add_argument("--attack", type=float, default=None, help="breath attack time in seconds")
    parser.add_argument("--pre-delay", type=float, default=None, help="quiet delay before breath pressure starts")
    parser.add_argument("--release", type=float, default=None, help="breath release time in seconds")
    parser.add_argument(
        "--pressure",
        type=float,
        default=None,
        help="sustain pressure magnitude in Pa; sign is set by --mode",
    )
    parser.add_argument("--duration", type=float, default=2.5, help="render duration in seconds")
    args = parser.parse_args(argv)

    output_dir = PROJECT_ROOT / "outputs" if output_dir is None else output_dir
    if args.analyze_reference is not None:
        analyze_reference(output_dir, args.analyze_reference)
    elif args.calibrate:
        render_calibration(output_dir, args.mode, args.compare_reference)
    elif args.sweep:
        render_sweep(output_dir)
    else:
        config = RenderConfig(duration_s=args.duration, sample_rate_hz=44_100)
        draw_params = _params_with_output_controls(
            _params_with_breath_controls(
                _preset_for_mode("draw"),
                mode="draw",
                duration_s=args.duration,
                pre_delay_s=args.pre_delay,
                attack_s=args.attack,
                release_s=args.release,
                pressure_pa=args.pressure,
            ),
            output_mode=args.output,
            noise_gain=args.noise,
            radiation=args.radiation,
        )
        blow_params = _params_with_output_controls(
            _params_with_breath_controls(
                _preset_for_mode("blow"),
                mode="blow",
                duration_s=args.duration,
                pre_delay_s=args.pre_delay,
                attack_s=args.attack,
                release_s=args.release,
                pressure_pa=args.pressure,
            ),
            output_mode=args.output,
            noise_gain=args.noise,
            radiation=args.radiation,
        )
        if args.output_compare:
            render_output_compare(output_dir, args.mode, draw_params, blow_params, config)
        elif args.mode == "both":
            render_both(output_dir, draw_params, blow_params, config)
            if args.compare_reference is not None:
                compare_render_to_reference(output_dir, render_note("draw", draw_params, config), args.compare_reference)
        else:
            params = draw_params if args.mode == "draw" else blow_params
            result = render_mode_outputs(output_dir, args.mode, params, config)
            if args.compare_reference is not None:
                compare_render_to_reference(output_dir, result, args.compare_reference)


if __name__ == "__main__":
    main()
