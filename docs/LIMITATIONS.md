# Limitations

This repository is a seminar-scale reduced physical model. It is not a full
commercial harmonica model.

The implementation deliberately has:

- no external radiation model
- no body/cover resonance
- no flow-noise synthesis
- no full CFD
- no detailed reed-plate contact mechanics
- no full vocal-tract geometry
- no full 3D reed elasticity
- no claim of commercial-quality realism
- no hardcoded bending
- WAV output as normalized chamber pressure only

The sound can be plain or too sinusoidal for some parameter settings. That is a
model limitation, not a reason to add post-processing. The physical next step
would be refining the opening and crossing behavior, contact/loss assumptions,
or a better documented acoustic load while keeping the solved model as the
source.

The current reduced vocal-tract state is simulated as a resonant pressure state
driven by net flow. It is also coupled back into the mouth-side pressure path
through

$$
p_{m,\mathrm{effective}} = p_{m,\mathrm{static}} - \eta_t p_t.
$$

That effective mouth pressure is used in the blow-side pressure drop and
blow-reed force. The coupling is still a reduced lumped acoustic load, not a
full vocal-tract geometry simulation.

## Missing versus proposal / next steps

Implemented and defensible in this branch:

- reed mass-spring-damper dynamics
- pressure forces on blow and draw reeds
- Bernoulli/orifice nonlinear flow through reed openings
- chamber-pressure feedback
- reduced vocal-tract resonator
- direct offline numerical integration

Deliberately reduced or absent:

- the opening/contact law is a clipped linear gap, not detailed reed-plate
  contact mechanics
- there is no external radiation model or body/cover acoustic coloration
- there is no full vocal-tract geometry
- the WAV is a normalized simulated chamber-pressure signal

The main proposal remains the binding model source. The newer sources are used
as support context: Bilbao for direct numerical physical-model simulation,
Fletcher for nonlinear instrument/free-reed behavior, and Rossing for general
acoustics background.
