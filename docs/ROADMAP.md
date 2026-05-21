# Roadmap

## Milestone 1: Stable Python Render Pipeline

Status: Done.

Expected result: stable non-silent output that may sound sine-like. It is not
expected to sound like a harmonica yet, because a single mostly linear reed
oscillator produces a sine-like tone.

## Milestone 2: Full Coupled Proposal State

Status: Done.

Implement the full proposal state vector:

```text
[x_b, v_b, x_d, v_d, p_c, p_t, v_t]
```

Use both blow and draw reeds, Bernoulli flows, chamber pressure, and
vocal-tract resonator in one coupled ODE system.

Acceptance: WAV is non-silent, stable, and diagnostics show nonlinear flow and
chamber-pressure feedback.

## Milestone 3: Self-Exciting Harmonica-Like Model

Status: Done. Milestone 3D remains the draw-note acoustic baseline.

Make the model self-exciting and harmonica-like.

Tune only physical parameters and physically plausible closures:

- reed rest openings
- effective surfaces
- discharge coefficients
- reed damping / Q
- pressure envelope
- chamber volume / pressure scaling
- opening function and reed closure
- output choice from `p_c`, `Q_b`, `Q_d`, or a weighted physical combination

Acceptance: sound is no longer a fading sine. It must show audible harmonic
content and a reed-like attack.

### Milestone 3A: Diagnostic Baseline

Status: Done.

Milestone 3A established objective checks for chamber feedback, reed
participation, reed-slot closure, harmonic energy, and stability. This gave the
project a way to distinguish physical coupling from a stable but sine-like
render.

### Milestone 3B: Stronger Reed-Slot Nonlinearity

Status: Done.

Milestone 3B tightened reed-slot modulation, added documented closure damping,
and used a physical pressure/flow radiation approximation. The sound now begins
to resemble a harmonica: it is stable, non-silent, no longer mostly sinusoidal,
and has substantially stronger harmonic content than Milestone 1 or Milestone 2.

Current default diagnostic metrics from `outputs/draw_note_report.md`:

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

Interpretation: the harmonic ratio and `mostly sinusoidal: no` result show that
the current sound is no longer the Milestone 1 sine-like tone. The draw reed
near-closed percentage shows useful reed-slot nonlinearity, and nonzero chamber
feedback confirms that the coupled model is active. The centroid is still only
`1.48x f0`, below the aspirational `2x f0` brightness target, so further tuning
should preserve stability while improving brightness and onset behavior.

Current strengths:

- stable offline render with the full coupled proposal model
- audible harmonic content from physical reed-slot and Bernoulli-flow behavior
- both reeds participate in the coupled system
- chamber and vocal-tract pressures are active simulated states
- output is derived from simulated pressure and flow, not from a fake oscillator

Current weaknesses:

- spectral centroid remains below the optional `2x f0` target
- blow reed does not reach near closure in the current draw-note preset
- after stronger nonlinear tuning, the natural breath/fade-in envelope became
  weaker than desired
- attack behavior needs to be made controllable without using a post-audio fade

### Milestone 3C: Physical Breath Envelope

Status: Done.

Restore attack behavior by introducing a physically meaningful breath pressure
envelope `p_breath(t)` as the source for mouth pressure `p_m`. The envelope
should control the pressure driving the ODE, not multiply the rendered audio
after the fact. This keeps the model unchanged while allowing attack time,
release time, sustain pressure, and optional breath noise to shape reed
excitation physically.

The intended tuning direction is to recover a smooth, audible breath attack
while preserving the Milestone 3B reed/chamber/vocal-tract coupling and harmonic
content.

### Milestone 3D: Audible Einschwingen

Status: Done.

Milestone 3D makes the physical breath attack audible and visible. The default
draw note now uses a `0.05 s` pre-delay, `0.35 s` raised-cosine attack,
`0.20 s` release, `2.5 s` duration, and `-900 Pa` signed sustain pressure. The
pressure envelope is applied to `p_m_source(t)` before the physical equations,
not as a post-render fade.

Current default diagnostic metrics from `outputs/draw_note_report.md`:

- RMS first 100 ms: `0.005430`
- RMS sustain region 0.7-1.2 s: `0.404238`
- attack ratio first/sustain: `0.013433`
- harmonic energy ratio: `0.701115`
- spectral centroid / f0: `1.47`
- mostly sinusoidal: `no`
- draw reed opening near closed: `48.58%`
- chamber pressure feedback nonzero: `yes`

Interpretation: the attack-ratio target `< 0.35` is met, the diagnostics show
the mouth-pressure envelope rising gradually, and the Milestone 3B harmonic
character is preserved.

## Milestone 4: Blow And Draw Presets

Status: Done. First stable implementation is available.

Add one draw note and one blow note. Use the sign convention cleanly.

Commands:

```text
python run.py --mode draw
python run.py --mode blow
python run.py --mode both
```

Sign convention:

- positive `p_m` means blow pressure from the mouth side
- negative `p_m` means draw suction from the mouth side
- `DeltaP_b = p_m - p_c`
- `DeltaP_d = p_c - p_out`
- the draw preset should be draw-reed dominant
- the blow preset should be blow-reed dominant

Outputs:

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

Current result:

- draw remains the best-sounding harmonica-like preset
- blow is stable, non-silent, pressure-sign-correct, and blow-reed dominant
- draw and blow outputs are not identical
- blow now has sustained reed oscillation, blow-reed near closure, and stronger
  harmonic content than the first dull preset
- both modes can still use further tone-quality and brightness tuning

## Milestone 5: Reference-Based Calibration And Radiation Layer

Status: Done. First reference-analysis and calibration implementation is
available.

Milestone 5 improves realism without replacing the physical model:

- optional reference WAV analysis for measurement only
- synthetic-vs-reference comparison reports and plots
- high-pass/differentiating radiation tendency for simulated flow/pressure
- optional low-Q body/chamber coloration
- optional low-level flow-driven turbulent noise
- bounded physical parameter calibration over reed Q/damping, openings,
  discharge coefficients, chamber volume/leakage-radiation conductance, tract
  resonance/Q/coupling, output source, radiation settings, and flow-noise amount

Commands:

```text
python run.py --analyze-reference path/to/reference.wav
python run.py --mode draw --compare-reference path/to/reference.wav
python run.py --calibrate
```

Current calibration result:

- best candidate: `brighter_flow_radiation`
- harmonic energy ratio, harmonics 2-12 vs fundamental: `1.017`
- spectral centroid: `765.7 Hz`
- top WAVs written under `outputs/calibration/`

Reference WAVs are never used as a synthesis source. The ODE state derivative
continues to implement the proposal reed, Bernoulli flow, chamber pressure, and
vocal-tract equations.

## Milestone 5B: Audible Blow/Draw Separation

Status: Done for the first tuned preset; keep one listening pass open.

The project does not pursue bends. Milestone 5B instead makes the existing blow
and draw modes audibly separated while keeping both on the same physical ODE
path.

Separation controls:

- signed breath pressure: draw suction vs blow pressure
- active high-Q reed: draw reed for draw, blow reed for blow
- mode-specific reed-slot closure regime
- vocal-tract loading parameters
- simulated pressure/flow radiation balance

Acceptance:

- `python run.py --mode both` writes draw and blow WAVs, traces, diagnostics,
  and comparison reports.
- draw is draw-reed dominant.
- blow is blow-reed dominant.
- both notes are stable, non-silent, and non-clipped.
- both notes show useful near-closure behavior in the expected active reed.
- blow harmonic ratio is no longer the first dull `~0.10` baseline and should
  stay above `0.25` in the regression test.
- the difference is documented as a physical preset difference, not as samples,
  wavetables, pitch shifting, or a separate oscillator.

Current full-render metrics from `outputs/comparison_report.md`:

- draw f0: `444.00 Hz`
- blow f0: `398.40 Hz`
- fundamental separation: `45.60 Hz`
- draw harmonic energy ratio: `0.784579`
- blow harmonic energy ratio: `0.449031`
- draw active closure: draw reed near closed `48.24%`
- blow active closure: blow reed near closed `49.84%`
- dominant reeds: draw=`draw reed`, blow=`blow reed`

## Milestone 6B: Release Cleanup And Chamber Loss

Status: Done for the first default render.

The previous default release used a `0.20 s` pressure ramp. During shutdown the
reed amplitude and chamber/tract operating point changed enough to create a
bend-like release tail. Milestone 6B fixes that in the physical model path:

- default release is now `0.05 s`
- release starts at `2.45 s` for a `2.5 s` render
- chamber pressure includes a small acoustic loss flow `Q_loss = G_c p_c`
- default `G_c = 2.0e-11 m^3/(s Pa)`
- traces and reports now include `Q_loss`

The chamber equation remains explicit:

```text
p_c' = rho c^2 / V_c * (Q_b - Q_d - Q_loss)
```

Setting `G_c = 0` recovers the original proposal chamber equation exactly.
Zero-crossing checks after the change show no meaningful release bend in the
default render: draw stays around `443.9 Hz`, and blow moves only from
`398.2 Hz` to `397.7 Hz` near the tail.

## Milestone 6: Audible Radiation / Output Stage

Status: Done. First selectable output implementation is available.

Milestone 6 keeps the proposal ODE intact and improves the audible path after
integration:

- output path audit written to `outputs/output_path_audit.md`
- selectable `--output pressure`, `--output flow`, and `--output mixed`
- explicit `--radiation on|off` control for high-pass/differentiating radiation
  tendency and broad body/cover coloration
- CLI `--noise` control for subtle flow-driven turbulent output noise
- `python run.py --output-compare` writes pressure/flow/mixed WAVs and reports
  under `outputs/output_compare/`
- render reports include output mode, radiation settings, noise gain, harmonic
  energy ratio, spectral centroid, spectral rolloff, and attack ratio

Physical boundary:

- pressure mode uses simulated chamber pressure `p_c`
- flow mode uses scaled simulated net flow `Q_b - Q_d`
- mixed mode combines simulated pressure and flow states
- reed displacement is not mixed directly into audio
- noise is injected only into the output/radiation layer and is driven by
  simulated flow magnitude
- no samples, wavetables, sawtooth/filter fake synthesis, pitch shifting, ML,
  realtime audio, GUI, or C++ are introduced

Commands:

```text
python run.py --mode draw --output pressure
python run.py --mode draw --output flow
python run.py --mode draw --output mixed
python run.py --mode both --output mixed
python run.py --mode draw --noise 0.02
python run.py --mode draw --radiation on
python run.py --output-compare
```

Acceptance: pressure, flow, and mixed renders are audibly different because the
radiation source and filters differ, while the internal physical model remains
the same.

## Milestone 7: Professor Demo Package

Create final WAVs, plots, CSV traces, and a short explanation connecting
implementation to the proposal equations.

Acceptance: the demo package can be reviewed without reading the whole codebase
and clearly explains which implemented blocks correspond to the proposal.
