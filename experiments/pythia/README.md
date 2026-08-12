# Pythia experiments

Tracked experiment manifests live here; generated arrays and journals live
under the ignored `runs/` directory.

The first implementation smoke uses `EleutherAI/pythia-70m`. The historically
intended first claim-bearing family is `EleutherAI/pythia-160m`, but it requires
a separately versioned and reviewed `SubjectProtocolManifest` that follows the
same capture discipline. Neither this 70M protocol nor the model-family intent
authorizes that future preparation or run.

A private identity-acquisition contract defines a bounded provider-metadata and
exact-`config.json` candidate for Pythia-160M. From exact merged source commit
`fb640788d3c036cb86127ed9d32d28d27c1e2aa9`, the unregistered one-shot script
was invoked exactly once and published the tracked four-file
[`pythia160-v0.1`](model_identity/pythia160-v0.1/) directory. Its receipt
resolves revision `50f5173d932e8e61f858120bcb800b97af589f46`, rejoins the
default and exact provider responses, and joins exact config bytes to the
provider's non-LFS Git blob. It is still `review_pending`: provider sibling
metadata is unrecomputed, weights and tokenizer bytes are unread, and every
preparation, model-access, execution, capture, VOY, scientific, `SCI-S1`, and
`SCI-S2` authority remains closed. The operation reserved and fsynced its empty
private stage before the first request, completed without retry, and left no
stage. Its no-replace publication assumed a quiescent, honest local checkout
and did not claim resistance to a hostile same-user rename race. Capture-time
0600 file and 0700 directory modes are not represented by Git.

The exact isolated Python 3.13 runtime was subsequently found to have an empty
default certificate store. A source-only correction makes TLS trust explicit:
before durable stage reservation, the private script reads the fixed
honest-local macOS bundle `/private/etc/ssl/cert.pem` through no-symlink path
anchors, requires a bounded root-owned regular file with no group or world
write bit, and builds one hostname-verifying `CERT_REQUIRED` client context
with TLS 1.2 or newer and a nonempty CA store. The same context is passed to all
three HTTPS requests through an explicit handler. Ambient OpenSSL
configuration, provider-module, and engine environment is rejected before TLS
initialization. That source correction itself invoked no live main. The later
acquisition used the explicit context and records only network, Hugging Face,
provider-metadata, and config-byte access. The v0.1 receipt does not record the
CA-bundle digest and therefore cannot attest the exact transport-trust bytes.

### Non-authoritative prerequisite projection

This table is a navigation aid only; the canonical route, receipts, and
roadmap control. None of these rows earns VOY completion credit.

| Work item | Operation state | Persisted evidence | Review/authority state |
| --- | --- | --- | --- |
| PR58 pre-observation declaration | synthetic only | none | `blocked_external_prerequisites`; no authority |
| PR59 adapter mechanism | offline fake only | tests only | no real-model parity or zero-intervention review |
| PR60–PR62 identity acquisition | one metadata/config attempt complete | exact four-file candidate | `review_pending`; external witness false; no authority |

Pythia-160M remains the VOY-V8 subject family and is still blocked by the
canonical `SCI-S1`/`SCI-S2` gates. This prerequisite projection must not be
read as progress through VOY-V1–V9.

The current 70M public-example smoke validates only exact offline model-file
resolution, bounded capture, storage, checksum, manifest reload, and receipt
plumbing. Its frozen protocol allows only atlas integrity validation.
Candidate-ledger and neighbor plumbing belong to the preserved historical
retrieval path or synthetic/fake fixtures; they are not consumers of a new
public-example engineering atlas.

The frozen declaration is
[`protocols/pythia70_public_example_plumbing_v0_1.yaml`](../../protocols/pythia70_public_example_plumbing_v0_1.yaml).
Its no-overwrite canonical receipt is published under
[`receipts/`](receipts/) only after checksum and reload validation.

The receipt records `model_accessed=true` and
`activation_values_persisted=true`, while keeping scientific claim eligibility
false and D0-D8 plus candidate, graph, field, core, loop, semantic, SAE, and
integer stages `not_run`. It is not evidence for semantic phase, holonomy, or
topology and is not a subject run. For any future claim-bearing run, retain the
resolved immutable model revision and capture backend recorded in its own
separately authorized manifest.
