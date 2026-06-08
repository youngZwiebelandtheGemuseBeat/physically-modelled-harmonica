# Source-Derived Parameters and Calibration Targets

The code uses three provenance categories:

- `SOURCE_DERIVED`: directly transcribed from a cited source.
- `PHYSICALLY_ESTIMATED`: SI conversions, standard constants, or values computed from source quantities.
- `MODEL_ASSUMPTION`: reduced-model values that are not supplied by the cited sources.

## Millot preset

`millot_channel4_4b` maps Millot upper 4b to the blow reed and lower 4b to the draw reed for normal blow.

| Reed | fr | K | Q | M | R | h00 |
|---|---:|---:|---:|---:|---:|---:|
| Upper / blow | 405 Hz | 77.5 N/m | 177 | 11.98 mg | 172 micro N s/m | -1298.0 micrometer |
| Lower / draw | 455 Hz | 49.6 N/m | 95 | 6.07 mg | 183 micro N s/m | +286.5 micrometer |

The named target set `millot_normal_blow_4b` contains 401 Hz, H1 = 1493 micrometer, H2 = 67 micrometer, ratio 22.28, mean openings -1171 and +320 micrometer, mean chamber over-pressure 219 Pa, and equivalent acoustic pressure amplitude 128 Pa.

## Source roles

Millot supplies the equivalent oscillators and normal-blow comparison data. Bahnson supplies mounting, closing/opening direction, active/passive plausibility, reed primacy, and vocal-tract motivation. Bilbao supplies direct numerical physical-modelling methodology, not harmonica-specific constants.

## Assumptions

Chamber volume, effective pressure-force coefficients, slot widths, discharge coefficients, breath pressure and envelope, tract frequency/Q/impedance/feedback, motion-flow area, and through-slot thresholds/gains/leakage/smoothing remain assumptions. The target-informed assumptions were selected by numerical comparison with published metrics, not by listening.

## Through-slot result

The clipped law is stable but one-sided. The simple through-slot law reopens on both sides but can remain open nearly all the time and distort harmonic balance. The calibrated law adds side-specific thresholds and gains, leakage, and compact smoothing. It improves source comparison in some metrics but still overpredicts pressure modulation and underpredicts passive-reed motion in the current reduced force/flow closure.

No seminar-paper source file exists in this branch, so the repository documentation is the maintained source-mapping record.
