# Implementation Notes

Current project state: Milestone 1 produced a stable but sine-like tone.
Milestone 2 implemented the full coupled proposal model. Milestone 3B increased
harmonic content and reed character through stronger reed-slot nonlinearity,
documented closure damping, and a pressure/flow output derived from simulated
states. The sound now begins to resemble a harmonica, but the natural
breath/fade-in envelope became weaker after stronger nonlinear tuning.
Milestone 3D restores the audible Einschwingen by applying a physically
meaningful mouth-pressure envelope before the reed force and Bernoulli flow
equations are evaluated, rather than fading the rendered WAV afterward.
Milestone 4 adds explicit draw, blow, and both render modes using the same
coupled physical model with mode-specific signed pressure and parameter
presets. Milestone 5 adds reference-based analysis, synthetic/reference
comparison, a more explicit radiation/output layer, low-level flow-driven noise,
and a bounded physical parameter calibration search. Milestone 6 makes the
output/radiation stage selectable and auditable so pressure, flow, and mixed
radiation can be compared without changing the core ODE state.

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
- `sigma_i` is the displacement-to-gap sign convention and can differ by
  mode-specific preset. In the draw preset, the draw reed uses negative
  `sigma_d`, so positive draw-reed displacement reduces its gap during the
  draw-note closure part of the cycle. In the blow preset, the blow reed uses
  positive displacement-to-gap coupling with a small rest opening. This lets
  the positive-pressure blow reed periodically enter the near-closed nonlinear
  region instead of settling into static DC flow.
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
- Milestone 5 moves the final audio construction into a documented radiation
  layer. The raw source can be `p_c`, `p_t`, `Q_b`, `Q_d`, `Q_b - Q_d`, or the
  existing physical pressure/flow mix. Flow-derived sources are high-passed and
  partly differentiated to approximate the pressure radiation tendency of a
  compact acoustic flow source. This is output radiation from simulated states,
  not a replacement oscillator.
- Optional body/chamber coloration is a low-Q resonant filter applied after the
  simulated pressure/flow source. It approximates broad cover-plate, hand, and
  small-cavity coloration. It is intentionally low-Q and cannot create a note by
  itself.
- Flow noise is subtle by default and can be set from the CLI. Its amplitude is
  `noise_gain * normalized(|Q_b| + |Q_d|)^noise_power`, so it grows only when
  the simulated Bernoulli flows are active. It is injected only in the
  output/radiation layer as an unresolved turbulent/noisy-flow approximation;
  it is not fed back into the reed equations and is not a constant noise bed.
- `chamber_leakage_conductance_m3_s_pa` is used only in the radiation/output
  stage as a small pressure-proportional leakage flow contribution. The core
  chamber pressure ODE remains the proposal equation
  `p_c' = rho c^2 / V_c * (Q_b - Q_d)`.
- The draw note uses a signed mouth-pressure source
  `p_m_source(t) = mouth_pressure_pa * envelope(t)`. For the default draw note,
  `mouth_pressure_pa` is negative. The envelope is zero during `pre_delay_s`,
  rises with a raised-cosine attack over `attack_s`, holds during sustain, and
  releases with a raised-cosine release over `release_s`. This pressure is used
  inside the ODE before computing `F_b`, `DeltaP_b`, and `Q_b`; it is not a
  post-render audio fade.
- Milestone 4 uses that same signed mouth-pressure source for both directions.
  Positive `mouth_pressure_pa` means blow pressure applied from the mouth side.
  Negative `mouth_pressure_pa` means draw suction at the mouth side.
  `DeltaP_b = p_m - p_c` is used for the blow-side force and flow, and
  `DeltaP_d = p_c - p_out` is used for the draw-side force and flow.
- The draw preset is the previous best-sounding Milestone 3D setup:
  `mouth_pressure_pa = -900 Pa`, a small draw-reed rest opening, strong
  draw-reed gap modulation, and output weighted toward tract pressure plus
  draw-side flow.
- The blow preset reverses the pressure direction with
  `mouth_pressure_pa = +600 Pa`. It uses a blow-reed-dominant parameter set:
  higher blow-reed Q than the passive draw reed, positive-pressure forcing on
  the blow reed, an active blow gap that reaches near closure during
  oscillation, and output weighted toward blow-side flow plus a small
  tract-pressure component.
- The default draw breath controls are `pre_delay_s = 0.05`,
  `attack_s = 0.35`, `release_s = 0.20`, `release_start_s = 2.30`,
  `mouth_pressure_pa = -900`, and `breath_noise_amount = 0`.
- Audio normalization is global peak scaling only. The renderer no longer
  subtracts a global DC mean before scaling, because doing so can add an
  artificial offset to the initial quiet breath-delay region. No RMS or
  per-window gain normalization is used.
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
- `python run.py --mode both` renders draw and blow outputs and writes
  `outputs/comparison_report.md` plus `outputs/comparison_diagnostics.png`.
- `python run.py --analyze-reference path/to/reference.wav` analyzes an
  external reference WAV for comparison only. It writes
  `outputs/reference_analysis.md` and `outputs/reference_analysis.png`.
- `python run.py --mode draw --compare-reference path/to/reference.wav` renders
  the physical model, analyzes both signals, and writes
  `outputs/reference_comparison.md` plus `outputs/reference_comparison.png`.
  Reference audio is never used as a synthesis source.
- `python run.py --calibrate` renders a bounded set of physical candidates and
  writes ranked reports plus the best candidate WAVs under
  `outputs/calibration/`. The current best draw candidate is
  `brighter_flow_radiation`, which increases the harmonic energy ratio from the
  radiated baseline `0.788` to `1.017` and the centroid from about `684 Hz` to
  about `766 Hz` in the calibration analysis.
- `python run.py --mode draw --output pressure`, `--output flow`, and
  `--output mixed` select the final radiation source. Pressure mode uses `p_c`.
  Flow mode uses scaled `Q_b - Q_d` after the small output-layer leakage term.
  Mixed mode combines simulated pressure and flow terms.
- `python run.py --mode draw --radiation on|off` enables or bypasses the
  radiation high-pass, differentiating tendency, and broad body/cover
  coloration. These filters are conservative output approximations only.
- `python run.py --mode draw --noise 0.02` sets the flow-driven turbulence
  approximation gain. The noise envelope is derived from simulated flows and is
  not part of the ODE by default.
- `python run.py --output-compare` writes pressure, flow, and mixed WAVs plus
  reports under `outputs/output_compare/`.

## Current Acoustic Observations

The current default render is audibly closer to a harmonica than the Milestone 1
and Milestone 2 baselines. It has a clear reed-centered pitch, stronger harmonic
content, and a less purely sinusoidal waveform. The stronger nonlinear
reed-slot tuning makes the tone more reed-like, but the breath-shaped onset is
less natural than desired. The next audible improvement should be a smooth,
controllable pressure attack rather than more output processing.

## Current Diagnostic Metrics

Latest draw metrics from `outputs/draw_note_report.md` after Milestone 4:

- peak audio: `0.850000`
- RMS audio: `0.373684`
- RMS first 100 ms: `0.005430`
- RMS sustain region 0.7-1.2 s: `0.404238`
- attack ratio first/sustain: `0.013433`
- estimated fundamental: `444.00 Hz`
- harmonic energy ratio, harmonics 2-8 vs fundamental: `0.701115`
- spectral centroid: `652.27 Hz`
- spectral centroid / f0: `1.47`
- mostly sinusoidal: `no`
- attack strength: `1.19`
- RMS `x_b`: `1.874150840e-05 m`
- RMS `x_d`: `2.917331347e-05 m`
- RMS `p_c`: `1.984474327e+02 Pa`
- RMS `p_t`: `4.928161716e+02 Pa`
- RMS `Q_b`: `1.147609846e-06 m^3/s`
- RMS `Q_d`: `1.748453097e-06 m^3/s`
- blow reed opening near closed: `0.00%`
- draw reed opening near closed: `48.58%`
- chamber pressure feedback nonzero: `yes`
- reed participation: `both reeds participate`
- dominant reed estimate: `draw reed`
- mouth pressure min/max: `-900.000 / -0.000 Pa`
- breath envelope min/max: `0.000 / 1.000`

Latest blow metrics from `outputs/blow_note_report.md` after Milestone 4:

- peak audio: `0.850000`
- RMS audio: `0.382622`
- RMS first 100 ms: `0.002765`
- RMS sustain region 0.7-1.2 s: `0.416823`
- attack ratio first/sustain: `0.006633`
- estimated fundamental: `398.00 Hz`
- harmonic energy ratio, harmonics 2-8 vs fundamental: `0.082648`
- spectral centroid: `439.17 Hz`
- spectral centroid / f0: `1.10`
- mostly sinusoidal: `no`
- RMS `x_b`: `3.697034001e-05 m`
- RMS `x_d`: `1.111069244e-05 m`
- RMS `p_c`: `4.056957853e+02 Pa`
- RMS `p_t`: `6.075870920e+02 Pa`
- RMS `Q_b`: `1.746924386e-06 m^3/s`
- RMS `Q_d`: `1.130973124e-06 m^3/s`
- blow reed opening near closed: `49.69%`
- draw reed opening near closed: `0.00%`
- chamber pressure feedback nonzero: `yes`
- reed participation: `both reeds participate`
- dominant reed estimate: `blow reed`
- mouth pressure min/max: `0.000 / 600.000 Pa`
- breath envelope min/max: `0.000 / 1.000`

Interpretation:

- The harmonic energy ratio is well above the `0.05` Milestone 3B threshold, so
  the output is no longer dominated by only the fundamental.
- `Mostly sinusoidal: no` confirms that the render moved beyond the stable but
  sine-like Milestone 1 result.
- Spectral centroid / f0 `1.47` shows added brightness, but it remains below
  the optional `2x f0` target.
- Draw reed near closure at `48.58%` shows that the reed-slot nonlinearity is
  physically active for a meaningful part of the note.
- Attack ratio `0.013433` is below the Milestone 3D target of `0.35`, so the
  first 100 ms is much quieter than the sustain region and the pressure buildup
  is audible and visible in diagnostics.
- Nonzero `p_c`, `p_t`, `Q_b`, and `Q_d` RMS values show that the chamber,
  vocal tract, and flows are participating in the coupled model.
- The blow preset is stable, non-silent, pressure-sign-correct, and
  blow-reed-dominant. It now shows sustained AC motion and blow-reed near
  closure instead of a static flow plateau.

## Current Strengths And Weaknesses

Strengths:

- stable non-silent offline render
- full Milestone 2 state vector and equation set remain in use
- stronger harmonic content and reed character after Milestone 3B
- physically coupled chamber pressure feedback
- both reeds participate in the current draw-note render
- explicit draw and blow render modes now share the same ODE path
- diagnostics estimate the dominant reed for each mode
- no samples, wavetables, fake sawtooth/filter synthesis, or pitch shifting

Weaknesses:

- current brightness remains below the aspirational `2x f0` centroid target
- blow reed near-closure is not active in the current draw-note preset
- both draw and blow still remain below the aspirational `2x f0` centroid target
- breath attack is now controllable, but still needs listening-based tuning for
  the most natural harmonica onset

## Tuning Direction

Milestone 3D restores a physically plausible breath envelope by driving the
existing model with a time-varying mouth pressure source `p_breath(t)`. It
exposes `attack_time`, `release_time`, `sustain_pressure`, and optional
`breath_noise_amount` controls while keeping the reed, chamber, Bernoulli flow,
and vocal-tract equations unchanged.

The rationale is physical: in a real harmonica note, the player does not apply
full pressure instantaneously. A smooth pressure buildup changes the pressure
drops that drive reed force and airflow, so the attack emerges from the ODE
states. A post-audio fade would only hide the rendered onset after the model has
already run; it would not change reed excitation, chamber pressure feedback, or
flow nonlinearity.

Next tuning should preserve the Milestone 3D attack ratio target while nudging
brightness and blow/draw balance through physical reed-slot, chamber, and
vocal-tract parameters.
