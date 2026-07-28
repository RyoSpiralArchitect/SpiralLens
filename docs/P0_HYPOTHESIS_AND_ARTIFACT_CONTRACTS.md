# P0 Hypothesis and Artifact Contracts

- **Status:** implemented experimental P0 contract and integrity-bundle
  boundary; the P0 loader runs no estimator and permits no subject access
- **Policy:** `spirallens.p0-registry-policy.v0.1`
- **Bundle schema:** `spirallens.instrument-bundle.v0.1`
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
does not estimate a field, construct a graph, decode calibration payload
values, load a model, inspect a subject tensor, authorize an integer output, or
promote any real-model claim beyond Level 0.

The later P1 instrument-development implementation lives under
`spirallens.synthetic` and instantiates these contracts without changing that
P0 claim. It generates and semantically self-audits one bounded F0/F1/F2
positive/null development cell, then hands its artifacts to the unchanged
closed-integrity validator. Its model-free
`SyntheticLatticeSubstrateBinding` embeds a
`SyntheticLatticeContextBinding`; it indexes no ContextBank and binds no model
or tokenizer. It requires `evolution_axis=synthetic_lattice` and
`role=instrument_dev`, while that axis remains excluded from the P0 model
observation-axis candidate set. It is not a token-position observation,
calibration selection, or subject artifact.

The P1 producer records the exact mutual-kNN/Euclidean/\(k=6\) development
graph as `instrument_dev_executed`. That state reports an implementation that
ran; it does not alter any unresolved registry choice, qualify a graph family,
or count as calibration resolution. Cycle construction remains `not_run`, and
all emitted F0/F1/F2 artifacts remain at Level 0.

The producer also records a versioned, safety-factored static resource
preflight whose claim is limited to guarding parameter-induced runaway
allocation, not guaranteeing operating-system OOM behavior. After semantic and
closed-integrity validation in private staging, the current Darwin-only
publisher exposes the complete directory through one exclusive no-replace
namespace transition. That atomic namespace property is not a claim of crash
durability. Post-publication loading is bound to the retained published
directory's `(device, inode)` identity rather than to the display path alone.

## 1. Implemented package boundary

`spirallens.instrument_contracts` is an experimental contract namespace. It is
deliberately separate from:

- `spirallens.contracts`, which contains reusable mathematical primitives;
- `spirallens.neighbors`, which remains a state-only retrieval boundary; and
- estimator, graph-construction, model-adapter, and subject-execution code.

Importing the contracts and running single-manifest validation do not
dereference payloads. Bundle validation streams indexed payload bytes only to
verify byte length and SHA-256; it does not decode their values. A separate
authorization-bound numeric session is now the first value-reading consumer;
it is not invoked by either manifest loader. None of these paths imports
Torch, Transformers, Faiss, or a model adapter.

The namespace provides:

- closed control-flow enums and typed digest references;
- a strict F0-F4 hypothesis registry;
- provisional metadata schemas for instrument artifacts;
- a canonical closed-world instrument-bundle manifest;
- strict YAML loading for the human-authored registry;
- strict canonical JSON loading for generated artifact manifests;
- source-byte and canonical-content SHA-256 verification;
- exact artifact and opaque-payload reference closure; and
- selected cross-manifest metadata joins with subject-role rejection.

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
identity. Single-manifest validation never opens a payload; closed-integrity
bundle validation opens it only as opaque bytes for length and SHA-256
verification.

## 4. Implemented artifact schemas

The metadata schemas cover:

- `SubstrateBinding`
- `SyntheticLatticeSubstrateBinding` with an embedded
  `SyntheticLatticeContextBinding`
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

The schemas bind content-addressed references and execution provenance; they do
not contain array values or model values, and loading them does not run an
estimator. `ArtifactType.SUBSTRATE_BINDING` currently admits two experimental
schemas:
`spirallens.instrument.substrate-binding.v0.1` for model-bound observations and
`spirallens.instrument.synthetic-lattice-substrate-binding.v0.1` for
model-free development lattices. The latter embeds
`spirallens.instrument.synthetic-lattice-context-binding.v0.1`.
These are pre-1.0 experimental contracts: this development slice refines the
unreleased v0.1 surface in place, and no backward-reader or migration guarantee
is claimed.

The ordinary `SubstrateBinding` rejects `synthetic_lattice` and requires a
ContextBank reference. Only `SyntheticLatticeSubstrateBinding` accepts the
development referent, and it requires both `role=instrument_dev` and a
model-free synthetic context whose claim eligibility is false. The F0-F4 P0
registry continues to expose only `token_position`, `layer_index`, and
`training_step` as selectable model observation axes.

There are now two deliberately different validation scopes.

Single-manifest validation verifies one manifest's exact schema, canonical
bytes, typed reference kinds, content digests, and declared row/order
identities. It does not resolve any referenced artifact or payload, so a
collection of individually valid manifests is not bundle evidence.

Closed-integrity bundle validation requires one canonical bundle manifest with
declared roots and a closed index of instrument artifacts, registries,
ContextBanks, and opaque payloads. It:

- requires at least one instrument artifact and one declared instrument root;
- resolves every `ArtifactRef` by exact type, schema version, artifact ID, and
  canonical digest;
- rejects missing, extra or unreachable artifact entries and logical
  dependency cycles;
- requires exact `PayloadRef` closure, rejects conflicting reuse of one payload
  digest, and streams each payload to verify its byte length and SHA-256;
- opens every manifest, artifact, ContextBank, registry, and payload through
  descriptor-relative no-follow traversal; rejects symlinks and multiply
  linked files; and fails with `secure_member_open_unavailable` rather than
  using an insecure fallback where that traversal is unsupported;
- binds each indexed ContextBank to its explicitly declared allowed
  `ContextRole`;
- validates an embedded synthetic-lattice context without treating it as a
  ContextBank, including its row-identity join, lattice site count, and
  `claim_eligible=false` boundary;
- checks the implemented substrate, graph, field, core, loop, registry,
  selection, and confirmation metadata joins; and
- rejects `subject_discovery` and `subject_confirmation` fit roles, requires
  `subject_data_access_authorized=false`, and performs no subject access or
  execution.

This establishes a closed, content-addressed **integrity bundle**, not a
synthetic-qualified or scientific instrument bundle. The validator does not
decode payloads, validate array layout or values, recompute row identities
from payload content, map `ContextRole` to `FitRole`, prove calibration-cell
completeness, or evaluate D0-D8. `LoadedBundlePayload` is only an integrity
receipt and exposes no reusable pathname or descriptor. The separate numeric
consumer retains only explicitly requested descriptors from the same secure
validation transaction, re-hashes those descriptors, and decodes immutable
NPY snapshots without pathname reopening. It still does not qualify an
estimator, graph, referent, or D gate.

The following distinctions are load-bearing:

- `SupportDiagnostic` has no order-parameter, core, loop, winding, or charge
  reference. It cannot be deserialized or relabelled as `CoreScore`.
- `CoreScore` is charge-blind and carries typed, content-addressed
  `OrderParameterSpec`/`OrderParameterField` references, its own substrate and
  row identity, a declared singularity rule, and one explicit
  core-neighborhood mode. Closed-integrity bundle validation checks its
  implemented spec/field, substrate, row-identity, singularity, and graph
  joins; single-manifest validation does not claim them.
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
  necessary but not sufficient: closed-integrity bundle validation resolves it
  and checks that the same hypothesis and locked integer path were advanced,
  but it does not prove that the underlying numerical or scientific
  prerequisites succeeded.
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
- `instrument_dev_executed` is a separate receipt for the exact family,
  metric, or scale run by a visible development graph. It is legal only when
  all three graph choices carry that resolution under `role=instrument_dev`,
  and every graph with that role must use it rather than a scientific
  resolution; it cannot refine a registry `calibration_selection`, count as
  `calibration_resolved`, or authorize promotion.
- The selection decision carries an exhaustive F0--F4 choice partition.
  Every registry-active calibration family appears exactly once as resolved
  or unresolved, every registry-fixed family appears exactly once with its
  fixed value, and non-applicable or invented families cannot acquire a
  receipt. Non-advanced competitors therefore remain visible as complete,
  typed selection outcomes rather than disappearing behind the winner. An
  advanced hypothesis must have every calibration-active family resolved;
  unresolved choices are allowed only on non-advanced competitors.
- For a selected artifact that is uniquely traceable to F1--F4, bundle
  validation follows that artifact back to its hypothesis and substrate. It
  requires that hypothesis to be `ADVANCE`, checks the locked observation axis
  and fit role, and for F2--F4 also checks the typed interpolation, lift,
  trivialization, and reference conventions carried by the resolved
  order-parameter specification. Non-selected crossed outputs remain
  stage-safe competitors and are not falsely required to match the winning
  receipt. Generic support, graph, substrate, and anchor artifacts have no
  unique hypothesis binding in v0.1 and therefore receive only the stage-role
  checks their schemas support.
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
  reference is accepted as integrity-bundle metadata only when that decision
  resolves, the hypothesis IDs and registry agree, its four typed
  order-parameter conventions match, and its substrate role and observation
  axis equal the locked receipts. The decision must also contain a selected
  precursor that traces to that exact order-parameter specification; the final
  Level-2T loop remains downstream of the decision, avoiding a
  content-addressing cycle. This is not Level-2T evidence.

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

Validate a generated canonical closed-world integrity bundle:

```bash
spirallens instrument-bundle validate \
  --path path/to/instrument-bundle.json \
  --expected-source-sha256 <sha256> \
  --expected-canonical-sha256 <sha256>
```

All three commands are read-only. They report identities and contract facts;
they cannot write an artifact, select a hypothesis, prepare a subject run, or
execute one. Instrument-artifact output explicitly reports
`validation_scope=single_manifest`, `references_resolved=false`, and
`bundle_validated=false`; `status=valid` means only that bounded scope.
Instrument-bundle output reports
`validation_scope=closed_integrity_bundle`,
`bundle_integrity_validated=true`, and
`payload_content_decoded=false`. It may read indexed payload bytes for
integrity verification, but it cannot interpret their values or authorize
subject access.

## 6. Explicitly deferred

The P0 contract and generic loader themselves do not include:

- F0-F4 estimators or numerical mathematics;
- phantom generation or hidden calibration data;
- graph constructors, scales, or graph-family selection;
- numerical floors, tolerances, or aggregation gates;
- payload semantic decoding and field-specific array validation, including the
  exact tensor rank, trailing dimensions, dtype class, encoding, and
  value-level constraints for each estimator output (v0.1 binds kind, media
  type, declared shape/dtype, minimum bytes, row identity, and within-manifest
  row count only);
- row-identity recomputation from payload content;
- numerical demonstration of orientability, U(1), winding, or scientific
  authorization of an integer output;
- an actual calibration selection or confirmation result;
- a validated `ContextRole`-to-`FitRole` mapping or
  selection/confirmation cell-set completeness checks;
- application-level verification of selected input-tensor, centering,
  residual, architecture-accounting, and estimator choices, because v0.1
  artifacts bind those executions only through opaque input and fit receipts;
- D0-D8 qualification or a synthetic-qualified/scientific instrument bundle;
- scientific, topological, semantic, or causal claim promotion;
- `SubjectProtocolManifest`, subject `prepare-only`, subject preparation, or
  subject execution; or
- a stable public API or migration guarantee.

The first synthetic, representation-shaped development slice now consumes
these definitions without changing them in response to subject outcomes. It
does not complete P1. A second, spectral-moment construction-family foundation
and a secure numeric payload consumer now exist separately; they are not yet a
qualification bundle or a D1 result. The next work is to integrate independent
families with genuinely distinct graph families, matched cycle construction,
the full crossed null, D0-D8 qualification, and locked calibration
selection/confirmation—still before any subject protocol is prepared.
