# Model Equations

This implementation solves one reduced diatonic harmonica channel with the
state vector

`[x_b, v_b, x_d, v_d, p_c, p_t, v_t]`.

`x_b, v_b` are blow reed displacement and velocity. `x_d, v_d` are draw reed
displacement and velocity. `p_c` is chamber pressure. `p_t, v_t` are the
reduced vocal-tract pressure state and its derivative.

## Implemented Equations

1. Reed dynamics

   `m_i x_i'' + r_i x_i' + k_i x_i = F_i`

   Implemented in `harmonica_minimal.equations.state_derivative`.

2. Blow reed force

   `F_b = S_b (p_m - p_c)`

   Implemented in `harmonica_minimal.equations.blow_reed_force`.

3. Draw reed force

   `F_d = S_d (p_c - p_out)`

   Implemented in `harmonica_minimal.equations.draw_reed_force`.

4. Reed opening

   `A_i(x_i) = W_i max(0, h_i0 + alpha_i x_i)`

   Implemented in `harmonica_minimal.equations.reed_gap` and
   `harmonica_minimal.equations.opening_area`.

5. Bernoulli/orifice gap flow

   `Q_gap,i = C_i A_i(x_i) sign(Delta p_i) sqrt(2 abs(Delta p_i) / rho)`

   Implemented in `harmonica_minimal.equations.bernoulli_gap_flow`.

6. Optional moving-reed flow

   `Q_motion,i = S_motion,i hdot_i`

   `hdot_i` is approximated as `alpha_i x_i'`, the derivative of the linear gap
   law. Implemented in `harmonica_minimal.equations.motion_flow`. It is off by
   default and switchable with `--motion-flow on/off`.

7. Total reed flow

   `Q_i = Q_gap,i + Q_motion,i`

   Implemented in `harmonica_minimal.equations.total_reed_flow`.

8. Chamber pressure

   `p_c' = rho c^2 / V_c (Q_b - Q_d)`

   Implemented in `harmonica_minimal.equations.chamber_pressure_derivative`.

9. Reduced vocal-tract resonator

   `p_t'' + (omega_t / Q_t) p_t' + omega_t^2 p_t = omega_t^2 Z_t (Q_b - Q_d)`

   Implemented in `harmonica_minimal.equations.state_derivative`.

## Output

The WAV is normalized chamber pressure from the solved physical model, not an
external radiation model.

