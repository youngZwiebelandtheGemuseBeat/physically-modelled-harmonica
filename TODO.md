# TODO

## Milestone 1: Stable Python Render Pipeline

- [x] Produce a non-silent offline WAV from Python.
- [x] Write draw-note WAV output.
- [x] Write draw-note CSV trace output.
- [x] Write draw-note diagnostics plot.
- [x] Add smoke tests for non-silent render.
- [x] Accept that the first stable sound may be sine-like.

## Milestone 2: Full Coupled Proposal State

- [x] Implement state vector `[x_b, v_b, x_d, v_d, p_c, p_t, v_t]`.
- [x] Use both blow and draw reed oscillators in one ODE system.
- [x] Use Bernoulli flow for `Q_b` and `Q_d`.
- [x] Feed chamber pressure back into reed forces and flows.
- [x] Add reduced vocal-tract resonator state.
- [x] Update diagnostics to show nonlinear flow and chamber-pressure feedback.
- [x] Keep WAV output non-silent and stable.
- [x] Keep `pytest` passing.
- [x] Confirm Milestone 2 implements the full coupled proposal model.

## Milestone 3: Self-Exciting Harmonica-Like Model

- [x] Establish diagnostic baseline for chamber feedback, reed participation,
      harmonic energy, and reed closure.
- [x] Tune reed rest openings for stronger draw-reed slot modulation.
- [x] Tune effective surfaces.
- [x] Tune discharge coefficients.
- [x] Tune reed damping / Q.
- [x] Tune chamber volume / pressure scaling.
- [x] Tune opening function and reed closure.
- [x] Add documented closure damping as a physical reed-slot approximation.
- [x] Choose physical output from `p_c`, `p_t`, `Q_b`, `Q_d`, or a weighted
      physical combination.
- [x] Verify sound is no longer the stable but sine-like Milestone 1 tone.
- [x] Verify audible harmonic content increased in Milestone 3B.
- [x] Document current acoustic observations, diagnostic metrics, strengths,
      weaknesses, and tuning direction.
- [x] Restore a physically plausible breath envelope through `p_breath(t)` as
      the source for `p_m`.
- [x] Add `attack_time`, `release_time`, `sustain_pressure`, and optional
      `breath_noise_amount` parameters.
- [x] Add CLI options `--attack`, `--release`, and `--pressure`.
- [x] Add CLI options `--pre-delay` and `--duration`.
- [x] Plot `p_breath(t)` or `p_m(t)` in diagnostics.
- [x] Include attack time, release time, and sustain pressure in the report.
- [x] Verify attack is audible, smooth, and not implemented as a post-audio
      fade.
- [x] Add attack-ratio test comparing first 100 ms against the sustain region.

## Current Milestone 3D Baseline

- [x] Stable, non-clipped, non-silent output.
- [x] Harmonic energy ratio: `0.701115`.
- [x] Spectral centroid / f0: `1.47`.
- [x] Mostly sinusoidal: `no`.
- [x] Draw reed opening near closed: `48.58%`.
- [x] Chamber pressure feedback nonzero: `yes`.
- [x] Reed participation: `both reeds participate`.
- [x] Attack ratio first 100 ms / sustain: `0.013433`.
- [ ] Improve spectral centroid toward `2x f0` only if stability and physical
      coupling are preserved.
- [x] Restore the weakened natural breath/fade-in envelope by shaping mouth
      pressure physically.

## Milestone 4: Blow And Draw Presets

- [x] Add draw-note preset.
- [x] Add blow-note preset.
- [x] Keep sign convention clean for both directions.
- [x] Add CLI mode `python run.py --mode draw`.
- [x] Add CLI mode `python run.py --mode blow`.
- [x] Add CLI mode `python run.py --mode both`.
- [x] Render `outputs/draw_note.wav`.
- [x] Render `outputs/draw_note_trace.csv`.
- [x] Render `outputs/draw_note_diagnostics.png`.
- [x] Render `outputs/draw_note_report.md`.
- [x] Render `outputs/blow_note.wav`.
- [x] Render `outputs/blow_note_trace.csv`.
- [x] Render `outputs/blow_note_diagnostics.png`.
- [x] Render `outputs/blow_note_report.md`.
- [x] Render `outputs/comparison_report.md`.
- [x] Render `outputs/comparison_diagnostics.png`.
- [x] Add tests for draw, blow, and both mode outputs.
- [x] Add tests that draw and blow audio are not identical.
- [x] Add tests for the pressure sign convention.
- [x] Improve the first blow preset so it has sustained reed oscillation.
- [x] Add a regression test so blow mode cannot pass with only a DC airflow
      plateau.
- [ ] Continue tuning draw/blow brightness and tone quality through physical
      parameters only.

## Milestone 5: Reference-Based Calibration And Radiation Layer

- [x] Add optional reference WAV analysis.
- [x] Compute fundamental estimate.
- [x] Compute harmonic amplitudes 1-12.
- [x] Compute harmonic energy ratio.
- [x] Compute spectral centroid and rolloff.
- [x] Compute attack time, RMS envelope, and spectral envelope.
- [x] Add synthetic-vs-reference comparison report.
- [x] Add synthetic-vs-reference comparison plot.
- [x] Add high-pass / differentiating radiation tendency for simulated flow
      output.
- [x] Add optional low-Q body/chamber coloration.
- [x] Add optional low-level flow-driven turbulence noise.
- [x] Keep flow noise driven by `abs(Q_b)`, `abs(Q_d)`, and pressure drops.
- [x] Add `python run.py --calibrate`.
- [x] Search reed Q/damping.
- [x] Search rest openings and opening scaling.
- [x] Search discharge coefficients.
- [x] Search chamber volume and leakage-radiation conductance.
- [x] Search tract resonance frequency, Q, and coupling.
- [x] Search output choice, radiation settings, and flow-noise amount.
- [x] Rank candidates by harmonic content, centroid, waveform shape, attack
      stability, and reference similarity when provided.
- [x] Write top candidate WAVs under `outputs/calibration/`.
- [x] Keep the core ODE proposal equations intact.
- [x] Document radiation and noise approximations physically.

## Milestone 5B: Vocal-Tract Sweep / Bend Demonstration

- [ ] Add tract parameter sweep.
- [ ] Change pitch/timbre through vocal-tract resonance/loading parameters.
- [ ] Do not use fake pitch shifting.
- [ ] Render a short bend demonstration.

## Milestone 6: Audible Radiation / Output Stage

- [x] Audit the current audio output path.
- [x] Document whether output uses `p_c`, `p_t`, `Q_b`, `Q_d`, `Q_b - Q_d`,
      and reed displacement in `outputs/output_path_audit.md`.
- [x] Add `--output pressure`.
- [x] Add `--output flow`.
- [x] Add `--output mixed`.
- [x] Add physically motivated radiation high-pass / differentiating tendency
      controls.
- [x] Add broad body/cover resonance coloration in the radiation layer.
- [x] Add flow-driven turbulent noise only in the output/radiation layer.
- [x] Add CLI `--noise`.
- [x] Add CLI `--radiation on|off`.
- [x] Add `python run.py --output-compare`.
- [x] Write comparison WAVs under `outputs/output_compare/`.
- [x] Include output mode, radiation settings, noise gain, harmonic energy
      ratio, spectral centroid, spectral rolloff, and attack ratio in reports.
- [x] Keep the core ODE proposal equations intact.
- [x] Keep `pytest` passing.

## Milestone 7: Professor Demo Package

- [ ] Create final WAV set.
- [ ] Create final diagnostic plots.
- [ ] Create final CSV traces.
- [ ] Write a short explanation connecting implementation blocks to proposal
      equations.
