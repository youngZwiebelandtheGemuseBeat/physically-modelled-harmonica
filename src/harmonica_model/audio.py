from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy import signal
import soundfile as sf

from .params import ModelParams


def write_wav(path: str | Path, audio: np.ndarray, sample_rate_hz: int) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(np.asarray(audio, dtype=np.float32), -1.0, 1.0)
    sf.write(output_path, clipped, sample_rate_hz, subtype="PCM_16")


def normalize_audio(signal_values: np.ndarray, peak: float = 0.85) -> np.ndarray:
    values = np.asarray(signal_values, dtype=float)
    max_abs = float(np.max(np.abs(values))) if values.size else 0.0
    if max_abs <= 0.0:
        return values
    return values * (peak / max_abs)


def physical_output_signal(
    *,
    params: ModelParams,
    sample_rate_hz: int,
    p_c: np.ndarray,
    p_t: np.ndarray,
    q_b: np.ndarray,
    q_d: np.ndarray,
    delta_p_b: np.ndarray,
    delta_p_d: np.ndarray,
) -> np.ndarray:
    """Build the audible pressure from simulated pressure/flow states.

    The core model produces pressure and flow states. This layer approximates
    how a small acoustic source radiates: flow components are high-passed and
    partly differentiated, while an optional low-Q body resonance colors the
    resulting pressure. No oscillator or subtractive-synthesis source is added.
    """

    p_c = np.asarray(p_c, dtype=float)
    p_t = np.asarray(p_t, dtype=float)
    q_b = np.asarray(q_b, dtype=float)
    q_d = np.asarray(q_d, dtype=float)
    delta_p_b = np.asarray(delta_p_b, dtype=float)
    delta_p_d = np.asarray(delta_p_d, dtype=float)

    leak_flow = params.chamber_leakage_conductance_m3_s_pa * p_c
    net_flow = q_b - q_d - leak_flow
    mixed = (
        params.chamber_pressure_output_gain * p_c
        + params.pressure_output_gain * p_t
        + params.acoustic_flow_gain_pa_s_m3 * net_flow
        + params.draw_flow_output_gain_pa_s_m3 * q_d
        + params.blow_flow_output_gain_pa_s_m3 * q_b
    )

    source = params.output_source
    if source == "chamber_pressure":
        raw = p_c
    elif source == "tract_pressure":
        raw = p_t
    elif source == "net_flow":
        raw = params.acoustic_flow_gain_pa_s_m3 * net_flow
    elif source == "draw_flow":
        raw = params.draw_flow_output_gain_pa_s_m3 * q_d
    elif source == "blow_flow":
        raw = params.blow_flow_output_gain_pa_s_m3 * q_b
    elif source == "mix":
        raw = mixed
    else:
        raise ValueError(f"unsupported output_source: {source}")

    radiated = np.asarray(raw, dtype=float)
    if params.radiation_highpass_hz > 0.0 and radiated.size > 8:
        cutoff = min(params.radiation_highpass_hz, sample_rate_hz * 0.45)
        sos = signal.butter(1, cutoff, btype="highpass", fs=sample_rate_hz, output="sos")
        radiated = signal.sosfilt(sos, radiated)

    diff_mix = float(np.clip(params.radiation_differentiation_mix, 0.0, 1.0))
    if diff_mix > 0.0 and radiated.size > 1:
        differentiated = np.gradient(radiated) * float(sample_rate_hz)
        diff_peak = float(np.max(np.abs(differentiated)))
        raw_peak = float(np.max(np.abs(radiated)))
        if diff_peak > 0.0 and raw_peak > 0.0:
            differentiated = differentiated * (raw_peak / diff_peak)
            radiated = (1.0 - diff_mix) * radiated + diff_mix * differentiated

    if (
        params.body_resonance_gain > 0.0
        and params.body_resonance_frequency_hz > 0.0
        and params.body_resonance_q > 0.0
        and radiated.size > 8
    ):
        frequency = min(params.body_resonance_frequency_hz, sample_rate_hz * 0.45)
        b, a = signal.iirpeak(frequency, params.body_resonance_q, fs=sample_rate_hz)
        body = signal.lfilter(b, a, radiated)
        radiated = radiated + params.body_resonance_gain * body

    if params.flow_noise_amount > 0.0 and radiated.size > 8:
        rng = np.random.default_rng(params.flow_noise_seed)
        white = rng.standard_normal(radiated.size)
        high_hz = min(9000.0, sample_rate_hz * 0.45)
        if high_hz > 800.0:
            noise_sos = signal.butter(2, [700.0, high_hz], btype="bandpass", fs=sample_rate_hz, output="sos")
            turbulent_noise = signal.sosfilt(noise_sos, white)
        else:
            noise_sos = signal.butter(1, high_hz, btype="highpass", fs=sample_rate_hz, output="sos")
            turbulent_noise = signal.sosfilt(noise_sos, white)
        flow_scale = np.abs(q_b) + np.abs(q_d)
        pressure_scale = np.sqrt(np.maximum(np.abs(delta_p_b) + np.abs(delta_p_d), 0.0))
        drive = flow_scale * pressure_scale
        drive_peak = float(np.max(drive))
        signal_peak = float(np.max(np.abs(radiated)))
        noise_peak = float(np.max(np.abs(turbulent_noise)))
        if drive_peak > 0.0 and signal_peak > 0.0 and noise_peak > 0.0:
            envelope = drive / drive_peak
            turbulent_noise = turbulent_noise / noise_peak
            radiated = radiated + params.flow_noise_amount * signal_peak * envelope * turbulent_noise

    return normalize_audio(radiated)
