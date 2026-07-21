# Code walkthrough

## Simulation and output path

`src/harmonica_minimal/simulate.py` integrates the seven-state ODE and returns a
`SimulationResult`. The physical state traces include chamber pressure `p_c`,
tract pressure `p_t`, and both reed displacements. The result also carries the
derived blow and draw flows evaluated from the solved state.

`src/harmonica_minimal/output.py` selects chamber pressure for the WAV and peak
normalizes it. An optional command-line DC blocker affects the WAV path only.
The current seminar model does not implement a separate radiation filter, body
or cover coloration, or an added flow-noise layer. Consequently, with the
default WAV settings the relative spectrum of `audio` should match `p_c`; the
cause audit keeps them separate so that this remains testable if the output
layer is extended later.

## Cause audit

`src/harmonica_minimal/diagnostics.py` is a read-only diagnostic layer. It does
not feed values back into the ODE, change model parameters, or alter the signal
written to the WAV. For each mode it compares:

- rendered audio
- chamber and tract pressure (`p_c`, `p_t`)
- blow flow, draw flow, and net flow
- blow and draw reed displacement (`x_b`, `x_d`)

Each trace receives a full-note spectrum and a steady-state-only spectrum. The
steady window begins after the attack plus a safety margin and ends before the
release minus a safety margin. For normal renders it is limited to the latest one
second before that endpoint so that post-attack settling is not averaged into a
stationary spectrum. The current envelope has no pre-delay, so its derived
pre-delay is zero. Very short smoke-test renders use a bounded fallback window
instead of failing.

Every spectrum removes the mean, applies a Hann window, and uses `rFFT` with
`rfftfreq`. Magnitudes are normalized to the largest component and expressed as
relative dB with a finite floor. This shared method makes the core ODE states
directly comparable with the output/radiation layer without changing either.

## Interpreting full-note and steady-state spectra

A full-note FFT includes the breath attack and release. Multiplying an
oscillation by this time envelope can spread energy around a harmonic, while a
finite FFT record and its window determine bin spacing and leakage. A feature
that appears only in the full-note spectrum can therefore be associated with
the note boundary or analysis choice; persistence in steady-state `p_c`, flow,
or reed motion places the observation earlier in the physical-model path.

The H1–H6 detector reports significant noncentral peaks with the neutral phrases
“sideband-like component detected” and “sideband-like component not detected.”
These shoulders are diagnostic observations. Their presence does not by itself
validate them as physical harmonica behavior, and their absence can depend on
duration, FFT resolution, the Hann window, and the documented detector
thresholds.

Normal runs add these files for every selected mode:

- `<mode>_note_cause_audit.png`
- `<mode>_note_cause_audit.md`

When both modes are rendered, the run also writes
`blow_draw_spectral_window_audit.png`, which compares full-note and late
chamber-pressure spectra using the same axes and method.

The presentation and validation pressure panels distinguish the prescribed
mouth boundary `p_m`, the outside reference `p_out = 0`, and the solved chamber
state `p_c`. For the default `+/-250 Pa` run, blow and draw use the same symmetric
`-260 Pa` to `+260 Pa` ordinate. This is a display-only comparison choice: it
does not clamp pressure, change the ODE, or alter the WAV. For larger command-line
pressure overrides the limit expands automatically to avoid clipping.

## Blow/draw operating presets

The default source boundaries now have equal magnitude: `+250 Pa` for blow and
`-250 Pa` for draw. The former `-700 Pa` draw default was bend-scale rather than
normal-play scale and was removed. This is a physical-model parameter change,
so it changes the draw trace and WAV; the cause audit itself remains read-only.

The two modes still share the source-oriented reed resonance, mass, and quality
factor data but use different effective gaps, pressure areas, and discharge
coefficients. These are reduced operating closures for the proposal's series
pressure-flow equations, not a claim that channel 4 changes geometry with flow
direction. Consequently, the draw output is a qualitative normal-pressure
operating regime and not an independently validated fixed-geometry prediction.
