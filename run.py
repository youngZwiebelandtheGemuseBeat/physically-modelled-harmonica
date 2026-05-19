from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from harmonica_model.audio import write_wav
from harmonica_model.diagnostics import write_diagnostics_plot, write_trace_csv
from harmonica_model.params import DEFAULT_PARAMS, RenderConfig
from harmonica_model.render import render_draw_note


def main() -> None:
    output_dir = PROJECT_ROOT / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    result = render_draw_note(DEFAULT_PARAMS, RenderConfig(duration_s=2.0, sample_rate_hz=44_100))

    wav_path = output_dir / "draw_note.wav"
    csv_path = output_dir / "draw_note_trace.csv"
    png_path = output_dir / "draw_note_diagnostics.png"

    write_wav(wav_path, result.audio, result.sample_rate_hz)
    write_trace_csv(csv_path, result)
    write_diagnostics_plot(png_path, result)

    peak = float(abs(result.audio).max())
    rms = float((result.audio**2).mean() ** 0.5)
    print(f"Wrote {wav_path}")
    print(f"Wrote {csv_path}")
    print(f"Wrote {png_path}")
    print(f"Audio peak={peak:.6f}, rms={rms:.6f}")


if __name__ == "__main__":
    main()
