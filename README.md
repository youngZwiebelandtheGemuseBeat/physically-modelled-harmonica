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
```

Optional simple controls:

```bash
python run.py --mode draw --duration 1.5 --pressure 750 --attack 0.2 --motion-flow off
```

## Outputs

The commands write:

- `outputs/draw_pressure.wav`
- `outputs/draw_trace.csv`
- `outputs/draw_validation.png`
- `outputs/blow_pressure.wav`
- `outputs/blow_trace.csv`
- `outputs/blow_validation.png`

The WAV is normalized chamber pressure from the solved physical model, not an
external radiation model.

## Documentation

- `docs/MODEL_EQUATIONS.md` lists the implemented equations.
- `docs/SOURCE_MAPPING.md` maps equations and functions to proposal source categories.
- `docs/LIMITATIONS.md` states what is deliberately excluded.
- `docs/MINIMAL_DEFENSE_GUIDE.md` gives a concise explanation for seminar discussion.

