# Sound Target

This project should become recognizably harmonica-like, but not through fake
synthesis shortcuts. The target is a physical model sound that has a reed-like
attack, pressure-dependent response, audible harmonic content, and coupling
between reed motion, airflow, chamber pressure, and acoustic loading.

## Milestone 1 Sound

Milestone 1 produced a stable sound, but it is not expected to sound like a
harmonica yet. A single mostly linear reed oscillator naturally produces a
sine-like tone. That is acceptable for Milestone 1 and should not be "fixed" by
adding fake bright oscillators or subtractive synthesis.

## Harmonica Identity

The harmonica character must emerge from:

1. blow and draw reeds as damped oscillators
2. Bernoulli-based nonlinear airflow through reed openings
3. chamber pressure feedback
4. reduced vocal-tract/acoustic load
5. physically derived output from chamber pressure and/or flow

## Desired Audible Qualities

- Non-silent, stable offline WAV output.
- Reed-like onset instead of a simple fade-in sine.
- Sustained oscillation driven by pressure and nonlinear flow.
- Harmonic content caused by reed closure, flow nonlinearity, and chamber/load
  coupling.
- Draw and blow notes with clean sign convention and different physical
  parameter presets.
- Bend demonstration caused by changing vocal-tract resonance/loading, not by
  pitch shifting.

## Explicit Non-Targets

Do not make the sound more harmonica-like by using samples, wavetable synthesis,
sawtooth/filter fake harmonica synthesis, pitch shifting as bending, machine
learning, a GUI, realtime audio, or a C++ rewrite for this prototype.
