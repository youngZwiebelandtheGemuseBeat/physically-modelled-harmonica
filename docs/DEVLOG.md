# Devlog

## Current State After Milestone 3B

Milestone 1 produced a stable but sine-like tone. This was acceptable because
the first milestone was about the offline Python render pipeline, non-silent
WAV output, CSV traces, diagnostics, and passing tests rather than harmonica
recognizability.

Milestone 2 implemented the full coupled proposal model with blow and draw reed
oscillators, Bernoulli flows, chamber pressure feedback, and the reduced
vocal-tract resonator in one ODE state. This moved the project from a simple
rendering baseline to the required physical model.

Milestone 3B increased harmonic content and reed character by strengthening
reed-slot nonlinearity, using documented closure damping near reed-slot
closure, and rendering from simulated pressure and flow states. The sound now
begins to resemble a harmonica. It is stable, non-silent, no longer mostly
sinusoidal, and clearly more harmonica-like than the Milestone 1 sine-like
tone.

Latest default metrics from `outputs/draw_note_report.md`:

- peak audio: `0.850000`
- RMS audio: `0.406446`
- estimated fundamental: `444.00 Hz`
- harmonic energy ratio, harmonics 2-8 vs fundamental: `0.701431`
- spectral centroid: `656.91 Hz`
- spectral centroid / f0: `1.48`
- mostly sinusoidal: `no`
- attack strength: `5432.41`
- RMS `p_c`: `2.110078032e+02 Pa`
- RMS `p_t`: `5.268223672e+02 Pa`
- RMS `Q_b`: `1.228234951e-06 m^3/s`
- RMS `Q_d`: `1.870442404e-06 m^3/s`
- blow reed opening near closed: `0.00%`
- draw reed opening near closed: `47.30%`
- chamber pressure feedback nonzero: `yes`
- reed participation: `both reeds participate`

Interpretation:

- The harmonic energy ratio is far above the `0.05` Milestone 3B target, so the
  render is no longer dominated by a single sine-like fundamental.
- The spectral centroid is `1.48x f0`, which confirms added brightness but
  remains below the optional `2x f0` goal.
- The draw reed is near closed for `47.30%` of the note, placing the current
  preset inside the intended nonlinear reed-slot regime.
- Nonzero chamber feedback and both-reed participation confirm that the tone is
  coming from the coupled model rather than an isolated oscillator.

Current strengths:

- stable offline rendering
- full proposal equation set remains active
- audible harmonic content and reed character
- physically meaningful reed-slot closure behavior
- pressure/flow output derived from simulated states

Current weaknesses:

- the natural breath/fade-in envelope became weaker after stronger nonlinear
  tuning
- the onset is not yet as controllable as a played breath gesture should be
- the centroid is still below the aspirational `2x f0` brightness target
- the current draw-note preset mainly exercises draw-reed closure

## Milestone 3C Direction

The next step is to restore attack behavior through a physically meaningful
mouth-pressure envelope `p_breath(t)`. This should shape `p_m(t)`, the pressure
source used by the existing reed-force and Bernoulli-flow equations. It should
not be implemented as a post-render audio fade.

The rationale is that the player's breath pressure is part of the physical
drive. A smooth attack and release should alter reed excitation, pressure
drops, chamber feedback, and airflow inside the ODE. Fading the WAV afterward
would only change the final signal amplitude and would not affect the model
states that create the harmonica-like onset.
