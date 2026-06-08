# Millot Opening-Model Comparison

Target set: `millot_normal_blow_4b`. All achieved values come from simulated physical states with motion flow off. No listening score or audio post-processing was used for selection.

| Metric | Target | Clipped | Through-slot simple | Through-slot calibrated |
|---|---:|---:|---:|---:|
| f0 (Hz) | 401 | 384.82* | numerical FAIL | 394.48 |
| Mean pressure (Pa) | 219 | 477.88 | numerical FAIL | 215.64 |
| Equivalent acoustic amplitude (Pa) | 128 | approximately 0 | numerical FAIL | 222.21 |
| Active amplitude (micrometer) | 1493 | approximately 0 | numerical FAIL | 1623.85 |
| Passive amplitude (micrometer) | 67 | approximately 0 | numerical FAIL | 32.36 |
| Active/passive ratio | 22.28 | not meaningful at equilibrium | numerical FAIL | 50.18 |
| H2/H1 | qualitative: below 1 | approximately 0 | numerical FAIL | 0.449 |
| H3/H1 | qualitative | approximately 0 | numerical FAIL | 0.308 |
| H4/H1 | qualitative | approximately 0 | numerical FAIL | 0.024 |
| Blow open positive / negative / closed (%) | crossing expected | 100 / 0 / 0 | numerical FAIL | 15.25 / 16.15 / 68.60 |
| Draw open positive / negative / closed (%) | passive opening reed | 100 / 0 / 0 | numerical FAIL | 100 / 0 / 0 |
| Fundamental strongest | yes | not meaningful at equilibrium | numerical FAIL | yes |

\*The clipped f0 value is estimated from numerical residual motion after the model settles to static equilibrium and should not be interpreted as a sustained played frequency.

## Interpretation

The clipped model reaches a stable but nearly static pressure equilibrium, so its spectral ratios and f0 are not meaningful normal-blow validation results. The simple symmetric through-slot model is excessively stiff with the source `h00` offsets: the exact requested command did not complete after more than seven minutes with `DOP853`, `Radau` also failed to complete promptly, and `LSODA` reported repeated convergence failures.

The calibrated through-slot model is recommended only for the numerical source
comparison. It is not recommended as the audible prototype. It is the only
tested source-validation law that sustains an active upper/blow-reed
oscillation, crosses the slot plane, keeps the fundamental strongest, and
approaches the 401 Hz, 219 Pa, and 1493 micrometer targets. It still
overpredicts AC pressure, underpredicts passive-reed amplitude, overpredicts
the active/passive ratio, leaves the passive opening path active for nearly
the full steady-state window, and can sound harsh or noise-like.
