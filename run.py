"""Run the minimal offline harmonica-channel simulation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
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
    return parser.parse_args()


def run_one(mode: str, args: argparse.Namespace) -> None:
    config = SimulationConfig(duration_s=args.duration)
    motion_enabled = args.motion_flow == "on"
    result = simulate_note(
        mode,
        config=config,
        pressure_pa=args.pressure,
        attack_s=args.attack,
        motion_flow_enabled=motion_enabled,
    )

    output_dir = PROJECT_ROOT / "outputs"
    write_pressure_wav(output_dir / f"{mode}_pressure.wav", result)
    write_trace_csv(output_dir / f"{mode}_trace.csv", result)
    write_validation_plot(output_dir / f"{mode}_validation.png", result)
    report = write_diagnostics(output_dir / f"{mode}_diagnostics.txt", result)

    print(report)
    print(f"wrote outputs/{mode}_pressure.wav")
    print(f"wrote outputs/{mode}_trace.csv")
    print(f"wrote outputs/{mode}_validation.png")
    print(f"wrote outputs/{mode}_diagnostics.txt")


def main() -> None:
    args = parse_args()
    modes = ["draw", "blow"] if args.mode == "both" else [args.mode]
    for mode in modes:
        run_one(mode, args)


if __name__ == "__main__":
    main()

