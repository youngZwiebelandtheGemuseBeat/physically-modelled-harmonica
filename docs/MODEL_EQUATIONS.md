# Model Equations

This project is a Python offline physical modelling prototype of one channel of
a diatonic harmonica. The implementation must stay tied to the proposal
equations below.

Milestone 1 produced a stable render pipeline and a non-silent sound. That sound
is not expected to be recognizably harmonica-like yet, because a single mostly
linear reed oscillator produces a sine-like tone. The harmonica identity must
come from the full coupled physical model:

1. blow and draw reeds as damped oscillators
2. Bernoulli-based nonlinear airflow through reed openings
3. chamber pressure feedback
4. reduced vocal-tract/acoustic load
5. physically derived output from chamber pressure and/or flow

## State Vector

Milestone 2 must implement the full proposal state vector:

```text
y = [x_b, v_b, x_d, v_d, p_c, p_t, v_t]
```

where `x_b` and `x_d` are blow and draw reed displacements, `v_b` and `v_d`
are reed velocities, `p_c` is chamber pressure, `p_t` is reduced vocal-tract
pressure, and `v_t = p_t'`.

## Reed Dynamics

For each reed `i`:

```text
m_i x_i'' + r_i x_i' + k_i x_i = F_air
```

Use this as a damped mass-spring oscillator with pressure-driven forcing.

## Pressure Forces

Blow reed force:

```text
F_b = S_b (p_m - p_c)
```

Draw reed force:

```text
F_d = S_d (p_c - p_out)
```

## Bernoulli Airflow

Blow-side flow:

```text
Q_b = C_b A_b(x_b) sgn(p_m - p_c) sqrt(2 |p_m - p_c| / rho)
```

Draw-side flow:

```text
Q_d = C_d A_d(x_d) sgn(p_c - p_out) sqrt(2 |p_c - p_out| / rho)
```

`A_b(x_b)` and `A_d(x_d)` are physical reed opening functions. Milestone 3B uses
the explicit form:

```text
A_b = max(A_min, W_b max(0, h_b0 + sigma_b x_b))
A_d = max(A_min, W_d max(0, h_d0 + sigma_d x_d))
```

The sign of `sigma_i` defines whether positive displacement opens or closes the
slot. Rest openings, closure clipping, and documented closure damping are
allowed as physical reed-slot approximations, but they must not become fake
synthesis sources.

## Chamber Pressure

```text
p_c' = rho c^2 / V_c * (Q_b - Q_d)
```

The chamber pressure must feed back into reed forces and the flow equations.
The implementation keeps this proposal term explicit and adds one documented
loss extension:

```text
Q_loss = G_c p_c
p_c' = rho c^2 / V_c * (Q_b - Q_d - Q_loss)
```

`G_c` is small and pressure-proportional. It represents unresolved chamber,
slot, cover-plate, and radiation losses so the chamber is not an ideal sealed
lossless compliance during note release. Setting `G_c = 0` recovers the proposal
equation exactly.

## Acoustic Load

Impedance definition:

```text
Z(omega) = P(omega) / Q(omega)
```

Reduced vocal-tract resonator:

```text
p_t'' + (omega_t / Q_t) p_t' + omega_t^2 p_t
= omega_t^2 Z_t (Q_b - Q_d)
```

The tract state is a reduced acoustic load, not a separate synthetic oscillator
used to fake timbre.

## Output Signal

The rendered audio must be physically derived from simulated chamber pressure
and/or flow, for example `p_c`, `Q_b`, `Q_d`, `p_t`, or a weighted physical
combination. It must not use samples, wavetables, sawtooth/filter fake harmonica
synthesis, pitch shifting, bend demonstrations, or machine learning.
