# Schema and Compatibility Change Record

SpiralLens records public and provisional persistence changes separately from
scientific results. Entries describe software contracts only; they do not
promote a claim.

## 2026-08-13 — Atlas reader/capture import-boundary split

- Moved mutable Atlas capture storage into private `_capture_store.py`; the
  manifest readers remain in `atlas.store`. The independent production reader
  consumers are `metrics.candidate_pairs` and `atlas.engineering_receipt`.
- The reader closure continues to permit NumPy and PyYAML. A fresh
  non-editable-wheel probe verifies that it loads none of `torch`,
  `transformers`, `huggingface_hub`, `safetensors`, `spirallens.adapters`,
  `spirallens.atlas.id_sweep`, `spirallens.atlas.engineering_run`, or
  `spirallens.atlas._capture_store`. Capture remains a model extra, and the
  whole Atlas namespace remains provisional/model extra.
- Against baseline commit `a1d6c615da9e39247afa0332658e9aee7b24bb5a`,
  `store.py` / `_capture_store.py` / `id_sweep.py` / `__init__.py` change from
  `1226/0/589/57` to `760/492/590/78` physical lines, or `1872 → 1920`
  (`+48`); the reader store loses 466 lines. Acceptance is based on the empty
  reader forbidden-import set rather than total-LOC reduction. The ordered
  20-name public `__all__`, symbol identities, reader signatures and defining modules,
  exception identities, exports, and dependencies are unchanged.
- The repository-only ephemeral distribution report advances to
  `spirallens.distribution-validation.v0.4` and adds
  `atlas_reader_inspection` for this installed-wheel boundary. This introduces
  no public persistence schema, artifact or protocol change, scientific or
  library promotion, authority or claim delta, D7/D8/SCI progress, or VOY-V4
  authorization.

## 2026-08-13 — Private bounded held-file reader extraction

- Replaced the duplicated held-file byte-reading bodies in
  `access.descriptor` and `referents.loader` with one private,
  standard-library-only primitive. Against baseline commit
  `be274333e77d7518cb21ddb6afda3d62222e4b6c`, the three-file production scope
  changes from `0/517/179` to `85/457/105` physical lines, or `696 → 647`
  (`-49`, 25.8 percent of the audited 190 duplicated lines), with no added
  export or dependency.
- The distribution validator now requires that private module as a wheel
  member and directly verifies its import origin from the non-editable wheel.
  The bounded two-prefix repository-experiment classification is unchanged.
- Exact wrapper-level equivalence remains frozen: path/digest preprocessing
  order, returned bytes, domain exception type/message, direct OS
  cause/context, policy no-cause/context, and held-descriptor cleanup order are
  unchanged. Parsing, digest validation, read traces, and domain meaning stay
  outside the primitive.
- The extraction preserves rather than removes the existing limits: it is
  POSIX `dir_fd`-oriented, uses `O_NOFOLLOW` only when available, can block on
  a FIFO before rejecting it as non-regular, and does not turn bounded
  before/after metadata checks into a complete hostile-race or TOCTOU proof.
  No public API, persistence schema, artifact, protocol, D7/Pythia operation,
  claim, authority, library-maturity, or VOY-V4 authorization changes in this
  entry.

## 2026-08-13 — LIB-L0 distribution-boundary inventory

- `spirallens.distribution-validation.v0.3` extends the repository-only,
  ephemeral wheel diagnostic with a bounded two-prefix wheel-membership
  observation.
  Valid build/install status remains distinct from the blocked fact that the
  current wheel contains repository-experiment modules. The report adds no
  public persistence schema or Python API and grants no scientific,
  experiment, VOY, or library authority.
- Recorded the previously implicit v1 packaging fact: current setuptools
  discovery physically includes all 20 D7 v1 `confirmation_v1_*` modules and
  both private Pythia-160M kernels. They remain internal/non-exported, but
  physical wheel separation is an open `LIB-L0` blocker. The distinct three
  v0.1 `experiments/.../post_d6_code` files remain correctly excluded.
- Added a non-authoritative extraction inventory with actual consumer pairs,
  input/failure-equivalence stop conditions, production/export deltas, and the
  explicit rule that artifacts, docs, tests, scripts, and one experiment
  chronology do not count as independent library consumers.
- No package export, dependency, artifact byte, protocol, route, D7/Pythia
  operation, claim, or authority field changes in this entry.

## 2026-08-13 — D7 v1 structural materialization and descriptive-result observation

- Recorded the already-persisted exact S → A → B chronology: source
  `a9b9da21954478e42982e27f9e6b02cbeba5a08d`, nine-file commit A
  `be4462c3eee666aff620292b1494cc4209a0c6a6`, and result-only commit B
  `9735ae8b231f5b6e967a4b7dbaed0fb2eca78061`. This entry changes no artifact,
  protocol, or route bytes.
- The 5,308,075-byte result has SHA-256
  `409d211fac2db52a88facaa79a526903379545af7b1619a8c50ee4820358d109`,
  status `insufficient`, 26 available outputs, and one blocked output caused by
  unpersisted historical main-D2 scalar values. The attempt remains
  `reserved_not_started`; reconstruction and rerun remain unauthorized.
- This docs-only projection records **VOY-V3 purpose evidence observed**. It
  grants no VOY completion credit, `D7-OPS` credit, VOY-V4 authorization,
  D7/D8/SCI progress, scientific result, or library promotion. Every authority
  fact remains false, claim ceiling remains Level 0, and claim delta is `none`.
- No supported schema, public API, CLI, dependency, or library-maturity
  change accompanies this observation. The frozen `frozen_not_run` field is
  retained as issue-time history, and any future route bend requires a new
  version and dated pre-consumption review.

## 2026-08-13 — Review-pending Pythia-160M identity candidate

- Invoked the private metadata/config-only acquisition exactly once from clean,
  merged source commit `fb640788d3c036cb86127ed9d32d28d27c1e2aa9` and
  tracked the resulting closed four-file `pythia160-v0.1` directory without
  rewriting its generated bytes. The operation completed without retry and
  left no stage.
- The canonical receipt resolves provider revision
  `50f5173d932e8e61f858120bcb800b97af589f46`, verifies the default-to-exact
  revision join, and joins the 569-byte config (SHA-256
  `76eb275107220e450d31258f792a2efcbee109d8b62ae0088260057dec06362f`)
  to provider Git blob `b8368ff94f3bcf3088de5e9912251fc0208ae524`.
  The receipt SHA-256 is
  `367867e45744f39ff285da84b4b2e619997d582b7c10a2df2cb91e40e75d5911`.
- This candidate is `review_pending`, not an identity or profile approval.
  Provider sibling facts remain unrecomputed; weights, tokenizer bytes, cache,
  model, forward, and activations were not accessed. All 14 authority facts,
  including VOY credit, remain false; claim ceiling is Level 0 and claim delta
  is none. `SCI-S1` is not satisfied and `SCI-S2` remains blocked.
- The acquisition used the explicit fixed-bundle TLS preflight, but the receipt
  does not persist the CA-bundle digest and therefore does not attest exact
  transport-trust bytes. No schema, public API, CLI, profile registry, route,
  protocol, dependency, or library promotion accompanies this evidence.

## 2026-08-13 — Private Pythia-160M TLS trust preflight

- Corrected the source-only identity-acquisition path after the exact isolated
  Python 3.13 runtime was found to construct an empty default certificate
  store. The unregistered script now builds one explicit TLS client context
  from the fixed honest-local macOS bundle at `/private/etc/ssl/cert.pem`.
- The preflight resolves every bundle path component without symlinks, accepts
  only one bounded, root-owned regular file with no group or world write bit,
  rechecks its held identity and metadata around the read, and loads its ASCII
  PEM bytes as explicit `cadata`. It requires certificate verification,
  hostname checking, TLS 1.2 or newer, and at least one CA certificate. The
  resulting context is constructed before durable stage reservation and the
  same object is supplied through an explicit HTTPS handler to all three
  bounded provider requests; no implicit default HTTPS trust handler is used.
  Ambient OpenSSL configuration, provider-module, and engine environment is
  rejected before TLS initialization.
- This is a source and synthetic-test correction only. The live capture main
  is not invoked, no provider request or model/config acquisition occurs, and
  no provider-backed/acquired or persisted receipt or output is created. It
  adds no evidence, access fact, review completion, preparation, execution,
  capture, D0-D8, VOY, `SCI-S1`, `SCI-S2`, or scientific authority.
- The CA-bundle digest is deliberately not added to the v0.1 identity receipt:
  the bundle is an operational transport-trust input, not model-identity or
  content evidence, and the receipt therefore does not attest its exact bytes.
  No receipt schema changes. A future PR62 may invoke only the separately
  reviewed, merged source and must preserve that limitation when reviewing any
  provider-backed candidate.

## 2026-08-13 — Private Pythia-160M identity-acquisition source

- Added a private, framework-neutral receipt kernel and an unregistered,
  zero-argument capture script for a later review of provider model metadata
  and exact `config.json` bytes. The source contract resolves the provider's
  default revision once, rejoins an exact-revision metadata response, records
  a sorted provider-reported sibling manifest, and joins the retrieved config
  bytes to the provider-reported non-LFS Git blob identity and byte count.
- The future script is fail-closed on an exact clean HEAD equal to the local
  `origin/main` tracking candidate, fixed repository and HTTPS routes, ambient
  credentials and proxies, bounded strict JSON, and no-replace publication.
  That local tracking equality does not prove that the remote is current or
  that the commit has been independently reviewed. The script authenticates
  and manually executes the committed private kernel bytes, retains both
  default and exact provider responses, writes the receipt last in a private
  stage, and atomically publishes the closed four-file directory. It durably
  reserves that empty stage before the first provider request; every later
  failure retains it and authorizes neither cleanup, resume, nor retry.
- This PR adds source and synthetic tests only. Live acquisition has only been
  exercised through blocked preflight; no provider request, network, Hugging
  Face, config, cache, tokenizer, weight, model, forward, activation, subject,
  or runtime-resource access occurs. Synthetic in-memory receipt candidates
  are tested, but no provider-backed or persisted receipt and no output
  directory is created. A later, separately reviewed operation must bind an
  exact selected source commit before any metadata request.
- The publication contract is honest and quiescent-local, not a security
  boundary against a hostile same-user process racing the final native
  directory rename. Held parent, stage, and file descriptors detect namespace
  or content drift before and after publication; detected ambiguity remains a
  terminal, non-retryable failure and grants no authority.
- The private receipt remains `review_pending`. Provider sibling facts are
  explicitly unrecomputed, config content does not establish a reviewed model
  profile, and every model, subject, execution, capture, D0-D8, VOY, and
  scientific authority remains false. Claim ceiling is `level_0`, claim delta
  is `none`, `SCI-S1` remains in progress, and `SCI-S2` remains blocked. No
  public API, CLI registration, dependency, model-profile registration, or
  supported schema is added.

## 2026-08-13 — Offline Pythia adapter mechanism hardening

- Hardened the current `PythiaAdapter.observe_batch` implementation so every
  selected-position residual capture is an owned, synchronous CPU/float32
  snapshot and every pre-existing per-module train/eval flag is restored
  exactly after both successful and failed observation.
- Added a deterministic offline fake-NeoX mechanism-conformance surface. It
  checks bit-identical baseline logits; unchanged parameters, buffers, tensor
  version counters, and absent gradients; inference/eval execution with
  `use_cache=false`; exact selected-position pre/post captures; preservation of
  pre-existing hooks; cleanup on success and failure; and fail-closed malformed
  layer/output behavior. These checks exercise only the fake structural surface
  and do not establish parity or compatibility with any real Pythia model.
- Advanced the current capture implementation identifier from residual-hooks
  v1 to v2. An incomplete v1 atlas cannot resume under v2 and no migration is
  performed. Completed v1 artifacts and the tracked Pythia-70M v0.1 receipt
  remain historical and readable under their frozen contract.
- No real model, tokenizer, Hub, cache, network, or subject value is accessed,
  and no persistent activation output, atlas, protocol instance, or receipt is
  created. The private engineering profile registry remains Pythia-70M-only,
  and the private Pythia-160M pre-observation declaration remains at its
  unchanged v1/not-run
  capture declaration; its assessment still records adapter parity and zero
  intervention as unverified/not run. `SCI-S1` remains in progress, `SCI-S2`
  remains blocked, and claim delta is `none`.
- The frozen Pythia-70M v0.1 protocol and receipt bytes remain unchanged and
  historical. Because that protocol binds its earlier adapter source, it does
  not authenticate this hardened implementation and is not made rerunnable by
  this change; any future model access requires a separately reviewed successor
  protocol. No new public API symbol or signature, schema, CLI, dependency,
  model-profile registration, or scientific/library milestone is introduced.

## 2026-08-13 — Private Pythia-160M pre-observation assessment source

- Added one internal, non-exported, framework-neutral declaration validator and
  static resource assessor for the historically intended Pythia-160M
  workstream. It accepts only caller-declared, explicitly unverified model
  identity, file, profile, capture, and resource-budget fields; this change
  ships no declaration or assessment instance and verifies none of those
  declarations against a model repository, cache, runtime, or host.
- The assessor performs closed integer arithmetic over the declared sizes and
  dimensions and can only return `blocked_external_prerequisites`. Physical
  memory, free disk, OOM safety, model identity, file bytes, adapter parity,
  independent context banks, instrument qualification, the terminal
  `SCI-S1` transition, and an external witness all remain unobserved or
  unverified. Every model, subject, execution, capture, and scientific
  authority remains false; claim ceiling is `level_0` and claim delta is
  `none`.
- The internal identifiers
  `spirallens.pythia160-preobservation-declaration.v0.1` and
  `spirallens.pythia160-preobservation-assessment.v0.1` are private,
  nonpersisted, and unsupported. They add no loader, writer, CLI, public API,
  schema registry entry, dependency, protocol, receipt, model-profile
  registration, or library/scientific milestone. No network, Hugging Face,
  model-file, tokenizer, forward, activation, atlas, payload, output, or
  receipt access occurs. `SCI-S1` remains in progress, `SCI-S2` remains
  blocked, and no Pythia-160M run or subject preparation begins.

## 2026-08-13 — Private D7 v1 pre-item-23 chronology source

- Added one internal, non-exported, uninvoked operation that accepts only a
  repository and asserted exact source commit, derives every record and fixed
  coordinate internally, makes the external claim durable before one captured
  fixed-supplier entry, makes the attempt durable, promotes and reverifies the
  exact two-file external store without replacement, forms the chronology
  receipt last, passes the joined hard gate, and delegates the exact nine-file
  repository publication to the existing private publisher. Failure never
  authorizes cleanup, resume, or retry.
- Extended that private publisher only with a sealed, factory-produced held-FD
  capability for the exact frozen external paths. It accepts no arbitrary
  reader, reauthenticates the full parent/store/child/file identity through all
  joined gates, and lets composite failures preserve facts for both namespaces.
- The preparation entrypoint remains deliberately unwired and fail-closed. The
  operation's commit argument does not attest independent source review,
  source selection, runtime/dependency closure, or invocation authority.
- No instance was created and no schema, protocol, route, structural record,
  public API, dependency, or library milestone changed. No C1/C2, claim,
  supplier invocation, seed, attempt, store, receipt, repository publication,
  commit A/B, execution, result, or scientific evidence exists. Claim delta is
  `none`; S remains unreviewed and unselected, VOY-V3 remains
  `frozen_not_run`, and D7/D8 remain `not_run`.

## 2026-08-13 — Private Pythia-70M engineering model profile

- Consolidated the existing exact Pythia-70M public-example identity,
  dimensions, parameter count, tensor count, and model-file set in one private,
  immutable model-profile seam inside the existing protocol implementation,
  shared by the protocol, runner, and receipt. No new executable source module
  or source-trust root is introduced; Python runtime and bytecode-cache
  authentication remain outside this refactor and are not claimed.
- The registry still contains only Pythia-70M. Pythia-160M remains
  unregistered and is rejected before model-file or ContextBank resolution,
  model loading, or output creation. This refactor does not create a readiness
  artifact, authorize model access, or begin a Pythia-160M run.
- The frozen Pythia-70M protocol and receipt bytes, public API, CLI, schemas,
  dependencies, capture implementation, authorizations, and `not_run` states
  are unchanged. `SCI-S1` remains in progress, `SCI-S2` remains blocked, and
  claim delta is `none`.

## 2026-08-12 — D7 v1 private referent-document work-package split

- Split the 2,108-line private full-design-referent module into a 721-line pure
  canonical-document kernel and a 1,808-line provenance facade. The leaf owns
  no Git or filesystem I/O and is joined to its import origin, live bytes,
  source-S blob, and C1 member before use.
- This internal refactor preserves referent semantics and provenance and
  authority boundaries. It creates no chronology fact, record, schema,
  protocol or route revision, public API, dependency, or library milestone.
  Claim delta is `none`; S remains unreviewed and unselected, VOY-V3 remains
  `frozen_not_run`, and D7/D8 remain `not_run`.

## 2026-08-12 — D7 v1 private virtual full-design referents

- Added one internal, non-exported source-derived layer that reads exactly five
  permitted pinned scientific parents, typed-rebuilds and cross-joins them,
  calls the approved seed-free execution-design builder exactly once, and
  derives six canonical virtual referents for confirmation family, non-issued
  admission, unfrozen protocol, Git source-member graph, graph/case/stress
  aggregation, and prospective lifecycle.
- The aggregation fixes 64 primary units, 192 core cells, 1,152 loop cells,
  and six strata. The lifecycle embeds the frozen protocol's exact 19-stage,
  three-commit future chronology. The joined materialization verifier
  independently rederives and exact-compares all six bindings.
- The virtual documents are private, in-memory, and nonpersisted. Their
  internal v0.1 identifiers add no persisted or supported schema and do not
  revise the frozen protocol, route, structural records, public API, or
  dependencies. External-binding and runtime authentication, runtime
  dependency-closure verification, family admission, official full-design
  creation/freeze, aggregation review/application, lifecycle instantiation,
  official coordinates, claim, supplier invocation, seed, persistence,
  execution, result, and scientific authority remain false. Claim delta is
  `none`; S remains unselected, VOY-V3 remains `frozen_not_run`, and D7/D8
  remain `not_run`.

## 2026-08-12 — D7 v1 source-selected supplier candidate

- Added one internal, non-exported source-selected supplier candidate with a
  fixed zero-argument module-global OS-CSPRNG callable, canonical identity
  bytes, and a canonical combined exclusion registry covering two predecessor,
  two parent-selection, and four development seeds.
- The joined-loader path now independently rederives the supplier ID and
  identity binding and constrains a future seed inventory to exactly two
  unique ascending signed-int64 values outside all eight exclusions. The
  supplier is not invoked and no seed value or record is created by this
  change.
- At this increment the six non-inventory full-design bindings remained
  unresolved and unauthenticated. It added no persisted or supported schema,
  protocol or route revision, public API, dependency, console script,
  artifact, authority, library maturity, or scientific claim. S remained
  unselected and VOY-V3 remained `frozen_not_run`.

## 2026-08-10 — D7 v1 deterministic-input contract candidate

- Added one internal, non-exported read-only candidate that rebuilds the
  choice-free C1/C2 source candidate and rejoins the supplier-identity role,
  exact two ordered confirmation seed slots, and seven embedded full-design
  field-to-role entries across the frozen v1 protocol, record implementation,
  and approved execution-design source.
- The candidate intentionally contains no supplier identifier, callable,
  identity or binding bytes, seed values, claim, inventory, full design, or
  chronology. Observing count and slot order does not authorize their use in a
  persisted record; at this increment the six non-inventory binding referents
  remained unresolved.
- This adds no persisted or supported schema, protocol or route revision,
  public API, dependency, console script, artifact, authority, library
  maturity, or scientific claim. S remains unselected and VOY-V3 remains
  `frozen_not_run`.

## 2026-08-10 — D7 v1 choice-free source-closure candidate builder

- Added one internal, non-exported source-only builder for prospective C1/C2
  construction. A caller supplies no member list, bytes, record identifier,
  path, writer, or callback; the full commit argument is only an assertion of
  the exact clean current `HEAD`, checked before and after construction.
- The exact inventory is derived from ordinary Git blobs below
  `src/spirallens` plus `pyproject.toml`, the declared D7 runtime lock, frozen
  protocol and route, and required v1 scripts. Existing C1/C2 factories are
  canonically reloaded and rejoined against that complete set.
- The entire frozen v1 repository root must be absent in the asserted current
  tree. This does not attest unique introduction history or artifact chronology;
  those facts remain false until the later commit verifiers.
- This remains an in-memory candidate. Runtime-lock membership does not attest
  installed-runtime conformity, S is not reviewed or selected, and no schema,
  persisted C1/C2 instance, artifact, authority, public API, dependency,
  console script, library maturity, or VOY-V3 status changed.

## 2026-08-10 — D7 v1 descriptive private work-package split

- Replaced the 4,699-line descriptive implementation module with a 287-line
  compatibility facade over eight private D1--D5, independence, and shared
  work packages. The six-input derivation, 27 output identities, validation
  order, and canonical 5,308,075-byte result remain unchanged.
- Extended the internal source-S gate so every helper must independently match
  its repository import origin, live bytes, Git blob at S, and C1 source-member
  tuple. The frozen protocol remains byte-unchanged; the code-level helper
  minimum is a later source provenance requirement.
- This is an uninvoked internal refactor. S remains unselected, VOY-V3 remains
  `frozen_not_run`, and no schema, artifact, authority, public API, dependency,
  console script, or library maturity changed.

## 2026-08-10 — D7 v1 private result-publication primitive

- Added one internal, non-exported source-only primitive for prospective
  stage-17 descriptive-result publication. It accepts no caller result, path,
  or stage; exact commit A and source S are rejoined before the six frozen
  inputs are freshly rederived into the fixed result bytes.
- The primitive uses an owned deterministic private file, file fsync, native
  no-replace rename, publication-parent fsync, and post-publication inode and
  byte reauthentication. Failure authorizes neither cleanup nor retry, and the
  in-memory success observation creates or verifies no result commit B.
- The primitive is uninvoked. No route or persisted schema changed; S remains
  unselected, VOY-V3 remains `frozen_not_run`, and no official artifact,
  result, authority, public API, dependency, console script, or library
  maturity was created.

## 2026-08-10 — D7 v1 descriptive source and blocked entrypoint coordinates

- Added an internal fresh derivation for the frozen post-D6 descriptive result
  shape. Its read surface is limited to the six declared historical bindings;
  it does not consume the predecessor result, its value-bearing source files,
  successor seeds, or confirmation outcomes. Commit-B verification requires
  its byte-exact rederivation and rejects schema-valid substitute outputs.
- Added the declared v1 preparation script, runner, and official-callable
  coordinate. The scripts authenticate import origins and route coordinates;
  all three coordinates fail closed before publication or dispatch because no
  closed external chronology, launch authority, or execution-start transition
  exists.
- No stage-17 result publisher is included. Reviewed source commit S remains
  unselected and source completion is not reached; no official artifact or
  result has been generated, and the claim delta, public API, supported schemas,
  dependencies, and library maturity are unchanged.

## 2026-08-10 — D7 v1 private-stage publication primitive

- Added one internal, non-exported source-only primitive for the prospective
  nine-file D7 v1 repository publication. It creates and retains its own
  deterministic private stage, uses anchored directory descriptors and
  exclusive file creation, fsyncs every member and directory, revalidates the
  closed tree and joined records, and publishes only with the platform's native
  no-replace directory rename followed by publication-parent fsync.
- Failures after stage creation retain their partial evidence. There is no
  cleanup, resume, retry, overwrite, or portable rename fallback; ambiguous
  rename outcomes are classified by the held stage inode rather than by an
  exception alone.
- The returned observation is in memory, structural-only, and explicitly
  carries no authority, materialization authorization, commit-A verification,
  execution eligibility, or scientific claim. The primitive has not been
  invoked, no official coordinate or artifact is created by this source change,
  and no public API, dependency, entrypoint, supported schema, or library
  maturity changes.

## 2026-08-10 — D7 v1 read-only joined verifier

- Added one internal, non-exported verifier for the frozen D7 v1 structural
  protocol. It strictly rejoins an exact supplied nine-file stage and verifies
  the prospective direct-parent artifact commit A and result-only commit B.
- Git verification uses system Git with a minimal non-inherited environment,
  disables replacement refs and lazy fetch, rejects shallow repositories and
  repository-local grafts, applies each role's byte cap before reading its blob,
  and checks exact add-only deltas and unique introductions over full history.
  Imported source modules join both to the repository under verification and
  to their exact blobs at reviewed source commit S; S must descend from the
  frozen protocol's merge.
- No publisher is provided. Publication from a caller-owned validated stage was
  rejected because validation and rename are not one atomic content operation;
  the later materializer must own its private stage and specify durability and
  partial-state behavior.
- This source-only change writes no official path, supplies no seed, creates no
  C1/C2 closure, claim, receipt, artifact, or result, invokes no model or
  producer, and changes no public API, supported-schema status, scientific
  claim, or library maturity.

## 2026-08-10 — D7 v1 structural records and pre-item-23 materialization contract

- Added the 43,288-byte canonical
  `spirallens.d7-v1-pre-item23-materialization-protocol.v0.1` planning record,
  SHA-256
  `13d013e007fa30775abb4cd092b264482207dcad23f772aecd966a51cbafbaad`.
  It closes 11 primary schema roles across nine co-published pre-item-23 files
  plus a later descriptive result; the embedded full design has one canonical
  subdocument shape and is not a second file.
- Added one internal, non-exported record kernel for those structural shapes.
  It retains canonical bytes, verifies digests before parse, rejects unknown
  fields, binds internal role to schema, joins receipt paths to eight
  predecessor digests without a recursive self-hash, and closes the permitted
  historical read surface and 27 embedded canonical output subdocuments.
- Froze domain-separated future derivations for source-tree, seed-claim, and
  official-attempt identities, and required later joined verification of Git
  source bytes, predecessor seed exclusion, external durable projections,
  atomic nine-file publication, unique commit-A introduction, result-namespace
  absence, and result-only commit B.
- Froze a 4 MiB default primary-record cap and a 16 MiB descriptive-result cap;
  the larger bound is required because the bound historical descriptive result
  is 5,293,662 bytes. Future loaders must enforce cap, digest, canonical parse,
  and joined verification in that order.
- The protocol remains `frozen_not_run`. This change performs no persistence,
  path observation or reservation, source closure, supplier invocation,
  artifact publication, model/subject access, execution, scientific claim,
  public-API addition, supported-schema promotion, or library maturity change.

## 2026-08-09 — V1–V9 navigation and strict-successor coordinate declaration

- Added the 13,806-byte canonical
  `spirallens.voy-navigation-route.v0.1` planning record, SHA-256
  `c8d28138c95d16ab96f508c2386de1d62360e1659057e0b8f7cbe8a380a90e35`.
  `VOY-V1` through `VOY-V9` are navigation aliases over existing Roadmap IDs;
  they carry no copied live status, completion credit, or execution authority.
- Selected the strict versioned-successor route and declared disjoint v1
  repository root, entrypoint names, external store, lanes, output, and
  terminal templates for one host. No filesystem reservation or ownership
  claim, successor source closure, physical identity, receipt, seed, attempt
  key, descriptor, result, or run is created here. The six predecessor root
  instances and their operational attempt/seed/physical/source-runtime
  descendants are non-reusable; unchanged scientific-parent identities may be
  cited only as authority-free historical evidence.
- Kept F2 and F4 unresolved and outcome-blind, with F0/F1/F3 as controls. Any
  future model-native derivation must be frozen before subject access.
- Bound the route to the PR #42 non-retroactive disposition and preserved a
  library guard that gives this route no public API, repository-bound export,
  console-script, runtime-dependency, maturity, claim-level, or supported-schema
  promotion and does not gate the independent library lane.

## 2026-08-09 — D7 v0.1 chronology disposition and official-entry block

- Added the canonical 4,728-byte
  `item23-chronology-disposition.json`, introduced by commit
  `897dd7c60411f5fd36c6c50fb5064802a25a471b`, with SHA-256
  `b0b0a84bcc594aa86d0fe53d1228eed80d0b08907de4dfa1a60f5b50685ce17c`.
  It binds the unchanged Fundamental Frame, historical Ledger decision source,
  frozen plan, full-design freeze, item-23 result, later descriptor, and
  descriptor bundle plus their Git ordering.
- Retained item 23's internal axes exactly: operational `complete`, scientific
  `insufficient`, Level 0, `claim_delta=none`, and D7/D8 `not_run`. A separate
  chronology-conformance axis is `deviated`, `D7-OPS-23` completion credit is
  false, and the later descriptor is explicitly non-curative.
- Made every official v0.1 entry fail closed before start publication or
  generator access: the fixed runner dispatches nothing, the canonical fused
  path checks the disposition before start, and the direct producer checks it
  before snapshot/C1/generator access. An absent, nonregular, unreadable,
  noncanonical, malformed, or valid disposition all block this v0.1 identity.
- The source change intentionally ends equality with the old v0.1
  execution-source closure. Any future execution requires a separately
  reviewed versioned identity and new coordinates. This is an honest-local
  protocol stop, not cryptographic revocation or hostile-local deletion/race
  resistance.

## 2026-08-09 — D7 item-24 closed launch projection and non-authorizing preparer

- Added experiment-only preparation and fixed-dispatch scripts outside the
  installed package and the pre-item-22 frozen execution-source surface. The
  preparer accepts no scientific/path override, never enters the producer or
  fused start, and publishes a fixed external empty start lane, seven new
  canonical member projections, and the descriptor last.
- Clarified the previously ambiguous external launch naming: canonical
  `launch.json` is the closed descriptor, while
  `launch-members/launch-intent.json` is the distinct launch-intent member.
  Together with the reused item-22 replay target and full-design-freeze receipt,
  the descriptor inventory contains exactly nine ordered roles.
- Artifact-only commit `09b0cc5c08c11e1dfea019ec13fd7a50bcc50bb4`
  introduces those exact eight repository files. Descriptor SHA-256 is
  `0335d80cfef3e54a9dc14045b6d76d3cf0f939dfeb373203a4cce2b1df7704ac`;
  bundle SHA-256 is
  `b796ef191840af4ada4172f157be1e7b3e98f1380c7df47d80f4950c0388ee94`.
  Strict current-HEAD replay rejoins all nine members and reports
  `launch-intent-present`, while authority, execution, result, scientific,
  retry, replay, D7, and D8 facts remain false.
- The preparer retains a promoted store/lane descriptor witness and reopens all
  member bytes before and after descriptor publication. Partial preparation is
  retained fail-closed and requires a reviewed versioned successor; it is not
  auto-resumed or cleaned up. The launcher bytes and mutable pre-entry process
  state remain outside the honest-local closure and are not authenticated.
- The later chronology disposition does not mutate this descriptor or its
  all-false facts, but it blocks the descriptor from being used for an official
  v0.1 invocation and prevents the descriptor from curing item 23 after the
  fact.

## 2026-08-06 — D7 item-23 post-D6 descriptive result source

- Added a repository-only fixed-path derivation and repository-bound
  no-replace publisher for the frozen
  `spirallens.postselection-descriptive-analysis-result.v0.1` result shape.
  The implementation reads the frozen plan, only its five PR #9/PR #10 file
  parents, and the committed item-22 full-design-freeze receipt. It verifies
  immutable Git introductions and exact analysis/source blob identities, and
  records an exact seven-file analysis-input trace. Seed-bearing item-22
  target members are checked only as immutable Git tree entries: their content
  bytes are neither read nor parsed, and their digest graph is not
  reauthenticated by item 23. The three implementation files are excluded
  from the installed wheel and required by exact path in the next reviewed
  source/runtime re-anchor. No such re-anchor receipt is created by this
  source change.
- Bound plan and parent identities are checked across their complete reachable
  Git histories, including merged incomparable branches, so a same-byte revert
  cannot erase an intervening path event. Runtime origin checks join the three
  repository-only modules and every loaded `spirallens` module to the supplied
  checkout; this is physical source identity, not scientific authority.
- The no-replace lifecycle retains the result and freeze-transaction directory
  descriptors across final validation and publication. Success additionally
  requires a descriptor-relative reread of the exact result bytes and the
  writer-returned device, inode, byte count, and one-link regular-file
  identity. A failure after publication is kept as visible evidence and
  normalized to an unproved post-publication binding for which rollback and
  republication are both forbidden.
- All eight frozen packages and 27 outputs are mandatory. Twenty-six outputs
  are derivable from persisted evidence. The full-scope D2
  amplitude/identifiability/support separation remains `blocked`: six
  confounder rows are present, while the historical main path retained only
  192 receipt bundles containing 576 relevant amplitude, identifiability, or
  support array descriptors and not the
  32-unit/96-graph scalar values. The result
  therefore remains `insufficient`, `claim_ceiling=level_0`, and
  `claim_delta=none` after an operationally complete run.
- The source creates no official artifact on import or in this source PR,
  exports no public API, reads no D7 result, subject, model, semantic, SAE, or
  Pythia value, and cannot authorize or tune D7. The narrower machine path
  treated launch intent and the closed fused descriptor as later and outside
  the item-23 inputs; the non-retroactive 2026-08-09 disposition above records
  that this contradicted the unchanged Fundamental Frame's broader
  receipt-bound chronology. The frozen PR #11 plan bytes, including its
  historical not-run metadata, are unchanged.

## 2026-08-05 — D7 item-22 one-shot transaction operation

- Added deep-internal re-anchor, transaction-manifest, abort-evidence, fixed OS-CSPRNG supplier-identity, and exclusive-claim-key v0.1 records plus a six-member atomic target; this operation supersedes and removes the immediately following contract-spec-only loader, while persisted instances remain absent, provisional, repository-local, non-authorizing, and non-scientific until the later artifact chronology executes them.

## 2026-08-05 — D7 item-22 seed-supply transaction contract specification

### Added

- The deep-internal canonical
  `spirallens.d7-item22-seed-supply-transaction-contract-spec.v0.1`
  (`D7Item22SeedSupplyTransactionContractSpec`) fixes the shape of the future
  item-22 transaction without creating one. The in-memory
  `LoadedD7Item22SeedSupplyContractFoundation` is reconstructed by the
  choice-free
  `load_d7_item22_seed_supply_contract_foundation(*, repository_root)` entry
  point only after strict reload of the complete, non-shallow historical
  item-21 chain. It accepts no caller snapshot, seed, supplier, claim key,
  callback, target document, or caller-authored layout and records
  `status=contract-defined-operational-instance-absent`.
- The specification keeps the reviewed re-anchor at the existing external path
  `item22-current-source-runtime-reanchor.json` and fixes
  `item22-seed-supply/` as the future transaction root. Its root leaves are
  `exclusive-seed-supply-claim.json` and `seed-supply-abort.json`; its atomic
  publication directory is `published-target/`, whose exact members are
  `official-seed-inventory.json`, `full-inventory.json`, `full-design.json`,
  `replay-target.json`, `single-supplier-invocation.json`, and
  `transaction-manifest.json`. The later freeze leaf is
  `full-design-freeze.json`. Launch intent remains the existing external
  `launch.json`, not a member of the seed-supply transaction root.
- All six `published-target/` members must be canonical regular unaliased files; no
  unknown member, partial visibility, replacement, or publication retry is
  allowed. `transaction-manifest.json` binds the other five members and never
  itself. The durable six-member set is deliberately distinct from the three
  chronology publication subjects: official seed inventory, full design, and
  replay target. Exact digest edges rejoin full inventory to seed inventory,
  full design to both inventories, replay target to those same member bytes,
  invocation receipt to the same inventory, and chronology subjects to their
  published members. A manifest around mutually inconsistent canonical files
  is invalid.
- The closed future state vocabulary is `preclaim`,
  `claim-present-publication-absent-nonretryable`,
  `seed-supply-aborted-established`, `publication-complete-unfrozen`,
  `full-design-frozen`, and `launch-intent-present`. The live pre-call claim
  interval is pending for its originating operation but immediately
  non-retryable and permits no restarted supplier entry. It becomes a semantic
  abort only when that operation ends without publication or the claim is
  observed on restart. The distinct durable
  `seed-supply-aborted-established` state requires an evidence receipt at
  `seed-supply-abort.json`; target absence alone does not establish it.
- This later item-22 specification explicitly refines the historical
  `spirallens.d7-replay-target-contract-spec.v0.1` field
  `seed_supply_chronology_contract.claim_without_target_is_seed_supply_aborted`
  without mutating its canonical bytes (SHA-256
  `d8387e29601a85df54513669919c591964b8fc99f3c8ec1126d527a854763ffa`, 6,550
  bytes). The older blanket flag grants no future behavior; operational code
  must use the active/ended-origin and semantic/durable-evidence split above.
- Supplier identity and the concrete exclusive claim-key value remain absent
  and mandatory before the exclusive claim. The frozen future
  `spirallens.d7-item22-exclusive-seed-supply-claim-key.v0.1` scheme uses SHA-256
  over canonical JSON with domain separator
  `spirallens:d7:item22:exclusive-seed-supply-claim:v0.1`. Its ordered roles bind
  one exact-key top-level object containing the fixed claim path, three
  historical item-21 artifacts, reviewed re-anchor, supplier identity, and
  development and parent exclusion registries. Dynamic artifacts use the exact
  five-field `spirallens.d7-item22-claim-key-binding-projection.v0.1` identity
  projection; alternate shapes, extra fields, and authority/provenance fields
  are excluded. No concrete re-anchor/supplier/key is present, the specification
  derives no key, and a caller-supplied value is rejected.
- The closed future transition graph requires verified supplier identity, the
  derived key, internally live-verified re-anchor, and durable claim before the
  supplier call. Only the same originating operation may move the claim-present
  state to complete publication or evidence-backed abort; restarted supplier
  entry is forbidden. Abort-established is terminal. Abort-evidence persistence
  failure remains claim-present/non-retryable; post-publication failure remains
  `publication-complete-unfrozen`, is not abort, and permits no supplier retry.
- Future exclusivity is scoped to repository-local no-replace and cross-process
  operation on the same filesystem. The specification proves no cross-host or
  distributed-filesystem exclusivity and no supplier-global idempotency;
  external coordination remains required before an operational boundary.
- The durable claim-before-call interval is required but is not a
  restart-resumable waiting state. Future operational code must fsync the
  owning experiment directory after creating the initially absent transaction
  namespace; claim data/metadata and its parent before supplier entry; each
  staged member and the staging directory before no-replace publication; the
  publication parent before success; and abort evidence and its parent before
  abort establishment. Restart recovery uses one mutually exclusive presence
  table in `(claim, target, abort, freeze, launch)` order: `00000` is preclaim,
  `10000` claim-present/nonretryable, `10100` abort-established, `11000`
  publication-complete/unfrozen, `11010` full-design-frozen, and `11011`
  launch-intent-present. Present artifacts must pass canonical strict reload.
  Any other combination—including target plus abort, downstream evidence
  without claim, or invalid/partial evidence—fails closed with no precedence or
  supplier retry. These requirements do not prove power-loss survival or
  authenticate filesystem fsync semantics.

### Compatibility and non-claims

- This addition is a contract-spec and in-memory loader foundation only. It
  writes no artifact, creates no filesystem object or persisted reservation,
  exposes no claim API, invokes no supplier, reads no seed, and publishes no
  target, abort, freeze, or launch record. It adds no stable or provisional
  public API.
- The committed item-21 receipt, readiness, and reviewed-admission artifacts
  remain historically valid and strictly reloadable. This later source change
  nevertheless fails their exact-current live-readiness comparison. Item 22
  therefore remains blocked until all item-22 execution source is final and a
  separately reviewed, versioned exact-current re-anchor is published at
  `item22-current-source-runtime-reanchor.json` and rebound to the historical
  item-21 chain. This contract specification is not that re-anchor.
- Historical reviewed-family-admission evidence may be retained on the loaded
  foundation, but it remains separate from the closed all-false authority map
  and is not promoted into current readiness or item-22 authority.
- No exclusive claim, supplier invocation, official seed inventory, atomic
  target publication, abort establishment, full-design freeze, launch intent,
  execution, D7 result, or D8 replay is created. All scientific and execution
  authority remains absent, false, or `not_run`.

## 2026-07-31 — Corrected D7 item-21 positive-authority artifact chain

An earlier unmerged Draft PR #27 candidate was rejected during final
adversarial review. Git's simplified default path history could hide a
side-branch artifact mutation that a merge resolved back to the original blob;
historical source reconstruction also omitted the issuer's per-member cap, and
live source checking was endpoint-only despite history-sensitive wording. No
candidate artifact was merged or promoted. The corrected v0.1 foundation treats
reachable-DAG state, issuer/loader bounds, and source-anchor descendant
continuity as protocol requirements rather than later additions.

### Added

- The corrected item-21 source anchor defines deep-internal issuance and strict
  reload boundaries for three
  distinct tracked item-21 artifacts: exact source/runtime receipt, seed-free
  readiness, and scoped reviewed successor-family admission. The source commit
  does not issue any of them and freezes all item-21 documentation. Three later
  artifact-only direct children add and strictly reload/rejoin them in order.
- The commit chronology is fail-closed. After all item-21 source code and
  documentation are final, the source/runtime receipt must be the only addition
  in its direct-child commit, readiness the only addition in the next direct
  child, and admission the only addition in the next direct child. Merges,
  intervening changes, combined-artifact commits, and embedded future-child
  identities do not satisfy the receipt-only chain.
- Full HEAD-reachable history must contain exactly one valid direct-child
  introduction. Every later path event must be its descendant and retain the
  identical `100644` blob. Merged-away mutation, delete/re-add, and parallel
  introduction fail; a preserving merge with an artifact-absent unrelated
  parent remains valid.

### Changed

- Roadmap item 21 is complete only after all three artifacts are tracked in
  that exact commit order, strictly reloaded, and pass their exact
  source/runtime and chronology rejoin checks. Implemented schemas, issuers,
  loaders, or uncommitted working-tree artifacts do not complete the item. It
  is partial at the source commit and complete at the final corrected tip after the
  third artifact-only child.
- C2 remains the historical C1 Git source-set closure only. Existing
  caller-constructible authority-prerequisite records keep false authority and
  verification fields and are not promoted or accepted in place of the three
  positive artifacts.
- With the versioned v0.1 loader retained, historical reload reconstructs the
  source inventory and runtime lock from the item-21 source commit plus fixed
  v0.1 pins, not current builder identities, and enforces the same per-member
  and aggregate source caps as issuance. Current readiness separately checks
  the anchor and HEAD plus every bounded source-path event on their descendant
  ancestry and rejects later execution-source changes, including exact revert
  or merged-away drift, as well as exact-runtime drift. A
  source-changing item-22
  implementation must therefore publish and review a versioned exact-current
  re-anchor at `item22-current-source-runtime-reanchor.json`, outside the
  reserved `item22-seed-supply/` namespace, bind it to this chain, and do so
  before its exclusive claim or supplier call.

### Compatibility and non-claims

- The chain retains the existing honest-local boundary. It observes its
  declared source/runtime surface but performs no canonical-origin check and
  explicitly records that equality as unverified. It is not signed trust-root
  provenance, hostile-local-operator resistance, or closure of package files,
  native libraries, mutable runtime state, unrecorded environment, models, or
  data.
- Neither the source commit nor the three artifact-only children create an
  item-22 exclusive supplier claim or invocation, official seed, atomic
  seed-bearing target/full-design publication, or committed freeze. At the
  final corrected tip, launch intent, the canonical nine-member descriptor, official
  invocation/start/run/terminal/result, D7, and D8 remain absent or `not_run`.
- No future R/Q/A introduction commit or precomputed R/Q/A artifact digest is
  embedded in the source commit; fixed historical predecessor hashes, schema
  identities, and reserved future paths remain explicit inputs to the verifier.

## 2026-07-31 — D7 exact runtime lock and fixed official-execution ingredients

### Added

- The exact tracked `requirements-d7-runtime-lock.txt` fixes the declared D7
  Python distribution inventory used by the deep-internal runtime boundary.
- A deep-internal zero-argument official producer and exact full-inventory,
  aggregation, and full-design builders now fix the code-side execution and
  construction rules. Their existence does not publish an official full design
  or invoke a run.

### Changed

- Runtime validation now requires exact equality of the complete installed
  distribution name/version inventory. Missing, extra, or version-drifted
  distributions fail closed.
- The fixed producer has one private, recorded-C1-only archival reconstruction
  route. It first verifies pinned C1/C2, loads the exact parent protocol,
  reconstructs the typed design from the C1-embedded binding, and requires
  whole-document equality with the design recorded in C1. This is not a general
  alternate construction path or a historical reinterpretation of D6 or C1,
  and it accepts no caller-authored design.
- The shared producer/validator path mechanically rederives the exact six
  stratum memberships from canonical joined-primary stress assignments and
  reconstructs the exact four-gate manifest, definitions, states, reasons,
  evidence digests, and outer-result reasons. These are code-side structural
  consistency checks, not authority or execution evidence.
- Roadmap item 21 is now code-side partial rather than wholly absent: the lock,
  fixed producer, exact full-inventory, aggregation, and full-design builders,
  and installed-inventory equality check exist, while its positive authority
  artifacts and decisions do not.

### Compatibility and non-claims

- The new surfaces remain deep internal and add no supported or provisional
  public Python API.
- No positive exact-current source/runtime receipt, readiness, admission,
  canonical descriptor, supplier invocation, seed, seed-bearing target or
  full-design publication, freeze, launch intent, official run, D7 result, or
  D8 replay is created. The lock, fixed producer, exact full-inventory,
  aggregation, and full-design builders, and inventory-equality check cannot
  substitute for those artifacts.
- Earlier C1, C2, D6, replay/attempt, evidence-prefix, terminal, and fused-start
  bytes are not rewritten or promoted.

## 2026-07-31 — D7 fused verification and structural-start mechanics

### Added

- `spirallens.d7-fused-authority-launch-descriptor.v0.1` defines the closed
  nine-member, current-HEAD locator and integrity inventory consumed by the
  deep-internal fused operation. Descriptor bytes carry no expected digest,
  trust token, or official authority by themselves.
- `spirallens.d7-fused-start-verification-evidence.v0.1`,
  `spirallens.d7-authoritative-start-member-binding.v0.1`, and
  `spirallens.d7-authoritative-start-manifest.v0.1` bind one same-call
  verification observation and one atomic structural start directory in the
  dedicated `d7-authoritative-start-v0/` lane.
- Verification-evidence replay is strict: exact fields, types, constants,
  digests, commit syntax, and canonical round-trip are required. The start
  writer and loader reparse the descriptor and evidence and rejoin the complete
  descriptor inventory plus attempt, replay-target, launch-intent,
  execution-identity, runtime-specification, and full-design-freeze bindings.
  Repository-HEAD, canonical-origin, source-tree, dependency-set, callable,
  and process observation digests are preserved but are not recomputed or
  independently reauthenticated by structural reload. Terminal lineage binds
  the exact evidence bytes, not the truth of those live observations.
- The following identifiers are internal digest domains, not independently
  persisted public schemas:
  `spirallens.d7-canonical-origin-observation.v0.1`,
  `spirallens.d7-fused-start-source-tree-observation.v0.1`,
  `spirallens.d7-fused-start-installed-dependency-set.v0.1`,
  `spirallens.d7-fused-start-callable-identity.v0.1`,
  `spirallens.d7-fused-start-process-identity.v0.1`, and
  `spirallens.d7-authoritative-start-directory-identity.v0.1`.

### Changed

- `spirallens.d7-launch-authority-input-bundle.v0.2` supersedes `v0.1`.
  `spirallens.d7-physical-store-lane-identity.v0.2` likewise supersedes
  `v0.1`; its exact lane is now `d7-authoritative-start-v0`, while that lane
  and the earlier evidence lane both remain persistence-reserved.
- `spirallens.d7-terminal-manifest.v0.2` supersedes `v0.1`. It adds a lineage
  group in which the authoritative-start manifest SHA-256, authoritative-start
  directory-identity SHA-256, and fused authority verification-evidence
  SHA-256 are either all non-null or all null. This permits the item-20
  terminal path to bind the exact structural start while retaining the
  structural item-19 form with all three canonical JSON values set to `null`.
- The evidence-only item-19 external finalizer now atomically consumes both
  callback entry and prepared-terminal publication before verification, so a
  visible external-abort terminal cannot be followed by a callback through the
  same private ownership.
- Repository/store tree disjointness is now checked through descriptor-relative
  physical device/inode ancestry in both directions. Path case or spelling
  cannot turn an in-repository store, containing store, or identical directory
  into a disjoint tree.
- When an ordinary producer exception publishes a failed terminal but the final
  terminal-parent fsync is unproved, the fused path now makes a best-effort
  attempt to attach the visible terminal identity and explicit durability
  warning to the same exception.
- Every fused-path exit after private ownership construction now atomically
  invalidates both callback entry and terminal publication. A pre-dispatch
  exception or traceback-retained object cannot re-enter the producer.
- These version changes affect deep-internal candidate bytes only. No
  repository-tracked or official `v0.1` launch bundle, physical identity, or
  terminal manifest is migrated. Out-of-tree deep-internal `v0.1` bytes are
  incompatible and unsupported; no migration API is provided, and no earlier
  C1, C2, D6, or evidence-prefix bytes are rewritten.

### Compatibility and non-claims

- The new modules remain deep internal with empty `__all__` values. This
  completes roadmap item 20 as mechanics implemented but not officially
  invoked; it adds no supported or provisional public Python API.
- Runtime matching is limited to the declared tracked source and runtime-lock
  bytes, installed distribution names/versions, interpreter executable bytes,
  producer source/code identity, and selected process-envelope fields. It is
  not closure of installed package files, loaded native libraries, mutable
  module globals, callable defaults or closures, unrecorded environment state,
  model state, or data state.
- Structural start bytes and their strict loader grant no authority and do not
  establish `started_unresolved`. The fused path makes at most one terminal
  publication attempt; hard exit or `BaseException`, post-start drift,
  unproved start-parent fsync, or success/failure publication error can leave a
  visible structural start with no terminal. The item-19 external finalizer is
  evidence-only and cannot accept the item-20 authoritative-start transaction.
  This does not alter the contract rule that a future verifier-established
  authoritative start without a terminal is `started_unresolved`; it clarifies
  that the item-20 structural start bytes and loader do not themselves
  establish that prerequisite.
- No tracked fused descriptor, `requirements-d7-runtime-lock.txt`, exact-current
  source/runtime artifacts, reviewed admission or readiness, official supplier
  claim or invocation, seed-bearing full design or replay target, freeze,
  launch intent, official start or terminal instance, official producer or
  exact aggregation, D7/D8 result, or replay is added. Current-main equality
  and honest-local reobservation do not prove signed trust-root provenance,
  hermetic runtime closure, hostile-local mutation resistance, or resistance
  to administrative deletion. Frozen planning-protocol JSON remains unchanged.

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
  committed freeze receipt. Its historical v0.1 physical layout placed launch
  intent later; the 2026-08-09 disposition records that this was insufficient
  for the broader pre-item-23 chronology. After its originating operation
  ends, a claim without a published target is a semantic,
  non-retryable abort, but remains in the durable claim-present state unless a
  separate valid abort receipt exists; target absence does not prove that the
  supplier was invoked.
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
  the validation-time current-loader HEAD or source-binding digest. Ordinary or
  novel builders still require `LoadedScopeLimitedD6Decision` and validate its
  typed authoritative receipt before deriving the stable historical parent
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
