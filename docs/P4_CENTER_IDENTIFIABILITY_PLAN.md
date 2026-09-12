# P4 center identifiability: conditional separation sets and null controls

Decision date: 2026-09-08. Status at commitment: specified, not run.
Synthetic development / Level0. Commit before drawing any of the new
calibration/reference cohorts or observing the registered geometry fixtures.
This is an exploratory successor, not independent model confirmation.

## Question, structural assumption and preserved evidence

Can reference uncertainty exclude a single double-charge center in favor
of two nearby centers, without turning a reference-induced null zero into
a supported defect? Exact single-center equality cannot generally be
established with nonzero reference error. The planned result is a
conditional separation set and an abstention, not a forced binary label.

Keep the predecessor background-only synthetic calibration channel,
five-point stencil, P128 exact-cube probes, noise0.03, moment adapter and
per-repeat affine fitting. This channel is not established for real models.
All predecessor fits, local components, loops, scores and failures remain
unchanged. No retrospective component merging or tolerance adjustment.

The new inference lane explicitly assumes a degree-two complex coefficient
field and an affine background error. It fits generic real quadratic
coefficients, tests their held-out predictions, then admits a holomorphic
or antiholomorphic quadratic family only when the observed curvature has
that form. It is not an unrestricted phase/core detector. Linear, mixed
quadratic and cubic controls test unsupported-family handling.

For an admitted family, write the variable as z or conjugate(z):
f = a z^2 + L z + M conjugate(z) + c. The pure-family constraint is M=0.
Center m=-L/(2a); discriminant D=m^2-c/a; unordered root separation
s=2 sqrt(abs(D)). A translated double zero and a same-center pair differ
only by a constant term. An unknown affine reference can therefore confound
their distinction even when curvature and outer winding are stable.
These parameters describe a conditional coefficient-field model, not a
verified physical core or a model-derived order parameter.

## Reference-error envelope, fixed before evaluation

Use a new noise namespace, SeedSequence[seed,0x50344944,repeat_index],
with4,096 independent repeat indices0–4,095 and the exact(5,128,3) draw
order. Fit each repeat separately, in chunks of at most256 repeats using
the existing adapter/fitter. Save raw probes, moments and all fitted
coefficients. Average the firstK=16,256,4,096 fits; never pool F4 probes.

Envelope-calibration seeds500–531 form16 fixed pairs in order:
(500,501), (502,503), ..., (530,531). At eachK and for eachF2/F4, use
the maximum over these16 pairs of the complex coefficient difference
norm separately for the constant, x and y affine rows. Add the fixed
1e-9 numerical margin to each resulting radius. No square-root rescaling,
quantile choice, oracle baseline or geometry score selects these radii.
Seal all six K/hypothesis envelopes before generating evaluation references.

Evaluation-reference seeds600–615 are a disjoint set of16 cohorts, each
with the same4,096-repeat construction and three prefixes. Their96
references are sealed before any geometry observation. Prefixes are
nested, F2/F4 share probes, and these16 cohorts are reused across geometry.
Do not count correlated conditions as independent trials.

The envelope is an empirical Cartesian product of three complex disks,
not a confidence region with certified coverage. Pair differences cannot
bound a common calibration bias. Only after classification, measure actual
reference-error coverage against the known synthetic background. Keep every
miss; do not enlarge the envelope using these evaluation observations.

## Prospective geometry and measurement matrix

Use new geometry seeds700–703 with the existing geometry namespace and
its center/angle construction, alpha0.08 and0.10. The ordered12 fixtures:

- double: one+2 center, separation0;
- pair-004, pair-008, pair-016, pair-040: two+1 centers with respective
  separation0.04,0.08,0.16,0.40;
- reverse-008, reverse-040: two-1 centers, separation0.08,0.40;
- dipole: +1/-1 at separation0.40, mixed-quadratic control;
- constant and zero: predecessor nonzero-constant and degenerate controls;
- linear:0.025(z-center), a genuine injected+1 outside the quadratic family;
- cubic:0.025(z-center)^3, a genuine injected+3 outside the model family.

Scale each residual by alpha/0.10, retaining fixed locations/orientation
and background. Every geometry unit has fresh P128 clean observations
on the same257x257 vertices. All reference choices consume that one full
field. Add one ideal-reference control per hypothesis; zero empirical
radius plus the same numerical margin, not a selected estimated reference.

Total144 execution positions:32 envelope cohorts,16 evaluation-reference
cohorts, then96 geometry units. There are196,608 repeat sets,393,216 fits,
96 evaluation references,9,216 estimated-reference reconstructions and192
ideal controls, totaling9,408 local records. The inference and unchanged
local-loop lanes share those records; they are not additional trials.

## Fixed inference, abstention and uncertainty propagation

Use9 fit coordinates {-1,0,1} x {-1,0,1}, ordered y then x, and16 disjoint
held-out coordinates {-0.75,-0.25,0.25,0.75} squared. Fit the measured
residual with [1,x,y,x^2,xy,y^2] by unweighted least squares. Compare its
prediction at all16 held-out coordinates; error above1e-9 is unsupported.
Curvature form is also tested at the fixed1e-9 numerical tolerance, never
using truth labels, centers, charges, counts or expected separation.

For the generic quadratic curvature coefficients Qxx,Qxy,Qyy, compute
A=(Qxx-Qyy-i Qxy)/4, B=(Qxx-Qyy+i Qxy)/4, C=(Qxx+Qyy)/2. Admit A-only
or B-only curvature when the active coefficient exceeds1e-6 and both
inactive coefficients have magnitude at most1e-9. Mixed or otherwise
unsupported curvature remains out_of_family. These tolerances are fixed
development roundoff allowances, not a certified floating-point proof.

The affine coefficient radii r0,rx,ry induce rL=(rx+ry)/2 for both L and M.
If the observed inactive linear term abs(M)>rL plus the numerical margin,
report reference_envelope_mismatch; do not silently project it away.
For admitted curvature use rA=1e-9 and abs(a)>rA. Propagate conservative
outer bounds through m and D:

    rm = (rL + 2 abs(m) rA) / (2 (abs(a)-rA))
    rD = 2 abs(m) rm + rm^2
         + (r0 + abs(c/a) rA) / (abs(a)-rA)
    s_lower = 2 sqrt(max(0, abs(D)-rD))
    s_upper = 2 sqrt(abs(D)+rD)

These deliberately relax correlations between transformed coefficients.
If s_lower>0, report two_required_in_family; otherwise one_not_excluded.
The latter is an unresolved alternative, not a verified single center or
a proof that every point in the outer set is feasible. Also retain the
estimated unordered roots, center disk, root disks with radius
rm+sqrt(rD), and whether those two root disks are disjoint. Do not confuse
exclusion of a double zero with precisely located disjoint root regions.

If all curvature terms are below tolerance, keep the affine field separate:
zero_compatible only if all three residual affine coefficients lie inside
their respective error disks. A constant/affine field has no core on the
square only when the triangle lower amplitude bound
abs(c)-abs(bx)-abs(by)-(r0+rx+ry) exceeds the unchanged amplitude floor.
Otherwise report affine_unresolved, including a strong linear+1 control.
Never call an unsupported field or unavailable result a zero observation.

Seal the new readout and the unchanged charge-blind locator/loop records
before truth-side scoring. Preserve the old0.10 primary and0.01 secondary
scores, component boxes, loop stops, outer winding and missingness. The
new scorer records actual envelope coverage, center/separation coverage,
double/zero false-two decisions, pair two-required counts, abstentions,
family mismatches and old-local-versus-model discrepancies. Counts and
conditional errors retain all16 reference cohorts at each fixed condition.
No required success, monotonicity or target false-positive rate is assumed.

## Execution, verification and claim ceiling

New plan/kernel/runner/tests on PR#122, with byte bindings and no predecessor
source changes. Test on nonregistered seeds: stream/prefix independence,
moment/fit replays, pairing/envelope closure and no geometry leakage,
the constant-term confounding identity, separation-bound coverage under
bounded affine perturbations, conjugation, zero/constant/linear/cubic
controls, all missingness states and tamper/incomplete-bank rejection.

Use a new isolated Furnace checkout: NumPy CPU, one child/one BLAS thread,
nice10; no GPU/model/managed-runtime changes. Limits180seconds per unit,
2,400seconds campaign,8GiB child address space,2GiB per file and8GiB pre-unit
output-disk admission. Preserve attempts, terminal records, failures,
timeouts and unrun positions. No reuse of an output directory or unrecorded
retry; a missing calibration/reference cohort blocks downstream geometry.

Replay every calibration fit/envelope/reference from raw observations and
every inference/local record from retained full fields and exact reference
coefficients. Bind source and complete bank hashes before/after consumption.
Return compact reports and an exact-file-closure receipt; raw arrays stay
on Furnace. Publish every separation/control, coverage failure and abstention.

No D7/D8, SCI-S1/S2, Pythia-160M, phase/transition, holonomy, model winding,
verified-core, model-order-parameter or scientific-authority gate changes.
This measures an explicitly restricted synthetic identifiability test,
not the discovery rate of model-internal vortices.
