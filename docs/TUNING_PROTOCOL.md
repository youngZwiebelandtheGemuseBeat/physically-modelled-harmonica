# Tuning Protocol

Tune the model only through physical parameters and physically plausible
closures. The goal is to make the coupled model self-exciting and harmonica-like
without adding a fake synthesis layer.

## Allowed Tuning Controls

- reed rest openings
- effective surfaces
- discharge coefficients
- reed damping / Q
- pressure envelope
- chamber volume / pressure scaling
- opening function and reed closure
- output choice from `p_c`, `Q_b`, `Q_d`, or a weighted physical combination
- vocal-tract resonance, Q, and loading parameters for bending demonstrations
- radiation high-pass / differentiating tendency for simulated flow output
- low-Q body/chamber coloration
- low-level turbulent flow noise driven by simulated flows and pressure drops

## Disallowed Tuning Shortcuts

- samples
- wavetable synthesis
- sawtooth/filter fake harmonica synthesis
- pitch shifting as bending
- machine learning
- GUI work
- realtime audio work
- C++ rewrite for this prototype

## Procedure

1. Start from a passing test suite and a stable non-silent render.
2. Render the affected mode after each parameter change.
3. Inspect `outputs/draw_note_trace.csv` or `outputs/blow_note_trace.csv` for reed displacement, reed velocity,
   chamber pressure, tract pressure, pressure drops, openings, and flows.
4. Inspect the matching diagnostics PNG for instability, clipping, flow
   sign errors, and lack of nonlinear behaviour.
5. Inspect the matching report for objective metrics: fundamental,
   harmonic energy ratio, spectral centroid, reed participation, opening
   closure percentage, and chamber feedback.
6. Change one physical parameter group at a time.
7. Prefer stability over brightness when a parameter creates runaway pressure or
   solver failure.
8. Commit or record parameter sets only when they are reproducible through
   `python run.py`.

## Milestone 3A Diagnostic Baseline

Before tuning for brightness or recognizability, confirm that the physical
states are doing useful work:

- `p_c` RMS should be clearly nonzero; if it is near zero, chamber compliance or
  flow magnitudes are too weak to feed back into the reeds.
- Both `DeltaP_b` and `DeltaP_d` should vary over the note; if one is nearly
  constant, that side is acting like a static leak rather than a coupled reed.
- At least one reed opening should approach closure for part of the cycle; if
  `A_b` and `A_d` never move near closed, the Bernoulli nonlinearity will stay
  too gentle and the sound will remain sine-like.
- `Q_b` and `Q_d` should not be simple scaled copies of one reed displacement;
  visible flattening, clipping, or asymmetric flow peaks indicate useful
  nonlinear aero-acoustic behavior.
- The harmonic energy ratio should rise as physical nonlinearities strengthen.
  A very low ratio with centroid close to the fundamental means the output is
  still mostly sinusoidal.

## Concrete Parameter-Tuning Plan

Work in short branches or recorded parameter sets and change only one group at a
time.

1. Establish the baseline report.
   Run `python run.py`, save the report metrics, and listen only after checking
   that the render is stable and non-silent.

2. Tune reed rest openings and closure thresholds.
   Reduce the active reed rest opening in small steps so `A_d` approaches
   closure during oscillation, then adjust the inactive reed so it participates
   without becoming a dominant static leak. Target visible area modulation and
   a higher harmonic energy ratio without solver failure.

3. Tune effective pressure areas and slot widths.
   Increase reed pressure areas only enough to strengthen reed motion. Use slot
   widths and rest gaps to control flow amplitude separately from mechanical
   forcing. Reject settings where chamber pressure becomes a one-way pressure
   ramp or either flow collapses to zero for the whole note.

4. Tune reed damping / Q.
   Raise Q to make self-excitation easier, but back off if displacement grows
   without bounded closure behavior. The desired result is a reed-like attack
   and sustained oscillation, not an undamped free oscillator.

5. Tune discharge coefficients.
   Adjust `C_b` and `C_d` to strengthen Bernoulli coupling after the openings
   are moving. Use the report to confirm that flow RMS and harmonic energy rise
   together.

6. Tune chamber volume and pressure scaling.
   Smaller effective chamber volume increases pressure feedback. Move in small
   factors and watch `p_c` RMS, `p_c'`, and solver stability. If `p_c` dominates
   but reed motion shrinks, the acoustic compliance is too stiff for the current
   reed parameters.

7. Tune the mouth-pressure envelope.
   Increase draw pressure or shorten attack only after the passive parameters
   are close. The onset should excite the reed system, not simply fade in a
   linear oscillator.

8. Tune vocal-tract loading.
   Move tract frequency near the reed frequency and adjust tract Q/impedance to
   reinforce pressure-flow feedback. Do not use the tract as a separate tone
   source; it must remain driven by `Q_b - Q_d`.

9. Revisit the physical output mix.
   Choose a weighted combination of `p_c`, `p_t`, `Q_b`, and `Q_d` only after
   the internal traces show nonlinear behavior. Keep the report honest: if the
   internal states are sine-like, output weighting should not be used to disguise
   that.

10. Accept a parameter set only when all required outputs are generated,
    `pytest` passes, the report says chamber feedback is nonzero, at least one
    reed closure percentage is meaningful, and the sound is audibly less
    sinusoidal for physical reasons.

## Milestone 4 Draw/Blow Protocol

Run:

```text
python run.py --mode draw
python run.py --mode blow
python run.py --mode both
```

Pressure convention:

- positive `p_m` means blow pressure from the mouth side
- negative `p_m` means draw suction from the mouth side
- `DeltaP_b = p_m - p_c`
- `DeltaP_d = p_c - p_out`

Draw tuning starts from the Milestone 3D baseline. It should preserve the
draw-reed near-closure behavior, the `444 Hz` fundamental estimate, the
non-sinusoidal harmonic ratio, and the slow physical breath attack.

Blow tuning starts from the first Milestone 4 blow preset. It should preserve
positive mouth pressure and blow-reed dominance. The next useful changes are
physical only: blow-reed rest opening, displacement-to-gap scale, pressure
area, Q/damping, chamber volume, vocal-tract loading, and the physical output
mix from pressure/flow states. Do not improve the blow note by adding a fake
oscillator, pitch shifter, sample, wavetable, or subtractive synth layer.

Use `outputs/comparison_report.md` and
`outputs/comparison_diagnostics.png` after `--mode both` to confirm:

- draw and blow pressures have opposite signs
- draw and blow outputs are not identical
- the draw report estimates draw-reed dominance
- the blow report estimates blow-reed dominance
- both modes remain stable and non-silent

## Milestone 5 Reference And Calibration Protocol

Reference audio may be used only for measurement and comparison:

```text
python run.py --analyze-reference path/to/reference.wav
python run.py --mode draw --compare-reference path/to/reference.wav
python run.py --calibrate
python run.py --calibrate --compare-reference path/to/reference.wav
```

The analysis reports estimate fundamental frequency, harmonic amplitudes 1-12,
harmonic energy ratio, spectral centroid, 85% spectral rolloff, attack time,
RMS envelope, and spectral envelope.

The calibration command ranks physical candidates by harmonic energy ratio,
spectral centroid, non-sinusoidal waveform behavior, stable attack, and
reference similarity when a reference is provided. Reject candidates that sound
brighter only because the internal model became unstable or clipped.

Radiation tuning rules:

- Flow output may be high-passed or partly differentiated because compact flow
  radiation tends toward pressure proportional to volume velocity derivative.
- Body coloration must remain a low-Q coloration of the simulated source, not a
  narrow resonator that creates an independent note.
- Flow-noise amount must remain low and must be driven by `abs(Q_b)` and
  `abs(Q_d)`. Do not add a constant noise bed.
- Reference files must not be loaded into the renderer, looped, resynthesized,
  pitch-shifted, or used as wavetables.

Current `--calibrate` baseline:

- best candidate: `brighter_flow_radiation`
- harmonic energy ratio: `1.017`
- spectral centroid: `765.7 Hz`
- top WAVs: `outputs/calibration/best_01_brighter_flow_radiation.wav`,
  `outputs/calibration/best_02_tract_near_second_harmonic.wav`, and
  `outputs/calibration/best_03_tighter_active_opening.wav`

## Milestone 6 Output/Radiation Protocol

Render and compare the output layer without changing the ODE:

```text
python run.py --mode draw --output pressure
python run.py --mode draw --output flow
python run.py --mode draw --output mixed
python run.py --mode both --output mixed
python run.py --mode draw --noise 0.02
python run.py --mode draw --radiation on
python run.py --output-compare
```

Interpretation rules:

- `pressure` should expose the raw chamber-pressure character from `p_c`.
- `flow` should sound brighter/more radiated because compact volume-velocity
  radiation has a high-pass or differentiating tendency.
- `mixed` should remain the default listening candidate because it combines
  simulated pressure and flow components without adding a separate oscillator.
- Radiation `off` is an audit path; radiation `on` is the intended acoustic
  output approximation.
- Noise gains should stay subtle. Values around `0.006` to `0.02` are intended
  as low-level unresolved turbulent-flow coloration, not hiss.

Each render report should include output mode, radiation settings, noise gain,
harmonic energy ratio, spectral centroid, spectral rolloff, and attack ratio.

## Milestone 3 Acceptance Checks

- The sound is no longer a fading sine.
- The attack is reed-like rather than a pure amplitude ramp.
- The trace shows pressure-flow feedback instead of a one-way oscillator.
- The spectrum or waveform shows audible harmonic content.
- The implementation still maps directly to the proposal equations.

## Milestone 3B Sweep

Run:

```text
python run.py --sweep
```

The command renders candidates into `outputs/sweep/`, with one WAV and one
Markdown report per candidate plus `summary.md`. The ranking score favors:

- stable, non-clipped, non-silent output
- higher harmonic energy ratio
- spectral centroid above the fundamental
- stronger attack
- one reed near closed for part of the note, but not always closed

The target for the next iteration is:

- harmonic energy ratio above `0.05`
- spectral centroid near `2x f0` if it can be reached without instability
- `Mostly sinusoidal: no`
- one reed near-closed between `5%` and `60%`
- stable, non-silent output

## Current Milestone 3B Baseline

The current default render is the Milestone 3B baseline. It uses the full
coupled proposal model from Milestone 2, with stronger reed-slot nonlinearity
and documented closure damping. The sound now begins to resemble a harmonica,
but the natural breath/fade-in envelope became weaker after the stronger
nonlinear tuning.

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

Metric interpretation:

- Harmonic energy ratio `0.701431` and `mostly sinusoidal: no` mean Milestone
  3B has moved well beyond the stable but sine-like Milestone 1 tone.
- Spectral centroid / f0 `1.48` means the tone has useful harmonic content but
  is still not as bright as the optional `2x f0` target.
- Draw reed near closure at `47.30%` means the active reed-slot aperture is
  entering the nonlinear region for a meaningful part of the note.
- Blow reed near closure at `0.00%` is acceptable for the current draw-note
  preset but remains a possible tuning target for later blow/draw balance.
- Nonzero chamber pressure feedback and both-reed participation confirm that
  the sound comes from the coupled physical model, not from an isolated reed or
  post-processing trick.

Current strengths:

- stable, non-clipped, non-silent output
- strong harmonic improvement over the Milestone 1 sine-like baseline
- full Milestone 2 coupled model remains active
- reed-slot modulation is visible in diagnostics
- chamber and vocal-tract states contribute to the pressure/flow output

Current weaknesses:

- the onset is less naturally breath-shaped than desired
- the current default pressure drive emphasizes quick excitation over a
  controllable breath attack
- the spectral centroid is below the aspirational `2x f0` target
- the current draw preset mainly closes the draw reed, while the blow reed stays
  open

## Milestone 3C Breath-Envelope Tuning

The next tuning step is to restore attack behavior physically through the mouth
pressure source. Add a smooth `p_breath(t)` and use it as the source for `p_m`
inside the ODE drive path. Do not use an arbitrary audio fade after rendering as
the main solution.

Required controls:

- `attack_time`
- `release_time`
- `sustain_pressure`
- optional `breath_noise_amount`, default `0`

Recommended envelope shape:

- raised cosine attack from zero pressure to `sustain_pressure`
- held sustain region
- raised cosine or exponential release back toward zero pressure

Tuning procedure for Milestone 3C:

1. Keep the Milestone 3B reed, chamber, flow, and vocal-tract equations
   unchanged.
2. Use `p_breath(t)` to define the mouth pressure `p_m(t)` that drives the
   existing pressure force and Bernoulli flow equations.
3. Start with a moderate attack, for example `0.20 s` to `0.30 s`, and compare
   the onset against the current default render.
4. Adjust `sustain_pressure` only enough to preserve stable self-excitation and
   the Milestone 3B harmonic ratio.
5. Use release time to model breath shutdown within the pressure source, not as
   a post-render WAV fade.
6. Plot `p_breath(t)` or `p_m(t)` in diagnostics and include attack time,
   release time, and sustain pressure in the report.

Acceptance for Milestone 3C:

- `pytest` passes
- `python run.py` works
- attack is audible and smooth
- the sound remains more harmonica-like than Milestone 2
- diagnostics show the pressure envelope
- the report includes `attack_time`, `release_time`, and `sustain_pressure`

## Milestone 3D Audible Einschwingen Baseline

Milestone 3D makes the physical breath attack audible and visible. The mouth
pressure source is now:

```text
p_m_source(t) = mouth_pressure_pa * envelope(t)
```

For the default draw note, `mouth_pressure_pa = -900 Pa`. The envelope is zero
for `pre_delay_s`, rises with a raised-cosine attack over `attack_s`, holds
during sustain, and releases near the end of the render over `release_s`. This
pressure source is applied before the physical equations, so it changes
`F_b`, `DeltaP_b`, `Q_b`, chamber pressure feedback, and the resulting reed
motion. It is not a post-render audio fade.

Default Milestone 3D controls:

- duration: `2.5 s`
- pre-delay: `0.05 s`
- attack time: `0.35 s`
- release time: `0.20 s`
- release start: `2.30 s`
- sustain pressure: `-900 Pa`
- breath noise amount: `0`

CLI controls:

```text
python run.py --attack 0.35
python run.py --pre-delay 0.05
python run.py --release 0.20
python run.py --duration 2.5
python run.py --pressure 900
```

Positive `--pressure` values are interpreted as draw suction and converted to a
negative signed mouth pressure. Negative values are used as given.

Latest default metrics from `outputs/draw_note_report.md`:

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
- draw reed opening near closed: `48.58%`
- chamber pressure feedback nonzero: `yes`
- reed participation: `both reeds participate`

Metric interpretation:

- Attack ratio `0.013433` is below the acceptance target `< 0.35`, so the first
  100 ms is much quieter than the sustain region.
- Harmonic energy ratio `0.701115` and `mostly sinusoidal: no` show that the
  Milestone 3B harmonic character survived the slower breath attack.
- Draw reed near closure at `48.58%` confirms that reed-slot nonlinearity
  remains active.
- Spectral centroid / f0 `1.47` remains below the optional `2x f0` brightness
  target, so future tuning should still focus on brightness only when stability
  and physical coupling are preserved.

Milestone 3D tuning checks:

1. Inspect the diagnostics plot and confirm that both `p_m_source(t)` and
   `envelope(t)` rise gradually.
2. Keep `attack_ratio < 0.35` while changing physical parameters.
3. Reject parameter sets where harmonic energy collapses or the sound becomes
   mostly sinusoidal again.
4. Do not use RMS normalization, per-window gain, or a cosmetic WAV fade to meet
   the attack target.
