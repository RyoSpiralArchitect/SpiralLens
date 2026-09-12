# P4 conditional center separation and held-out null controls

The registered campaign completed on2026-09-08: **144/144 execution
positions**, no failed, timed-out or rerun measurement units. Conditional
separation becomes informative at larger averaging counts, while nearby
pairs remain difficult. At alpha0.10/K4096, separation0.16 requires two
roots in59/64 F2 and20/64 F4 records; separation0.04 never does. Every
injected single center retains the one-center alternative, and every
zero control remains compatible with zero. Synthetic development / Level0,
no model access; these are conditional distinctions, not verified cores.

## 1. What this instrument can distinguish

The [protocol](P4_CENTER_IDENTIFIABILITY_PLAN.md), committed at`07b7d91`,
precedes every new calibration, reference and geometry observation. It keeps
the predecessor's separately observable background-only synthetic channel.
That channel is not established in real models. It does not revise the
earlier full-response-fit experiment or merge any of its components.

The new lane is explicitly a restricted quadratic coefficient-field model,
with affine reference error. Nine observations fit a generic real quadratic;
16 disjoint held-out coordinates test its predictions. Curvature selects
holomorphic, antiholomorphic or unsupported families using fixed numerical
tolerances. Neither truth labels nor expected centers/counts/charges enter
inference. Truth scores follow the sealed inference and unchanged local
component/loop readings.

For an admitted family, a translated double zero and a same-center pair
differ only in the constant term. Thus a finer grid alone cannot remove
the ambiguity caused by an uncertain reference. The registered propagation
produces an outer range for center separation. A positive lower endpoint
requires two distinct roots *within this family and error envelope*; an
endpoint of0 means one is not excluded, not that one center is verified.

The outer range relaxes coefficient correlations: it is not a guarantee
that every point inside it is feasible. Root-disk disjointness is a separate
measurement. These are roots of a conditional global polynomial model,
not automatic admission of two localized cores inside the observed square.
The1e-9 numerical allowance is not a certified floating-point error bound.

## 2. Prospective reference envelopes and denominators

Each of32 calibration cohorts, seeds500–531, has4,096 independent noisy
background repeat sets at the five-point P128 stencil. Average per-repeat
fits at K16,256,4,096; never pool F4 probes. At each K/F2/F4, the maximum
complex row difference over16 predeclared cohort pairs plus1e-9 defines
three affine error radii. All six envelopes seal before generating the
16 evaluation-reference cohorts, seeds600–615. Their96 references seal
before any geometry observation.

The empirical envelope is a product of three complex disks, not a calibrated
confidence region. Pair differences cannot bound a shared calibration bias.
Actual errors against the known background are scored only afterward; an
uncovered evaluation reference does not enlarge the envelope.

All16 evaluation cohorts lie inside each of the six frozen envelopes.
The radii below use the fixed affine coefficient basis, not spatial units:

| Hypothesis | K | Constant radius | x radius | y radius | Covered cohorts |
| --- | ---: | ---: | ---: | ---: | ---: |
| F2 | 16 | 0.001210889 | 0.004078986 | 0.004710900 | 16/16 |
| F4 | 16 | 0.001486753 | 0.005654248 | 0.005432598 | 16/16 |
| F2 | 256 | 0.000277305 | 0.000744811 | 0.001208943 | 16/16 |
| F4 | 256 | 0.000445960 | 0.001732024 | 0.001596871 | 16/16 |
| F2 | 4096 | 0.000071872 | 0.000274785 | 0.000240017 | 16/16 |
| F4 | 4096 | 0.000113638 | 0.000360370 | 0.000466575 | 16/16 |

This complete held-out coverage is an observed property of these cohorts,
not certification of future coverage or a test of common-mode bias.

Four geometry seeds700–703, strengths0.08/0.10 and12 ordered fixtures give
96 geometry units. Each full measured field is shared by96 estimated
references and two ideal controls. Totals:144 execution positions,
196,608 repeat sets,393,216 F2/F4 fits,9,216 estimated reconstructions and
192 ideal controls, or9,408 local records. Inference and legacy-loop lanes
share those records; they are not extra trials.

K prefixes are nested, F2/F4 share probes, and the same16 reference cohorts
are reused across geometry/strength. The64-record summaries below combine
four geometries and16 references, not64 independent trials. Identical
zero-field replicas do not enlarge their16-cohort denominator.

## 3. Conditional separation results

Counts of`two_required_in_family`, each out of64 correlated records:

| Alpha | Hypothesis | K | Distance0.04 | Distance0.08 | Distance0.16 | Distance0.40 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 0.08 | F2 | 16 | 0 | 0 | 0 | 0 |
| 0.08 | F2 | 256 | 0 | 0 | 0 | 64 |
| 0.08 | F2 | 4096 | 0 | 1 | 44 | 64 |
| 0.08 | F4 | 16 | 0 | 0 | 0 | 0 |
| 0.08 | F4 | 256 | 0 | 0 | 0 | 45 |
| 0.08 | F4 | 4096 | 0 | 0 | 7 | 64 |
| 0.10 | F2 | 16 | 0 | 0 | 0 | 1 |
| 0.10 | F2 | 256 | 0 | 0 | 0 | 64 |
| 0.10 | F2 | 4096 | 0 | 1 | 59 | 64 |
| 0.10 | F4 | 16 | 0 | 0 | 0 | 2 |
| 0.10 | F4 | 256 | 0 | 0 | 0 | 61 |
| 0.10 | F4 | 4096 | 0 | 0 | 20 | 64 |

Every remaining entry is`one_not_excluded`, not an omitted/failed run.
The768 estimated-reference single+2 records all retain that alternative;
none falsely requires two. All5,376 quadratic-family estimated-reference
records have an interval, contain the injected separation and cover the
injected center with their center disk. No reference-envelope mismatch
occurs. The other3,840 estimated records have separate nonquadratic/null
statuses, not zero-width separation intervals.

The lone distance0.08 positive is geometry701/reference608/K4096/F2 at
both strengths: ranges[0.033393,0.182306] at0.08 and[0.046773,0.166891]
at0.10. This is the same shared-reference/geometry condition, not two
independent confirmations or a broad robust-resolution regime. The
reverse distance0.08 controls never exclude one. For reverse distance0.40,
F2 counts across K16/256/4096 are0/64/64 at alpha0.08 and1/64/64 at0.10;
F4 counts are0/45/64 and0/58/64, respectively. Positive and reverse cases
are not silently pooled or required to match under the same noisy reference.

At distance0.16/K4096, disjoint root disks occur in32/64 F2 and1/64 F4
records at alpha0.08, versus44/64 and7/64 two-required decisions. At
alpha0.10 they occur in52/64 and8/64, versus59/64 and20/64 decisions.
Excluding a double zero is therefore not the same as localizing two
nonoverlapping root regions. Distance0.40/K4096 has64/64 disjoint disks
for both signs, hypotheses and strengths.

For an injected single+2 center at alpha0.10, all64 lower endpoints remain0.
Median upper separation bounds shrink from0.619704 to0.147539 forF2 and
0.723885 to0.185426 forF4 between K16 and4096. Median center-disk radii
shrink0.087899 ->0.005148 and0.110868 ->0.008269. A tightly bounded center
can still allow appreciable separation. The measured uncertainty does not
justify converting the one-center alternative into an exact single-center
claim.

Ideal-reference controls require two for all96 injected same-sign pairs
across the six pair fixtures, and retain one for all16 double-zero controls.
That is a restricted-family control, not evidence that the noisy instrument
can distinguish every such pair or that local loop extraction succeeds.

## 4. Null and unsupported-family controls

Each frozen envelope classifies16/16 independent zero-injection reference
cohorts as`zero_compatible`. This is an uncertainty-aware abstention from
asserting a defect, not a proof that an unknown field is exactly zero.
The original local reader still reports the following charged components
relative to the injected null:

| K | F2 cohorts with a resolved charged component, /16 | F4 cohorts, /16 |
| ---: | ---: | ---: |
| 16 | 9 | 15 |
| 256 | 12 | 7 |
| 4096 | 0 | 4 |

All98 estimated/ideal reference-key readouts are byte-identical across
the eight zero geometry/strength replicas; they do not add independent
trials. At K4096 F2, the absence of resolved components is not a general
null guarantee:11/16 outer loops still read+1 or-1, and one is undefined.
Their local candidate stops include the unchanged amplitude floor and an
overlap case. The ideal zero field remains below floor, with undefined
winding. The new lane does not relabel those legacy loops as zero.

All768 estimated nonzero-constant records meet the conditional global
affine amplitude lower bound and report`nonzero_no_core_on_domain`.
All768 linear+1 records report`affine_unresolved`. All768 mixed-quadratic
dipoles and768 cubic+3 records are`out_of_family`: the former has
unsupported curvature, the latter fails held-out quadratic prediction.
Their ideal controls retain the same statuses. These injected nonzero
structures are not interchangeable with a zero field, and rejection by
this restricted model is not evidence of their absence.

## 5. Separation is not legacy local-structure recovery

The charge-blind locator, component boxes, overlapping-loop stops, outer
winding and both original0.10 and secondary0.01 position-match scores are
retained without alteration. A conditional polynomial decision cannot
retroactively repair an unavailable component or a failed legacy score.

At alpha0.10/K4096, the single+2 legacy results are59 two-component,
one single-component and four unavailable records forF2; forF4,62 have
two components and two are unavailable. The overlap stops remain recorded;
no components were merged to match the injected single-center label.

At distance0.04, ideal geometry702 has overlapping component loops and
zero resolved components for both hypotheses at both strengths: the
legacy score is12/16 even though the polynomial lane requires two in16/16.
Conversely, geometry701/alpha0.10/distance0.40 with references608 and611
at K16/F4 requires two, but fails the original0.10 position match. Its
legacy measured spans are0.586848/0.598511 against the injected0.40.
These are two of the estimated-reference two-required records; all are
retained as failed position matches, not repaired by the new inference.

## Interpretation and next bounded question

The useful advance is a conditional resolution boundary with a null
alternative, not a universal binary classifier. In this construction,
reference averaging moves distance0.16 from complete ambiguity toward
partial separation, while0.04/0.08 remain mostly ambiguous. That boundary
is not a fitted universal threshold, a detection probability estimate,
or evidence that unseparated structures do not exist.

The next bounded experiment should keep this panel fixed and prospectively
slice distance0.08–0.16 with new reference/geometry cohorts. Decompose
constant-term and center/linear-reference contributions to the discriminant
error before choosing whether to collect more repeats or change calibration
placement. In a separate stress lane, test common reference bias and noisy
evaluation observations: neither is covered by the present clean-evaluation,
paired-difference calibration. Freeze any revised error model before its
new evaluation; do not tune it to make this panel's ambiguous cases pass.

No D7/D8, SCI-S1/S2 or Pythia-160M gate changes. This is not model-derived
phase, transition, holonomy, winding, order parameter, verified core,
scientific authority or a validated digital twin of model dynamics.

## Execution, verification and artifacts

Execution source:`fc9123fec91a82b5eee5c2da422d94f98277bf8d`.
Isolated Furnace checkout:
`/home/ryospiralarchitect/scratch/spirallens-center-identifiability-20260908-apkjwi/checkout`.
The sibling`campaign/` retains raw background probes, moments, per-repeat
fits, shared full fields and exact reference coefficients. NumPy CPU,
one child/one BLAS thread, nice10; no GPU/model access, managed-runtime
changes or interference with other jobs.

The run took1,120.114530 seconds; peak child RSS294,944,768 bytes;
compressed arrays3,140,479,659 bytes. Environment: Python3.14.4,
NumPy2.5.2, Linux7.0.0-29. All planned resource limits remain unchanged.

The45 new tests and predecessor suites pass270 on Mac and270 on Furnace.
All three clean-wheel jobs for execution source`fc9123f` pass on Python
3.11.16,3.12.14,3.13.15 / Ubuntu24.04. Later result-document revisions have
their own checks. The71 predecessor bindings and four new implementation
bindings remain unchanged.

Independent post-run verification checks211 source bindings and288 output
hashes, replays all393,216 fits from raw observations and all9,408 local
inference/legacy records from saved fields and exact reference coefficients.
The empirical envelopes and full reference bank are replayed and checked
before/after consumption. No missing unit or score is omitted.

Local evidence:`artifacts/p4-center-identifiability-20260908/campaign/`.
The12,730,594-byte compact archive contains exactly728 files, including
all144 report/attempt/terminal/log sets, both sealed banks and the summarizer.
Local verification checks every returned byte, manifest/attempt/terminal
joins and byte-exact regeneration of both summary and visual-data projections.
The3.14GB raw arrays remain on Furnace; no claim of Mac raw-array replay.

The interactive view displays both hypotheses, all three K values, all96
fixture/strength/geometry contexts and every cohort's available interval
or explicit alternative status. Actual marks, interval counts, legend
visibility, exact-cursor cross-series hover, labeled display interpolation,
pinned/nearest-interval details and text/mark clipping pass at736/360/320px
in light/dark themes. Display numbers use eight significant digits; raw
records and compact projections retain full precision. The initial visual
receipt remains separate from the final wording/320px-expanded check.

| Binding | SHA-256 |
| --- | --- |
| Protocol | `ad65b0facdcf453dbd6e62a57b78e8e0da82bd81204a47eb04e050de8c791072` |
| Launch plan | `0b8cdae8721fce53e40f4cb805b4cba15ed6fa0a322b9a01e58ede7ec33a87a4` |
| Envelope bank | `fc42c19e7d561eee00ce14abf4652d24a4b440e3aba1046d1bc82762a37a403b` |
| Reference bank | `fdcfaada01eca604ca4248e084412483c5a282583a5c8d025a178ac858e67f4b` |
| Manifest | `958ebd592e5dd48166aefb1808b05dacc21bfb6780a3814e85ab0c998e09400b` |
| Summary | `91772b5fff56afc92883db87ba0f74ba5546c639ff5dea1c8c58e5641b08776c` |
| Visual data | `78ecfbc2186de769cfeafc69f5fa4a04aedf3f6ff2582d57a68866f7317409a1` |
| Furnace verification | `aeaa138a9ddc0cbd7054355de01530ba14d7d3c39187fb2fa7ca1678bf5435f4` |
| Returned archive | `18a678a3e28915186be69536c029d672385ae2083505c6dccac49375545686b4` |
| Local returned-evidence verification | `00bd07a1d451e2298632b326734af613a0eede71865480581df9159cc4df4228` |
| Compact-summary helper | `094caef1377cd87f29aef27eddb8bdfa0db90e43c2c831c79ee2b2da7b347e2a` |
| Compact-return verifier | `349a593b1f9d7bcfb78aa5c476b7221db4608d13369f2337a30f12c5c71bb6ca` |
| Complete-panel audit helper | `c525ea6eb585a6a674ad54b921de8a299303d39c3514f914e0c7be77f2a3b016` |
| Interactive separation view | `54219f5fffb1d4f2e3ee356143bd25e16ee5af40d6905934dc37d685a1857294` |
| Final visual checks,v2 | `c19296235aa8c04ab6a48840334dc9d7f599ffb72bb62394f22d61e04a7bb985` |
| Visual-check helper | `a3b3b571aaac7b175db58f0d3714972f92fc2a752f94641f5709e8e27f665030` |
