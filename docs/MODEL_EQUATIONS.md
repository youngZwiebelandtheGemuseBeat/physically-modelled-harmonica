# Model Equations

This implementation solves one reduced diatonic harmonica channel with the
state vector

$$
[x_b,\ v_b,\ x_d,\ v_d,\ p_c,\ p_t,\ v_t]
$$

$x_b, v_b$ are blow reed displacement and velocity. $x_d, v_d$ are draw reed
displacement and velocity. $p_c$ is chamber pressure. $p_t, v_t$ are the
reduced vocal-tract pressure state and its derivative.

## Implemented Equations

1. Reed dynamics

   $$
   m_i \ddot{x}_i + r_i \dot{x}_i + k_i x_i = F_i
   $$

   Implemented in `harmonica_minimal.equations.state_derivative`.

2. Blow reed force

   $$
   F_b = S_b(p_m - p_c)
   $$

   Implemented in `harmonica_minimal.equations.blow_reed_force`.

3. Draw reed force

   $$
   F_d = S_d(p_c - p_{\mathrm{out}})
   $$

   Implemented in `harmonica_minimal.equations.draw_reed_force`.

4. Reed opening

   $$
   A_i(x_i) = W_i \max(0, h_{i,0} + \alpha_i x_i)
   $$

   Implemented in `harmonica_minimal.equations.reed_gap` and
   `harmonica_minimal.equations.opening_area`.

5. Bernoulli/orifice gap flow

   $$
   Q_{\mathrm{gap},i}
   =
   C_i A_i(x_i)
   \operatorname{sgn}(\Delta p_i)
   \sqrt{\frac{2|\Delta p_i|}{\rho}}
   $$

   Implemented in `harmonica_minimal.equations.bernoulli_gap_flow`.

6. Optional moving-reed flow

   $$
   Q_{\mathrm{motion},i} = S_{\mathrm{motion},i}\dot{h}_i
   $$

   $\dot{h}_i$ is approximated as $\alpha_i \dot{x}_i$, the derivative of the linear gap
   law. Implemented in `harmonica_minimal.equations.motion_flow`. It is off by
   default and switchable with `--motion-flow on/off`.

7. Total reed flow

   $$
   Q_i = Q_{\mathrm{gap},i} + Q_{\mathrm{motion},i}
   $$

   Implemented in `harmonica_minimal.equations.total_reed_flow`.

8. Chamber pressure

   $$
   \dot{p}_c = \frac{\rho c^2}{V_c}(Q_b - Q_d)
   $$

   Implemented in `harmonica_minimal.equations.chamber_pressure_derivative`.

9. Reduced vocal-tract resonator

   $$
   \ddot{p}_t
   +
   \frac{\omega_t}{Q_t}\dot{p}_t
   +
   \omega_t^2 p_t
   =
   \omega_t^2 Z_t(Q_b - Q_d)
   $$

   Implemented in `harmonica_minimal.equations.state_derivative`.

## Output

The WAV is normalized chamber pressure from the solved physical model, not an
external radiation model.
