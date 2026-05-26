# Source Mapping

## Purpose

This document maps the implemented seminar-core model to the proposal sections and source categories.

It is intentionally concise. It is not a separate literature review.

## Model overview

The implemented model follows the proposal structure:

1. reed dynamics
2. nonlinear airflow
3. chamber-pressure evolution
4. reduced vocal-tract loading

## 1. Reed dynamics

### Implemented equation

$$
m_i \ddot{x}_i + r_i \dot{x}_i + k_i x_i = F_i
$$

### Code

- `harmonica_minimal.equations.state_derivative`
- `harmonica_minimal.parameters.ReedParameters`

### Proposal location

- Section 1.1
- Section 1.3

### Source category

**Millot et al. (2001)**

Supports the use of equivalent one-degree-of-freedom damped oscillators for harmonica reeds and reports that reed motion during playing is approximately sinusoidal.

**Systemdynamik**

Supports the state-space formulation and conversion of second-order oscillator equations into a first-order ODE system.

## 2. Pressure-driven reed forces

### Implemented equations

$$
F_b = S_b(p_{m,\mathrm{effective}} - p_c)
$$

$$
F_d = S_d(p_c - p_{\mathrm{out}})
$$

### Code

- `harmonica_minimal.equations.effective_mouth_pressure`
- `harmonica_minimal.equations.blow_pressure_drop`
- `harmonica_minimal.equations.blow_reed_force`
- `harmonica_minimal.equations.draw_reed_force`

### Proposal location

- Section 1.1
- Section 1.2

### Source category

**Proposal reduced-force closure**

The force law is treated as a lumped pressure-loading approximation:

$$
F \approx S_i \Delta p
$$

This uses effective pressure-loaded reed surfaces rather than detailed pressure distributions.

## 3. Reed opening law

### Implemented equation

$$
A_i(x_i) = W_i \max(0, h_{i,0} + \alpha_i x_i)
$$

### Code

- `harmonica_minimal.equations.reed_gap`
- `harmonica_minimal.equations.opening_area`

### Proposal location

- Section 1.4
- Nomenclature

### Source category

**Fletcher / Förtsch / Millot source context**

The simple opening law is a reduced representation of reed-gap geometry. It connects reed displacement to effective airflow area.

This is a modeling simplification.

## 4. Bernoulli/orifice gap flow

### Implemented equations

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

### Code

- `harmonica_minimal.equations.bernoulli_gap_flow`

### Proposal location

- Section 1.4
- Equations (8) and (9)

### Source category

**Fletcher / Förtsch**

Motivates the reduced pressure-controlled valve and Bernoulli-style free-reed airflow formulation.

**Millot et al. (2001)**

Supports the interpretation that harmonic richness comes mainly from nonlinear airflow rather than strongly distorted reed displacement.

## 5. Optional moving-reed flow

### Optional implemented equation

$$
Q_{\mathrm{motion},i}
=
S_{\mathrm{motion},i}\dot{h}_i
$$

### Code

- `harmonica_minimal.equations.motion_flow`
- switchable with `--motion-flow on/off`

### Proposal location

- Section 1.4 discussion before equations (8) and (9)

### Source category

**Fuller free-reed flow formulation discussed in the proposal**

The proposal states that the full flow formulation can contain both a gap-flow term and a moving-reed term. It then explicitly neglects the moving-reed term in the compact seminar model.

Therefore, this term is source-aligned but not part of the main compact proposal equations.

Recommended interpretation:

- default off: compact proposal model
- on: optional extension / comparison

## 6. Chamber-pressure evolution

### Implemented equation

$$
\dot{p}_c =
\frac{\rho c^2}{V_c}
(Q_b - Q_d)
$$

### Code

- `harmonica_minimal.equations.chamber_pressure_derivative`

### Proposal location

- Section 1.5
- Equation (10)

### Source category

**Möser / EA_1 / Zollner & Zwicker**

Motivates the lumped acoustic compliance relation, pressure-flow analogies, and compressible cavity interpretation.

## 7. Vocal-tract loading

### Implemented equation

$$
\ddot{p}_t
+
\frac{\omega_t}{Q_t}\dot{p}_t
+
\omega_t^2 p_t
=
\omega_t^2 Z_t(Q_b - Q_d)
$$

### Code

- `harmonica_minimal.equations.state_derivative`
- `harmonica_minimal.equations.effective_mouth_pressure`

### Proposal location

- Section 1.7
- Equation (12)

### Source category

**Wolfe et al. (2009)**

Motivates vocal-tract resonances and acoustic loading in musical instrument performance.

**Egbert et al. (2013)**

Motivates the relevance of vocal-tract geometry and tongue configuration in harmonica pitch bending.

### Implemented coupling term

The state $p_t$ is the reduced vocal-tract pressure state. The static breath
source is denoted $p_{m,\mathrm{static}}$. The mouth-side pressure after reduced
tract loading is:

$$
p_{m,\mathrm{effective}} = p_{m,\mathrm{static}} - \eta_t p_t
$$

The parameter $\eta_t$ is implemented as `vocal_tract_feedback_gain`.
$p_{m,\mathrm{effective}}$ is used in the blow-side pressure drop and blow-reed
force:

$$
\Delta p_b = p_{m,\mathrm{effective}} - p_c
$$

$$
F_b = S_b(p_{m,\mathrm{effective}} - p_c)
$$

The draw-side pressure law remains $p_c - p_{\mathrm{out}}$. Setting
$\eta_t=0$ recovers the previous one-way tract state behavior. This is still a
reduced lumped acoustic load, not a full vocal-tract geometry simulation.

## 8. Numerical simulation

### Implemented method

Direct numerical integration of the first-order ODE system.

### Code

- `harmonica_minimal.simulate.simulate_note`
- `harmonica_minimal.parameters.SimulationConfig`

### Proposal location

- Section 1.8
- Section 2 approach

### Source category

**Bilbao**

Motivates direct numerical simulation in physical modeling.

**Systemdynamik**

Motivates state-space representation of coupled dynamical systems.

## 9. Output

### Implemented output

The WAV file is normalized chamber pressure:

$$
\mathrm{wav}(t)=p_c(t)/\max|p_c(t)|
$$

### Code

- `harmonica_minimal.output.normalized_chamber_pressure`
- `harmonica_minimal.output.write_pressure_wav`

### Source category

This is not a separate physical model. It is only an export of the simulated state variable $p_c(t)$.

No external radiation model is implemented in seminar-core.

## 10. Excluded processing

The seminar-core branch deliberately excludes:

- radiation filtering
- body/cover resonance
- flow-noise synthesis
- mixed pressure/flow rendering
- EQ
- reference matching
- calibration search
- sample playback
- pitch shifting

These exclusions preserve the distinction between a reduced physical model and a sound-design system.
