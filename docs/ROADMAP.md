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
- blow now has sustained reed oscillation and blow-reed near closure
- both modes can still use further tone-quality and brightness tuning

## Milestone 5: Vocal-Tract Sweep / Bend Demonstration

Add a vocal-tract parameter sweep / bend demonstration. Do not use fake pitch
shifting. Bending must come from changing vocal-tract resonance/loading
parameters.

Acceptance: render a short sweep where pitch and timbre change because of tract
parameters.

## Milestone 6: Professor Demo Package

Create final WAVs, plots, CSV traces, and a short explanation connecting
implementation to the proposal equations.

Acceptance: the demo package can be reviewed without reading the whole codebase
and clearly explains which implemented blocks correspond to the proposal.
