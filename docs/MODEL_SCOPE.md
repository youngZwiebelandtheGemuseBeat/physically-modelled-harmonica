# Model Scope

## Project goal

This project implements a reduced physical model of one channel of a diatonic harmonica.

The goal is not to build a commercial harmonica synthesizer, audio-analysis toolkit, or polished sound-design system. The goal is to implement a compact, physically interpretable model based on the proposal equations and to simulate its state variables directly.

The scientific output of the model is the simulated chamber pressure $p_c(t)$. The WAV file is only a normalized version of this simulated pressure signal.

## Included components

The seminar-core model contains four coupled components:

1. reed dynamics
2. nonlinear airflow
3. chamber-pressure evolution
4. reduced vocal-tract loading

These are the four model blocks named in the proposal.

## 1. Reed dynamics

Each reed is modeled as an equivalent one-degree-of-freedom damped oscillator:

$$
m_i \ddot{x}_i + r_i \dot{x}_i + k_i x_i = F_i
$$

where:

- $m_i$ is the effective reed mass
- $r_i$ is the damping coefficient
- $k_i$ is the stiffness
- $x_i$ is reed displacement
- $F_i$ is the pressure-driven force

This is a lumped reduced model. It does not simulate full three-dimensional reed elasticity.

## 2. Pressure-driven reed forces

The pressure force is modeled as a lumped pressure load acting on an effective reed surface:

$$
F_b = S_b(p_{m,\mathrm{effective}} - p_c)
$$

$$
F_d = S_d(p_c - p_{\mathrm{out}})
$$

where:

- $F_b$ is the blow-reed force
- $F_d$ is the draw-reed force
- $S_b, S_d$ are effective pressure-loaded surfaces
- $p_{m,\mathrm{static}}$ is the imposed breath pressure envelope
- $p_{m,\mathrm{effective}}$ is the mouth-side pressure after reduced tract loading
- $p_c$ is chamber pressure
- $p_{\mathrm{out}}$ is outside pressure

This is a reduced force closure, not a detailed aerodynamic force distribution.

## 3. Nonlinear airflow

The compact proposal model uses Bernoulli/orifice-style airflow through reed openings:

$$
Q_b =
C_b A_b(x_b)
\operatorname{sgn}(p_{m,\mathrm{effective}} - p_c)
\sqrt{\frac{2|p_{m,\mathrm{effective}} - p_c|}{\rho}}
$$

$$
Q_d =
C_d A_d(x_d)
\operatorname{sgn}(p_c - p_{\mathrm{out}})
\sqrt{\frac{2|p_c - p_{\mathrm{out}}|}{\rho}}
$$

where:

- $Q_b, Q_d$ are volume flows
- $C_b, C_d$ are discharge coefficients
- $A_b, A_d$ are effective opening areas
- $\rho$ is air density

This is not a CFD model.

## 4. Reed opening

The opening area is modeled with a simple clipped gap law:

$$
A_i(x_i) = W_i \max(0, h_{i,0} + \alpha_i x_i)
$$

where:

- $W_i$ is effective reed-slot width
- $h_{i,0}$ is rest gap
- $\alpha_i$ maps reed displacement to gap change
- the maximum operation prevents negative geometric opening

This is a deliberately simple reduced opening model.

## 5. Optional moving-reed flow

The proposal discusses a fuller free-reed flow form containing a moving-reed contribution:

$$
Q_{\mathrm{motion},i} = S_{\mathrm{motion},i}\dot{h}_i
$$

However, the compact seminar model explicitly neglects this term and keeps only the Bernoulli/orifice gap-flow term.

Therefore:

- `--motion-flow off` is the proposal-faithful default.
- `--motion-flow on` is an optional source-aligned extension.
- Results generated with `--motion-flow on` should not be presented as the main compact proposal model.

## 6. Chamber pressure

The chamber is modeled as a lumped acoustic compliance:

$$
\dot{p}_c =
\frac{\rho c^2}{V_c}
(Q_b - Q_d)
$$

where:

- $p_c$ is chamber pressure
- $V_c$ is chamber volume
- $c$ is speed of sound
- $\rho c^2$ is the bulk modulus of air

This is the central feedback path:

$$
x_i \rightarrow A_i(x_i) \rightarrow Q_i \rightarrow p_c \rightarrow F_i \rightarrow x_i
$$

## 7. Reduced vocal-tract loading

The vocal tract is modeled as a reduced one-mode pressure resonator:

$$
\ddot{p}_t
+
\frac{\omega_t}{Q_t}\dot{p}_t
+
\omega_t^2 p_t
=
\omega_t^2 Z_t(Q_b - Q_d)
$$

where:

- $p_t$ is reduced vocal-tract pressure
- $\omega_t$ is tract resonance angular frequency
- $Q_t$ is tract quality factor
- $Z_t$ is effective tract coupling
- $Q_b - Q_d$ is the net flow drive

The tract pressure state is also coupled back into the mouth-side pressure path:

$$
p_{m,\mathrm{effective}} = p_{m,\mathrm{static}} - \eta_t p_t
$$

where $\eta_t$ is the dimensionless `vocal_tract_feedback_gain`.
$p_{m,\mathrm{effective}}$ is used in the blow-side pressure drop
$p_{m,\mathrm{effective}} - p_c$ and in the blow-reed force. The draw-side
pressure law remains $p_c - p_{\mathrm{out}}$.

Setting $\eta_t=0$ recovers the previous one-way tract state behavior:
$p_t$ is still simulated from the net flow, but it does not modify the
mouth-side pressure used by the reed/channel system.

This is a reduced lumped acoustic load, not a full vocal-tract geometry
simulation.

## 8. Numerical simulation

The model is solved by direct numerical integration of the coupled state equations.

The state vector is:

$$
[x_b,\ v_b,\ x_d,\ v_d,\ p_c,\ p_t,\ v_t]
$$

where $v_b=\dot{x}_b$, $v_d=\dot{x}_d$, and $v_t=\dot{p}_t$.

## Explicit exclusions

The seminar-core model deliberately excludes:

- external radiation model
- body/cover resonance coloration
- synthetic airflow noise
- EQ or post-processing coloration
- mixed pressure/flow rendering
- samples
- wavetables
- pitch shifting
- hidden audio oscillator
- machine learning
- automatic calibration search
- reference-audio matching
- full CFD
- full reed-contact mechanics
- full 3D reed elasticity
- full vocal-tract geometry
- hardcoded bending
- commercial-quality harmonica realism

## Output interpretation

The WAV output is normalized chamber pressure:

$$
\mathrm{wav}(t) =
\frac{p_c(t)}{\max |p_c(t)|}
$$

It is not an external acoustic radiation model.

## Missing versus proposal / next steps

The proposal-level core is implemented: reed ODEs, pressure forces,
Bernoulli/orifice flows, chamber-pressure evolution, reduced vocal-tract
loading, and direct numerical integration.

The main remaining work is physical refinement rather than adding a synthetic
audio layer:

- refine the clipped opening/contact closure
- tune physical parameters for stronger nonlinear flow while preserving
  stability
- document any future acoustic load more explicitly
- keep any external radiation or body/cover model out of the seminar-core
  branch unless it is introduced as a separate, documented physical extension

## Source roles

The main proposal is the binding source for the equations and scope. Bilbao is
used as support for direct numerical physical-model simulation, Fletcher for
nonlinear instrument/free-reed behavior, and Rossing for broader acoustics
background.

## Documentation philosophy

The documentation is descriptive.

Its purpose is to explain:

- which equations are implemented
- which assumptions are made
- which simplifications are used
- which limitations remain

Simplifications are stated directly.
