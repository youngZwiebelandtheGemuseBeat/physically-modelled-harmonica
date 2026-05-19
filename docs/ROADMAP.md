# Roadmap

## Milestone 1: Stable Python Render Pipeline

Status: Done.

Expected result: stable non-silent output that may sound sine-like. It is not
expected to sound like a harmonica yet, because a single mostly linear reed
oscillator produces a sine-like tone.

## Milestone 2: Full Coupled Proposal State

Implement the full proposal state vector:

```text
[x_b, v_b, x_d, v_d, p_c, p_t, v_t]
```

Use both blow and draw reeds, Bernoulli flows, chamber pressure, and
vocal-tract resonator in one coupled ODE system.

Acceptance: WAV is non-silent, stable, and diagnostics show nonlinear flow and
chamber-pressure feedback.

## Milestone 3: Self-Exciting Harmonica-Like Model

Make the model self-exciting and harmonica-like.

Tune only physical parameters and physically plausible closures:

- reed rest openings
- effective surfaces
- discharge coefficients
- reed damping / Q
- pressure envelope
- chamber volume / pressure scaling
- opening function and reed closure
- output choice from `p_c`, `Q_b`, `Q_d`, or a weighted physical combination

Acceptance: sound is no longer a fading sine. It must show audible harmonic
content and a reed-like attack.

## Milestone 4: Blow And Draw Presets

Add one draw note and one blow note. Use the sign convention cleanly.

Acceptance: `python run.py` can render `draw_note.wav` and `blow_note.wav`.

## Milestone 5: Vocal-Tract Sweep / Bend Demonstration

Add a vocal-tract parameter sweep / bend demonstration. Do not use fake pitch
shifting. Bending must come from changing vocal-tract resonance/loading
parameters.

Acceptance: render a short sweep where pitch and timbre change because of tract
parameters.

## Milestone 6: Professor Demo Package

Create final WAVs, plots, CSV traces, and a short explanation connecting
implementation to the proposal equations.

Acceptance: the demo package can be reviewed without reading the whole codebase
and clearly explains which implemented blocks correspond to the proposal.
