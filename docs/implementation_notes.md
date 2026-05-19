# Implementation Notes

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
