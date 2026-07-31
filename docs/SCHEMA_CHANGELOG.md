# Schema and Compatibility Change Record

SpiralLens records public and provisional persistence changes separately from
scientific results. Entries describe software contracts only; they do not
promote a claim.

## 2026-07-31 — D7 terminal, external-witness, and post-start runner mechanics

### Added

- The deep-internal `confirmation_attempt_terminal_persistence` module now
  persists one complete scientific-result or failed-attempt structural
  terminal as a closed directory inventory. Every canonical member, manifest,
  and consumption record is staged and fsynced before one descriptor-relative
  native no-replace directory rename; publication is followed by strict reload
  of the exact inventory, digests, record types, joins, and file identities.
- Terminal persistence fails closed on a competing attempt-scoped stage,
  destination race, symlink, hardlink, FIFO, missing/extra/unknown member,
  staged-byte or file-identity mutation, parent/stage descriptor drift, and
  cleanup whose ownership cannot be proved. A failed terminal-parent fsync is
  reported as `parent_directory_fsync_proved=false`, not silently converted to
  a durability claim.
- `spirallens.d7-external-abort-witness-statement.v0.1` and
  `spirallens.d7-signed-external-abort-witness-envelope.v0.1` bind the exact
  replay target, attempt/start, execution identity, failure payload, structural
  receipt, external observation, store/terminal coordinates, three separated
  principals, observer/verifier key identities, and the explicit runtime
  trust-root digest. The envelope carries separate Ed25519 observer and
  verifier signatures. Its canonical file is a required immutable member of
  an evidenced-abort failed-terminal inventory, and the finalization record
  binds its digest and byte count.
- The deep-internal external terminal operation performs one joined sequence:
  digest-first envelope loading and signature verification against explicit
  runtime pins; fixed live revalidation of prefix, terminal coordinates,
  parent identity, and terminal absence; internal derivation of the
  finalization, failed-attempt, manifest, and consumption records; one-shot
  witness consumption; atomic no-replace publication; and strict reload.
  Existing external-abort terminals can be strictly reloaded and
  reauthenticated to exact supplied pins.
- The deep-internal post-start runner accepts only a private,
  nonserializable, primary-confirmation ownership handoff and one zero-argument
  producer callback. It validates all six result components and the outer
  payload, including the replay-target/full-inventory/aggregation/result-schema
  projection, before preparing a typed terminal handoff. Ordinary exceptions
  retain their identity and may receive a typed in-process failure handoff;
  `BaseException` is not reclassified as an abort.

### Compatibility and non-claims

- These modules declare empty `__all__` values and introduce no supported or
  provisional public Python API. The terminal/witness/runner work completes
  roadmap item 19 as mechanics only; roadmap item 20, the fused
  verify-and-exclusive-start operation, is next.
- Witness authentication is exactly `explicit-runtime-pins-only`. The supplied
  pins do not prove SpiralLens trust-root provenance or official authority,
  and the envelope has no wall-clock freshness proof. The private post-start
  ownership object has no issuer in this change.
- No official target/start, supplier, seed, exact scientific executor or
  aggregation, execution observation, scientific eligibility, retry/replay
  authority, D7, or D8 is created. The complete official executor and
  aggregation remain separately auditable behind the zero-argument producer
  callback.
- The new signed-witness member extends only the previously unpersisted
  provisional evidenced-abort terminal shape. No earlier C1, C2, D6,
  caller-prefix evidence, or historical result bytes are rewritten or
  promoted.

## 2026-07-31 — D7 non-authorizing launch-authority prerequisite inputs

### Added

- The deep-internal `confirmation_attempt_authority` module defines canonical
  records for a concrete subset of inputs that a future operational
  verify-and-exclusive-start boundary must obtain. The outer bundle and its
  loaded structural candidate are not an authorization, capability, attempt,
  target publication, or execution record.
- The replay-target-shaped input uses the required field surface of the
  already frozen `D7ReplayTargetContractSpec` rather than inventing a parallel
  target schema. Target admission, exact full design, and exact source/runtime
  are dedicated candidate leaf types, not generic opaque bindings. Their
  positive semantics are named caller claims and every leaf and nested
  artifact binding records `identity_authenticated=false`; the artifact
  binding also records `authoritative_source_loaded=false`. The admission
  candidate preserves the full construction-review and admission-spec
  bindings, including role, contract, digest, and byte count.
- Seed handling is explicit: the candidate separates the development-seed and
  parent-selection-seed exclusion registries from the proposed official-seed
  inventory and binds their declared sources and cardinalities. A typed
  exclusive-supply-claim input causally joins the exact supplier, both
  registries, readiness, and the actual admission and
  execution-source/runtime receipt-binding fields, which remain
  caller-alleged. A typed single-invocation input
  rejoins that exact claim and supplier to the official inventory; chronology
  then rejoins the invocation output to atomic publication of the exact
  inventory, full design, and target. Completeness is structural relative to
  the bound sources, and the claim, invocation, inventory-output, supplier
  chronology, and atomic-publication verification fields remain false.
- Separate records describe those admission, source/runtime, supplier,
  invocation, execution-identity, physical-identity, full-design-freeze, and
  launch-intent inputs. The chronology keeps the full-design freeze distinct
  from and prior to launch intent, but does not establish that any alleged
  event occurred.
- Physical identity fixes the `primary-confirmation` role and derives the exact
  attempt key from the canonical replay-target digest. It binds normalized
  absolute paths, requires positive device/inode coordinates for the store,
  evidence lane, lane parent, output parent, and terminal parent; binds the
  lane's parent identity to the store while requiring the lane identity to
  differ; and rejects output/terminal overlap with each other and with the
  persistence-reserved lane, evidence directory, attempt-specific
  declaration/authorization/claim/start envelopes, and chronology leaf by
  lexical path or known declared physical key. No
  live filesystem observation, absence check, reservation, or hostile-process
  protection follows from the record. Double-slash aliases, embedded NUL, and
  overlong declared paths are rejected before persistence.
- The generic artifact binding intentionally has no raw `from_bytes` factory.
  The strict bundle loader applies its byte-size cap before hashing, requires
  the expected outer SHA-256 to match before parsing, translates canonical
  JSON parser failures, including deep nesting and oversized integer literals,
  into `D7AuthorityInputError`, canonicalizes every nested record, rejects
  unknown or malformed fields, and rejoins the declared bindings. It performs
  no callback, filesystem access, process inspection, seed supply,
  persistence, or execution.

### Compatibility and non-claims

- The module is deep internal, declares an empty `__all__`, and is not
  re-exported. It adds no stable or provisional public Python API and writes no
  persisted artifact.
- The loaded candidate permanently reports authority, target authority,
  source/runtime verification, admission, readiness, supplier claim,
  invocation, chronology, inventory-output, atomic publication, freeze,
  launch-intent verification, live physical reobservation, path absence,
  exclusive start, lifecycle eligibility, execution, terminal/finalization,
  isolated replay, D7/D8, and scientific claims as false. A
  caller-constructible record, matching digest, serialized “capability,” or
  token cannot be promoted into authority.
- This change exposes a prerequisite that earlier work left abstract. It does
  not reinterpret or rewrite C1, C2, D6, the replay/attempt contract
  specifications, caller-evidence envelopes, or any prior result.
- The successor order is terminal/witness/runner mechanics with no official
  execution; one fused verify-and-exclusive-start operation with no reusable
  token; exact final source/runtime closure plus reviewed admission; one seed
  supplier invocation followed by atomic target/full-design publication,
  freeze, and launch intent; then invocation of the fused start. All remain
  future work.

## 2026-07-30 — D7 caller-supplied prefix evidence persistence

### Added

- The deep-internal `confirmation_attempt_persistence` module persists a
  caller-supplied Level-0 primary declaration, launch-authorization record,
  claim record, and start record beneath an immutable store scope and four
  predecessor-chained envelopes in `d7-prefix-evidence-only-v0/`. Raw
  lifecycle records are never top-level stage files. The scope and envelopes
  permanently encode false authority/capability fields and prohibit in-place
  promotion.
- Every envelope is canonical, bounded, descriptor-read, digest-checked before
  parse, and published by descriptor-relative native exclusive rename plus file
  and parent-directory fsync. Darwin `renameatx_np(RENAME_EXCL, ...)` and Linux
  `renameat2(RENAME_NOREPLACE)` branches are present; other platforms fail
  closed. Only the current Darwin host is qualified by this change.
- A hard interruption before rename may leave a dot-prefixed staging entry.
  Its presence blocks retry/reload and never counts as a stage or authority.
  Automatic scavenging is omitted because it cannot safely distinguish an
  orphan from a concurrent live writer. Writers must first quiesce; only a
  confirmed orphan may enter separate offline recovery.
- Authorization and pre-start absence receipts are content-addressed
  companions. Before authorization or start becomes visible, the writer
  reobserves the declared real store root, parent device/inode, and absent
  output/terminal leaf. Stage envelopes remain strictly non-idempotent; even
  identical existing bytes are a conflict.
- A complete strict reload preserves all structural joins and classifies exact
  caller-supplied start-record plus terminal absence only as
  `caller_supplied_start_record_present_terminal_absent`. Any file, directory,
  symlink, or otherwise unverified terminal entry is
  `terminal_path_present_unverified`. The inspection records
  `execution_observed=false` and `started_unresolved_established=false`;
  neither state authorizes retry, replay, or D8.
- Prefix validators now expose separate authorization and claim joins so each
  persisted stage can revalidate its complete predecessor set. Output and
  terminal subjects must be non-nested within one attempt as well as across
  isolated primary/replay attempts.
- Isolated-replay declarations are rejected before the evidence lane is
  created because passed-primary terminal consumption cannot yet be loaded
  authoritatively.

### Compatibility and non-claims

- The module declares an empty `__all__` and is not re-exported. Persisted scope
  and envelope bytes, not only ephemeral Python identities, set
  `authority_granted=false`; no official replay target, attempt, seed, launch
  authorization, execution capability, result, or D7/D8 status is created.
- Path reobservation is a trusted-local-operator check, not reservation,
  hostile-process TOCTOU resistance, or post-publication inode proof. The
  append-only property assumes store entries are not administratively
  deleted.
- No terminal transaction or external-abort finalizer is exposed. The
  directly constructible external receipt remains structurally valid but
  unauthenticated and cannot mint finalization authority. A later operational
  verifier must issue a separate non-caller-constructible capability and write
  a distinct authoritative lane; evidence envelopes cannot be promoted in
  place.
- C2 does not close this source. Exact current execution-source/runtime
  closure, authoritative target joins, admission, freeze, official seeds,
  terminal publication, isolated replay, D7, and D8 remain future work.

## 2026-07-30 — D7 result-component and attempt-evidence payload schemas

### Added

- The deep-internal `confirmation_result_components` module defines six
  distinct canonical, attempt-independent D7 payload schemas. Their schema
  versions remain separate from the frozen component contract IDs, and
  canonical-byte loading requires the expected SHA-256 before parsing.
- The matching pure structural validator rejoins exactly 1,344 event lanes
  (192 core and 1,152 loop cells), 64 joined primary units, six required
  strata, four-state aggregate gates, and the outer scientific-result
  bindings. Every event stage is derived from exact outcome fields. Primary
  summaries are reconciled from their cells; graph axes, fingerprints,
  seed-slot case pairs, canonical row reconstruction, and structural
  non-pass floors are enforced.
- The deep-internal `confirmation_attempt_evidence` module defines canonical
  authorization/pre-start path-absence receipts, an exact in-process/external
  failure-payload union, and an external-abort verification receipt. Its pure
  validator binds actual start bytes, evidence and failed-attempt records,
  external finalization records, authorization/pre-start continuity, and
  isolated primary/replay path separation.
- Path identities accept normalized absolute POSIX parents and lowercase
  portable ASCII leaves. Isolation rejects both textual aliases and repeated
  parent-device/inode/leaf identities.

### Compatibility and non-claims

- All four modules are deep internal, declare an empty `__all__`, and add no
  package-root export. They create no official instance and provide no loader,
  writer, persistence transaction, runner, seed supplier, or authority.
- Target exact-set closure, gate definitions, and gate-evidence semantics
  remain unavailable until an authoritative replay-target loader exists. The
  structural bundle validator cannot authorize any scientific result.
- Path-absence receipts are directly constructible, point-in-time assertions.
  No filesystem observer, destination reservation, TOCTOU resistance, or
  post-publication inode-disjointness proof exists yet.
- A schema-valid external-abort receipt does not authenticate the observer,
  verifier, observation, source/runtime identity, or actor separation. No
  witness verifier or finalizer capability is introduced.
- C2 does not close these sources. Exact current execution-source/runtime
  closure, admission, freeze, official seeds, persistence, execution,
  publication, D7, and D8 remain future work.

## 2026-07-30 — D7 attempt-record and structural-validation schemas

### Added

- The deep-internal
  `spirallens.qualification.confirmation_attempt_records` module defines
  canonical v0.1 role-evidence, declaration, authorization, claim, start,
  gate-summary, result-component, scientific-result, failure-evidence,
  externally evidenced `started_unresolved` finalization, failed-attempt,
  terminal-member, terminal-manifest, and terminal-consumption records.
- Authorization binds the exact execution-source/runtime receipt and runtime
  specification digests that start must observe again. Authorization-time and
  pre-start namespace/path absence-receipt digests are separate and must all
  be distinct; this type layer does not define or verify the receipt bytes.
- Required gates retain the four-valued
  `pass`/`fail`/`insufficient`/`not_run` vocabulary. A `not_run` gate is
  persisted and forces the overall scientific result to `insufficient`;
  overall `not_run` is not a result.
- The scientific-result envelope fixes the complete component inventory,
  filenames, future payload contract IDs, record-count semantics, aggregation
  precedence, reason-code rules, claim ceiling, and byte caps. Infrastructure
  failure is a separate terminal variant, always records
  `aggregate_outcome_observed=false`, and carries a tri-state confirmation
  value-access fact.
- Failure evidence binds a bounded evidence payload under a fixed future
  contract ID. An externally evidenced abort additionally binds a bounded
  verification receipt under its own future contract ID and a finalization
  record; all applicable byte identities are members of the immutable
  terminal inventory.
- The separate
  `spirallens.qualification.confirmation_attempt_validation` module implements
  pure typed joins for the attempt prefix, scientific and failed terminal
  chains, externally evidenced unresolved finalization, and isolated replay.
  Isolated-replay role evidence is derived only after validating the complete
  consumed, passed-primary chain. A replay attempt is accepted only by a
  combined validator that rejoins that complete primary chain and the complete
  scientific or failed replay chain; the generic scientific-attempt validator
  is primary-only. Replay stays in the same store identity because
  alternate-store global one-shot behavior is unproved. Across primary and
  replay, the five execution/intent/key/namespace/path identifiers and four
  authorization/pre-start absence-receipt digests must form disjoint sets.

### Compatibility and non-claims

- These are deep-internal type and structural-validation surfaces. They may
  construct and round-trip in-memory values, but create no official or
  persisted attempt record, filesystem writer, loader, namespace claim,
  terminal transaction, witness verifier, runner, seed, or authority. Both
  modules declare an empty `__all__`; direct named deep imports remain
  unsupported internals.
- The terminal identity graph is acyclic: the manifest binds the typed
  scientific-result or failed-attempt artifact and its immutable members;
  consumption binds the manifest. The manifest never binds consumption.
- In the future authoritative lifecycle, a verifier-established visible start
  without a terminal remains `started_unresolved`. Elapsed time, process
  absence, or a caller assertion cannot finalize it.
- At this record-layer introduction, the six result-component payload schemas,
  absence-receipt schemas, failure payload, external-abort receipt, and their
  byte validators were still unimplemented. The later entry above adds those
  structural byte contracts without adding observation, witness, persistence,
  or scientific authority.
- C2 does not close these new sources. A later exact closure of the final
  execution source and runtime remains mandatory before official seed supply,
  target freeze, authorization, or execution.
- Family admission, full-design freeze, official seeds, persistence,
  launch/execution, result or failure publication, terminal publication,
  witness verification, D7, D8, and every higher scientific claim remain
  absent, false, or `not_run`.

## 2026-07-30 — D7 replay-target and attempt-envelope contract specifications

### Added

- The deep-internal canonical
  `spirallens.d7-replay-target-contract-spec.v0.1`
  (`D7ReplayTargetContractSpec`) defines the required identity and
  source/runtime bindings of a future immutable, seed-bearing replay target
  while forbidding attempt-local paths, authorization, outcomes, terminal
  lineage, gates, and placeholder output.
- The separate canonical
  `spirallens.d7-attempt-envelope-contract-spec.v0.1`
  (`D7AttemptEnvelopeContractSpec`) binds the replay-target contract and
  defines append-only attempt declaration, launch authorization, exclusive
  claim, execution start, scientific-result-or-failed-attempt, terminal
  manifest, and terminal consumption stages. Attempt stages may bind but cannot redefine
  the target identity or its seed, design, graph/cycle, aggregation, result
  schema, or family choices.
- Start must exactly rejoin target, authorization, claim, and observed runtime
  while rechecking namespace absence. Scientific payloads bind the exact
  target and full inventory. Isolated replay derives from a consumed,
  passed-primary terminal, and the final result/failure, manifest, and
  consumption publish as one atomic no-replace transaction.
- `load_d7_replay_attempt_contract_foundation()` internally reruns the pinned
  committed-C2 verifier and reconstructs both specs in memory. It accepts no
  caller-supplied loaded closure, expected digest, seed, result, namespace,
  authorization, or prebuilt mapping.
- The seed-supply contract orders final-code source/runtime closure and
  reviewed family admission before its exclusive claim and one supplier
  invocation, then atomic no-replace full-design/target publication and a
  committed freeze receipt before launch intent. A claim without a published
  target is an aborted, non-retryable seed supply; target absence does not
  prove that the supplier was invoked.
- The future target's claim ceiling is exactly Level 0 and its local authority
  truth vector is closed and all-false; nested authority extensions are
  forbidden.
- Target, authorization, start, and scientific-result bindings are connected
  by an explicit closed table of canonical byte equalities. A start without a
  terminal remains `started_unresolved`, blocks retry/replay/D8, and can be
  finalized only by an append-only record binding external abort evidence.

### Compatibility and non-claims

- Both specs are canonical but unpersisted internal surfaces. No writer,
  replay-target instance, attempt-envelope instance, official seed inventory,
  lifecycle record, result/failure, terminal, or replay artifact is created.
- The append-only stage model is a contract, not an implemented lifecycle.
  The later record-schema slice documented above implements structural
  lifecycle, scientific-result/infrastructure-failure, and terminal types and
  joins only. It still does not persist an instance, invoke the official seed
  supplier, or issue seed values.
- C2 verifies only the historical C1 Git source set. It does not close this
  module or later lifecycle, result, terminal, or runner code. After those
  execution surfaces are final, a separate exact current execution-source and
  runtime closure is required before any seed-bearing target may be issued.
- Family admission, full-design freeze, launch/execution, D7, D8, synthetic
  qualification, and every scientific, representation, semantic,
  integer/topology, model, Pythia, and subject authority remain absent, false,
  or `not_run`.

## 2026-07-30 — D7 C2 declared historical Git source-set closure

### Recorded

- The canonical
  `spirallens.d7-c2-source-closure-receipt.v0.1` artifact has SHA-256
  `d28a87bce5ec80c3388df1e21bccbc052f34beb637ff86f81f4f502d9fdd71a3`.
- C2 is the unique receipt-only child
  `2f4e715a951211af8ca0ca4f6b2f7473134bf92b` of exact post-merge C1
  `e58a8169b41be688628ab7dda583e68088d3affc`. The normal merge commit is
  `b79299a7c4ad47947fbeff536c1c609f0da0ccb2`.
- The committed loader derives rather than accepts those commits and verifies
  C1/C2 ancestry, the one-file receipt delta, the unchanged C1 bundle, and
  every declared historical source blob's mode, object identity, size, and
  digest.

### Compatibility and non-claims

- This is Level-0 declared historical Git source-set closure only. It does not
  execute historical code or attest Python/native runtime, transitive
  dependencies, in-process identity, hostile-local-mutation resistance, or
  current-source compatibility.
- C1 remains byte-identical and truthfully retains its own
  `source_closure_verified=false`, because C1 cannot attest its future commit.
  C2 supplies the separate later receipt; it does not rewrite C1.
- Repository-review attestation, family admission, full-design freeze,
  official seeds, lifecycle, execution, result/failure, terminal publication,
  D7, and D8 remain absent, false, or `not_run`.

## 2026-07-30 — D7 C1 seed-free source-set candidate and C2 verifier foundation

### Added

- One atomic internal `spirallens.d7-c1-seed-free-source-set.v0.1` candidate
  binds six canonical components:
  `spirallens.d7-stable-seed-free-execution-design.v0.1`,
  `spirallens.d7-construction-diversity-review.v0.1`,
  `spirallens.d7-confirmation-implementation-registry.v0.1`,
  `spirallens.d7-confirmation-aggregation-application.v0.1`,
  `spirallens.d7-successor-rebinding-review-contract.v0.1`, and
  `spirallens.d7-c1-source-set-manifest.v0.1`.
- The aggregation component embeds
  `spirallens.d7-confirmation-evaluation-design.v0.1` and
  `spirallens.d7-locked-confirmation-aggregation.v0.1`.
- `spirallens.d7-c2-source-closure-receipt.v0.1` and its choice-free
  issuer/loader are implemented and included in the C1 declared source set.
  The schema and code exist so they can be reviewed before C1 is merged; no C2
  receipt is issued in this change.

### Compatibility and non-migrations

- C1 is a Level-0 repository artifact and deep internal pre-1.0 surface, not a
  package-root or `spirallens.qualification` export. It declares and hashes
  `src/spirallens/**/*.py` plus `pyproject.toml`; it does not attest its future
  commit, repository review, runtime dependency closure, or source closure.
- The construction review is explicitly limited to declared static direct
  source/dependency evidence. Dynamic/transitive and epistemic independence
  remain unproved. The successor component encodes a review contract while
  preserving the historical unreviewed proposal unchanged; no repository
  review attestation is embedded.
- C2 must be created separately from the clean post-merge C1 and must commit
  only its receipt. Family admission, full-design freeze, official seeds,
  lifecycle, launch/execution, result/failure, terminal publication, D7, and
  D8 remain absent, false, or `not_run`.

## 2026-07-30 — D7 seed-slot prediction-kernel extraction

### Added

- `spirallens.d7-seed-slot-primary-prediction.v0.1` is an internal,
  in-memory-only prediction payload produced by one oracle-free numerical
  kernel from an explicitly supplied seed and a member of the seed-free D7
  inventory. The record explicitly attests no seed freeze, authorization,
  chronology, gate, result, or scientific claim.
- The permanently excluded development-seed executor is now a policy adapter
  over that kernel. A conformance test locks equality of graph/input
  fingerprints and observable core/loop prediction semantics between the
  adapter and kernel.

### Compatibility and non-migrations

- The extracted kernel uses stable seed-slot policy and primary-content
  identities, so internal sealed-prediction provenance fingerprints can differ
  from the former development-specific implementation. Prediction classes,
  reason codes, candidate rows, continuous loop estimates, and graph/input
  fingerprints are required to remain equivalent.
- The kernel and payload have no parser or writer and are not re-exported from
  `spirallens.qualification` or the package root. This extraction adds no
  official seed source, source closure, family admission, lifecycle, D7
  scoring, persistence, result, terminal, or D7/D8 authority.

## 2026-07-30 — PR #14 commit-stable D7 drafts and successor rebinding

### Added

- `spirallens.d7-parent-d6-binding.v0.2`,
  `spirallens.d7-confirmation-foundation.v0.2`, and
  `spirallens.d7-confirmation-execution-design-draft.v0.2` supersede their
  internal, unpersisted `v0.1` drafts. Canonical D7 identity no longer contains
  the validation-time current-loader HEAD or source-binding digest. Builders
  still require `LoadedScopeLimitedD6Decision` and validate its typed
  authoritative receipt before deriving the stable historical parent
  projection.
- `spirallens.d6-d7-structural-rebinding-amendment.v0.1` and its internal
  `d7-seed-free-design-identity`, `d7-exact-carry-forward`,
  `d7-structural-manifest-rebinding`, and
  `d7-deferred-successor-obligations` `v0.1` records type a proposed
  successor-only fulfillment rule. Graph axes and thresholds retain exact parent byte
  identity; cells and stress manifests require distinct successor identities
  and exact equality of their typed structural-projection digests.
- The rebinding factory reconstructs the seed-free design from an authoritative
  D6 receipt plus the strict parent protocol. Its strict canonical reader
  requires an expected SHA-256, canonical duplicate-free JSON, bounded bytes,
  and whole-document equality with authoritative reconstruction.

### Compatibility and non-migrations

- All affected D7 schemas remain deep internal, unpersisted surfaces.
  There is no `v0.1` artifact migration and no package-root or
  `spirallens.qualification` re-export.
- The D6 v0.1 decision, embedded admission, cells, and stress bytes are not
  modified or reinterpreted. Exact parent cells/stress satisfaction and
  `d6_admission_spec_satisfied` remain false; the new rule applies only to a
  future D7 successor.
- The rebinding rule is explicitly encoded but unreviewed, unpublished, and
  ineffective for admission. Construction-diversity review,
  source closure, the D7 implementation registry and aggregation application,
  family admission, full-design freeze, official seeds, lifecycle,
  result/failure and terminal schemas, D7, and D8 remain absent, false, or
  `not_run`.
- The next sequence is C1 stable design and reviewed rebinding artifacts plus
  the complete executable source set, then a choice-free C2 closure receipt
  from a clean descendant. C1 contains no self-referential source receipt.
  Lifecycle and terminal work
  follow later; the immutable replay target and attempt envelope will be
  separate types rather than a placeholder result.

## 2026-07-30 — PR #13 seed-free D7 execution topology

### Added

- `spirallens.spectral-moment-confirmation-spec.v0.2` requires explicit seed,
  state-warp, and observation-perturbation values. The spectral states use
  ambient-dimension root normalization; the warp changes states only; the
  deterministic perturbation reuses the D6 nuisance operator and changes
  observations only. Prerequisite units record requested and effective
  perturbation values separately.
- `spirallens.spectral-moment-prepared-case.v0.1` and
  `spirallens.spectral-moment-prepared-bundle.v0.1` are in-memory,
  development-only inputs that construct no oracle-truth record and expose
  label-free estimator arrays to the numerical estimator path. The surrounding
  synthetic-control orchestration retains case and unit identity and is not
  claimed label-blind.
- The now-superseded internal
  `spirallens.d7-confirmation-execution-design-draft.v0.1` strictly joined an
  authoritative D6 decision identity to the full canonical parent protocol,
  reproduces every graph/cell/stress/threshold/aggregation body hash, and
  constructs the exact seed-slot inventory of 64 primary, 192 core, and 1,152
  loop cells.
- `spirallens.d7-parent-manifest-compatibility.v0.1` records that the typed
  parent and D7 structural projections match while exact parent cells/stress
  hash satisfaction is false. A reviewed successor admission contract remains
  required.
- `spirallens.d7-development-prediction-inventory.v0.1` is an in-memory,
  claim-ineligible receipt for the complete graph/field/blind-core/continuous
  loop development path. It accepts only permanently excluded development
  seeds and cannot score a gate or publish a result.

### Compatibility and non-migrations

- The spectral implementation version advances from `v0.1` to `v0.2`; the
  current mechanism SHA-256 is
  `3dedf73dab90463025b527a5e7a1265c6c860cf95d59bdd165ede0fbcfb107fb`.
  PR #12 remains the historical foundation milestone; no persisted PR #12
  artifact is rewritten.
- The D6 v0.1 required-cell and required-stress hashes are preserved exactly.
  They are not redefined as structural hashes. Their selection-specific seed
  and identifier content is recorded as an explicit incompatibility, not
  silently migrated.
- The historical internal `v0.1` draft bound the exact authoritative D6
  decision, admission, and validation-time current-loader identities. PR #14
  supersedes that unpersisted draft with `v0.2`; historical terminal companions
  remain verified upstream and their raw bytes remain absent from design
  members.
- The design draft has a strict canonical reader but no publisher. The
  development prediction records have no parser or writer. All new modules
  remain deep internal imports and are not re-exported from
  `spirallens.qualification` or the package root.
- Concrete confirmation seeds, construction-family admission, source closure,
  lifecycle, result/failure schemas, terminal publication, D7/D8 execution,
  global synthetic qualification, representation, integer/topology, semantic,
  Pythia, and subject authority remain absent or false.

## 2026-07-30 — PR #12 D7 construction foundation

### Added

- `spirallens.spectral-moment-confirmation-*` in-memory development records
  generate the exact four D6-required case semantics on one matched 7 by 7
  discrete domain. Estimator-visible arrays and evaluator-only oracle truth are
  separate, and no confirmation seed has a library default.
- The now-superseded internal
  `spirallens.d7-confirmation-foundation.v0.1` was reconstructed only from a
  `LoadedScopeLimitedD6Decision` returned by the authoritative committed-D6
  loader. It bound the D6 decision, embedded admission, loader-source receipt,
  estimator/trivialization IDs, and inherited
  graph/cell/stress/threshold/aggregation hashes.
- The strict foundation reader requires canonical bytes, an expected SHA-256,
  and the same authoritative D6 receipt, then compares the whole document with
  a fresh reconstruction. The four case bindings derive from the generator's
  single canonical case registry.
- The provisional `CartesianFourierEstimatorInputs` type adds
  `from_observable_arrays()`, an owner-provided factory that derives its
  label-free content pseudonym from the exact arrays. Both the Cartesian and
  spectral-moment generators use this boundary instead of duplicating the
  private digest algorithm.

### Compatibility and non-migrations

- The new owner factory is a provisional constructor on an already provisional
  type; it does not mutate existing persisted artifacts or estimator-visible
  array semantics. New source-bound development receipts naturally carry the
  updated source identity.
- The remaining addition is an internal implementation foundation, not a D7
  protocol, design freeze, receipt, admission, runner, result, or replay API.
  It is not exported from `spirallens.qualification` or the package root.
- Same-schema construction-diversity review, committed seed-free source
  closure, exact seed/execution inventory, stress translation, off-core and
  crossed graph/core/loop paths, lifecycle, namespace absence, terminal
  schemas, and atomic publication remain serialized as false.
- D7 and D8 remain `not_run`; global synthetic qualification, representation,
  P0, localized core-loop join, integer/topology, semantic, Pythia, and subject
  authority remain false.

## 2026-07-29 — PR #11 post-D6 analysis separation

### Added

- `spirallens.postselection-descriptive-analysis-plan.v0.1` is a canonical
  research artifact bound to the exact PR #9 terminal and PR #10 D6 decision.
  It declares prior outcome exposure, use of opened outcome values during
  planning, eight mandatory descriptive work packages, fixed 32-unit D2 and
  64-execution D4/D5 grains, including nine graph pairs times two loop roles
  per execution, and `claim_delta=none`; its runner and result remain
  unexecuted.
- `spirallens.d7-structural-gap-matrix.v0.1` is a separate value-blind research
  artifact bound to the D6 contract and the tracked PR #10 source snapshot.
  Its non-promotional vocabulary is `absent`, `contract_only`,
  `implementation_foundation_only`, `evidence_present_but_ineligible`, and
  `blocked`. Existing truth-blind core and label-free loop kernels are recorded
  as implementation foundations only; confirmation-family integration,
  matched support, source closure, and evidence remain missing.

### Compatibility and non-migrations

- Both files are declarations under `protocols/`; no public Python schema,
  reader, writer, runner, arbitrary-mapping validator, D7 admission helper, or
  D8 promotion helper is added.
- The descriptive plan cannot be cited as preregistration and cannot inform D7
  family, threshold, graph, cell, exclusion, estimator, trivialization, or
  stress design. Its runner is blocked until a committed receipt binds the
  complete D7 design, admission, source closure, lifecycle, launch intent,
  exclusive attempt, and absent result namespace. That one receipt is an
  explicit future input class whose repository-relative path, Git blob/commit,
  and SHA-256 must be fixed before execution; D7 result and confirmation values
  remain forbidden.
- The D7 matrix accepts no terminal, Pythia, subject, semantic, SAE, model,
  seed, or confirmation values as inputs. Its value-blindness is an input
  policy, not a claim that its operator lacked prior outcome exposure. It names
  no candidate and exposes no percentage, score, or partial-pass state.
- PR #9, PR #10, Pythia engineering protocol/receipt, and all existing public
  API bytes remain unchanged. D7/D8, global synthetic qualification, P0,
  representation, core-loop join, integer/topology, semantic, Pythia, and
  subject authority remain false or `not_run`.

## 2026-07-29 — PR #10 D6 independent-family admission boundary

### Added

- `spirallens.d6-selection-terminal-binding.v0.1` binds the exact official
  D0-D5 protocol, freeze, claim, launch authorization, terminal manifest,
  consumption, result, evidence root, all-pass gate scopes, and locked
  graph/cell/stress/threshold/aggregation identities. It is an archival
  historical binding and explicitly records
  `current_engine_reexecution_verified=false`.
- `spirallens.independent-confirmation-admission.v0.1` freezes the
  Cartesian-surrogate-only profile and the requirements for a future distinct
  mathematical construction family. Same-family seed changes, source or
  implementation relabeling, policy overrides, post-selection exclusions, and
  selection-evidence reuse cannot satisfy it. The schema is embedded inside
  the decision bundle rather than published through a separate authoritative
  writer.
- `spirallens.surrogate-advancement-decision.v0.1` records a scope-limited D6
  pass while fixing D7 and D8 to `not_run`, global
  `d6_d8_advanced=false`, `synthetic_qualified=false`, and every P0,
  representation, localized-join, integer/topology, semantic, Pythia, and
  subject authority to false.
- `spirallens.advancement-source-binding.v0.1` binds the D6 decision to exact
  Git blobs for the sealing script and the complete tracked
  `src/spirallens/**/*.py` surface at the source commit. It remains source-only,
  not a runtime or transitive native-dependency attestation.
- `load_committed_selection_terminal()` reconstructs the exact historical
  committed-G authorization and H terminal from Git/artifact lineage. The
  historical receipt route is private-token-gated and skips current D1
  recomputation; it records current-engine compatibility and historical
  reexecution as false. The ordinary successor-aware validator retains its
  live-current-source semantics.
- `publish_scope_limited_d6_decision()` produces a validated but
  `committed_artifact_verified=false` candidate; only
  `load_scope_limited_d6_decision()` after a clean tracked descendant commit
  returns the authoritative committed receipt.
- The authoritative decision is recorded at
  `experiments/qualification/d0_d5_f2_cartesian_selection_v0_1/d6-surrogate-advancement-decision.json`
  with canonical SHA-256
  `c1c3fbbb9a06e8df120755dcf159e015636d96993bd6ec3a6792312618587a07`,
  source commit `7673ef81bbd67afce5d20255cc6ca6d68e453c3f`, and first
  artifact commit `1fcff8bfedc7d3ae8386bc409595607b5b57b8c4`.

### Compatibility and non-migrations

- PR #9 protocol, result, terminal, and consumption bytes are unchanged. The
  D6 artifacts refer to them; they do not mutate or reinterpret their fixed
  authority fields.
- The generic instrument `CalibrationSelectionDecision` is unchanged and is
  not used as a type bridge from a qualification result.
- No D7 confirmation, D8 replay, global synthetic qualification,
  representation transfer, P0 winner, subject preparation/execution, semantic,
  integer, or topology schema is promoted by this entry.
- No label/self-attestation D7 validator or caller-byte-only D8 validator is
  exported. Those surfaces require future typed evidence and execution
  receipts.

## 2026-07-29 — PR #9 D0-D5 engine hardening

### Changed

- Graph constructor implementation identity advanced to v0.2. Euclidean
  coordinate magnitudes are now stably sorted before the fixed float64
  `hypot` reduction, making distances and graph receipts bit-identical under
  signed coordinate permutations while retaining deterministic
  vertex-identity tie breaking.
- The graph metric, edge-weight, tie-policy, and implementation IDs now name
  that canonical-coordinate-order rule. Existing PR #8 in-memory receipts
  remain historical v0.1 identities and are not silently reinterpreted.
- The D3 pipeline execution receipt advances to v0.3. Representation D3 now
  records two complete base/transformed field executions, all nine matched
  A-by-B blind-loop cells, 27 reference-rotation, reference-reflection, and
  loop-reversal estimator reruns, and 45 sealed loop predictions. Each
  crossed cell retains the O(2) alignment matrix and determinant and
  mechanically revalidates the determinant-aware signed-total law.
- The representation field estimate adds two read-only generic crossed-pipeline
  binding properties. Its serialized receipt and fingerprint are unchanged.
- The qualification protocol advances to v0.8 with mandatory gate-specific
  positive claim scopes and a derived repeated-measures design. The closed
  design records two declared seed blocks, four matched controls, eight paired
  stress variants per block/control, 64 execution variants, and 32
  boundary-collapsed D2 scientific input units. It also records
  `seed_block_independence_proved=false`,
  `execution_variants_are_independent_replicates=false`, and
  `inferential_sample_size_claimed=false`.
- The canonical numeric stress IDs are now `state-geometry-warp` and
  `structured-observation-perturbation`. The former is a deterministic
  fixed-grid state-coordinate warp rather than sample density; the latter is a
  deterministic seeded cosine observation term rather than stochastic noise.
- D2 requires complete central/wide boundary pairs and exact identity-free
  estimator-input fingerprint and core-observation agreement before collapsing
  them for gate counts. The 64 execution variants and all loop evidence remain
  stored; D2 counts 32 unique scientific input units, while D4/D5 retain 64
  loop variants.
- The qualification result advances to v0.9. Every `GateResult` now persists
  its mandatory positive claim scope: D0 engine/protocol contracts; D1/D3
  Cartesian surrogate plus representation development checks; D2/D4/D5
  Cartesian surrogate only. Every core execution summary also persists the
  boundary- and execution-ID-free D2 scientific-input fingerprint used by the
  boundary-repeat equality gate.
- The qualification protocol also retains the exact, selection-seed-
  free D2-only confounder registry and
  `core_graph_mode=inherit_field_estimation_graph`. The core prerequisite
  policy advances to v0.5 and the closed localizer identity advances to v0.3:
  localized same-section low amplitude alone defines a core candidate.
  Identifiability, coherence, and support instead qualify measurements on
  non-core support, while candidate-site degree support is checked
  independently.
- The protocol authority boundary now explicitly denies P0 competitor
  selection, representation D2-D5 transfer, localized core-loop joining, and
  synthetic qualification. The qualification result persists the corresponding
  `p0_winner_selected=false`,
  `representation_d2_d5_qualified=false`, and
  `localized_core_loop_join_established=false` facts.
- The qualification evidence bundle advances to v0.4; the D2 confounder cell
  and matrix receipts advance to v0.2 with probe-row terminology. The typed
  two-by-A matrix records that no selection seed, oracle scorer, or joint loop
  registry was consumed. Its high-amplitude local-identifiability-loss decoy
  must be evaluable `no_core`, and the low-amplitude missing-candidate-support
  point must abstain with its exact frozen reason.
- D1 metric validation now uses a closed family/metric mapping from each
  metric to its exact comparator and frozen protocol threshold field. Every
  attempted result validation reruns both fixed-development-seed D1 families
  under the current source-bound engine and requires exact canonical-byte
  equality with the persisted receipts. The D1 receipt schemas and serialized
  fields are unchanged; this is stricter validation of existing bytes.
- The source-binding receipt advances to v0.3 and explicitly records that in-process
  callable identity, Python/native runtime attestation, and hostile-local-
  mutation resistance are false. Its transitive local-import closure includes
  package initializers and rejects unsupported dynamic import primitives.
- The event-ledger receipt is v0.4 and the result field is
  `posthoc_logical_dependency_manifest_validated`. The digest chain is a
  source-enforced, post-score logical dependency reconstruction, not a
  real-time, durable, or independently observed event log.
- Selection freeze advances to v0.3, the attempt claim advances to v0.3, and
  the launch descriptor advances to v0.3. They bind a canonical, no-overwrite
  pre-seed readiness artifact that the official process publishes and
  strictly reloads before invoking its seed supplier. The artifact records
  `chronology_claim=official-process-attested` while cryptographic and
  human/external-process unseen proofs remain false.
- `spirallens.prepared-selection-launch-intent.v0.1` is published and strictly
  reloaded after all F preconditions pass and before the attempt claim is
  acquired. Raw claims without that earlier exact intent are rejected;
  crash-gap recovery accepts only the same canonical intent and claim after
  complete revalidation.
- `spirallens.selection-launch-authorization.v0.1` is an in-memory capability
  derived only when the descriptor, store freeze, launch intent, and claim are
  exact clean tracked blobs at one unchanged G HEAD. The official runner
  repeats that four-artifact and HEAD check before execution start. The exact
  three official prepare/launch/run scripts remain part of the engine-bound
  executable closure and successor verification.
- `spirallens.selection-execution-start.v0.2` persists the exact launch-
  authorization digest and its authorized G HEAD. The official start writer
  accepts the typed capability rather than a caller-supplied digest and
  revalidates all committed-G companions immediately before the exclusive
  transition. Custom/development starts require both fields to be null.
- `spirallens.qualification-result.v0.10`, its evidence root v0.3, and runner
  v0.4 bind that authorization digest into result identity and canonical
  evidence. `spirallens.selection-failed-attempt.v0.2` binds the same digest
  for ordinary after-start failures. Official result and failure terminal
  publication and reload require the digest to equal the persisted execution
  start.
- Generic standalone qualification-result write/load remains available for
  custom/development protocols only, with null authorization. It now rejects
  the official closed D0-D5 protocol ID, whose only admissible persistence
  boundary is the atomic terminal transaction. Provisional constructors may
  still form non-authoritative in-memory records; this change scopes authority
  to validated persisted artifacts rather than object construction.
- Without another serialized schema bump, official execution-start loading,
  terminal publication, and terminal reload now require the typed launch
  authorization rather than trusting a digest copied from stored artifacts.
  Successor-aware validation proves
  `engine commit -> authorized G -> current HEAD`, exact equality of the four G
  blobs at authorized/current commits and the clean worktree, and absence of
  the freeze-keyed start/terminal paths from the authorized G tree. Custom and
  development chronology keeps both loaded protocol and authorization null.
- After-start ordinary failures strictly reload the typed failed terminal
  transaction before re-raising the unchanged original exception.
  `spirallens.orchestrated-terminal-publication-receipt.v0.1` also covers a
  result or failed terminal that became visible before a final
  parent-directory fsync raised. It records terminal kind and identity,
  strict round-trip status, publication-return status, parent-fsync proof, and
  permanently false retry authority.
- Selection consumption remains v0.2. The label-independent
  `spirallens.selection-attempt-key.v0.1` binds protocol, engine, selection
  manifest, and seed-family size to one store-local freeze/claim/start/
  terminal namespace. Result-or-failure publication uses a typed terminal
  manifest and an exclusive no-replace directory transition on supported
  Darwin/Linux hosts.
- Terminal result publication and reload now use successor-aware source
  validation. The verifier proves
  `engine.commit -> stored execution HEAD -> current HEAD`, checks every
  module, official executable, registry, and referent blob at the execution
  HEAD, repeats current live source verification, reconstructs the exact
  historical receipt, and requires the existing summary-to-receipt canonical
  digest equality. No source receipt or result field is dropped or
  reinterpreted; this closes the engine-commit → execution →
  artifact-commit lifecycle without accepting sibling histories, historical
  blob mismatches, or current path drift.

### Compatibility and claim boundary

- This is an implementation-identity change inside the model-free graph
  and qualification foundation. The D3 records remain fixed-development-seed,
  oracle-free Level-0 calibration evidence. They do not grant topology,
  subject, semantic, SAE, causal, or integer authority.
- The D1 rerun does not read selection seeds and is not cryptographic proof of
  source integrity or an independent/native-runtime attestation.
- D2 emits only a Level-0 localized zero/core candidate. It does not prove a
  vortex, topology, charge quantization, or a core-loop join.
- Cartesian D2-D5 does not transfer to or select the representation estimator;
  the fixed-seed representation D1/D3 checks establish only their declared
  construct and transformation obligations.
- Successor verification remains source-only Level-0 evidence. It does not
  attest in-process callables, Python/native runtime state, or hostile local
  mutation resistance.

## 2026-07-29 — PR #8 graph and discrete-domain foundation

### Added

- Provisional `spirallens.graphs` in-memory fingerprints for one exact
  numerical input, three graph specifications and construction receipts,
  pairwise structural-diversity measurements, an oriented triangular
  `DiscreteDomainComplex`, a declared face-support boundary, and exact graph
  refinement of that boundary.
- Exhaustive rounded-float64 mutual-kNN, inclusive fixed-radius, and
  all-unordered-pair shared-neighbor constructors with deterministic
  tie/order rules, immutable array backing, derived structural audits,
  arithmetic-collapse rejection, and conservative pre-allocation resource
  limits.
- Exact integer boundary matrices and the finite-chain identity
  `boundary_1 @ boundary_2 == 0`.

### Compatibility and claim boundary

- Every new versioned mapping declares
  `record_scope=in-memory-fingerprint-only` and
  `persistence_round_trip_supported=false`. No parser, loader, writer, or
  payload-backed persistence schema is introduced.
- Existing P1 graph artifacts and their empty, unconstructed cycle-support
  field are not reinterpreted or migrated. The P1 producer/protocol and frozen
  Pythia protocol/receipt remain byte-identical.
- `same-induced-support-boundary` means exact refinement of one supplied
  combinatorial boundary only. It is not generic homology, homotopy,
  continuous topology, latent-manifold triangulation, a core, winding, or
  charge.
- The API accepts no field/core/loop observable, but it does not verify the
  caller's support/rule selection history or a pre-observation seal.
  Cross-family matches establish common-boundary availability only, not D4
  graph-family cycle invariance.
- Graph diversity is measured without a threshold or gate result. Graph cells
  are repeated measurements of one primary unit, not independent statistical
  replicates.
- No field, core, holonomy, winding, semantic, subject, Level 2T, or D0-D8
  state is read or promoted.

## 2026-07-29 — PR #7 referent and numeric foundation

### Added

- `spirallens.referent-contract-set.v0.1`: canonical, registry-bound F0-F4
  pointwise referents, same-object rules, transformation formula identities,
  explicit unbound-field/interpolation state, ceilings, qualifiers, and
  non-claims.
- `spirallens.value-access-lineage.v0.1`: trusted-parent-bound, exact
  one-consumer value-decoding policy derivation.
- `spirallens.synthetic-generator-family-identity.v0.1`: mathematical
  construction-family identity separated from seed, implementation, and source
  digest.
- Provisional in-memory spectral-moment phantom/spec, estimator-input,
  oracle-truth, and case fingerprints: model-free F2/F4 development controls
  with fit/evaluation and truth/input separation, spec-derived canonical-case
  binding, harmonic resolvability/recovery and derived-arithmetic safety gates,
  and a conservative pre-allocation resource gate.
- `spirallens.observation-partition-receipt.v0.1`: an in-memory identity
  fingerprint with immutable array backing. It is not a persistence schema or
  parser contract.

The spectral and partition records' versioned `to_dict()` forms are content
fingerprints, not persistence schemas or parser contracts.

The persisted schemas are provisional. The tracked registry maps to
referent-contract digest
`4108ccda4f2a76920091bf2bf422b97297fe4d91ee54f14e2b03362e53e358f2`.

### Value-consumer boundary

- `load_instrument_bundle()` remains value-opaque. It exposes manifest relative
  paths and source-root metadata, but retains no payload descriptor and returns
  no payload bytes or decoded arrays; path secrecy is not the boundary.
- `open_numeric_payload_session()` is a separate lineage-gated API. It retains
  only requested descriptors from the same secure validation transaction and
  validates strict NPY, content row identity, and closed numeric relations.
  Decoded arrays use immutable `bytes` backing, so callers cannot re-enable
  their write flag.

### Compatibility and non-migrations

- Existing instrument artifact and bundle schema bytes and structural fields
  are unchanged.
- The closed `AtlasConsumer` vocabulary gains the compatible
  `numeric_payload_validation` value. Existing serialized policies keep their
  canonical bytes; this is an accepted-vocabulary extension, not a migration
  of stored records.
- The tracked P1 representation-phantom protocol and generator source are
  unchanged; the spectral-moment family is a separate foundation rather than a
  migration of that bundle.
- The frozen Pythia-70M engineering protocol and receipt remain byte-identical.
- No graph, domain, cycle, core, winding, D0-D8, subject, semantic, SAE, causal,
  or topology schema is promoted by this entry.

## 2026-07-29 — PR #6 boundary foundation

### Added

- `spirallens.atlas-preparation-descriptor.v0.1`: canonical,
  pre-observation-only protocol, model, context, row-domain, capture, access,
  attempt, and interpretation declarations.
- `spirallens.atlas-preparation-view.v0.1`: descriptor-only preparation result
  with explicit no-manifest, no-payload, and no-execution facts.
- `spirallens.execution-attempt-terminal.v0.1`: terminal execution
  classification, access facts, quarantine disposition, and restricted
  provenance policy.

All three schemas are provisional.

### Internal diagnostic output

- `spirallens.distribution-validation.v0.2` labels the ephemeral JSON emitted
  by the repository-only wheel validator. It retains the dependency-free
  core/access probe and adds a second fresh-environment installed-wheel import
  of the dependency-bearing `spirallens.qualification` public surface. Host
  system/user site packages may supply numerical dependencies for that second
  probe; the SpiralLens module itself must still resolve from the exact
  non-editable wheel. It is not a public persistence schema or Python API, and
  no downstream artifact may bind it as evidence.

### Compatibility

- Canonical JSON primitives moved to the stable-candidate
  `spirallens.core.canonical` namespace.
- `spirallens.instrument_contracts.canonical` remains a compatibility
  re-export. Existing import paths and canonical bytes are unchanged.
- The frozen Pythia-70M public-example engineering protocol and receipt remain
  byte-identical. Their consumer gate now delegates to the generic typed
  access policy while preserving the historical string call sites.

### Non-migrations

- Existing atlas manifests are not preparation descriptors and must not be
  converted into them after observation.
- The historical neighbor `--prepare-only` flow remains a retrieval preflight,
  not subject protocol preparation.
- No D0-D8, subject, graph, referent, semantic, SAE, causal, or topological
  schema is promoted by this entry.
