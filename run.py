"""Run the minimal offline harmonica-channel simulation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = PROJECT_ROOT / "output"
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from harmonica_minimal.output import (
    DEFAULT_DC_BLOCK_CUTOFF_HZ,
    rendered_audio_signal,
    write_diagnostics,
    write_pressure_wav,
    write_trace_csv,
)
from harmonica_minimal.diagnostics import analyze_cause_audit, write_cause_audit
from harmonica_minimal.parameters import SimulationConfig
from harmonica_minimal.plots import (
    plot_presentation_pressure_result,
    write_millot_style_spectra,
    write_spectral_window_comparison_plot,
    write_tract_load_effect_plot,
    write_validation_plot,
)
from harmonica_minimal.simulate import SimulationResult, simulate_note


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline reduced physical model of one harmonica channel.")
    parser.add_argument("--mode", choices=["draw", "blow", "both"], default="draw")
    parser.add_argument("--duration", type=float, default=2.0)
    parser.add_argument("--pressure", type=float, default=None, help="Breath pressure magnitude in pascals.")
    parser.add_argument("--attack", type=float, default=None, help="Attack time in seconds.")
    parser.add_argument("--motion-flow", choices=["on", "off"], default="off")
    parser.add_argument(
        "--opening-model",
        choices=["clipped", "symmetric_smooth", "asymmetric_reopen"],
        default="clipped",
    )
    parser.add_argument("--opening-negative-gain", type=float, default=0.25)
    parser.add_argument("--opening-closed-band-um", type=float, default=5.0)
    parser.add_argument("--active-pressure-area-scale", type=float, default=1.0)
    parser.add_argument("--active-damping-scale", type=float, default=1.0)
    parser.add_argument("--active-discharge-scale", type=float, default=1.0)
    parser.add_argument("--passive-pressure-area-scale", type=float, default=1.0)
    parser.add_argument("--passive-damping-scale", type=float, default=1.0)
    parser.add_argument("--passive-discharge-scale", type=float, default=1.0)
    parser.add_argument("--tract-feedback-gain", type=float, default=None, help="Vocal tract feedback gain. Overrides vocal_tract_feedback_gain.")
    parser.add_argument(
        "--wav-dc-block",
        action="store_true",
        help="Apply an optional first-order DC blocker to the WAV only. Physical traces remain unchanged.",
    )
    parser.add_argument(
        "--wav-dc-block-cutoff",
        type=float,
        default=DEFAULT_DC_BLOCK_CUTOFF_HZ,
        help="Cutoff frequency for --wav-dc-block in Hz.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output subdirectory under output/. Defaults to the next output/output-N directory.",
    )
    return parser.parse_args()


def next_output_dir() -> Path:
    index = 1
    while True:
        output_dir = OUTPUT_ROOT / f"output-{index}"
        if not output_dir.exists():
            output_dir.mkdir(parents=True)
            return output_dir
        index += 1


def resolve_output_dir(args: argparse.Namespace) -> Path:
    if args.output_dir is None:
        return next_output_dir()
    if args.output_dir.is_absolute():
        raise ValueError("--output-dir must be a folder inside the project output/ directory")
    parts = args.output_dir.parts
    if parts and parts[0] == "output":
        output_dir = PROJECT_ROOT / args.output_dir
    else:
        output_dir = OUTPUT_ROOT / args.output_dir
    try:
        output_dir.resolve().relative_to(OUTPUT_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("--output-dir must stay inside the project output/ directory") from exc
    return output_dir


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def validate_opening_parameters(negative_gain: float, closed_band_um: float) -> None:
    if negative_gain < 0.0:
        raise ValueError("--opening-negative-gain must be >= 0.0")
    if closed_band_um < 0.0:
        raise ValueError("--opening-closed-band-um must be >= 0.0")


def validate_active_scales(
    pressure_area_scale: float,
    damping_scale: float,
    discharge_scale: float,
) -> None:
    if pressure_area_scale <= 0.0:
        raise ValueError("--active-pressure-area-scale must be > 0.0")
    if damping_scale <= 0.0:
        raise ValueError("--active-damping-scale must be > 0.0")
    if discharge_scale <= 0.0:
        raise ValueError("--active-discharge-scale must be > 0.0")


def validate_passive_scales(
    pressure_area_scale: float,
    damping_scale: float,
    discharge_scale: float,
) -> None:
    if pressure_area_scale <= 0.0:
        raise ValueError("--passive-pressure-area-scale must be > 0.0")
    if damping_scale <= 0.0:
        raise ValueError("--passive-damping-scale must be > 0.0")
    if discharge_scale <= 0.0:
        raise ValueError("--passive-discharge-scale must be > 0.0")


def run_one(mode: str, args: argparse.Namespace, output_dir: Path) -> SimulationResult:
    config = SimulationConfig(duration_s=args.duration)
    motion_enabled = args.motion_flow == "on"
    result = simulate_note(
        mode,
        config=config,
        pressure_pa=args.pressure,
        attack_s=args.attack,
        motion_flow_enabled=motion_enabled,
        vocal_tract_feedback_gain=args.tract_feedback_gain,
        opening_model=args.opening_model,
        opening_negative_gain=args.opening_negative_gain,
        opening_closed_band_m=args.opening_closed_band_um * 1.0e-6,
        active_pressure_area_scale=args.active_pressure_area_scale,
        active_damping_scale=args.active_damping_scale,
        active_discharge_scale=args.active_discharge_scale,
        passive_pressure_area_scale=args.passive_pressure_area_scale,
        passive_damping_scale=args.passive_damping_scale,
        passive_discharge_scale=args.passive_discharge_scale,
    )

    wav_path = output_dir / f"{mode}_pressure.wav"
    trace_path = output_dir / f"{mode}_trace.csv"
    plot_path = output_dir / f"{mode}_validation.png"
    presentation_plot_path = output_dir / f"{mode}_presentation_pressure.png"
    diagnostics_path = output_dir / f"{mode}_diagnostics.txt"

    dc_block_cutoff = args.wav_dc_block_cutoff if args.wav_dc_block else None
    wav_processing = (
        f"optional first-order DC blocker at {args.wav_dc_block_cutoff:.6g} Hz, then peak normalization"
        if args.wav_dc_block
        else "peak normalization only"
    )
    final_audio = rendered_audio_signal(result, dc_block_cutoff)

    write_pressure_wav(wav_path, result, dc_block_cutoff)
    write_trace_csv(trace_path, result)
    write_validation_plot(plot_path, result)
    plot_presentation_pressure_result(presentation_plot_path, result)
    write_millot_style_spectra(output_dir, result)
    report = write_diagnostics(diagnostics_path, result, final_audio, wav_processing)

    print(report)
    print(f"wrote {display_path(wav_path)}")
    print(f"wrote {display_path(trace_path)}")
    print(f"wrote {display_path(plot_path)}")
    print(f"wrote {display_path(presentation_plot_path)}")
    print(f"wrote {display_path(output_dir / f'{mode}_millot_style_reed_spectrum.png')}")
    print(f"wrote {display_path(output_dir / f'{mode}_millot_style_pressure_spectrum.png')}")
    print(f"wrote {display_path(diagnostics_path)}")
    return result


def write_cause_audits(
    results: list[SimulationResult],
    args: argparse.Namespace,
    output_dir: Path,
) -> None:
    """Write read-only cause audits after all requested modes are available."""

    dc_block_cutoff = args.wav_dc_block_cutoff if args.wav_dc_block else None
    wav_processing = (
        f"optional first-order DC blocker at {args.wav_dc_block_cutoff:.6g} Hz, then peak normalization"
        if args.wav_dc_block
        else "peak normalization only"
    )
    final_audio_by_mode = {
        result.mode: rendered_audio_signal(result, dc_block_cutoff)
        for result in results
    }
    audits = {
        result.mode: analyze_cause_audit(
            result,
            final_audio_by_mode[result.mode],
            wav_processing,
        )
        for result in results
    }

    for result in results:
        comparison = next(
            (audit for mode, audit in audits.items() if mode != result.mode),
            None,
        )
        plot_path = output_dir / f"{result.mode}_note_cause_audit.png"
        report_path = output_dir / f"{result.mode}_note_cause_audit.md"
        write_cause_audit(
            plot_path,
            report_path,
            result,
            final_audio_by_mode[result.mode],
            wav_processing,
            comparison=comparison,
            audit=audits[result.mode],
        )
        print(f"wrote {display_path(plot_path)}")
        print(f"wrote {display_path(report_path)}")


def plot_tract_load_effect_if_available(
    results: list[SimulationResult],
    args: argparse.Namespace,
    output_dir: Path,
) -> None:
    loaded_results = [result for result in results if result.params.vocal_tract_feedback_gain != 0.0]
    if not loaded_results:
        return

    config = SimulationConfig(duration_s=args.duration)
    motion_enabled = args.motion_flow == "on"
    unloaded_results = [
        simulate_note(
            result.mode,
            config=config,
            pressure_pa=args.pressure,
            attack_s=args.attack,
            motion_flow_enabled=motion_enabled,
            vocal_tract_feedback_gain=0.0,
            opening_model=args.opening_model,
            opening_negative_gain=args.opening_negative_gain,
            opening_closed_band_m=args.opening_closed_band_um * 1.0e-6,
            active_pressure_area_scale=args.active_pressure_area_scale,
            active_damping_scale=args.active_damping_scale,
            active_discharge_scale=args.active_discharge_scale,
            passive_pressure_area_scale=args.passive_pressure_area_scale,
            passive_damping_scale=args.passive_damping_scale,
            passive_discharge_scale=args.passive_discharge_scale,
        )
        for result in loaded_results
    ]
    plot_path = output_dir / "tract_load_effect.png"
    write_tract_load_effect_plot(plot_path, loaded_results, unloaded_results)
    print(f"wrote {display_path(plot_path)}")


def plot_spectral_window_comparison_if_available(
    results: list[SimulationResult],
    output_dir: Path,
) -> None:
    if {result.mode for result in results} != {"blow", "draw"}:
        return
    plot_path = output_dir / "blow_draw_spectral_window_audit.png"
    write_spectral_window_comparison_plot(plot_path, results)
    print(f"wrote {display_path(plot_path)}")


def main() -> None:
    args = parse_args()
    try:
        validate_opening_parameters(args.opening_negative_gain, args.opening_closed_band_um)
        validate_active_scales(
            args.active_pressure_area_scale,
            args.active_damping_scale,
            args.active_discharge_scale,
        )
        validate_passive_scales(
            args.passive_pressure_area_scale,
            args.passive_damping_scale,
            args.passive_discharge_scale,
        )
        output_dir = resolve_output_dir(args)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    modes = ["draw", "blow"] if args.mode == "both" else [args.mode]
    results = []
    for mode in modes:
        results.append(run_one(mode, args, output_dir))
    write_cause_audits(results, args, output_dir)
    plot_spectral_window_comparison_if_available(results, output_dir)
    plot_tract_load_effect_if_available(results, args, output_dir)


if __name__ == "__main__":
    main()
