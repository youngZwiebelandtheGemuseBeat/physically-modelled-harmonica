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

from .render import RenderResult


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
                    f"{result.force_b[i]:.9e}",
                    f"{result.force_d[i]:.9e}",
                    f"{result.dp_c[i]:.9e}",
                ]
            )


def write_diagnostics_plot(path: str | Path, result: RenderResult) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(4, 1, figsize=(11, 8), sharex=True)
    fig.suptitle("Draw Note Physical Model Diagnostics")

    axes[0].plot(result.time_s, result.audio, color="black", linewidth=0.7)
    axes[0].set_ylabel("audio")

    axes[1].plot(result.time_s, result.p_m, label="p_m", linewidth=0.9)
    axes[1].plot(result.time_s, result.p_c, label="p_c", linewidth=0.9)
    axes[1].plot(result.time_s, result.p_t, label="p_t", linewidth=0.7)
    axes[1].set_ylabel("pressure Pa")
    axes[1].legend(loc="upper right")

    axes[2].plot(result.time_s, result.x_b * 1.0e6, label="x_b", linewidth=0.8)
    axes[2].plot(result.time_s, result.x_d * 1.0e6, label="x_d", linewidth=0.8)
    axes[2].set_ylabel("reed um")
    axes[2].legend(loc="upper right")

    axes[3].plot(result.time_s, result.q_b * 1.0e6, label="Q_b", linewidth=0.8)
    axes[3].plot(result.time_s, result.q_d * 1.0e6, label="Q_d", linewidth=0.8)
    axes[3].set_ylabel("flow ml/s")
    axes[3].set_xlabel("time s")
    axes[3].legend(loc="upper right")

    for axis in axes:
        axis.grid(True, alpha=0.25)

    fig.tight_layout()
    fig.savefig(output_path, dpi=140)
    plt.close(fig)
