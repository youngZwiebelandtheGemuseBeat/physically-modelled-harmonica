"""Compact validation plots for simulated state variables."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .output import estimate_fundamental_hz
from .simulate import SimulationResult


def _steady_window(result: SimulationResult) -> tuple[int, int]:
    length = max(1, int(0.08 * result.sample_rate_hz))
    preferred_start = int(0.45 * result.sample_rate_hz)
    latest_start = max(0, len(result.time_s) - length)
    start = min(preferred_start, latest_start)
    stop = min(len(result.time_s), start + length)
    return start, max(start + 1, stop)


def _spectrum(signal: np.ndarray, sample_rate_hz: int) -> tuple[np.ndarray, np.ndarray]:
    centered = np.asarray(signal, dtype=float) - float(np.mean(signal))
    if centered.size < 8:
        return np.array([0.0]), np.array([0.0])
    window = np.hanning(centered.size)
    magnitudes = np.abs(np.fft.rfft(centered * window))
    freqs = np.fft.rfftfreq(centered.size, 1.0 / sample_rate_hz)
    if float(np.max(magnitudes)) > 0.0:
        magnitudes = magnitudes / float(np.max(magnitudes))
    return freqs, magnitudes


def _scaled_points(
    x_values: np.ndarray,
    y_values: np.ndarray,
    box: tuple[int, int, int, int],
) -> list[tuple[int, int]]:
    left, top, right, bottom = box
    x = np.asarray(x_values, dtype=float)
    y = np.asarray(y_values, dtype=float)
    if x.size == 0 or y.size == 0:
        return []

    max_points = max(2, right - left)
    if x.size > max_points:
        indices = np.linspace(0, x.size - 1, max_points).astype(int)
        x = x[indices]
        y = y[indices]

    x_min = float(np.min(x))
    x_max = float(np.max(x))
    y_min = float(np.min(y))
    y_max = float(np.max(y))
    if x_max == x_min:
        x_max = x_min + 1.0
    if y_max == y_min:
        y_max = y_min + 1.0

    points = []
    for x_value, y_value in zip(x, y):
        px = left + int((float(x_value) - x_min) / (x_max - x_min) * (right - left))
        py = bottom - int((float(y_value) - y_min) / (y_max - y_min) * (bottom - top))
        points.append((px, py))
    return points


def _draw_panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    x_values: np.ndarray,
    y_values: np.ndarray,
    color: tuple[int, int, int],
) -> None:
    left, top, right, bottom = box
    draw.rectangle(box, outline=(170, 170, 170))
    draw.text((left + 6, top + 4), title, fill=(20, 20, 20))
    for fraction in (0.25, 0.5, 0.75):
        y = top + int(fraction * (bottom - top))
        draw.line((left, y, right, y), fill=(225, 225, 225))
    points = _scaled_points(x_values, y_values, (left + 4, top + 20, right - 4, bottom - 4))
    if len(points) >= 2:
        draw.line(points, fill=color, width=2)


def write_validation_plot(path: Path, result: SimulationResult) -> None:
    """Generate the required compact five-panel validation figure."""

    path.parent.mkdir(parents=True, exist_ok=True)
    start, stop = _steady_window(result)
    time_ms = 1000.0 * (result.time_s[start:stop] - result.time_s[start])

    if result.mode == "draw":
        active_motion = result.x_d[start:stop]
        active_label = "draw reed"
    else:
        active_motion = result.x_b[start:stop]
        active_label = "blow reed"

    f0 = estimate_fundamental_hz(active_motion, result.sample_rate_hz)
    freqs_reed, spec_reed = _spectrum(active_motion, result.sample_rate_hz)
    freqs_p, spec_p = _spectrum(result.p_c[start:stop], result.sample_rate_hz)
    reed_band = freqs_reed <= 4000.0
    pressure_band = freqs_p <= 4000.0

    image = Image.new("RGB", (1000, 900), "white")
    draw = ImageDraw.Draw(image)
    draw.text((24, 16), f"{result.mode} validation, f0 approx {f0:.1f} Hz", fill=(0, 0, 0))

    panels = [
        (40, 60, 960, 205),
        (40, 220, 960, 365),
        (40, 380, 960, 525),
        (40, 540, 960, 685),
        (40, 700, 960, 845),
    ]
    _draw_panel(draw, panels[0], "blow reed opening (um)", time_ms, result.gap_b[start:stop] * 1.0e6, (33, 90, 160))
    _draw_panel(draw, panels[1], "draw reed opening (um)", time_ms, result.gap_d[start:stop] * 1.0e6, (160, 70, 50))
    _draw_panel(draw, panels[2], "chamber pressure p_c (Pa)", time_ms, result.p_c[start:stop], (20, 120, 80))
    _draw_panel(draw, panels[3], f"{active_label} spectrum", freqs_reed[reed_band], spec_reed[reed_band], (100, 70, 150))
    _draw_panel(draw, panels[4], "chamber pressure spectrum", freqs_p[pressure_band], spec_p[pressure_band], (80, 80, 80))
    draw.text((40, 858), "Time panels use the same short steady-state window. Spectrum panels show 0-4000 Hz.", fill=(60, 60, 60))

    image.save(path)
