# P0 Hypothesis and Artifact Contracts

- **Status:** implemented experimental contract; no estimator or subject access
- **Policy:** `spirallens.p0-registry-policy.v0.1`
- **Registry:** [`order_parameter_hypothesis_registry_v0_1.yaml`](../protocols/order_parameter_hypothesis_registry_v0_1.yaml)
- **Depends on:** [Order-Parameter-First Fundamental Frame](FUNDAMENTAL_FRAME.md)

This contract is the first executable boundary of the post-outcome
order-parameter-first frame. It was created after the terminal Pythia-70M
retrieval audit. The audit establishes chronology, but its status, counts, and
candidate values are forbidden inputs to hypothesis, graph, threshold,
exclusion, model, context, and preprocessing selection.

Chronology is content-bound rather than asserted only by a boolean. The
registry fixes the pre-outcome execution commit, the post-outcome integration
commit, the tracked outcome-observation record path and source SHA-256, and
the retained terminal artifact's source SHA-256. It stores none of the
observed values. The registry commit must remain a descendant of the bound
integration commit; repository ancestry is verified at freeze/review time,
not by the YAML loader.

P0 makes the research question representable without choosing its answer. It
does not estimate a field, construct a graph, open calibration payloads, load a
model, inspect a subject tensor, authorize an integer output, or promote any
real-model claim beyond Level 0.

## 1. Implemented package boundary

`spirallens.instrument_contracts` is a metadata-only experimental namespace.
It is deliberately separate from:

- `spirallens.contracts`, which contains reusable mathematical primitives;
- `spirallens.neighbors`, which remains a state-only retrieval boundary; and
- estimator, graph-construction, model-adapter, and subject-execution code.

Importing or validating these contracts does not dereference payloads or
import Torch, Transformers, Faiss, or a model adapter.

The namespace provides:

- closed control-flow enums and typed digest references;
- a strict F0-F4 hypothesis registry;
- provisional metadata schemas for instrument artifacts;
- strict YAML loading for the human-authored registry;
- strict canonical JSON loading for generated artifact manifests; and
- source-byte and canonical-content SHA-256 verification.

These are experimental pre-1.0 contracts. Their existence is software
evidence, not scientific evidence.

## 2. P0 registry boundary

The tracked registry contains exactly one entry for each initial family:

| ID | Branch | Prospective ceiling | P0 boundary |
| --- | --- | --- | --- |
| F0 | support | Level 1G | field-unbound diagnostics only |
| F1 | geometry | Level 2G | rank-two projector/connection; no integer charge |
| F2 | defect | Level 2T | rank-two covariant section; conditional eligibility only |
| F3 | defect baseline | Level 1D | fixed/global-plane projection-dependent baseline |
| F4 | defect | Level 2T | spin-two/doubled-angle convention kept distinct from F2 |

Every entry remains at Level 0. The registry has no winner, advanced
disposition, numeric threshold, subject identifier, model choice, observed
outcome value, semantic label, or SAE label. Choices that calibration may
later make are encoded as unresolved `RuleChoice` values with a closed
candidate set, rather than as `null` or an implicit default.

Structural parsing and P0 policy validation are separate. A document can be
well-formed yet still fail the P0 policy if, for example, F1 authorizes an
integer, F2 omits its conditional winding prerequisites, F3 omits a
random-plane control, or F4 uses the ordinary-vector convention.

## 3. Canonical identity

Canonical manifests use one versioned JSON rule:

- UTF-8;
- lexicographically sorted object keys;
- compact separators;
- Unicode preserved rather than ASCII-escaped;
- no trailing newline or surrounding whitespace;
- finite numbers only, with negative zero rejected; and
- exact field sets at every typed boundary.

The loader reconstructs the typed object and requires its emitted canonical
mapping and bytes to equal the input. Duplicate keys, noncanonical bytes,
unknown schemas, aliases, merge keys, custom YAML tags, multiple YAML
documents, boolean-as-integer values, and oversized manifests fail closed.

Two identities remain distinct:

1. `source_sha256` hashes the exact file bytes and changes with comments or
   YAML formatting;
2. `canonical_sha256` hashes the validated semantic mapping and remains stable
   across non-semantic YAML formatting changes.

An `ArtifactRef` binds artifact type, the one exact schema version registered
for that type, artifact ID, and canonical digest. A `PayloadRef` binds payload
kind, byte length, media type, content digest, and the
shape/record-count/row-identity fields required by its kind. Array payloads
use canonical NumPy dtype strings and `application/x-npy`, cannot declare
fewer bytes than their uncompressed values, and must agree on first-axis row
count within an artifact's row-bound payload group. Calibration-cell manifests
are structured records with explicit cell-order digests; supplied anchors are
structured arrays with explicit substrate-row order. Paths are not canonical
identity, and validation never opens a payload.

## 4. Implemented artifact schemas

The metadata schemas cover:

- `SubstrateBinding`
- `GraphConstructionSpec`
- `CandidateGraph`
- `SupportDiagnostic`
- `GeometricFieldEstimate`
- `OrderParameterSpec`
- `OrderParameterField`
- `CoreScore`
- `CoreCandidate`
- `GroundTruthAnchor`
- `EdgeConnection`
- geometry and defect variants of `LoopEstimate`
- `CalibrationSelectionDecision`
- `CalibrationConfirmationResult`

The schemas bind content-addressed references; they do not contain arrays,
model values, or estimator execution.

Validation is deliberately local to one manifest. It verifies the manifest's
own exact schema, canonical bytes, typed reference kinds, content digests, and
declared row/order identities, but it does not resolve referenced artifacts or
payloads. Consequently, existence and digest resolution across a bundle,
cross-manifest equality of row/vertex/edge/cycle/loop order digests, and
selection/confirmation cell completeness remain unproved until a separate
bundle validator is implemented. A collection of individually valid manifests
must not be described as an internally consistent instrument bundle.

The following distinctions are load-bearing:

- `SupportDiagnostic` has no order-parameter, core, loop, winding, or charge
  reference. It cannot be deserialized or relabelled as `CoreScore`.
- `CoreScore` is charge-blind and carries typed, content-addressed
  `OrderParameterSpec`/`OrderParameterField` references, its own substrate and
  row identity, a declared singularity rule, and one explicit
  core-neighborhood mode. Equality with the referenced spec/field substrate,
  row identity, and singularity contract is a future bundle-validator check;
  single-manifest validation does not claim it.
- A core-neighborhood binding is exactly one of `graph_free`,
  `inherit_field_estimation_graph`, or `explicit_core_graph`. The latter two
  cannot collapse the field, core, and cycle graph axes into one unnamed
  digest.
- `GroundTruthAnchor` is supplied synthetic calibration metadata and is never
  localization-gate eligible. `CoreCandidate` is inferred, charge-blind, and
  sealed without loop-observable input. Neither can be substituted for the
  other.
- A geometry loop binds a geometric field, edge connection, and continuous
  holonomy. It cannot carry an order parameter, core, winding, or charge.
- A defect loop binds an order-parameter field and declared
  interpolation/lift/reference evidence. Local-frame coordinates require an
  edge connection. A localized-defect variant requires an inferred
  `CoreCandidate`; an unlocalized sampled winding cannot exceed Level 1D.
  The specification, field, and loop each repeat the F2/F3/F4 hypothesis ID,
  and F3 cannot declare a ceiling above Level 1D even before bundle joins are
  checked. A Level-2T loop additionally carries a typed, sealed
  `CalibrationSelectionDecision` authorization reference. That reference is
  necessary but not sufficient: the future bundle validator must resolve it
  and prove that the same hypothesis and locked integer path were advanced.
- A confirmation result binds a sealed selection decision and cannot contain
  replacement estimator, graph, threshold, coverage, abstention, or
  aggregation settings.
- Still-unresolved selection choices are keyed by
  `(hypothesis_id, family_id)`, remain `calibration_selection`, and cannot be
  smuggled in as an arbitrary fixed choice.
- Resolved selection choices are separately typed, keyed by the same pair, and
  must be `calibration_resolved`; a named rule field cannot carry another
  field's family ID.
- Registry-fixed choices use a distinct `fixed_by_hypothesis` receipt, so a
  frozen convention cannot be relabelled as calibration-selected.
- The selection decision carries an exhaustive F0--F4 choice partition.
  Every registry-active calibration family appears exactly once as resolved
  or unresolved, every registry-fixed family appears exactly once with its
  fixed value, and non-applicable or invented families cannot acquire a
  receipt. Non-advanced competitors therefore remain visible as complete,
  typed selection outcomes rather than disappearing behind the winner. An
  advanced hypothesis must have every calibration-active family resolved;
  unresolved choices are allowed only on non-advanced competitors.
- A selection decision may authorize an integer path only for an advanced F2
  or F4 hypothesis, only together with its Level-2T ceiling, and never while
  that hypothesis retains an unresolved rule choice. Any nonzero selection
  claim ceiling must likewise be supported by at least one advanced
  hypothesis whose frozen branch admits that level. Every registry-delegated
  input, axis, centering, residual, architecture-accounting, estimator,
  fit-role, interpolation, trivialization, and reference choice—and F2's lift
  choice—must be present with an allowed selected ID, with no invented extra
  family. F4's fixed lift must instead retain its hypothesis-fixed provenance
  and is its only fixed receipt. A loop's authorization
  reference is not accepted as bundle evidence until that decision is
  resolved and the hypothesis IDs agree.

Malformed, tampered, or leaky manifests are invalid inputs. They are not
scientific `fail` or `insufficient` results. Valid gate states remain
`pass|fail|insufficient|not_run`.

## 5. Read-only validation

Validate the tracked P0 registry:

```bash
spirallens hypothesis-registry validate \
  --path protocols/order_parameter_hypothesis_registry_v0_1.yaml
```

Validate a generated canonical instrument manifest:

```bash
spirallens instrument-artifact validate \
  --path path/to/canonical-artifact.json \
  --expected-source-sha256 <sha256> \
  --expected-canonical-sha256 <sha256>
```

Both commands are read-only. They report identities and schema facts; they
cannot write an artifact, select a hypothesis, access a payload, or prepare a
subject run. Instrument-artifact output explicitly reports
`validation_scope=single_manifest`, `references_resolved=false`, and
`bundle_validated=false`; `status=valid` means only that bounded scope.

## 6. Explicitly deferred

This P0 implementation does not include:

- F0-F4 estimators or numerical mathematics;
- phantom generation or hidden calibration data;
- graph constructors, scales, or graph-family selection;
- numerical floors, tolerances, or aggregation gates;
- field-specific payload-layout schemas such as the exact tensor rank, trailing
  dimensions, dtype class, and encoding for each estimator output (v0.1 binds
  kind, media type, declared shape/dtype, minimum bytes, row identity, and
  within-manifest row count only);
- orientability, U(1), winding, or integer-output authorization;
- an actual calibration selection or confirmation result;
- referenced-artifact/payload resolution; registry-entry joins for selected
  rules; referenced fit-role/split validation; cross-manifest identity checks;
  or selection/confirmation cell-set completeness checks;
- D1-D8 qualification or a validated instrument bundle;
- `SubjectProtocolManifest`, subject `prepare-only`, or subject execution; or
- a stable public API or migration guarantee.

The next implementation step is synthetic, representation-shaped substrate
generation and analytic contract tests. It must consume these definitions
without changing them in response to subject outcomes.
