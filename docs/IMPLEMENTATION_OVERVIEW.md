# Implementation Overview

## Purpose

This document explains the structure of the seminar-core implementation.

The project implements a reduced physical model of one channel of a diatonic harmonica. It is intended as a compact class-project implementation of the proposal equations.

The documentation is explanatory rather than argumentative. Simplifications and limitations are stated directly.

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