# AGENTS.md

## Project goal
Implement an offline Python physical model of one diatonic harmonica channel.

The goal is a first audible prototype that is clearly recognizable as harmonica-like, while staying based on the proposal equations.

## Hard constraints
Use Python only.
Use offline rendering only.
Do not implement realtime audio.
Do not use C++ in this prototype.
Do not use machine learning.
Do not use samples.
Do not use wavetable synthesis.
Do not use sawtooth/filter fake harmonica synthesis.
Do not fake bending with pitch shifting.

## Required physical model
The implementation must use these model blocks:

1. Reed dynamics:

$$
m_i \ddot{x}_i + r_i \dot{x}_i + k_i x_i = F_{\mathrm{air}}
$$

2. Blow reed pressure force:

$$
F_b = S_b(p_m - p_c)
$$

3. Draw reed pressure force:

$$
F_d = S_d(p_c - p_{\mathrm{out}})
$$

4. Bernoulli-based nonlinear airflow:

$$
Q_b =
C_b A_b(x_b)
\operatorname{sgn}(p_m - p_c)
\sqrt{\frac{2|p_m - p_c|}{\rho}}
$$

$$
Q_d =
C_d A_d(x_d)
\operatorname{sgn}(p_c - p_{\mathrm{out}})
\sqrt{\frac{2|p_c - p_{\mathrm{out}}|}{\rho}}
$$

5. Chamber pressure:

$$
\dot{p}_c = \frac{\rho c^2}{V_c}(Q_b - Q_d)
$$

6. Reduced vocal-tract resonator:

$$
\ddot{p}_t
+
\frac{\omega_t}{Q_t}\dot{p}_t
+
\omega_t^2 p_t
=
\omega_t^2 Z_t(Q_b - Q_d)
$$

## Implementation priorities
First priority: produce a non-silent WAV from the physical model.
Second priority: make it stable.
Third priority: tune parameters until it is clearly harmonica-like.
Do not over-engineer.

## Required outputs
python run.py must produce:
- outputs/draw_note.wav
- outputs/draw_note_trace.csv
- outputs/draw_note_diagnostics.png

## Required tests
pytest must pass.
Tests should check:
- flow sign convention
- flow is zero when opening is closed
- chamber pressure derivative has the expected sign
- render smoke test produces non-silent audio

## Coding style
Keep equations explicit.
Keep physical parameters in params.py.
Keep ODE right-hand side in equations.py.
Keep audio export in audio.py.
Keep diagnostics in diagnostics.py.
Document every approximation in docs/implementation_notes.md.
