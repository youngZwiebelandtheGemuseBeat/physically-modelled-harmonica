# physically-modelled-harmonica
Physical modeling of one channel of a diatonic harmonica.

This is an offline Python prototype. It renders audio from the coupled reed,
Bernoulli flow, chamber pressure, and reduced vocal-tract equations; it does
not use samples, wavetables, fake saw/filter synthesis, pitch shifting, machine
learning, bend demonstrations, realtime audio, a GUI, or C++.

## Render Modes

```text
python run.py --mode draw
python run.py --mode blow
python run.py --mode both
```

`python run.py` defaults to `--mode draw`.

Outputs:

- `outputs/draw_note.wav`
- `outputs/draw_note_trace.csv`
- `outputs/draw_note_diagnostics.png`
- `outputs/draw_note_report.md`
- `outputs/blow_note.wav`
- `outputs/blow_note_trace.csv`
- `outputs/blow_note_diagnostics.png`
- `outputs/blow_note_report.md`
- `outputs/comparison_report.md`
- `outputs/comparison_diagnostics.png`

## Pressure Sign Convention

Positive mouth pressure means the player blows into the channel. Negative mouth
pressure means draw suction at the mouth side. The implemented pressure drops
are:

```text
DeltaP_b = p_m - p_c
DeltaP_d = p_c - p_out
```

The draw preset uses negative `p_m` and is expected to be draw-reed dominant.
The blow preset uses positive `p_m` and is expected to be blow-reed dominant.
