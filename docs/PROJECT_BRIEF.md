# Project Brief

This repository implements a Python offline physical modelling prototype of one
channel of a diatonic harmonica. The goal is a first audible prototype that is
clearly connected to the proposal equations and can become recognizably
harmonica-like through coupled reed, airflow, chamber, and acoustic-load
physics.

## Current Status

Milestone 1 is done: the project has a stable Python render pipeline that can
produce a non-silent WAV and diagnostics. The first sound is not expected to
sound like a harmonica yet, because a single mostly linear reed oscillator
produces a sine-like tone.

The harmonica identity must come from the full coupled physical model:

1. blow and draw reeds as damped oscillators
2. Bernoulli-based nonlinear airflow through reed openings
3. chamber pressure feedback
4. reduced vocal-tract/acoustic load
5. physically derived output from chamber pressure and/or flow

## Working Boundary

This is not a realtime instrument, plugin, GUI app, sample library, or fake
subtractive synthesizer. It is an offline Python research prototype whose main
output is rendered audio plus trace and diagnostic files.

The required command remains:

```text
python run.py
```

The draw-note baseline must produce:

```text
outputs/draw_note.wav
outputs/draw_note_trace.csv
outputs/draw_note_diagnostics.png
```

Later milestones add more outputs, but they must keep the same offline Python
model boundary.

## Repository Shape

- Keep physical parameters in `src/harmonica_model/params.py`.
- Keep the ODE right-hand side in `src/harmonica_model/equations.py`.
- Keep audio export in `src/harmonica_model/audio.py`.
- Keep diagnostics in `src/harmonica_model/diagnostics.py`.
- Document modelling approximations in `docs/implementation_notes.md`.
- Keep proposal equations and model intent in `docs/MODEL_EQUATIONS.md`.
- Keep milestone planning in `docs/ROADMAP.md` and `TODO.md`.

## Success Definition

The project succeeds when a professor can run an offline Python command, inspect
the WAV, trace, and plots, and see how each implemented block maps to the
proposal equations. Sound quality matters, but only when achieved through
physical model parameters and physically plausible closures.
