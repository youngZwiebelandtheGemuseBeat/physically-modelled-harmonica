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

## Milestone 3D Breath Attack

Milestone 3D implements the breath envelope as an audible and visible physical
drive. The default render now uses `pre_delay = 0.05 s`, `attack_time = 0.35 s`,
`release_time = 0.20 s`, `duration = 2.5 s`, and `sustain_pressure = -900 Pa`.
The envelope is a raised-cosine pressure buildup applied to `p_m_source(t)`
before the reed-force and Bernoulli-flow equations run.

This keeps the physical model intact: the attack changes reed excitation,
pressure drops, airflow, chamber feedback, and vocal-tract response. It is not
implemented as a post-render audio fade. Audio normalization is global peak
scaling only, so the first part of the note remains quieter than the sustain
region.

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

Interpretation:

- The Milestone 3D attack target is met because `0.013433 < 0.35`.
- The harmonic ratio remains essentially at the Milestone 3B level, so the more
  gradual breath attack did not erase the reed character.
- The diagnostics now show both `p_m_source(t)` and `envelope(t)`, making the
  Einschwingen visible as a pressure-drive event rather than an audio edit.

Current remaining tuning direction:

- preserve the breath attack ratio while listening for a natural onset
- improve brightness only through physical coupling and reed-slot parameters
- keep the full coupled proposal model as the source of the sound

## Milestone 4 Blow/Draw Modes

Milestone 4 adds explicit render modes:

```text
python run.py --mode draw
python run.py --mode blow
python run.py --mode both
```

The draw mode uses the existing best Milestone 3D preset. The blow mode uses
the same ODE and equations with the physically reversed mouth-pressure
direction: positive `p_m` means blowing into the mouth side, while negative
`p_m` means draw suction. The pressure drops remain:

```text
DeltaP_b = p_m - p_c
DeltaP_d = p_c - p_out
```

The blow preset is now a real sustained tone rather than the earlier DC-flow
plateau. It is stable, non-silent, and blow-reed dominant. Milestone 5B then
replaced the old bend-demo direction with audible blow/draw separation: the
blow preset now uses stronger positive mouth pressure, brighter tract loading,
and a stronger mixed pressure/net-flow radiation path derived from simulated
states. The blow reed periodically enters near closure during the sustained
part of the note.

Latest generated metrics:

- draw dominant reed estimate: `draw reed`
- draw fundamental estimate: `444.00 Hz`
- draw harmonic energy ratio: `0.784579`
- draw attack ratio: `0.001640`
- blow dominant reed estimate: `blow reed`
- blow fundamental estimate: `398.40 Hz`
- blow harmonic energy ratio: `0.449031`
- blow attack ratio: `0.000056`
- blow reed opening near closed: `49.84%`
- fundamental separation: `45.60 Hz`
- chamber loss conductance: `2.0e-11 m^3/(s Pa)`
- release time: `0.05 s`
- comparison report confirms draw and blow audio arrays are not identical

Files generated by `--mode both`:

- `outputs/draw_note.wav`
- `outputs/draw_note_trace.csv`
- `outputs/draw_note_diagnostics.png`
- `outputs/draw_note_report.md`
- `outputs/blow_note.wav`
- `outputs/blow_note_trace.csv`
- `outputs/blow_note_diagnostics.png`
- `outputs/blow_note_report.md`
- `outputs/comparison_report.md`
- `outputs/comparison_diagnostics.png`

Next tuning direction: keep the pressure sign convention fixed, listen to the
new draw/blow pair, and make only a final subjective pass through physical
parameters if the blow note is now too bright or too assertive.

## Milestone 5 Reference Calibration And Radiation

Milestone 5 adds reference-based analysis and physical calibration while keeping
the coupled ODE intact. The new analysis command reads a reference WAV only to
measure fundamental frequency, harmonic amplitudes 1-12, harmonic energy ratio,
spectral centroid, rolloff, attack time, RMS envelope, and spectral envelope.
The renderer never uses reference audio as a source.

The audio output stage now explicitly models radiation from simulated
pressure/flow states. It can select `p_c`, `p_t`, `Q_b`, `Q_d`, `Q_b - Q_d`, or
the previous physical mix, then applies a compact-source radiation
approximation: low-frequency high-pass behavior plus a controllable
differentiating component for flow radiation. A broad low-Q body/chamber
coloration can be added after that source. This is not a sawtooth/filter patch;
it has no independent oscillator and cannot create a note without the simulated
reed/flow/chamber states.

Optional flow noise remains disabled by default. When enabled, its gain follows
`(|Q_b| + |Q_d|) * sqrt(|DeltaP_b| + |DeltaP_d|)`, so the noise is tied to
simulated turbulent flow conditions rather than added as a constant bed.

New commands verified:

```text
python run.py --analyze-reference path/to/reference.wav
python run.py --mode draw --compare-reference path/to/reference.wav
python run.py --calibrate
```

Current calibration run:

- best candidate: `brighter_flow_radiation`
- baseline radiated harmonic ratio: `0.788`
- best harmonic ratio: `1.017`
- baseline centroid: `683.7 Hz`
- best centroid: `765.7 Hz`
- top candidate WAVs written under `outputs/calibration/`

The calibration search covers reed Q/damping, active reed rest opening and
opening scale, discharge coefficients, chamber volume, leakage-radiation
conductance, vocal-tract resonance/Q/coupling, output source, radiation
settings, and flow-noise amount.

## Milestone 6 Audible Radiation Controls

Milestone 6 audits and exposes the output path rather than changing the core
physical equations. The render still solves the coupled reed, Bernoulli flow,
chamber pressure, and reduced vocal-tract ODE first. Audio is then built in
`physical_output_signal()` from simulated states only.

Output path audit:

- `p_c`: used directly by `--output pressure`
- `p_t`: available as a simulated pressure component in the mixed output
- `Q_b` and `Q_d`: available in mixed output and net-flow radiation
- `Q_b - Q_d`: used by `--output flow`
- reed displacement: not mixed directly into audio

New CLI controls:

```text
python run.py --mode draw --output pressure
python run.py --mode draw --output flow
python run.py --mode draw --output mixed
python run.py --mode both --output mixed
python run.py --mode draw --noise 0.02
python run.py --mode draw --radiation on
python run.py --output-compare
```

Radiation remains a conservative post-ODE approximation: high-pass behavior for
compact acoustic radiation, optional partial differentiation for flow-derived
sources, and a broad low-Q body/cover coloration. Flow noise is subtle by
default and follows `normalized(abs(Q_b) + abs(Q_d))^noise_power`, so it is
present only when simulated flow is present. It is not fed back into reed
dynamics.

Reports now include output mode, radiation settings, noise gain, harmonic
energy ratio, spectral centroid, spectral rolloff, and attack ratio. The
`--output-compare` command writes pressure, flow, and mixed WAVs under
`outputs/output_compare/` so the audible contribution of the output layer can be
checked directly.
