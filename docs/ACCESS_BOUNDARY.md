# Access, Provenance, and Execution-Lifecycle Boundary

- **Status:** provisional library contract
- **Scope:** access authorization and pre-observation metadata only
- **Non-claim:** this is not a security sandbox or scientific qualification

SpiralLens keeps a data product's value provenance separate from the code or
protocol pattern used to create it. A public-example engineering atlas may
teach the library how to capture and receipt data, but its values and
value-derived summaries can never be relabelled as scientific inputs.

## 1. Dependency direction

`spirallens.access` is framework-neutral and imports no atlas, model adapter,
NumPy, Torch, Transformers, Hugging Face, Safetensors, or Faiss code.
Capture, retrieval, CLI, and future subject services depend on this access
boundary, never the reverse.

The access namespace is provisional before 1.0. Its canonical JSON codec comes
from the stable-candidate `spirallens.core` namespace.

## 2. Monotone provenance and consumer authorization

An access policy declares:

- execution class;
- append-only provenance taints;
- an exact consumer allowlist;
- a claim ceiling; and
- scientific claim eligibility.

The supported `restrict_atlas_access` derivation operation may only narrow a
consumer allowlist and add taints. It refuses to remove a taint, increase claim
eligibility, change a claim ceiling or origin, or broaden consumers.
Subject-value access is represented by an exact typed consumer, not by an
independent boolean that could drift from the allowlist.

A freely constructed or parsed `AtlasAccessPolicy` is a declaration, not proof
that it descended from another policy. Python code can always construct a new
object. The first value-decoding consumer therefore uses
`spirallens.value-access-lineage.v0.1`: it requires an out-of-band trusted
parent-policy digest, derives an exact one-consumer policy, and appends both
`value_derived` and `outcome_exposed`. A parsed lineage remains a declaration
until `reverify_value_access_lineage()` reconstructs it from the trusted parent.
This is a content-bound library correctness contract, not an ambient security
sandbox. Referencing an independently qualified artifact by digest is not value
derivation; future subject manifests must represent that distinction
explicitly.

The public-example engineering adapter remains restricted to atlas integrity
validation. Existing frozen protocol, receipt, and manifest bytes do not
change when the generic policy service is introduced.

`numeric_payload_validation` is a separate typed consumer. Public-example
engineering provenance cannot authorize it because that origin remains
integrity-only. The secure numeric session checks this authorization and the
trusted parent digest before inspecting any bundle path or opening any file.

## 3. Prepare-only is descriptor-only

Prepare-only never reads an activation manifest and then redacts it. Atlas
manifests contain outcome-bearing fields such as progress, attempts, run
identity, array hashes, summaries, predictions, failures, and runtime facts.
Reading those fields before discarding them is still an observation.

The sole input to the provisional prepare-only reader is an independently
persisted, canonical pre-observation descriptor. The descriptor contains only
predeclared identities and scope:

- protocol and model declarations;
- context and row-domain declarations;
- capture and output declarations;
- access and attempt policies; and
- interpretation ceilings and non-claims.

It contains no manifest digest, run ID, timestamp, progress, array pathname or
digest, batch receipt, summary, prediction, failure, outcome, or observed
resource fact. A descriptor is created before observation; a descriptor
reconstructed from a completed manifest cannot claim pre-observation status.

The descriptor reader accepts no atlas directory, manifest, receipt, or array
argument. Its typed preparation view reports only the canonical descriptor
identity and the declared access result.

The Python API is primary. The thin CLI adapter exposes the same fixed
consumer and requires both out-of-band descriptor digests:

```bash
spirallens access prepare \
  --descriptor /absolute/path/to/atlas-access.json \
  --expected-source-sha256 <sha256-of-exact-bytes> \
  --expected-canonical-sha256 <sha256-of-canonical-content>
```

There is deliberately no consumer selector, atlas directory, manifest,
receipt, or payload option.

## 4. Noninterference contract

The declared prepare-only function is tested with paired canary directories
whose activation payloads, value-derived summaries, array hashes, run IDs,
timestamps, and failures differ while the descriptor is identical.

The gate requires:

- byte-identical preparation output;
- an identical read trace containing the descriptor file only;
- no manifest, receipt, array, memory-map, or model access;
- success even when canary payload files are unreadable; and
- a changed output digest when a predeclared descriptor field changes.

This proves noninterference for the declared reader and inputs. It does not
prove that arbitrary Python code, another process, or a malicious operator
cannot read local files.

## 5. Attempt and terminal lifecycle

Execution status is not a scientific gate state. `pass`, `fail`,
`insufficient`, and `not_run` remain scientific or qualification data. The
attempt lifecycle instead classifies one terminal outcome, the phase where it
ended, its known access facts, and any quarantine requirement.

The attempt policy keeps these decisions distinct:

- resume the same attempt;
- reuse an output namespace;
- perform a fresh replay under the same protocol;
- retry after outcome exposure; and
- relabel the resulting values.

A terminal record is canonical, and one `AttemptLifecycle` capability permits
exactly one terminal transition. Durable run stores must separately enforce
unique attempt identity when this provisional primitive is integrated. Once
values or an outcome are exposed, the same attempt cannot be revived by
changing a threshold, required cell, schema, graph, or code path. A new
attempt requires a new identity and, for hidden confirmation, a new unopened
family.

An atlas completed without its required receipt receives
`terminal_unreceipted` provenance and is quarantine-only. Repairing receipt
publication does not authorize reuse of that atlas; replay uses a fresh
namespace. Partial payload failures and unknown interruptions receive the
broader `terminal_quarantined` taint without falsely asserting that a complete
unreceipted payload exists.

## 6. Historical and future boundaries

The historical neighbor `--prepare-only` command is a retrieval binding
preflight that reads an existing manifest and token array. It is not the
subject prepare-only contract described here and must not be renamed as such.

The access package does not create a trusted `SubjectProtocolManifest`, qualify
D0-D8, grant project-level subject preparation or execution, or make the
Pythia-70M engineering atlas scientifically eligible. It can authorize only
the descriptor-declared `subject_protocol_preparation` consumer and emit its
metadata-only view. That mechanism-level decision is not a reviewed subject
protocol, execution authority, or scientific gate. Those remain later
artifacts and decisions.
