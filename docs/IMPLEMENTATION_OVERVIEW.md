# Implementation Overview

## Purpose

This document explains the structure of the seminar-core implementation.

The project implements a reduced physical model of one channel of a diatonic harmonica. It is intended as a compact class-project implementation of the proposal equations.

The documentation states simplifications and limitations directly.

## What the model does

The program numerically simulates a coupled system consisting of:

1. one blow reed
2. one draw reed
3. nonlinear Bernoulli/orifice airflow
4. chamber pressure
5. reduced vocal-tract pressure loading

The model is offline. It solves the ODE over a note duration and exports simulated state variables.

## What the model does not do

The seminar-core branch does not implement:

- samples
- wavetables
- pitch shifting
- external radiation filtering
- body coloration
- synthetic airflow noise
- reference matching
- calibration search
- full CFD
- full reed-contact mechanics
- full vocal-tract geometry
- commercial-quality harmonica realism

## State vector

The ODE state is:

$$
[x_b,\ v_b,\ x_d,\ v_d,\ p_c,\ p_t,\ v_t]
$$

where:

- $x_b$: blow reed displacement
- $v_b$: blow reed velocity
- $x_d$: draw reed displacement
- $v_d$: draw reed velocity
- $p_c$: chamber pressure
- $p_t$: reduced vocal-tract pressure
- $v_t=\dot{p}_t$: vocal-tract pressure derivative

## Execution flow

Running:

```bash
python run.py --mode draw
python run.py --mode both --tract-feedback-gain 0.0
python run.py --mode both --tract-feedback-gain 0.05
```

The main execution path is:

1. `run.py` parses mode, breath options, motion-flow state, and optional tract feedback gain.
2. `parameters_for_mode` selects draw or blow parameters.
3. `simulate_note` integrates the ODE state.
4. `output.py` writes normalized chamber pressure, CSV trace, and text diagnostics.
5. `plots.py` writes the validation figure from simulated state variables.

## Vocal-tract load term

$p_t$ is the reduced vocal-tract pressure state. $p_{m,\mathrm{static}}$ is the
imposed breath pressure envelope. The pressure seen on the mouth side of the
blow reed/channel path is:

$$
p_{m,\mathrm{effective}} = p_{m,\mathrm{static}} - \eta_t p_t
$$

where $\eta_t$ is `vocal_tract_feedback_gain`.

`p_m_effective` is used in:

1. the blow-side pressure drop, $\Delta p_b = p_{m,\mathrm{effective}} - p_c$
2. the blow-reed force, $F_b = S_b(p_{m,\mathrm{effective}} - p_c)$

The draw-side pressure law remains $\Delta p_d = p_c - p_{\mathrm{out}}$.
Setting $\eta_t=0$ recovers the previous one-way tract state behavior: $p_t$
is still simulated, but it does not modify the mouth-side pressure path. This
is a reduced lumped acoustic load, not a full vocal-tract geometry simulation.

## Output files

Each run writes a WAV file, trace CSV, validation plot, and text diagnostics.
The WAV signal remains normalized chamber pressure:

$$
\mathrm{wav}(t)=p_c(t)/\max|p_c(t)|
$$

## Demo readiness boundary

The branch implements the proposal-level core: reed ODEs, pressure forces,
Bernoulli/orifice flow, chamber-pressure feedback, reduced vocal-tract loading,
and direct offline numerical integration.

The remaining gap to a more realistic harmonica sound is physical refinement,
not fake synthesis. The most important candidates are the clipped reed-opening
and contact closure, parameter tuning for stronger nonlinear flow, and a more
explicit acoustic load. The seminar-core branch still excludes radiation
filtering, body/cover coloration, synthetic airflow noise, samples, wavetables,
pitch shifting, and machine learning.
