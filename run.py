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
from harmonica_model.diagnostics import (
    diagnostic_metrics,
    write_diagnostic_report,
    write_diagnostics_plot,
    write_trace_csv,
)
from harmonica_model.params import DEFAULT_PARAMS, ModelParams, ReedParams, RenderConfig
from harmonica_model.render import render_draw_note


def _reed_with_q(reed: ReedParams, quality_factor: float) -> ReedParams:
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


def _sweep_candidates() -> list[tuple[str, ModelParams]]:
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


def _write_sweep_report(path: Path, name: str, metrics: dict[str, float | bool | str], score: float) -> None:
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


def _signed_draw_pressure(value_pa: float) -> float:
    return -abs(value_pa) if value_pa > 0.0 else value_pa


def _params_with_breath_controls(
    params: ModelParams,
    *,
    duration_s: float,
    pre_delay_s: float | None,
    attack_s: float | None,
    release_s: float | None,
    pressure_pa: float | None,
) -> ModelParams:
    next_params = params
    if pre_delay_s is not None:
        next_params = replace(next_params, pre_delay_s=pre_delay_s)
    if attack_s is not None:
        next_params = replace(next_params, attack_s=attack_s)
    if release_s is not None:
        next_params = replace(next_params, release_s=release_s)
    if pressure_pa is not None:
        next_params = replace(next_params, mouth_pressure_pa=_signed_draw_pressure(pressure_pa))

    release_start_s = max(
        next_params.pre_delay_s + next_params.attack_s,
        duration_s - next_params.release_s,
    )
    return replace(next_params, release_start_s=release_start_s)


def render_default(output_dir: Path, params: ModelParams, config: RenderConfig) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    result = render_draw_note(params, config)

    wav_path = output_dir / "draw_note.wav"
    csv_path = output_dir / "draw_note_trace.csv"
    png_path = output_dir / "draw_note_diagnostics.png"
    report_path = output_dir / "draw_note_report.md"

    write_wav(wav_path, result.audio, result.sample_rate_hz)
    write_trace_csv(csv_path, result)
    write_diagnostics_plot(png_path, result)
    write_diagnostic_report(report_path, result)

    peak = float(abs(result.audio).max())
    rms = float((result.audio**2).mean() ** 0.5)
    print(f"Wrote {wav_path}")
    print(f"Wrote {csv_path}")
    print(f"Wrote {png_path}")
    print(f"Wrote {report_path}")
    print(f"Audio peak={peak:.6f}, rms={rms:.6f}")
    print(
        "Breath "
        f"pre_delay={params.pre_delay_s:.3f}s, "
        f"attack={params.attack_s:.3f}s, "
        f"release={params.release_s:.3f}s, "
        f"pressure={params.mouth_pressure_pa:.1f}Pa"
    )


def render_sweep(output_dir: Path) -> None:
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the offline harmonica physical model.")
    parser.add_argument("--sweep", action="store_true", help="render Milestone 3D parameter candidates")
    parser.add_argument("--attack", type=float, default=None, help="breath attack time in seconds")
    parser.add_argument("--pre-delay", type=float, default=None, help="quiet delay before breath pressure starts")
    parser.add_argument("--release", type=float, default=None, help="breath release time in seconds")
    parser.add_argument(
        "--pressure",
        type=float,
        default=None,
        help="draw sustain pressure in Pa; positive values are treated as draw suction",
    )
    parser.add_argument("--duration", type=float, default=2.5, help="render duration in seconds")
    args = parser.parse_args()

    output_dir = PROJECT_ROOT / "outputs"
    if args.sweep:
        render_sweep(output_dir)
    else:
        params = _params_with_breath_controls(
            DEFAULT_PARAMS,
            duration_s=args.duration,
            pre_delay_s=args.pre_delay,
            attack_s=args.attack,
            release_s=args.release,
            pressure_pa=args.pressure,
        )
        config = RenderConfig(duration_s=args.duration, sample_rate_hz=44_100)
        render_default(output_dir, params, config)


if __name__ == "__main__":
    main()
