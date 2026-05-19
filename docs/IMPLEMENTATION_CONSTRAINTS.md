# Implementation Constraints

This is a Python offline physical modelling prototype of one channel of a
diatonic harmonica. Future work must preserve that boundary.

## Must Use

- Python only.
- Offline rendering only.
- Explicit proposal equations.
- Physical parameters in `src/harmonica_model/params.py`.
- ODE right-hand side in `src/harmonica_model/equations.py`.
- Audio export in `src/harmonica_model/audio.py`.
- Diagnostics in `src/harmonica_model/diagnostics.py`.
- Approximations documented in `docs/implementation_notes.md`.

## Must Not Use

- samples
- wavetable synthesis
- sawtooth/filter fake harmonica synthesis
- pitch shifting as bending
- machine learning
- GUI
- realtime audio
- C++ rewrite for this prototype

## Required Equations

```text
m_i x_i'' + r_i x_i' + k_i x_i = F_air

F_b = S_b (p_m - p_c)

F_d = S_d (p_c - p_out)

Q_b = C_b A_b(x_b) sgn(p_m - p_c) sqrt(2 |p_m - p_c| / rho)

Q_d = C_d A_d(x_d) sgn(p_c - p_out) sqrt(2 |p_c - p_out| / rho)

p_c' = rho c^2 / V_c * (Q_b - Q_d)

Z(omega) = P(omega) / Q(omega)

p_t'' + (omega_t / Q_t) p_t' + omega_t^2 p_t
= omega_t^2 Z_t (Q_b - Q_d)
```

## Required Baseline Outputs

`python run.py` must produce:

```text
outputs/draw_note.wav
outputs/draw_note_trace.csv
outputs/draw_note_diagnostics.png
```

Milestone 4 adds:

```text
outputs/blow_note.wav
```

## Required Tests

`pytest` must pass. Tests should cover:

- flow sign convention
- flow is zero when opening is closed
- chamber pressure derivative has the expected sign
- render smoke test produces non-silent audio

Add tests when changing model contracts, sign conventions, outputs, or
diagnostic trace columns.
