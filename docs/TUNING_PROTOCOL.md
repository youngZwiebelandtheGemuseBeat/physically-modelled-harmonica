# Tuning Protocol

Tune the model only through physical parameters and physically plausible
closures. The goal is to make the coupled model self-exciting and harmonica-like
without adding a fake synthesis layer.

## Allowed Tuning Controls

- reed rest openings
- effective surfaces
- discharge coefficients
- reed damping / Q
- pressure envelope
- chamber volume / pressure scaling
- opening function and reed closure
- output choice from `p_c`, `Q_b`, `Q_d`, or a weighted physical combination
- vocal-tract resonance, Q, and loading parameters for bending demonstrations

## Disallowed Tuning Shortcuts

- samples
- wavetable synthesis
- sawtooth/filter fake harmonica synthesis
- pitch shifting as bending
- machine learning
- GUI work
- realtime audio work
- C++ rewrite for this prototype

## Procedure

1. Start from a passing test suite and a stable non-silent render.
2. Render the same note after each parameter change.
3. Inspect `outputs/draw_note_trace.csv` for reed displacement, reed velocity,
   chamber pressure, tract pressure, and flows.
4. Inspect `outputs/draw_note_diagnostics.png` for instability, clipping, flow
   sign errors, and lack of nonlinear behaviour.
5. Change one physical parameter group at a time.
6. Prefer stability over brightness when a parameter creates runaway pressure or
   solver failure.
7. Commit or record parameter sets only when they are reproducible through
   `python run.py`.

## Milestone 3 Acceptance Checks

- The sound is no longer a fading sine.
- The attack is reed-like rather than a pure amplitude ramp.
- The trace shows pressure-flow feedback instead of a one-way oscillator.
- The spectrum or waveform shows audible harmonic content.
- The implementation still maps directly to the proposal equations.
