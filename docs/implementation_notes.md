# Implementation Notes

Milestone 1 is intentionally conservative: it uses a small explicit state vector
and `scipy.integrate.solve_ivp` rather than a custom integrator. The default
solver method is DOP853, which handled the first sustained-oscillation parameter
set more reliably than LSODA around the clipped reed openings.

The ODE is evaluated on a 12 kHz integration grid, then the solved pressure and
reed states are interpolated to the 44.1 kHz output grid. This keeps the WAV and
trace at the requested audio rate without forcing the adaptive ODE solver to
report every audio sample.

Approximations:

- Each reed is a single lumped mass-spring-damper oscillator.
- Reed openings are rectangular effective areas: slot width times a clipped reed
  gap. The gap is never allowed to go below zero.
- The blow reed opens for positive blow displacement. The draw reed opens for
  negative draw displacement, matching the sign of its pressure force during a
  draw note.
- The chamber volume is an effective acoustic compliance chosen for stable
  offline integration, not a detailed geometric measurement.
- Turbulent flow is represented only by the Bernoulli equations in the proposal
  with fixed discharge coefficients.
- The vocal tract is a single second-order pressure resonator.
- The rendered WAV uses simulated pressure: vocal-tract pressure plus a small
  pressure-scaled net-flow term. It does not use samples, wavetables, sawtooth
  synthesis, filtering of a fake source, pitch shifting, machine learning, C++,
  realtime audio, or a GUI.
- The draw note uses one smooth negative mouth-pressure envelope with a short
  attack ramp. The default release starts just after the 2-second render window
  because the first milestone prioritizes a stable sustained tone over modeling
  reed shutdown.
