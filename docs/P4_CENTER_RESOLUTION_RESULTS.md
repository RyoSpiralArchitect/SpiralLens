# P4 expanded resolution slice and separate stress controls

The 2026-09-09 campaign completed **188/188 execution positions**, with no
failed, timed-out or rerun measurement unit. More independent reference and
geometry cohorts resolve a *conditional decision-frequency curve*, not a new
per-record instrument. At alpha 0.10 / K4096 / distance 0.16, F2 requires two
roots in 979/1,024 records and F4 in 285/1,024. Shared reference bias can both
split an injected single center and conceal a true pair. Synthetic development
/ Level 0 only; no model, scientific authority or gate promotion.

## 1. Prospective scope and what changed

The [protocol](P4_CENTER_RESOLUTION_PLAN.md), committed at `6a7ba80`, precedes
every new registered observation. Execution source is `95ea514000270056bbf1b5d412c72d889696abb4`.
The [predecessor](P4_CENTER_IDENTIFIABILITY_RESULTS.md), its 32-cohort empirical
envelope, numerical tolerances, inference, local reader, loops and position
scores retain their original bytes. The inherited envelope is copied exactly
to `protocols/p4_center_resolution_envelope_v0_1.json`; it is never enlarged
using the new observations.

New evaluation references use 64 cohorts, seeds 800–863, versus 16 previously.
Each has 4,096 background-only repeat sets at the unchanged five positions
and P128 probes: 262,144 repeat sets and 524,288 F2/F4 fits. The 384 estimated
references at K16/256/4096 seal before observing any new geometry. Geometry
seeds 900–915 supply 16 center/angle groups, versus four previously.

The primary slice observes 28 fixtures at strengths 0.08 and 0.10, with
positive-pair distances 0.080–0.160 in 0.005 increments, plus the registered
anchors, reverse pairs, single, zero and unsupported-family controls.
Inference consumes the same nine fitting and 16 disjoint held-out points as
before, measured through actual P128 probes and the dense moment adapter.
It does not use oracle coefficients. Saving only this 25-point support in
the main matrix changes the input footprint/seals, not the numerical rule.

| Lane | Units | Inference outputs | Interpretation |
| --- | ---: | ---: | --- |
| Evaluation-reference construction | 64 | 0 | 524,288 reference fits |
| Primary slice | 32 | 345,856 | 344,064 estimated + 1,792 ideal |
| Separate bias/noise stress | 28 | 25,088 | Estimated references only |
| Preselected full-grid cross-check | 64 | 1,664 | Paired duplicates, not extra independent trials |

Total: 372,608 inference outputs. Only the last 1,664 have new full-grid
local-loop readings. At a primary alpha/fixture/hypothesis/K cell, the
1,024 records are **64 reference cohorts × 16 geometry groups**, not 1,024
independent trials. K prefixes are nested; hypotheses share probes;
fixtures and strengths reuse those cohorts. Increasing this population
estimates the decision curve more precisely; it does not itself shrink an
individual separation range.

## 2. Expanded cohorts expose an empirical-envelope tail

The frozen envelope does not cover every new reference:

| Hypothesis | K | Covered cohorts /64 | Uncovered reference |
| --- | ---: | ---: | --- |
| F2 | 16 | 64 | none |
| F4 | 16 | 63 | 849: constant error / radius = 1.205545 |
| F2 | 256 | 63 | 802: x-row error / radius = 1.246603 |
| F4 | 256 | 64 | none |
| F2 | 4096 | 64 | none |
| F4 | 4096 | 64 | none |

These are retained, not excluded or used to expand a radius. All 282,624
estimated quadratic-family records still have ranges covering the injected
center and separation. This does not repair the two uncovered reference
rows or certify future coverage. There are no `reference_envelope_mismatch`
inference statuses; that observable gate is not an oracle test that every
true reference coefficient lies inside the assumed envelope.

Every one of the 12,288 estimated single-center records retains
`one_not_excluded`; none falsely requires two in this primary lane.
Zero controls are `zero_compatible` for 64/64 cohorts in four K/hypothesis
groups and 63/64 in F4/K16 and F2/K256. The latter references give
`affine_unresolved`, not discovered defects. Their 32 identical geometry/
strength replicas produce 64 such records, not 64 independent null failures.

The nonzero-constant control has 12,272 `nonzero_no_core_on_domain` and
16 `affine_unresolved` estimated records. Linear controls remain
`affine_unresolved`; all 12,288 dipole and 12,288 cubic controls remain
`out_of_family`. No unavailable interval is replaced by separation zero.
Ideal controls require two for all 1,408 injected pair records and retain
one for all 64 single-center records; their null/family controls keep the
intended alternatives. None establishes an unrestricted core detector.

## 3. Fine separation curve

Counts of `two_required_in_family` at K4096, each out of 1,024 correlated
records. Every other record in these cells is `one_not_excluded`.

| Distance | Alpha 0.08 F2 | Alpha 0.08 F4 | Alpha 0.10 F2 | Alpha 0.10 F4 |
| ---: | ---: | ---: | ---: | ---: |
| 0.080 | 1 | 0 | 2 | 0 |
| 0.085 | 2 | 0 | 3 | 0 |
| 0.090 | 2 | 0 | 6 | 0 |
| 0.095 | 3 | 0 | 10 | 0 |
| 0.100 | 5 | 0 | 17 | 1 |
| 0.105 | 10 | 0 | 32 | 1 |
| 0.110 | 11 | 0 | 62 | 2 |
| 0.115 | 24 | 1 | 106 | 6 |
| 0.120 | 43 | 1 | 173 | 12 |
| 0.125 | 73 | 3 | 252 | 18 |
| 0.130 | 127 | 7 | 364 | 26 |
| 0.135 | 178 | 13 | 495 | 43 |
| 0.140 | 253 | 18 | 639 | 64 |
| 0.145 | 356 | 26 | 765 | 104 |
| 0.150 | 467 | 38 | 856 | 155 |
| 0.155 | 596 | 54 | 930 | 217 |
| 0.160 | 719 | 90 | 979 | 285 |

K16 and K256 never require two anywhere on this fine slice, for either
strength or hypothesis. Distance 0.04 retains one in every estimated case.
At distance 0.40 / alpha 0.10, F2 counts across K16/256/4096 are
2/1,024/1,024; F4 counts are 7/940/1,024. Reverse distance 0.08 at K4096
has no positives at alpha 0.08 and one per hypothesis at alpha 0.10;
reverse distance 0.16 has 723/85 and 970/287 F2/F4 positives at the two
strengths. No sign pooling or universal resolution threshold is fitted.

The registered 2,000 two-way resamples independently resample the 64
reference and 16 geometry identities, sharing weights across every paired
curve. At alpha 0.10 / distance 0.16, the observed fractions and pointwise
5–95% resampling bands are F2 95.6% [91.4%, 98.8%] and F4 27.8%
[18.3%, 39.2%]. At distance 0.135, F2 is 48.3% [37.4%, 60.2%].
Per-reference and per-geometry fractions and statuses remain in the full
summary. These are finite-sample conditional resampling bands, not
calibrated confidence/simultaneous bands, uncertainty over the fixed
calibration, or evidence of absence below some threshold. A zero-width
band on an all-zero empirical cell is not zero population uncertainty.

Two-required decisions are not disjoint root regions. At distance 0.16,
the disjoint-root-disk counts are 388/10 for F2/F4 at alpha 0.08, and
858/75 at alpha 0.10, versus 719/90 and 979/285 two-required decisions.
Global conditional roots are not automatically localized, admitted cores.

## 4. Where the separation bound comes from

For the injected single center at alpha 0.10 / K4096, median shares of
the registered discriminant bound are:

| Hypothesis | Constant term | Center/linear term | Numerical-term median fraction |
| --- | ---: | ---: | ---: |
| F2 | 60.2041% | 39.7959% | 2.780592e-7 |
| F4 | 59.6621% | 40.3379% | 1.754005e-7 |

The three terms reproduce each original bound without tightening its
feasible set. These are contributions to an outer model-bound calculation,
not independent physical noise components or a causal variance partition.
Constant uncertainty matters, but the roughly 40% center/linear term is not
negligible. More spatial samples alone do not remove either reference term.

Median single-center upper separation bounds at alpha 0.10 shrink from
0.636460 to 0.150813 for F2 and 0.741247 to 0.190381 for F4 between
K16 and K4096. Median center radii shrink from 0.087899 to 0.005148
and 0.110868 to 0.008269. These are within-campaign K contrasts, not
improvements caused by increasing the number of evaluation cohorts.

## 5. Separate stress: improved counts can be misleading

The stress lane uses only alpha 0.10, K4096, geometry 900–903, all 64
reference cohorts, and seven fixtures. Each reported cell has 256 correlated
records. Its nominal comparator is the *same four-geometry subset*, not
the 1,024-record primary aggregate. A common deterministic coefficient
bias is not a new calibration draw or an observed biased raw-channel fit.

Constant bias is added in the registered direction, at multiples of the
fixed constant radius. Counts below are each /256:

| Bias / radius | Single falsely requires two F2 | F4 | True distance 0.16 requires two F2 | F4 | Zero-compatible F2 | F4 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 243 | 37 | 256 | 256 |
| 0.5 | 0 | 0 | 164 | 3 | 244 | 240 |
| 1 | 3 | 1 | 49 | 0 | 124 | 112 |
| 2 | 196 | 204 | 14 | 6 | 0 | 0 |

At bias 2, every transformed reference lies outside the assumed envelope;
single-center separation coverage fails in those same 196/204 false-two
records. Center coverage remains 256/256, so an accurate midpoint does
not validate the inferred split. Distance-0.16 separation coverage also
fails in 51/256 F2 cases. Non-zero-compatible zero controls are
`affine_unresolved`, not nonzero structure discoveries. Their deterministic
four-geometry repetition must not enlarge the 64-reference denominator.

The registered linear bias produces no single false-two decision, yet
single-center disks miss the injected center in 132/256 F2 and 100/256 F4
records. Distance-0.16 two-required counts *increase* to 253/169 from
243/37, while the same 132/100 center misses persist. Higher apparent
pair sensitivity is therefore not sufficient evidence of a better instrument.

Probe noise is added before the moment adapter, with the same standard-
normal draw reused across the three noise scales, hypotheses and fixtures within each
of the four geometry groups. At sigma 1e-9 all 3,584 statuses match their
nominal counterparts, although measured values change. At sigma 1e-7
and 1e-4, all 3,584 records per mode are `out_of_family`, including nulls,
and have unavailable separation bounds. The original held-out/numerical
gate was not retuned. This diagnoses the clean-evaluation assumption;
it does not measure physical disappearance or an exact noise threshold.
Stress cases are not pooled into the primary curve or its resampling bands.

## 6. Full-grid local readings remain distinct

The prospectively selected 1,664 full-grid records exactly match their
primary support-point numerical rows, while retaining distinct full-input
inference seals. Their component/loop readings and original 0.10 / secondary
0.01 position scores are independently retained. No truth-based merging or
rescoring is used to make the local reader agree with the polynomial lane.

At alpha 0.10 / K4096 in this four-reference × four-geometry subset, both
hypotheses resolve two local components in all 16 injected-single records,
even though the conditional inference retains the single-center alternative
in all 16. For distance 0.08, the unchanged primary local score passes
16/16 F2 and 15/16 F4, but the stricter score passes only 3/16 and 6/16.
One F4 pair retains its overlapping-loop stop. At distance 0.16, primary
scores pass 16/16 for both, while strict scores pass 12/16 F2 and 9/16 F4.
A two-required decision is not a replacement for position fidelity.

For the four independent null references at K4096, the old local reader
still reports a charged component in 0/4 F2 and 1/4 F4. Both hypotheses
have three nonzero outer-loop readings out of four. All 26 estimated/ideal
reference-key null records are identical across eight full-grid geometry/
strength replicas. Those replicas are not new null trials. Ideal nulls
remain below floor with undefined winding. Nothing in the new inference
relabels the legacy loops or repairs earlier results.

## Interpretation and next bounded question

The useful advance is a finer curve and concrete failure modes, not a
higher universal discovery rate. The changed proportions relative to the
smaller predecessor sample are not a matched instrument improvement.
The larger sample also falsifies a naive reading of the earlier 16/16
reference coverage: the empirical envelope has observable uncovered tails.

Before increasing K again or moving to a model, the next useful design is
a separately registered bias-aware calibration check and a noisy-evaluation
error model. It should distinguish random reference scatter from shared
constant/linear bias, preserve zero and known-single alternatives, and
measure both separation and center coverage. Freeze any revised bounds
and calibration-placement comparison before new cohorts; retain this panel
as historical evaluation rather than fitting away its failures. The roughly
60/40 bound decomposition argues for measuring both reference contributions.
No successor rule or model experiment has been run here.

The separately measurable background-only channel remains a synthetic
assumption. Conditional polynomial roots are not verified in-domain cores,
model order parameters, phase/transition/holonomy evidence, sampled model
winding or a validated digital twin. D7/D8, SCI-S1/S2 and Pythia-160M gates
retain their status; scientific authority remains false.

## Execution and evidence

Isolated Furnace checkout:
`/home/ryospiralarchitect/scratch/spirallens-center-resolution-20260909-mWF7zQ/checkout`.
Sibling `campaign/` retains all raw arrays: actual reference probes, moments,
repeat fits, compact support probes/fields, exact coefficients and the
preselected full grids. The run used NumPy CPU, one child/one BLAS thread,
nice10, with no GPU/model access, managed-runtime changes or interference
with other workloads. Elapsed campaign time: 732.546728 seconds; peak child
RSS: 293,371,904 bytes; compressed arrays: 3,993,550,385 bytes. No registered
resource limit was reached.

All 62 new tests and predecessor suites pass 332 on Mac and 332 on Furnace.
The execution source's three clean-wheel jobs pass on Python 3.11.16,
3.12.14 and 3.13.15 / Ubuntu 24.04. Later result commits have separate CI.
All 81 existing P4 CI file bindings remain unchanged; this result adds its own.

Post-run verification checks 214 source bindings and 376 output hashes,
replaying all 524,288 reference fits, 345,856 primary, 25,088 stress and
1,664 paired full-grid outputs. Local evidence is under
`artifacts/p4-center-resolution-20260909/`. The 94,951,895-byte compact
archive has exactly 947 files, including all 188 report/attempt/terminal/
log sets and the summarizer. Exact closure, every returned byte, bank and
launch joins, and byte-exact regeneration of summary and visual data are
verified on Mac. The approximately 3.99GB raw arrays stay on Furnace;
there is no claim of Mac raw-array replay.

The interactive view shows both strengths and hypotheses simultaneously,
all three K curves, all 204 fine-slice aggregate points with their paired
resampling bands, and a separate fixed-cohort constant-bias contrast. It
exposes the uncovered-reference counts without deleting those cohorts.
All 228 marks, 12 bands, six plots, legend visibility, exact-cursor
cross-series hover, labeled interpolation, pinned details and text/mark
bounds pass at 736/360/320px in light/dark themes. Display rounding does
not change the full-precision returned records or projections.
Coarse-pointer legend targets and touch-pinned details also pass. The
visual deliberately keeps the primary resolution curves and bias contrasts
in separate plots; no combined discovery or specificity score is reported.
The final fragment is `center-resolution-v2.html`; final visual/touch and
document-audit helpers/receipts use the `-v2` suffix. This display-only
revision caps narrow-view x tick labels at four. The initial fragment and
its receipts remain unchanged; every measurement and projected value is
identical between the two display versions.

| Binding | SHA-256 |
| --- | --- |
| Protocol | `ac6975ab41369d316797a29c49769f5c1cbf051d4c0f706dd2acb49d7a6e7309` |
| Launch plan | `3985043815fd7de3c634bcddbc840e1c6776a0b1c490e11207e400a17e85376a` |
| Inherited envelope | `fc42c19e7d561eee00ce14abf4652d24a4b440e3aba1046d1bc82762a37a403b` |
| Reference bank | `d5a648cf656c4bed3cb07c40c97ee065f68976ef188e3a3518e36bf579656620` |
| Manifest | `5042ba733739a2f836ec7b0df0e14bf0f4f2c3e7be03f83856159e5520e1dd21` |
| Furnace raw verification | `9082492007bc356e8dbd8ef40fdc33fdcf04af2e04d37c27abc16372758ffa68` |
| Summary | `c047314145167461c4897c8d3b6da141baacfd2a20e92ef949b20e81625379bf` |
| Visual data | `759cda43b4ab8726c37164b184fb2585216fc99970c48a88125c6b52e6b81b07` |
| Compact archive | `37decf841fe68b4ceeaffc3f8d99a65a40a7e1f7c54e60e4df93ea4bce0917fe` |
| Local returned-evidence verification | `b0bb9f838643661bb9036e94867361f26d89debe709c492aa011feb6cd0b26d1` |
| Compact summary helper | `874143f4a8198f4385690ea47e1a7cb471d74960ae589f309e416b5eafe84f70` |
| Compact return verifier | `7033081980209ae5c63d543e1442895c186f8c0dbe8212d8fea8c73460952917` |
| Exact-closure archive helper | `14ade0932ee4c0f1dd96d7417227778390cba5055a70108dd359221d6c6fdcb9` |
| All-record audit helper | `c2d192f4cbcae138ae6b073f0b4eec1a8ea6be57ae00fd0804c475a9218abb31` |
| All-record audit | `5c91b2046c684c4e831d4efe21dba9a0e592880c0ccf2d18f8f238c624aaad3d` |
| Result-table/closure/CI audit helper | `8e3d97cc1ea597ca7622372e820dae2ae2a67ccf01a21a3f6467feb05b84402c` |
| Visual projection helper | `73a18a654bed9c89aa73dc50e045c68fef6cd6c145f13890b105d608b4b1c534` |
| Interactive resolution view | `4123bfc899dd62cc518bf13d66dbe2f0f28133ddeeb234182e6eda322f3e1478` |
| Six-layout visual validation | `8b04698722da133179ec5ecb936c4eb86a83e27cf20a087afef140e0aeff17a3` |
| Visual-check helper | `dac67ddf65a7b1e382ea764e5c8dffad2a1744b23ea1b97741eaf59a58d0f0a8` |
| Touch validation | `2f2bfd16602ad40744a84a3d8b6666a16a9b2226c34919e97d4ff8bf08fe5ee2` |
| Touch-check helper | `422cce1e60a1e35c6f77cf52abe034aa375fab17abee47a93bf8797ec05e1210` |
