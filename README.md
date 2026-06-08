# Physically Modelled Harmonica

This is an offline reduced physical model of one diatonic harmonica channel for
a class project.

The implementation solves a seven-state ODE containing blow reed motion, draw
reed motion, chamber pressure, and a reduced vocal-tract pressure state. It uses
no samples, no wavetable synthesis, and no pitch shifting.

## Run

```bash
.venv/bin/python run.py --mode draw
.venv/bin/python run.py --mode blow
.venv/bin/python run.py --mode both
.venv/bin/python run.py --mode both --motion-flow off --wav-dc-block --parameter-preset generic_default --opening-model clipped --output-dir audible_all
.venv/bin/python run.py --mode both --motion-flow off --output-dir outputs_motion_flow_off
.venv/bin/python run.py --mode both --motion-flow on --output-dir outputs_motion_flow_on
.venv/bin/python run.py --mode both --motion-flow off --tract-feedback-gain 0.0 --output-dir tract_feedback_000
.venv/bin/python run.py --mode both --motion-flow off --tract-feedback-gain 0.05 --output-dir tract_feedback_005
.venv/bin/python run.py --mode both --motion-flow off --tract-feedback-gain 0.10 --output-dir tract_feedback_010
.venv/bin/python run.py --mode both --opening-model clipped
.venv/bin/python run.py --mode both --opening-model through_slot_simple --output-dir through_slot
.venv/bin/python run.py --mode blow --motion-flow off --wav-dc-block --parameter-preset millot_channel4_4b --opening-model through_slot_calibrated --source-validation millot_normal_blow_4b --output-dir millot_calibrated_blow
.venv/bin/python run.py --mode both --motion-flow off --wav-dc-block --parameter-preset millot_channel4_4b --opening-model clipped --source-validation millot_normal_blow_4b --output-dir baseline_clipped_millot
```

Optional simple controls:

```bash
.venv/bin/python run.py --mode draw --duration 1.5 --pressure 750 --attack 0.2 --motion-flow off
```

If the virtual environment is activated, `python run.py ...` is equivalent.

`generic_default` is the audible seminar prototype. `millot_channel4_4b` is an
experimental validation preset for comparing simulated state metrics with
Millot; it is not a replacement for the audible default and may sound harsh or
noise-like.

## Outputs

The commands write:

- `output/output-1/draw_pressure.wav`
- `output/output-1/draw_trace.csv`
- `output/output-1/draw_validation.png`
- `output/output-1/blow_pressure.wav`
- `output/output-1/blow_trace.csv`
- `output/output-1/blow_validation.png`
- `output/output-1/blow_source_validation.png` for a targeted source run
- `output/output-1/source_validation_report.md` for a targeted source run
- `output/output-1/blow_validation_metrics.json`

If `--output-dir` is omitted, `run.py` creates the next available `output-N`
directory inside the project-root `output/` directory, creating `output/` first
if needed. If `--output-dir` is passed, it is treated as a subdirectory of
`output/`, for example `--output-dir outputs_motion_flow_off` writes to
`output/outputs_motion_flow_off/`. Passing `--output-dir output/name` is also
accepted, but paths outside `output/` are rejected.

The WAV is normalized chamber pressure from the solved physical model, not an
external radiation model.

## Demo status

The branch implements the main proposal blocks: reed dynamics, pressure forces,
Bernoulli/orifice airflow, chamber-pressure feedback, a reduced vocal-tract
resonator, and direct offline numerical integration. It is ready to demonstrate
as a reduced proposal-based prototype.

The branch does not claim commercial-quality realism. The default opening
remains the clipped linear effective-gap law. An optional signed through-slot
law can close near the reedplate plane and reopen after a reed crosses it.
Both are reduced approximations; other major simplifications are the absence
of external radiation or body/cover acoustics and the reduced one-mode
vocal-tract load.

The generic preset remains the audible prototype. The experimental
`millot_channel4_4b` validation preset uses Millot Table 3 oscillator values
and labels all other constants as physical estimates or model assumptions. It
matches selected scalar targets but is not an audio-quality preset. Bahnson is
used for geometry and reed-function constraints. Bilbao is used for numerical
methodology, not harmonica-specific parameter values.

## Documentation

- `docs/MODEL_EQUATIONS.md` lists the implemented equations.
- `docs/SOURCE_MAPPING.md` maps equations and functions to proposal source categories.
- `docs/LIMITATIONS.md` states what is deliberately excluded.
- `docs/IMPLEMENTATION_OVERVIEW.md` explains the implementation structure.
- `docs/SOURCE_DERIVED_PARAMETERS.md` documents provenance and targets.
