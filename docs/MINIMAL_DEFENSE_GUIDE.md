# Minimal Defense Guide

## Project Goal

The project implements an offline reduced physical model of one diatonic
harmonica channel for a class project. The goal is an audible prototype whose
sound comes from solved model states.

## Model Assumptions

- Each reed is a lumped mass-spring-damper oscillator.
- The reed-slot opening is a linear gap law clipped at zero.
- Airflow through each reed slot uses a Bernoulli/orifice approximation.
- The chamber is a lumped acoustic compliance.
- The vocal tract is a reduced second-order resonator driven by net reed flow.
- The breath input is a simple smooth pressure envelope.

## State Vector

$$
[x_b,\ v_b,\ x_d,\ v_d,\ p_c,\ p_t,\ v_t]
$$

## Equations

The implemented equations are listed in `docs/MODEL_EQUATIONS.md`. The central
right-hand side is `harmonica_minimal.equations.state_derivative`.

## Execution Flow

1. `run.py` parses mode and simple breath options.
2. `parameters_for_mode` selects draw or blow physical parameters.
3. `simulate_note` integrates the seven-state ODE with `solve_ivp`.
4. `output.py` writes normalized chamber pressure, trace CSV, and diagnostics.
5. `plots.py` writes one compact validation figure per note.

By default, `run.py` writes to the next `output/output-N/` directory. Passing
`--output-dir name` writes to `output/name/`.

## File Map

- `run.py`: command-line entry point
- `src/harmonica_minimal/parameters.py`: physical and numerical parameters
- `src/harmonica_minimal/equations.py`: proposal equations and ODE right-hand side
- `src/harmonica_minimal/simulate.py`: offline numerical integration
- `src/harmonica_minimal/output.py`: WAV, CSV, and text diagnostics
- `src/harmonica_minimal/plots.py`: compact validation figure
- `tests/`: minimal behavior tests

## Inside The Model

The model includes reed mechanics, pressure forces, nonlinear Bernoulli slot
flow, chamber pressure integration, optional source-aligned moving-reed flow,
and a reduced vocal-tract resonator.

## Deliberately Excluded

There is no external acoustic renderer, no samples, no pitch shifting, no
post-processing chain, no automated parameter search, and no reference-audio
matching workflow. The WAV is normalized chamber pressure from the solved
physical model, not an external radiation model.

## Missing Versus Full Realism

Implemented from the proposal: reed dynamics, pressure forces, nonlinear
Bernoulli flow, chamber-pressure feedback, the reduced vocal-tract resonator,
and direct numerical integration.

Still reduced: the reed opening/contact law is a clipped linear gap; there is
no body/cover acoustic coloration, no external radiation model, and no full
vocal-tract geometry. These omissions should be presented as model scope, not
as hidden defects.

## Source Roles

The main proposal is the binding model source. Bilbao supports the direct
numerical physical-modeling approach. Fletcher supports the nonlinear
instrument/free-reed framing. Rossing supports general acoustics context.

## Answering Defense Questions

- If asked where the sound comes from: from the solved chamber pressure $p_c(t)$.
- If asked why it is not fully realistic: the model is intentionally reduced.
- If asked why no polishing was added: the branch is constrained to proposal
  equations and direct state export.
- If asked what to improve physically: refine the reed opening/crossing law,
  add documented contact mechanics, or replace the reduced vocal tract with a
  better physical load.
