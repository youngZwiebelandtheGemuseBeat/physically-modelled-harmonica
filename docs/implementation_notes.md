# Implementation Notes

Current project state: Milestone 1 produced a stable but sine-like tone.
Milestone 2 implemented the full coupled proposal model. Milestone 3B increased
harmonic content and reed character through stronger reed-slot nonlinearity,
documented closure damping, and a pressure/flow output derived from simulated
states. The sound now begins to resemble a harmonica, but the natural
breath/fade-in envelope became weaker after stronger nonlinear tuning. The next
step is to restore attack behavior through a physically meaningful
mouth-pressure envelope rather than a post-audio fade.

Milestone 2 implements the full proposal state vector
`[x_b, v_b, x_d, v_d, p_c, p_t, v_t]` in one coupled ODE system solved with
`scipy.integrate.solve_ivp`. The default solver method is DOP853, which handled
the coupled reed, flow, chamber, and vocal-tract system reliably around the
clipped reed openings.

The ODE is evaluated on a 12 kHz integration grid, then the solved pressure and
reed states are interpolated to the 44.1 kHz output grid. This keeps the WAV and
trace at the requested audio rate without forcing the adaptive ODE solver to
report every audio sample.

Approximations:

- Each reed is a single lumped mass-spring-damper oscillator.
- Reed openings are rectangular effective areas with the explicit Milestone 3B
  law `A_i = max(A_min, W_i * max(0, h_i0 + sigma_i * x_i))`. The default
  `A_min` is zero so a geometrically closed reed has zero Bernoulli flow, which
  preserves the test contract for closed openings.
- `sigma_i` is the displacement-to-gap sign convention. The blow reed uses
  positive `sigma_b`, so positive blow-reed displacement increases its gap. The
  draw reed uses negative `sigma_d`, so positive draw-reed displacement reduces
  its gap during the draw-note closure part of the cycle. This makes the draw
  opening enter near closure periodically without adding a synthetic waveform.
- The draw reed has a small rest opening and stronger displacement-to-gap scale
  than the earlier baseline. This is a physical reed-slot modulation tuning:
  the nonlinearity comes from Bernoulli flow through a changing aperture.
- Milestone 3B adds optional reed-slot closure damping. When
  `h_i0 + sigma_i * x_i` falls inside a small closure zone, a smooth extra
  damping term is added to that reed's mechanical damping. This approximates
  reed/slot contact losses near closure. It is not an audio waveshaper and is
  applied inside the reed ODE before any audio output is formed.
- Blow and draw flows use the Bernoulli square-root pressure law directly:
  fixed discharge coefficient times effective area times signed jet speed.
- Chamber pressure is an acoustic compliance state driven by `Q_b - Q_d` and
  feeds back into both reed pressure forces and both flow pressure drops.
- The chamber volume is an effective acoustic compliance chosen for stable
  offline integration and stronger pressure feedback, not a detailed geometric
  measurement.
- Turbulent flow is represented only by the Bernoulli equations in the proposal
  with fixed discharge coefficients.
- The vocal tract is a single second-order pressure resonator driven by the same
  net flow `Q_b - Q_d`; it is not an independent tone source.
- The rendered WAV uses a pressure/flow radiation approximation from simulated
  states: a small vocal-tract pressure component plus an outlet draw-flow
  component. Sweep mode also renders flow-only and parameter variants. These
  are documented output choices from `p_t`, `Q_d`, and related simulated
  pressure/flow states, not oscillator layering or fake subtractive synthesis.
- The draw note uses one smooth negative mouth-pressure envelope with a short
  attack ramp. Milestone 3B raises the pressure and shortens the attack to make
  the coupled reed-slot system speak more strongly; the pressure is still only
  the physical drive term used by the ODE. The default release starts just after
  the 2-second render window because this milestone prioritizes a stable
  sustained coupled tone over modeling reed shutdown.
- The reduced vocal tract is tuned near the draw reed frequency region with
  moderate Q and impedance. It remains driven by `Q_b - Q_d`; it is not an
  independent sound source.
- `python run.py --sweep` renders physically tuned candidates under
  `outputs/sweep/`. Candidates are ranked by stable/non-clipped output,
  harmonic energy ratio, spectral centroid relative to f0, attack strength, and
  reed near-closure percentage. The current stable candidates improve harmonic
  content substantially over the Milestone 3A baseline, but the spectral
  centroid remains below 2x f0; forcing that target harder caused less useful
  parameter choices than accepting the stable reed-closure result.

## Current Acoustic Observations

The current default render is audibly closer to a harmonica than the Milestone 1
and Milestone 2 baselines. It has a clear reed-centered pitch, stronger harmonic
content, and a less purely sinusoidal waveform. The stronger nonlinear
reed-slot tuning makes the tone more reed-like, but the breath-shaped onset is
less natural than desired. The next audible improvement should be a smooth,
controllable pressure attack rather than more output processing.

## Current Diagnostic Metrics

Latest default metrics from `outputs/draw_note_report.md`:

- peak audio: `0.850000`
- RMS audio: `0.406446`
- estimated fundamental: `444.00 Hz`
- harmonic energy ratio, harmonics 2-8 vs fundamental: `0.701431`
- spectral centroid: `656.91 Hz`
- spectral centroid / f0: `1.48`
- mostly sinusoidal: `no`
- attack strength: `5432.41`
- RMS `x_b`: `2.028569135e-05 m`
- RMS `x_d`: `3.108101046e-05 m`
- RMS `p_c`: `2.110078032e+02 Pa`
- RMS `p_t`: `5.268223672e+02 Pa`
- RMS `Q_b`: `1.228234951e-06 m^3/s`
- RMS `Q_d`: `1.870442404e-06 m^3/s`
- blow reed opening near closed: `0.00%`
- draw reed opening near closed: `47.30%`
- chamber pressure feedback nonzero: `yes`
- reed participation: `both reeds participate`

Interpretation:

- The harmonic energy ratio is well above the `0.05` Milestone 3B threshold, so
  the output is no longer dominated by only the fundamental.
- `Mostly sinusoidal: no` confirms that the render moved beyond the stable but
  sine-like Milestone 1 result.
- Spectral centroid / f0 `1.48` shows added brightness, but it remains below
  the optional `2x f0` target.
- Draw reed near closure at `47.30%` shows that the reed-slot nonlinearity is
  physically active for a meaningful part of the note.
- Nonzero `p_c`, `p_t`, `Q_b`, and `Q_d` RMS values show that the chamber,
  vocal tract, and flows are participating in the coupled model.

## Current Strengths And Weaknesses

Strengths:

- stable non-silent offline render
- full Milestone 2 state vector and equation set remain in use
- stronger harmonic content and reed character after Milestone 3B
- physically coupled chamber pressure feedback
- both reeds participate in the current draw-note render
- no samples, wavetables, fake sawtooth/filter synthesis, or pitch shifting

Weaknesses:

- breath attack is not yet as natural or controllable as desired
- current brightness remains below the aspirational `2x f0` centroid target
- blow reed near-closure is not active in the current draw-note preset
- the current default pressure drive favors reliable excitation over expressive
  breath shaping

## Tuning Direction

The next tuning direction is Milestone 3C: restore a physically plausible breath
envelope by driving the existing model with a time-varying mouth pressure source
`p_breath(t)`. This should expose `attack_time`, `release_time`,
`sustain_pressure`, and optional `breath_noise_amount` parameters while keeping
the reed, chamber, Bernoulli flow, and vocal-tract equations unchanged.

The rationale is physical: in a real harmonica note, the player does not apply
full pressure instantaneously. A smooth pressure buildup changes the pressure
drops that drive reed force and airflow, so the attack emerges from the ODE
states. A post-audio fade would only hide the rendered onset after the model has
already run; it would not change reed excitation, chamber pressure feedback, or
flow nonlinearity.
