# Physically Modelled Harmonica

This is an offline reduced physical model of one diatonic harmonica channel for
a class project.

The implementation solves a seven-state ODE containing blow reed motion, draw
reed motion, chamber pressure, and a reduced vocal-tract pressure state. It uses
no samples, no wavetable synthesis, and no pitch shifting.

## Run

```bash
python run.py --mode draw
python run.py --mode blow
python run.py --mode both
python run.py --mode both --motion-flow off --output-dir outputs_motion_flow_off
python run.py --mode both --motion-flow on --output-dir outputs_motion_flow_on
python run.py --mode both --motion-flow off --tract-feedback-gain 0.0 --output-dir tract_feedback_000
python run.py --mode both --motion-flow off --tract-feedback-gain 0.05 --output-dir tract_feedback_005
python run.py --mode both --motion-flow off --tract-feedback-gain 0.10 --output-dir tract_feedback_010
```

Optional simple controls:

```bash
python run.py --mode draw --duration 1.5 --pressure 750 --attack 0.2 --motion-flow off
```

## Outputs

The commands write:

- `output/output-1/draw_pressure.wav`
- `output/output-1/draw_trace.csv`
- `output/output-1/draw_validation.png`
- `output/output-1/blow_pressure.wav`
- `output/output-1/blow_trace.csv`
- `output/output-1/blow_validation.png`

If `--output-dir` is omitted, `run.py` creates the next available `output-N`
directory inside the project-root `output/` directory, creating `output/` first
if needed. If `--output-dir` is passed, it is treated as a subdirectory of
`output/`, for example `--output-dir outputs_motion_flow_off` writes to
`output/outputs_motion_flow_off/`. Passing `--output-dir output/name` is also
accepted, but paths outside `output/` are rejected.

The WAV is normalized chamber pressure from the solved physical model, not an
external radiation model.

## Documentation

- `docs/MODEL_EQUATIONS.md` lists the implemented equations.
- `docs/SOURCE_MAPPING.md` maps equations and functions to proposal source categories.
- `docs/LIMITATIONS.md` states what is deliberately excluded.
- `docs/IMPLEMENTATION_OVERVIEW.md` explains the implementation structure.
