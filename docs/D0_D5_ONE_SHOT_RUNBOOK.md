# D0–D5 closed Cartesian one-shot runbook

Status: pre-selection operational contract. This runbook does not authorize
Pythia, subject data, semantic labels, integer output, topology, D6–D8,
representation D2–D5 transfer, P0 winner selection, a localized core/loop
join, or synthetic qualification.

## What the run can establish

The official run can establish only whether the exact source-bound
F2/Cartesian surrogate profile meets D0–D5 on its frozen synthetic selection
family.

- D0: engine and protocol contracts.
- D1 and D3: Cartesian surrogate checks plus separately identified
  representation-development checks.
- D2, D4, and D5: Cartesian surrogate only.
- The manifest has 64 execution variants formed as two declared seed blocks ×
  four matched controls × eight paired stress variants.
- Those 64 variants are not 64 independent replicates and do not define an
  inferential sample size.
- Boundary is a repeated-measure view for D2. D2 therefore requires exact
  agreement before collapsing 64 stored variants to 32 unique scientific
  input units. D4 and D5 retain all 64 loop-bearing variants.

## Immutable local paths

The canonical preparation uses these repository files:

- hypothesis registry:
  `protocols/order_parameter_hypothesis_registry_v0_1.yaml`
- referent contracts:
  `protocols/order_parameter_referent_contracts_v0_1.json`
- protocol:
  `protocols/d0_d5_f2_cartesian_selection_v0_1.json`
- freeze:
  `protocols/d0_d5_f2_cartesian_selection_freeze_v0_1.json`
- pre-seed readiness artifact:
  `experiments/qualification/d0_d5_f2_cartesian_selection_v0_1/source_readiness.json`
- attempt store:
  `experiments/qualification/d0_d5_f2_cartesian_selection_v0_1/attempt`
- store freeze, launch intent, and attempt claim:
  freeze-keyed canonical files below the attempt store
- launch descriptor:
  `experiments/qualification/d0_d5_f2_cartesian_selection_v0_1/launch.json`

The launch descriptor binds normalized absolute local paths. It is deliberately
not cross-worktree or cross-machine portable. The same worktree must remain at
the same path through execution and terminal verification.

## Chronology

### E — engine/source commit

Before E, only development or adversarially chosen excluded seeds may be used.
Complete all tests, stress sweeps, size checks, and review fixes first. E must
contain:

- the full qualification source closure;
- the three official scripts;
- the canonical seed-independent referent file;
- tests and claim-boundary documentation.

After E, do not edit the bound engine source. The preparation script requires
its declared engine commit to be the exact current HEAD and rejects dirty
engine or launch-script paths before its delayed seed supplier is called.

### F — source readiness, delayed seed generation, protocol, and freeze

Create the experiment parent directory, then run:

```bash
uv run python scripts/prepare_d0_d5_selection.py \
  --repository-root /absolute/path/to/spirallens-worktree \
  --engine-commit <E_COMMIT> \
  --registry /absolute/path/to/protocols/order_parameter_hypothesis_registry_v0_1.yaml \
  --referent /absolute/path/to/protocols/order_parameter_referent_contracts_v0_1.json \
  --source-readiness-output /absolute/path/to/experiments/qualification/d0_d5_f2_cartesian_selection_v0_1/source_readiness.json \
  --protocol-output /absolute/path/to/protocols/d0_d5_f2_cartesian_selection_v0_1.json \
  --freeze-output /absolute/path/to/protocols/d0_d5_f2_cartesian_selection_freeze_v0_1.json \
  --freeze-id d0-d5-f2-cartesian-selection-freeze-v0-1 \
  --seed-family-id d0-d5-f2-cartesian-selection-family-v0-1
```

The CLI accepts no seed values. The library first verifies the exact Git
closure, including all three official scripts, the strict registry, and the
registry-derived canonical referent. It then publishes the canonical
pre-seed readiness artifact without overwrite and strictly reloads its exact
absolute path and source/canonical digests. Only after that durable round trip
does it invoke a once-only delayed supplier backed by the operating system
random source. The generated seeds must be distinct, canonical, signed-int64,
and absent from the finite known-development-seed exclusion registry.

This is `official-process-attested` procedural evidence. It is not
cryptographic proof, nor proof that a human or external process had not
already chosen or observed a seed. The protocol, freeze, and later claim bind
the exact earlier readiness path and identity. Commit the readiness artifact,
protocol, and freeze as F before acquiring a claim; launch requires all three
to be clean tracked HEAD blobs.

### G — launch intent, fixed-store claim, and launch descriptor

At clean F, create the attempt-store parent and run:

```bash
uv run python scripts/prepare_d0_d5_launch.py \
  --descriptor-id d0-d5-f2-cartesian-selection-launch-v0-1 \
  --descriptor-output /absolute/path/to/experiments/qualification/d0_d5_f2_cartesian_selection_v0_1/launch.json \
  --repository-root /absolute/path/to/spirallens-worktree \
  --registry /absolute/path/to/protocols/order_parameter_hypothesis_registry_v0_1.yaml \
  --referent /absolute/path/to/protocols/order_parameter_referent_contracts_v0_1.json \
  --protocol /absolute/path/to/protocols/d0_d5_f2_cartesian_selection_v0_1.json \
  --protocol-source-sha256 <PROTOCOL_SOURCE_SHA256> \
  --protocol-canonical-sha256 <PROTOCOL_CANONICAL_SHA256> \
  --freeze /absolute/path/to/protocols/d0_d5_f2_cartesian_selection_freeze_v0_1.json \
  --freeze-source-sha256 <FREEZE_SOURCE_SHA256> \
  --freeze-canonical-sha256 <FREEZE_CANONICAL_SHA256> \
  --attempt-store /absolute/path/to/experiments/qualification/d0_d5_f2_cartesian_selection_v0_1/attempt \
  --claim-id d0-d5-f2-cartesian-selection-claim-v0-1
```

Preparation verifies the exact closed profile, source closure, clean tracked F
artifacts, freeze, and availability of the platform no-replace
terminal-rename symbol. It then publishes and strictly reloads a canonical
launch intent before it can acquire the claim. The claim binds that exact
intent, and the descriptor binds both. Commit the persisted store freeze,
launch intent, claim, and descriptor as G before execution.

If publication fails within the intent-to-claim-to-descriptor sequence,
rerunning the same launch command may recover only the exact canonical intent
and claim for the same fully revalidated F inputs, freeze, pre-seed artifact,
claim ID, capability, and store. A raw preexisting claim without the earlier
intent is rejected. Recovery does not create a second claim and remains
forbidden after an execution-start or terminal record appears.

The symbol preflight is read-only. It does not invoke the primitive and does
not prove operational filesystem behavior. The one-shot boundary is
store-local and requires a trusted operator. Global, cross-store, multi-host,
deletion-resistant, and hostile-mutation-resistant uniqueness are all false.

### H — fresh one-shot execution and terminal artifact

From the same clean worktree at G, launch a fresh interpreter:

```bash
uv run python scripts/run_d0_d5_selection.py \
  --launch-descriptor /absolute/path/to/experiments/qualification/d0_d5_f2_cartesian_selection_v0_1/launch.json \
  --launch-descriptor-source-sha256 <LAUNCH_SOURCE_SHA256> \
  --launch-descriptor-canonical-sha256 <LAUNCH_CANONICAL_SHA256>
```

The execution script has no repository, protocol, freeze, claim, or store
override. It loads the existing descriptor, intent, and claim; requires the
descriptor, store freeze, intent, and claim to be exact clean tracked blobs at
one unchanged G HEAD; and only then derives an in-memory launch authorization.
The official terminal-owning orchestrator revalidates that authorization and
all four G artifacts again before creating the execution-start transition.
That transition stores the authorization digest and authorized G HEAD. The
result or failed-attempt artifact stores the same digest, and terminal
publication plus reload require the typed authorization and an exact join to
the persisted start. Terminal validation proves
`engine commit -> authorized G -> current HEAD`, requires the four G blobs to
be unchanged at the authorized commit, current commit, and clean worktree, and
requires the start and terminal paths to have been absent from the authorized
G tree. It is called once, and the script immediately reloads the complete
terminal transaction using the returned digests.

Commit the execution-start marker and terminal transaction as H, regardless
of scientific verdict. Never replace or delete them.

## Failure authority

- Failure before claim: correct source or path inputs; no attempt exists.
- Failure after claim but before execution start: the fixed claim remains.
  Diagnose without deleting or replacing it. The launch preparation may
  recover only that exact same validated claim and publish its descriptor.
- Execution-start present, terminal absent: terminal-aborted. No retry.
- Terminal present: consumed, even if stdout, post-return reporting, or a later
  reload failed. Never execute again.
- Ordinary Python failure after start: the orchestrator attempts to publish a
  typed failed terminal, strictly reloads its exact manifest/artifact/
  consumption identities, attaches a machine-readable round-trip receipt to
  the original exception, and then re-raises that original error.
- Result or failed terminal visible after a publication call raises: the
  orchestrator never overlays it. It strictly reloads only the exact expected
  terminal and attaches a typed receipt with
  `publication_call_returned=false`,
  `parent_directory_durability_fsync_proved=false`, and
  `retry_authorized=false`.
- Process kill, machine loss, or storage failure can leave start-only state.
  This is fail-closed evidence, not retry authority.

No terminal verdict changes the claim ceiling or any of the explicit negative
authorities listed at the top of this runbook.

The official authority is a persisted-and-validated property, not a promise
that arbitrary in-memory record objects cannot be constructed. Generic
standalone qualification-result write/load APIs reject this official protocol
ID; use only the terminal transaction publisher and loader for H.

## Development full-envelope stress evidence

Before E, the known fixed seeds `424242` and `424243` were used only inside an
isolated disposable Git repository to exercise the complete
readiness–freeze–launch–terminal machinery. The same normalized absolute path,
source tree, deterministic E/F/G history, and seeds were reconstructed twice.
The two runs were byte-identical from source readiness through execution start,
terminal manifest, result, and consumption.

- All D0–D5 gates passed without reason codes.
- The canonical result was exactly 19,964,272 bytes, below both 32 MiB
  persistence caps.
- The stored result contained 64 core primary units, 192 core graph cells,
  64 loop primary units, 1,152 crossed loop cells, 64 non-vacuity receipts,
  six stress strata, 1,344 event lanes, and 8,064 events.
- D2 counted 32 boundary-collapsed scientific units; D4 and D5 each counted
  all 64 loop-bearing variants.
- A committed H successor strictly reloaded the terminal transaction against
  its unchanged authorized G ancestry and four exact G blobs.

This was engineering stress evidence, not the official selection and not
scientific qualification. The fixed seeds were known in advance,
`external_prior_observation_excluded` was false, and the result retained
`claim_ceiling=level_0`, `scientific_claim_eligible=false`,
`synthetic_qualified=false`, and every subject, semantic, integer/topology,
P0-winner, representation-transfer, localized core/loop-join, and D6–D8
authority as false. No disposable protocol, freeze, launch, or result artifact
is reusable by the official run. Both seeds are permanently present in the
known-development-seed exclusion registry before E.
