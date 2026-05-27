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

from harmonica_minimal.output import write_diagnostics, write_pressure_wav, write_trace_csv
from harmonica_minimal.parameters import SimulationConfig
from harmonica_minimal.plots import write_validation_plot
from harmonica_minimal.simulate import simulate_note


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline reduced physical model of one harmonica channel.")
    parser.add_argument("--mode", choices=["draw", "blow", "both"], default="draw")
    parser.add_argument("--duration", type=float, default=2.0)
    parser.add_argument("--pressure", type=float, default=None, help="Breath pressure magnitude in pascals.")
    parser.add_argument("--attack", type=float, default=None, help="Attack time in seconds.")
    parser.add_argument("--motion-flow", choices=["on", "off"], default="off")
    parser.add_argument("--tract-feedback-gain", type=float, default=None, help="Vocal tract feedback gain. Overrides vocal_tract_feedback_gain.")
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


def run_one(mode: str, args: argparse.Namespace, output_dir: Path) -> None:
    config = SimulationConfig(duration_s=args.duration)
    motion_enabled = args.motion_flow == "on"
    result = simulate_note(
        mode,
        config=config,
        pressure_pa=args.pressure,
        attack_s=args.attack,
        motion_flow_enabled=motion_enabled,
        vocal_tract_feedback_gain=args.tract_feedback_gain,
    )

    wav_path = output_dir / f"{mode}_pressure.wav"
    trace_path = output_dir / f"{mode}_trace.csv"
    plot_path = output_dir / f"{mode}_validation.png"
    diagnostics_path = output_dir / f"{mode}_diagnostics.txt"

    write_pressure_wav(wav_path, result)
    write_trace_csv(trace_path, result)
    write_validation_plot(plot_path, result)
    report = write_diagnostics(diagnostics_path, result)

    print(report)
    print(f"wrote {display_path(wav_path)}")
    print(f"wrote {display_path(trace_path)}")
    print(f"wrote {display_path(plot_path)}")
    print(f"wrote {display_path(diagnostics_path)}")


def main() -> None:
    args = parse_args()
    try:
        output_dir = resolve_output_dir(args)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    modes = ["draw", "blow"] if args.mode == "both" else [args.mode]
    for mode in modes:
        run_one(mode, args, output_dir)


if __name__ == "__main__":
    main()
