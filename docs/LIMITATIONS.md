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
driven by net flow. In the current seminar-core version it is not yet used as a
feedback pressure in the reed pressure drops. A later source-aligned improvement
would be to couple it back as a mouth-side acoustic load.
