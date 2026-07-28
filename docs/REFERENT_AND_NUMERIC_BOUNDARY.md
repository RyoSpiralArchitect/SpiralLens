# Pointwise Referents and Numeric Payload Boundary

- **Status:** provisional library contract
- **Referent schema:** `spirallens.referent-contract-set.v0.1`
- **Value-lineage schema:** `spirallens.value-access-lineage.v0.1`
- **Scientific status:** model-free construct and implementation checks only
- **Non-claim:** no D0-D8 gate, model-side referent, core, winding, topology,
  semantic content, or subject access is established here

This boundary supplies one prerequisite for the positive half of the
order-parameter-first frame. It says exactly what pointwise or fiber object
each F0-F4 hypothesis would observe, and it makes the same-object
amplitude/direction rule executable. It does **not** yet turn that formula into
a field or order parameter: the substrate, ordered domain, interpolation, and
cross-vertex comparison law remain separate bindings. It also introduces the
first independently authorized consumer that may decode values from a closed
instrument bundle.

The two capabilities remain distinct:

1. a referent contract defines the pointwise mathematical object and its
   transformation law, while explicitly recording that no substrate field or
   interpolation is bound; and
2. a numeric payload session can establish that decoded bytes are the exact
   authorized, content-addressed bytes and that declared value relations hold
   when the corresponding decode and relation validations succeed.

Neither capability says that the object exists in a transformer model.

## 1. Canonical F0-F4 pointwise referents

The canonical contract factory is
`canonical_f0_f4_referent_contracts(registry_digest)`. For the tracked P0
hypothesis registry, the resulting contract-set digest is:

```text
4108ccda4f2a76920091bf2bf422b97297fe4d91ee54f14e2b03362e53e358f2
```

The digest is pinned by a compatibility test. Any formula, transformation
law, qualifier, forbidden label, ordering, or registry binding change produces
a different identity and requires an explicit schema/change-record decision.

| Hypothesis | Pointwise referent | Amplitude and direction | Maximum ceiling |
| --- | --- | --- | --- |
| F0 | declared local-covariance support diagnostic | no order parameter; no direction | Level 1G |
| F1 | rank-two projector \(P=UU^\top\), later with an edge connection | no order parameter; a frame is coordinates, not phase | Level 2G |
| F2 | local covariant vector section \(z=U^\top s\) | both come from \(z\) | conditional Level 2T |
| F3 | global-plane projection \(z=B^\top s\) | both come from \(z\), but remain projection-dependent | Level 1D |
| F4 | in-plane traceless symmetric tensor and its spin-two vector | both come from the same traceless tensor | conditional Level 2T |

A ceiling is only a maximum permitted claim type. This PR emits no claim at
those ceilings and does not advance any D gate.

### 1.1 F0 is not \(\psi\)

F0 contains scalar support diagnostics such as effective rank, eigenspectrum,
gap, density, or coherence. These quantities may determine whether another
field is identifiable. They do not provide a normalized direction, singular
phase, winding, or charge.

### 1.2 F1 is geometry, not \(\psi\)

F1 observes the projector

\[
P_i = U_iU_i^\top .
\]

Under an ambient orthogonal transformation \(Q\),

\[
P_i' = QP_iQ^\top .
\]

Under a local frame change \(U_i'=U_iG_i\), \(G_i\in O(2)\), the projector is
unchanged. A later connection or matrix holonomy may establish continuous
geometry. It cannot be rounded or relabelled as an integer charge.

### 1.3 F2 same-object vector formula

At one row, F2 defines

\[
z_i=U_i^\top s_i,\qquad
a_i=\lVert z_i\rVert_2,\qquad
n_i=z_i/a_i.
\]

The fitted frame \(U_i\) and evaluation response \(s_i\) must be bound to the
declared disjoint fit/evaluation partition and its exact ordered row identity.
The amplitude is recomputed from the same `z`; an independently supplied
amplitude or angle cannot be joined later.

When \(a_i\) is at or below the predeclared floor, `n_i` is undefined. The
library emits a false direction-support mask rather than a zero direction.

For \(U_i'=U_iG_i\), \(G_i\in O(2)\),

\[
z_i'=G_i^\top z_i,\qquad a_i'=a_i .
\]

Reflections remain part of \(O(2)\). An oriented integer path requires a later
reviewed SO(2) reduction or orientation contract; it cannot silently discard
the determinant.

This pointwise formula is not yet an `OrderParameterField`. Raw directions at
different rows cannot be compared until a substrate, interpolation, and
connection or globally frozen frame are bound.

### 1.4 F3 projection-dependent pointwise baseline

F3 uses a fixed or fit-split global plane:

\[
z_i=B^\top s_i,\qquad a_i=\lVert z_i\rVert_2.
\]

It obeys the same-object rule, but its direction and any sampled winding are
relative to the selected global plane. Its claim must remain a
projection-dependent baseline and cannot be promoted to Level 2T.

If the plane is learned rather than fixed independently, its derivation is
bound to the same exact fit/evaluation partition and ordered row identity.

### 1.5 F4 spin-two pointwise formula

For an in-plane symmetric tensor \(A_i\), define

\[
T_i=A_i-\frac{\operatorname{tr}(A_i)}{2}I,\qquad
w_i=\left(\frac{T_{00}-T_{11}}{2},T_{01}\right),
\qquad
\rho_i=\lVert w_i\rVert_2=\frac{\lVert T_i\rVert_F}{\sqrt2}.
\]

The direction is `w / rho` only above the declared floor. For an in-plane
rotation \(G=R(\alpha)\),

\[
T_i'=G^\top T_iG
\]

and the two-component section transforms with doubled angle. Reflections are
tested through the full \(O(2)\) action. A future F4 integer therefore uses the
frozen doubled-angle convention; it is never reported as an ordinary F2
vector winding.

As with F2, this formula does not define cross-row phase or a field until the
missing substrate and interpolation bindings exist.

## 2. Fit/evaluation partition

`validate_observation_partition` verifies identities from their actual
integer arrays. It requires:

- unique fit and evaluation observation identities;
- disjoint fit and evaluation identities;
- the same ordered row domain, with the same multiplicity, on both sides; and
- finite, fixed-layout input arrays.

A pair of self-attested digest strings is not accepted as proof of
disjointness. The resulting receipt contains content-derived identities for
the two partitions and their shared row domain.

This in-memory fingerprint receipt proves the declared identity split and
binds it to each split-dependent numeric derivation. It is not a persistence
schema and cannot, by itself, prove that arbitrary upstream frame- or
plane-fitting code honored the read boundary; later estimator execution and
provenance receipts must establish that fact.

## 3. Authorized value decoding

The public closed-bundle loader remains metadata/integrity-only.
`load_instrument_bundle()` retains no payload descriptor and returns no
payload bytes or decoded array. Relative member paths remain visible in the
loaded manifest; path secrecy is not the boundary. Numeric decoding occurs
only through the separate `open_numeric_payload_session()` capability.

The transaction order is load-bearing:

1. verify the out-of-band parent access-policy digest;
2. require the exact `numeric_payload_validation` consumer;
3. derive a one-consumer child policy and append `value_derived` and
   `outcome_exposed` taints;
4. validate the closed bundle;
5. retain only the requested payload descriptors from that same secure
   validation transaction;
6. re-hash the retained descriptor bytes;
7. decode an immutable snapshot without reopening a pathname; and
8. close every retained descriptor at session exit or failure.

An unauthorized request fails before any bundle path inspection or file read.
`ValueAccessLineage.from_dict()` parses a declaration only.
`reverify_value_access_lineage()` must reconstruct it from the trusted parent
policy and its out-of-band digest before it is used as lineage evidence.

### 3.1 Strict NPY contract

The decoder accepts only NPY v1 or v2 and requires:

- a bounded header and total payload size;
- `allow_pickle`-free, simple numeric or boolean dtype;
- no object, structured, string, datetime, or subarray dtype;
- exact header dtype and shape agreement with `PayloadRef`;
- C order, exact data extent, and no trailing bytes;
- finite values;
- a C-contiguous returned array sealed by immutable `bytes` backing, so its
  write flag cannot be re-enabled; and
- a content-derived row identity joined to every dependent array.

Contract failures such as nonfinite values, a forged row identity, or a wrong
amplitude relation are validation failures. They are not converted to
`insufficient`.

The first closed cross-payload relation is a predeclared L2 check:

\[
\text{amplitude} =
\left\lVert\text{values}\right\rVert_2
\]

along an explicitly named axis and fixed `rtol`/`atol`.

## 4. Independent generator-family foundation

`GeneratorFamilyIdentity` separates:

- the public family identity;
- the mathematical construction-family identity;
- the implementation identity and version; and
- the exact implementation source digest.

`require_distinct_construction_families()` rejects a pair that differs only by
seed, source digest, implementation label, or display family name. Passing
this metadata gate is necessary but is not proof of epistemic independence.

The existing representation phantom is now exposed through a thin family
identity adapter. A second construction,
`SpectralMomentGenerator`, uses interleaved Fourier quadrature rather than the
representation-phantom generator. It emits:

- F2/F4 varying-direction positives;
- fixed-direction nulls; and
- zero first/second-moment prerequisite failures.

Fit and evaluation quadrature samples are disjoint. Estimator inputs and
oracle truth are separate typed objects, and the estimator-facing record
contains no truth payload. Each evaluator-side case recomputes its first and
second moments from both splits, and the enclosing phantom regenerates the
canonical three controls from its bound spec before accepting their linkage.

The spectral spec applies a conservative static resource estimate with safety
factor four and a 256 MiB cap before generator allocation. This guards
parameter-induced runaway allocation; it is not an operating-system OOM
guarantee. It also requires each declared harmonic to clear a predeclared
signal-to-scale and absolute numerical floor. Supported rows are accepted only
when the recovered moment's row-wise error is below the frozen relative bound;
zero-signal controls use a separate scale-aware absolute bound. A maximum
combined scalar scale is also fixed below the safe range of the generator's
derived square-and-sum operations, so every accepted spec reaches allocation
with finite internal arithmetic bounds.

The spectral records' versioned dictionaries are in-memory content
fingerprints only. This slice supplies no parser or persistence-schema
compatibility promise for them.

These are development controls only. The generator constructs no scientific
graph, core, loop, winding, selection, confirmation, or D-gate result.

## 5. Explicit remaining gap

PR #7 makes the narrower question “what same-object pointwise formula could
later supply the fibers of \(\psi\)?” executable and falsifiable on model-free
inputs. It deliberately records that the answer is not yet a field or order
parameter. It does not establish:

- a model-side source object;
- a discrete domain, oriented face complex, or inside/outside relation;
- matched cycle classes across genuinely distinct graph constructions;
- charge-blind core localization;
- graph, radius, density, or worst-case robustness;
- integer stability or topology;
- calibration selection or independent confirmation;
- D0-D8 completion; or
- any subject, semantic, SAE, or causal result.

Those obligations remain later, separate library and experiment layers.
