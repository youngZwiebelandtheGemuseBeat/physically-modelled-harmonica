# Model Equations

Milestone 1 implements one offline diatonic harmonica channel with two lumped reed
states, one chamber pressure state, and one reduced vocal-tract pressure resonator.

State vector:

```text
y = [x_b, v_b, x_d, v_d, p_c, p_t, v_t]
```

where `x_b` and `x_d` are blow and draw reed displacements, `v_b` and `v_d`
are their velocities, `p_c` is chamber pressure, `p_t` is vocal-tract pressure,
and `v_t = p_t'`.

Reed dynamics:

```text
m_i x_i'' + r_i x_i' + k_i x_i = F_air
```

Pressure forces:

```text
F_b = S_b (p_m - p_c)
F_d = S_d (p_c - p_out)
```

Bernoulli airflow:

```text
Q_b = C_b A_b(x_b) sgn(p_m - p_c) sqrt(2 |p_m - p_c| / rho)
Q_d = C_d A_d(x_d) sgn(p_c - p_out) sqrt(2 |p_c - p_out| / rho)
```

Chamber pressure:

```text
p_c' = rho c^2 / V_c * (Q_b - Q_d)
```

Reduced vocal tract:

```text
p_t'' + (omega_t / Q_t) p_t' + omega_t^2 p_t
    = omega_t^2 Z_t (Q_b - Q_d)
```

The offline audio signal is derived from the simulated vocal-tract pressure plus
a small pressure contribution proportional to the same net acoustic flow that
drives the tract resonator.
