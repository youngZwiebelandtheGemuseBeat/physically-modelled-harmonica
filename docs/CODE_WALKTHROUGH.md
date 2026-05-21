# Code Walkthrough For Defending The Model

This project renders one diatonic harmonica channel from an offline physical
model. It does not use samples, wavetables, pitch shifting, or a separate synth
oscillator. The sound comes from a coupled reed/air/chamber/tract model.

## Most Important Files

1. `src/harmonica_model/equations.py`
   - The core physics engine.
   - Contains the reed mass-spring-damper equations, pressure forces,
     Bernoulli flow equations, chamber pressure equation, chamber loss term,
     and reduced vocal-tract resonator.
   - If you need to defend the formulas, start here.

2. `src/harmonica_model/params.py`
   - The parameter sheet.
   - Defines the physical constants, reed masses/stiffness/damping/openings,
     chamber volume, mouth pressure, vocal-tract load, and radiation settings.
   - Draw and blow differ by parameters and pressure sign, not by a different
     synthesis algorithm.

3. `src/harmonica_model/controls.py`
   - The player input model.
   - Builds the smooth breath envelope and signed mouth pressure used inside
     the equations before the ODE is solved.
   - Important defense point: this is a physical drive signal, not a fade
     applied to the finished audio.

4. `src/harmonica_model/render.py`
   - The offline solver pipeline.
   - Calls `scipy.integrate.solve_ivp()` on the coupled ODE, interpolates the
     solved state to audio rate, and stores all diagnostic traces.
   - This is where the time simulation actually happens.

5. `src/harmonica_model/audio.py`
   - The output/radiation layer.
   - Converts simulated pressure and flow states into the final WAV signal with
     conservative high-pass, differentiation, body coloration, and optional
     flow-driven noise.
   - Important defense point: this layer uses simulated states only; it does
     not create a new note source.

## Supporting But Still Important Files

6. `src/harmonica_model/diagnostics.py`
   - Writes CSV traces, diagnostic plots, and model audit reports.
   - Useful for showing that both reeds, chamber pressure, tract pressure, and
     Bernoulli flows actually participate.

7. `src/harmonica_model/analysis.py`
   - Measures rendered or reference audio.
   - Computes fundamental frequency, harmonic energy, spectral centroid,
     rolloff, attack time, and reference similarity.

8. `run.py`
   - The command-line entry point.
   - Selects draw/blow/both mode, applies CLI settings, runs renders, writes
     output artifacts, and starts sweeps or calibration.

9. `tests/`
   - Regression checks proving sign conventions, closed-flow behavior, chamber
     pressure signs, non-silent renders, output modes, and draw/blow separation.

## End-To-End Workflow

1. `run.py` chooses a preset from `params.py`.
2. `controls.py` computes signed mouth pressure over time.
3. `render.py` asks SciPy to solve the ODE.
4. During the solve, `equations.py` repeatedly computes reed forces, openings,
   Bernoulli flows, chamber pressure feedback, and vocal-tract pressure.
5. `render.py` interpolates the solved state to audio sample rate and stores
   trace arrays.
6. `audio.py` turns simulated pressure/flow states into the final audio signal.
7. `diagnostics.py` and `analysis.py` write reports proving what happened.

## Core State Vector

The ODE state is:

```text
[x_b, v_b, x_d, v_d, p_c, p_t, v_t]
```

- `x_b`, `v_b`: blow reed displacement and velocity.
- `x_d`, `v_d`: draw reed displacement and velocity.
- `p_c`: chamber pressure.
- `p_t`: reduced vocal-tract pressure.
- `v_t`: vocal-tract pressure derivative.

## Core Equations Implemented

- Reed oscillator:
  `m_i x_i'' + r_i x_i' + k_i x_i = F_air`
- Blow reed force:
  `F_b = S_b (p_m - p_c)`
- Draw reed force:
  `F_d = S_d (p_c - p_out)`
- Blow-side Bernoulli flow:
  `Q_b = C_b A_b(x_b) sgn(p_m - p_c) sqrt(2 |p_m - p_c| / rho)`
- Draw-side Bernoulli flow:
  `Q_d = C_d A_d(x_d) sgn(p_c - p_out) sqrt(2 |p_c - p_out| / rho)`
- Chamber pressure:
  `p_c' = rho c^2 / V_c * (Q_b - Q_d - Q_loss)`
- Chamber loss extension:
  `Q_loss = G_c p_c`
- Vocal tract:
  `p_t'' + (omega_t / Q_t) p_t' + omega_t^2 p_t = omega_t^2 Z_t (Q_b - Q_d)`

## Defense Points

- The nonlinear harmonic content comes mainly from pressure-dependent Bernoulli
  flow through reed openings that change with reed displacement.
- Draw and blow are separated by signed mouth pressure, active reed parameters,
  reed-slot closure regime, tract loading, and output balance.
- The output stage is not the physical core; it is a radiation approximation
  applied after the coupled ODE has produced pressure and flow states.
- The reports and tests are part of the evidence that the implementation
  follows the stated physics.
