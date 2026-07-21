"""Cause-audit spectra for rendered audio and physical-model traces."""

from __future__ import annotations

from dataclasses import dataclass
from math import pi, sqrt
import os
from pathlib import Path
import tempfile

import numpy as np
from scipy.signal import find_peaks

_MPL_CACHE = Path(tempfile.gettempdir()) / "harmonica_minimal_matplotlib"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CACHE))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .analysis import (
    MAX_STEADY_WINDOW_S,
    RelativeSpectrum,
    SPECTRUM_FLOOR_DB,
    SteadyStateWindow,
    relative_spectrum,
    select_steady_state_window,
)
from .output import estimate_fundamental_hz, rendered_audio_signal
from .simulate import SimulationResult


SIDE_COMPONENT_RANGE_DB = 55.0
SIDE_COMPONENT_MINIMUM_DB = -80.0
SIDE_COMPONENT_PROMINENCE_DB = 3.0
PASSIVE_FAMILY_RANGE_DB = 60.0
PASSIVE_FAMILY_MINIMUM_DB = -80.0


@dataclass(frozen=True)
class HarmonicShoulder:
    """Noncentral spectral-peak evidence around one expected harmonic."""

    harmonic: int
    target_hz: float
    main_hz: float
    main_db: float
    detected: bool
    components: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class TraceCauseAudit:
    """Full-note and steady-state evidence for one trace."""

    name: str
    unit: str
    full_spectrum: RelativeSpectrum
    steady_spectrum: RelativeSpectrum
    full_shoulders: tuple[HarmonicShoulder, ...]
    steady_shoulders: tuple[HarmonicShoulder, ...]


@dataclass(frozen=True)
class SettlingEvidence:
    """Early/late level comparison at the passive reed resonance."""

    active_reed_hz: float
    passive_reed_hz: float
    separation_hz: float
    early_start_s: float
    early_stop_s: float
    late_start_s: float
    late_stop_s: float
    pressure_early_db: float
    pressure_late_db: float
    passive_motion_early_db: float
    passive_motion_late_db: float


@dataclass(frozen=True)
class CauseAudit:
    """Read-only spectral audit of one simulation result."""

    mode: str
    sample_rate_hz: int
    sample_count: int
    duration_s: float
    f0_hz: float
    steady_window: SteadyStateWindow
    settling: SettlingEvidence
    traces: tuple[TraceCauseAudit, ...]
    audio_processing: str


def detect_sideband_like_components(
    spectrum: RelativeSpectrum,
    f0_hz: float,
    harmonic_count: int = 6,
) -> tuple[HarmonicShoulder, ...]:
    """Find significant noncentral peaks near H1-H6 using conservative thresholds."""

    frequencies = spectrum.frequencies_hz
    levels = spectrum.relative_db
    if frequencies.size < 3 or f0_hz <= 0.0:
        return tuple(
            HarmonicShoulder(n, n * f0_hz, 0.0, SPECTRUM_FLOOR_DB, False, ())
            for n in range(1, harmonic_count + 1)
        )

    bin_width_hz = float(frequencies[1] - frequencies[0])
    evidence: list[HarmonicShoulder] = []
    for harmonic in range(1, harmonic_count + 1):
        target_hz = harmonic * f0_hz
        if target_hz > frequencies[-1]:
            evidence.append(
                HarmonicShoulder(harmonic, target_hz, 0.0, SPECTRUM_FLOOR_DB, False, ())
            )
            continue

        central_half_width_hz = max(0.08 * f0_hz, 3.0 * bin_width_hz)
        central_mask = np.abs(frequencies - target_hz) <= central_half_width_hz
        central_indices = np.flatnonzero(central_mask)
        if central_indices.size == 0:
            evidence.append(
                HarmonicShoulder(harmonic, target_hz, 0.0, SPECTRUM_FLOOR_DB, False, ())
            )
            continue

        main_index = int(central_indices[np.argmax(levels[central_indices])])
        main_hz = float(frequencies[main_index])
        main_db = float(levels[main_index])
        region_half_width_hz = max(0.30 * f0_hz, 8.0 * bin_width_hz)
        region_mask = np.abs(frequencies - target_hz) <= region_half_width_hz
        region_indices = np.flatnonzero(region_mask)
        region_levels = levels[region_indices]
        minimum_distance = max(2, int(round(0.01 * f0_hz / max(bin_width_hz, 1.0e-12))))
        peaks, properties = find_peaks(
            region_levels,
            prominence=SIDE_COMPONENT_PROMINENCE_DB,
            distance=minimum_distance,
        )
        peak_indices = region_indices[peaks]
        prominences = properties.get("prominences", np.zeros_like(peaks, dtype=float))

        guard_hz = max(0.035 * f0_hz, 4.0 * bin_width_hz)
        threshold_db = max(main_db - SIDE_COMPONENT_RANGE_DB, SIDE_COMPONENT_MINIMUM_DB)
        candidates: list[tuple[float, float, float]] = []
        for peak_index, prominence in zip(peak_indices, prominences):
            peak_hz = float(frequencies[peak_index])
            peak_db = float(levels[peak_index])
            if abs(peak_hz - main_hz) <= guard_hz:
                continue
            if peak_db < threshold_db:
                continue
            candidates.append((peak_hz, peak_db - main_db, float(prominence)))

        candidates.sort(key=lambda item: item[1], reverse=True)
        components = tuple((frequency_hz, relative_to_main_db) for frequency_hz, relative_to_main_db, _ in candidates[:3])
        evidence.append(
            HarmonicShoulder(
                harmonic=harmonic,
                target_hz=target_hz,
                main_hz=main_hz,
                main_db=main_db,
                detected=bool(components),
                components=components,
            )
        )
    return tuple(evidence)


def _trace_sources(
    result: SimulationResult,
    final_audio: np.ndarray,
) -> tuple[tuple[str, str, np.ndarray], ...]:
    q_loss = np.zeros_like(result.q_b_total)
    net_flow = result.q_b_total - result.q_d_total - q_loss
    return (
        ("audio", "normalized", final_audio),
        ("p_c", "Pa", result.p_c),
        ("p_t", "Pa", result.p_t),
        ("q_b", "m^3/s", result.q_b_total),
        ("q_d", "m^3/s", result.q_d_total),
        ("net_flow", "m^3/s", net_flow),
        ("x_b", "m", result.x_b),
        ("x_d", "m", result.x_d),
    )


def _component_level_db(
    signal: np.ndarray,
    sample_rate_hz: int,
    start: int,
    stop: int,
    main_hz: float,
    component_hz: float,
) -> float:
    spectrum = relative_spectrum(signal[start:stop], sample_rate_hz)
    frequencies = spectrum.frequencies_hz
    levels = spectrum.relative_db
    if frequencies.size < 2:
        return SPECTRUM_FLOOR_DB
    bin_width_hz = float(frequencies[1] - frequencies[0])
    search_half_width_hz = max(3.0 * bin_width_hz, 3.0)
    main_indices = np.flatnonzero(np.abs(frequencies - main_hz) <= search_half_width_hz)
    component_indices = np.flatnonzero(np.abs(frequencies - component_hz) <= search_half_width_hz)
    if main_indices.size == 0 or component_indices.size == 0:
        return SPECTRUM_FLOOR_DB
    main_db = float(np.max(levels[main_indices]))
    component_db = float(np.max(levels[component_indices]))
    return component_db - main_db


def _settling_evidence(result: SimulationResult, window: SteadyStateWindow) -> SettlingEvidence:
    if result.mode == "blow":
        active_reed = result.params.blow_reed
        passive_reed = result.params.draw_reed
        passive_motion = result.x_d
    else:
        active_reed = result.params.draw_reed
        passive_reed = result.params.blow_reed
        passive_motion = result.x_b

    active_hz = sqrt(active_reed.stiffness_n_m / active_reed.mass_kg) / (2.0 * pi)
    passive_hz = sqrt(passive_reed.stiffness_n_m / passive_reed.mass_kg) / (2.0 * pi)
    sample_rate_hz = result.sample_rate_hz
    late_length = max(1, window.stop - window.start)
    early_start = min(
        len(result.time_s),
        int(np.ceil((window.attack_end_s + window.safety_margin_s) * sample_rate_hz)),
    )
    early_stop = min(len(result.time_s), early_start + late_length)
    if early_stop <= early_start:
        early_start, early_stop = window.start, window.stop

    return SettlingEvidence(
        active_reed_hz=active_hz,
        passive_reed_hz=passive_hz,
        separation_hz=abs(passive_hz - active_hz),
        early_start_s=early_start / float(sample_rate_hz),
        early_stop_s=early_stop / float(sample_rate_hz),
        late_start_s=window.start_s,
        late_stop_s=window.stop_s,
        pressure_early_db=_component_level_db(
            result.p_c,
            sample_rate_hz,
            early_start,
            early_stop,
            active_hz,
            passive_hz,
        ),
        pressure_late_db=_component_level_db(
            result.p_c,
            sample_rate_hz,
            window.start,
            window.stop,
            active_hz,
            passive_hz,
        ),
        passive_motion_early_db=_component_level_db(
            passive_motion,
            sample_rate_hz,
            early_start,
            early_stop,
            active_hz,
            passive_hz,
        ),
        passive_motion_late_db=_component_level_db(
            passive_motion,
            sample_rate_hz,
            window.start,
            window.stop,
            active_hz,
            passive_hz,
        ),
    )


def analyze_cause_audit(
    result: SimulationResult,
    final_audio: np.ndarray | None = None,
    audio_processing: str = "peak normalization only",
) -> CauseAudit:
    """Compute full-note and steady-state spectra without modifying the result."""

    audio = rendered_audio_signal(result) if final_audio is None else np.asarray(final_audio, dtype=float)
    steady_window = select_steady_state_window(result)
    p_c_steady = result.p_c[steady_window.start : steady_window.stop]
    f0_hz = estimate_fundamental_hz(p_c_steady, result.sample_rate_hz)
    if f0_hz <= 0.0:
        f0_hz = estimate_fundamental_hz(result.p_c, result.sample_rate_hz)

    trace_audits = []
    for name, unit, values in _trace_sources(result, audio):
        full_spectrum = relative_spectrum(values, result.sample_rate_hz)
        steady_spectrum = relative_spectrum(
            values[steady_window.start : steady_window.stop],
            result.sample_rate_hz,
        )
        trace_audits.append(
            TraceCauseAudit(
                name=name,
                unit=unit,
                full_spectrum=full_spectrum,
                steady_spectrum=steady_spectrum,
                full_shoulders=detect_sideband_like_components(full_spectrum, f0_hz),
                steady_shoulders=detect_sideband_like_components(steady_spectrum, f0_hz),
            )
        )
    return CauseAudit(
        mode=result.mode,
        sample_rate_hz=result.sample_rate_hz,
        sample_count=len(result.time_s),
        duration_s=len(result.time_s) / float(result.sample_rate_hz),
        f0_hz=f0_hz,
        steady_window=steady_window,
        settling=_settling_evidence(result, steady_window),
        traces=tuple(trace_audits),
        audio_processing=audio_processing,
    )


def _trace_by_name(audit: CauseAudit, name: str) -> TraceCauseAudit:
    return next(trace for trace in audit.traces if trace.name == name)


def _detected_harmonics(shoulders: tuple[HarmonicShoulder, ...]) -> list[int]:
    return [item.harmonic for item in shoulders if item.detected]


def _status(shoulders: tuple[HarmonicShoulder, ...]) -> str:
    detected = _detected_harmonics(shoulders)
    if detected:
        labels = ", ".join(f"H{harmonic}" for harmonic in detected)
        return f"sideband-like component detected ({labels})"
    return "sideband-like component not detected"


def _offset_family_levels(
    spectrum: RelativeSpectrum,
    f0_hz: float,
    offset_hz: float,
    harmonic_count: int = 6,
) -> tuple[tuple[int, float], ...]:
    """Measure the strongest +/- offset component beside each harmonic."""

    frequencies = spectrum.frequencies_hz
    levels = spectrum.relative_db
    if frequencies.size < 2 or f0_hz <= 0.0 or offset_hz <= 0.0:
        return ()
    bin_width_hz = float(frequencies[1] - frequencies[0])
    search_half_width_hz = max(3.0, 2.0 * bin_width_hz)
    measured: list[tuple[int, float]] = []
    for harmonic in range(1, harmonic_count + 1):
        central_hz = harmonic * f0_hz
        central_indices = np.flatnonzero(np.abs(frequencies - central_hz) <= search_half_width_hz)
        if central_indices.size == 0:
            continue
        main_db = float(np.max(levels[central_indices]))
        if main_db < PASSIVE_FAMILY_MINIMUM_DB:
            continue
        candidates = []
        for target_hz in (central_hz - offset_hz, central_hz + offset_hz):
            if target_hz <= 0.0 or target_hz > frequencies[-1]:
                continue
            indices = np.flatnonzero(np.abs(frequencies - target_hz) <= search_half_width_hz)
            if indices.size:
                component_db = float(np.max(levels[indices]))
                if component_db >= PASSIVE_FAMILY_MINIMUM_DB:
                    candidates.append(component_db - main_db)
        if candidates:
            measured.append((harmonic, max(candidates)))
    return tuple(measured)


def _offset_family_status(trace: TraceCauseAudit, audit: CauseAudit, steady: bool) -> str:
    spectrum = trace.steady_spectrum if steady else trace.full_spectrum
    levels = _offset_family_levels(spectrum, audit.f0_hz, audit.settling.separation_hz)
    detected = [(harmonic, level_db) for harmonic, level_db in levels if level_db >= -PASSIVE_FAMILY_RANGE_DB]
    if not detected:
        return "sideband-like component not detected at the active/passive reed-frequency offset"
    harmonic_labels = ", ".join(f"H{harmonic}" for harmonic, _level_db in detected)
    strongest_db = max(level_db for _harmonic, level_db in detected)
    return (
        "sideband-like component detected at the active/passive reed-frequency offset "
        f"({harmonic_labels}; strongest {strongest_db:.1f} dB relative to its local harmonic)"
    )


def _offset_family_strongest_db(audit: CauseAudit, trace_name: str = "audio") -> float | None:
    trace = _trace_by_name(audit, trace_name)
    levels = _offset_family_levels(trace.steady_spectrum, audit.f0_hz, audit.settling.separation_hz)
    detected = [level_db for _harmonic, level_db in levels if level_db >= -PASSIVE_FAMILY_RANGE_DB]
    return max(detected) if detected else None


def _blow_draw_answer(audit: CauseAudit, comparison: CauseAudit | None) -> str:
    if comparison is None or {audit.mode, comparison.mode} != {"blow", "draw"}:
        return "not assessed in a one-mode run; render both modes for a direct comparison."

    blow = audit if audit.mode == "blow" else comparison
    draw = audit if audit.mode == "draw" else comparison
    blow_level = _offset_family_strongest_db(blow)
    draw_level = _offset_family_strongest_db(draw)

    if blow_level is None and draw_level is None:
        return "no; the active/passive reed-frequency offset was not detected in either steady audio."
    if blow_level is not None and draw_level is None:
        return "yes by this detector; only blow has the active/passive reed-frequency-offset family in steady audio."
    if blow_level is None and draw_level is not None:
        return "no by this detector; only draw has the active/passive reed-frequency-offset family in steady audio."

    assert blow_level is not None and draw_level is not None
    level_details = f"strongest offset-family levels relative to the local harmonic: blow {blow_level:.1f} dB, draw {draw_level:.1f} dB"
    if blow_level > draw_level + 3.0:
        return f"yes by the stated 3 dB comparison rule ({level_details})."
    if draw_level > blow_level + 3.0:
        return f"no; draw is stronger by the stated 3 dB comparison rule ({level_details})."
    return f"no clear difference within 3 dB ({level_details})."


def _localization_lines(audit: CauseAudit) -> list[str]:
    traces = {trace.name: trace for trace in audit.traces}
    full_audio = bool(_detected_harmonics(traces["audio"].full_shoulders))
    steady_audio = bool(_detected_harmonics(traces["audio"].steady_shoulders))
    steady_pressure = bool(_detected_harmonics(traces["p_c"].steady_shoulders))
    steady_flow = bool(_detected_harmonics(traces["net_flow"].steady_shoulders))
    steady_reeds = bool(
        _detected_harmonics(traces["x_b"].steady_shoulders)
        or _detected_harmonics(traces["x_d"].steady_shoulders)
    )

    if steady_pressure:
        pressure_line = (
            "The observation is already present in steady-state `p_c`, before WAV processing; "
            "the audio export is therefore not required to create it."
        )
    else:
        pressure_line = "No qualifying component was found in steady-state `p_c` under the stated thresholds."

    if full_audio and not steady_audio:
        envelope_line = (
            "The audio detection is confined to the full-note window, which is consistent with a note-boundary "
            "or finite-record contribution but does not establish one unique cause."
        )
    elif steady_audio:
        envelope_line = (
            "The audio detection remains after attack and release are excluded, so the breath boundaries are not "
            "required for the observation."
        )
    else:
        envelope_line = "No qualifying audio component was found in either analysis window."

    flow_line = (
        "A qualifying component is present in steady net flow."
        if steady_flow
        else "No qualifying component is present in steady net flow."
    )
    reed_line = (
        "A qualifying component is present in at least one steady reed-displacement trace."
        if steady_reeds
        else "No qualifying component is present in either steady reed-displacement trace."
    )
    return [pressure_line, envelope_line, flow_line, reed_line]


def cause_audit_markdown(audit: CauseAudit, comparison: CauseAudit | None = None) -> str:
    """Format one audit using neutral observational wording."""

    traces = {trace.name: trace for trace in audit.traces}
    window = audit.steady_window
    fallback_text = "yes" if window.used_fallback else "no"
    settling = audit.settling
    pressure_change_db = settling.pressure_late_db - settling.pressure_early_db
    passive_change_db = settling.passive_motion_late_db - settling.passive_motion_early_db

    lines = [
        f"# {audit.mode.capitalize()} note cause audit",
        "",
        "This is a diagnostic observation, not a claim of physical validation.",
        "",
        "## Analysis setup",
        "",
        f"- Estimated f0 from the strongest steady-state `p_c` component in 60–2000 Hz: {audit.f0_hz:.3f} Hz",
        f"- Spectrum method: remove mean, apply Hann window, use rFFT/rfftfreq, normalize magnitude to its maximum, report relative dB with a {SPECTRUM_FLOOR_DB:.0f} dB floor",
        f"- Full-note window: 0.000000–{audit.duration_s:.6f} s ({audit.sample_count} samples)",
        f"- Derived envelope boundaries: pre-delay {window.pre_delay_s:.6f} s, attack end {window.attack_end_s:.6f} s, release start {window.release_start_s:.6f} s",
        f"- Steady-state window: {window.start_s:.6f}–{window.stop_s:.6f} s; safety margin {window.safety_margin_s:.3f} s; fallback used: {fallback_text}",
        f"- The late analysis window is capped at {MAX_STEADY_WINDOW_S:.3f} s so early post-attack settling is not averaged into the stationary result.",
        f"- Audio path used for this audit: {audit.audio_processing}",
        "- `q_loss` is zero because this model has no separate loss-flow state.",
        "",
        f"The targeted sideband check measures components at each harmonic plus or minus the {settling.separation_hz:.1f} Hz separation between the active and passive reed resonances. A component within {PASSIVE_FAMILY_RANGE_DB:.0f} dB of its local harmonic and above {PASSIVE_FAMILY_MINIMUM_DB:.0f} dB relative to the trace maximum is reported as detected. A separate broad peak scan is retained below for exploratory localization.",
        "",
        "## Ablation answers",
        "",
        f"- Are the shoulders present in full-note audio? **{_offset_family_status(traces['audio'], audit, steady=False)}.**",
        f"- Are they still present in steady-state audio? **{_offset_family_status(traces['audio'], audit, steady=True)}.**",
        f"- Are they present in steady-state `p_c`? **{_offset_family_status(traces['p_c'], audit, steady=True)}.**",
        f"- Are they present in reed displacement `x_b` or `x_d`? **`x_b`: {_offset_family_status(traces['x_b'], audit, steady=True)}; `x_d`: {_offset_family_status(traces['x_d'], audit, steady=True)}.**",
        f"- Are they present in net flow? **{_offset_family_status(traces['net_flow'], audit, steady=True)}.**",
        f"- Are they stronger in blow than draw? **{_blow_draw_answer(audit, comparison)}**",
        "",
        "In this implementation the normal audio source is chamber pressure followed by peak normalization; peak normalization alone cannot change relative spectral levels. If the optional WAV-only DC blocker is enabled, its effect is included in the audio trace while `p_c` remains untouched.",
        "",
        "## Post-attack settling check",
        "",
        f"- Active reed resonance: {settling.active_reed_hz:.3f} Hz; passive reed resonance: {settling.passive_reed_hz:.3f} Hz; separation: {settling.separation_hz:.3f} Hz.",
        f"- Early post-attack window: {settling.early_start_s:.6f}–{settling.early_stop_s:.6f} s; late window: {settling.late_start_s:.6f}–{settling.late_stop_s:.6f} s.",
        f"- `p_c` level near the passive resonance, relative to the active component: early {settling.pressure_early_db:.1f} dB, late {settling.pressure_late_db:.1f} dB, change {pressure_change_db:.1f} dB.",
        f"- Passive-reed displacement level near its own resonance, relative to the active component: early {settling.passive_motion_early_db:.1f} dB, late {settling.passive_motion_late_db:.1f} dB, change {passive_change_db:.1f} dB.",
        "- A substantial negative early-to-late change is evidence of post-attack settling rather than a stationary imposed modulation.",
        "",
        "## Broad noncentral-peak localization",
        "",
        *[f"- {line}" for line in _localization_lines(audit)],
        "",
        "## Broad peak-scan trace summary",
        "",
        "| Trace | Full note | Steady state |",
        "|---|---|---|",
    ]
    for trace in audit.traces:
        lines.append(f"| `{trace.name}` [{trace.unit}] | {_status(trace.full_shoulders)} | {_status(trace.steady_shoulders)} |")

    lines.extend(["", "## Detected-component details", ""])
    detail_count = 0
    for trace in audit.traces:
        for window_name, shoulders in (("full", trace.full_shoulders), ("steady", trace.steady_shoulders)):
            for item in shoulders:
                if not item.detected:
                    continue
                detail_count += 1
                components = ", ".join(
                    f"{frequency_hz:.2f} Hz ({component_db:.1f} dB relative to local main peak)"
                    for frequency_hz, component_db in item.components
                )
                lines.append(
                    f"- `{trace.name}` {window_name} H{item.harmonic}: main {item.main_hz:.2f} Hz; {components} — sideband-like component detected."
                )
    if detail_count == 0:
        lines.append("- No significant noncentral peaks met the stated detector thresholds.")
    lines.extend(
        [
            "",
            "Absence or presence under this detector can depend on note duration, FFT-bin spacing, window choice, and the stated thresholds. The result should therefore be used to locate a possible source layer, not as automatic confirmation of physical behavior.",
            "",
        ]
    )
    return "\n".join(lines)


def write_cause_audit_plot(path: Path, audit: CauseAudit) -> None:
    """Write a two-column full/steady spectrum plot for all audited traces."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with plt.rc_context(
        {
            "font.size": 8,
            "axes.titlesize": 9,
            "axes.labelsize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.dpi": 220,
        }
    ):
        fig, axes = plt.subplots(8, 2, figsize=(12.0, 18.0), sharex=True, sharey=True, constrained_layout=True)
        fig.suptitle(
            f"{audit.mode.capitalize()} note cause audit | f0 {audit.f0_hz:.2f} Hz | diagnostic observation",
            fontweight="bold",
        )
        for row, trace in enumerate(audit.traces):
            for column, (window_name, spectrum, shoulders) in enumerate(
                (
                    ("full note", trace.full_spectrum, trace.full_shoulders),
                    ("steady state", trace.steady_spectrum, trace.steady_shoulders),
                )
            ):
                ax = axes[row, column]
                band = spectrum.frequencies_hz <= min(4000.0, 0.5 * audit.sample_rate_hz)
                ax.plot(spectrum.frequencies_hz[band], spectrum.relative_db[band], color="#202020", linewidth=0.8)
                for harmonic in range(1, 7):
                    target_hz = harmonic * audit.f0_hz
                    if target_hz <= 4000.0:
                        ax.axvline(target_hz, color="#a0a0a0", linewidth=0.45, linestyle=":")
                for item in shoulders:
                    for component_hz, _component_db in item.components:
                        index = int(np.argmin(np.abs(spectrum.frequencies_hz - component_hz)))
                        ax.plot(component_hz, spectrum.relative_db[index], marker="o", markersize=3.0, color="#b6403a")
                ax.set_title(f"{trace.name} — {window_name}")
                ax.set_ylim(-100.0, 2.0)
                ax.grid(True, color="0.88", linewidth=0.45)
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                if row == len(audit.traces) - 1:
                    ax.set_xlabel("frequency (Hz)")
                if column == 0:
                    ax.set_ylabel("relative magnitude (dB)")
        axes[0, 0].set_xlim(0.0, min(4000.0, 0.5 * audit.sample_rate_hz))
        fig.savefig(path)
        plt.close(fig)


def write_cause_audit(
    plot_path: Path,
    report_path: Path,
    result: SimulationResult,
    final_audio: np.ndarray | None = None,
    audio_processing: str = "peak normalization only",
    comparison: CauseAudit | None = None,
    audit: CauseAudit | None = None,
) -> CauseAudit:
    """Analyze one result and write its cause-audit plot and Markdown report."""

    computed = audit or analyze_cause_audit(result, final_audio, audio_processing)
    write_cause_audit_plot(plot_path, computed)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(cause_audit_markdown(computed, comparison), encoding="utf-8")
    return computed
