# API Maturity and Compatibility Status

- **Package version:** `0.1.x`
- **Software maturity:** experimental, pre-1.0
- **Scientific maturity:** tracked separately by the claim ladder

This document declares which Python surfaces downstream users may treat as
supported, which ones are compatibility candidates, and which ones remain
provisional research APIs. A scientific result cannot stabilize an API, and a
stable software contract cannot promote a scientific claim.

## Maturity labels

- **Supported root surface:** intentionally tiny and covered by the package
  versioning policy. At present this is only `spirallens.__version__`.
- **Stable candidate:** framework-neutral functionality whose compatibility
  tests have started, but which has not met the two-independent-consumer rule
  for a stable API.
- **Provisional:** documented and tested, but allowed to change between minor
  pre-1.0 releases with migration notes.
- **Internal:** repository or experiment implementation detail. Import paths,
  call signatures, and persistence behavior are not public contracts.

## Current surface

| Namespace or symbol | Status | Compatibility boundary |
| --- | --- | --- |
| `spirallens.__version__` | supported root surface | single package version |
| `spirallens.core.canonical` | stable candidate | canonical bytes and legacy `instrument_contracts.canonical` compatibility |
| `spirallens.access` | provisional | typed access, value lineage, pre-observation descriptor, and execution-lifecycle contracts |
| `spirallens.referents` | provisional | canonical F0-F4 pointwise definitions and model-free same-object numeric relations; no substrate field |
| `spirallens.instrument_contracts` | provisional | versioned v0.x artifacts plus an explicit lineage-gated numeric payload session |
| `spirallens.contracts`, `loops`, `holonomy`, `topology` | provisional | framework-neutral mathematics; scientific meaning remains artifact-bound |
| `spirallens.synthetic`, `spirallens.graphs` | provisional | model-free generator-family controls plus exact graph/domain fingerprints; `CartesianFourierEstimatorInputs.from_observable_arrays()` is the owner boundary for deriving label-free content IDs; scientific qualification remains artifact-bound |
| `spirallens.qualification` | provisional | frozen model-free D0-D5 protocol and terminal chronology, read-only historical terminal binding, plus a single scope-limited D6 surrogate-profile decision with embedded admission spec; publish is provisional until a clean tracked descendant reload, the archival loader uses the current strict parser but skips current D1 recomputation and proves neither current-engine compatibility nor reexecution, and D7/D8/global synthetic, topology, representation, and subject authority remain false |
| future subject APIs | provisional | no subject execution surface is stabilized or authorized by this table |
| `spirallens.adapters`, capture-side `atlas`, `factors`, `interventions` | provisional/model extra | no framework types may define core artifact schemas |
| CLI handlers, workers, frozen one-experiment runners | internal | CLI is a thin adapter, never the Python API |

The PR #11 post-D6 descriptive plan and value-blind D7 gap matrix are canonical
research artifacts, not Python APIs. They intentionally add no analysis
runner, writer, generic mapping validator, family-admission helper, or
promotion surface. The descriptive artifact is also non-executable until a
committed full-D7-design freeze receipt exists. Reusable analysis primitives
remain extraction candidates until a second independent consumer exists.

The spectral-moment four-case generator and
`spirallens.qualification.confirmation_protocol` foundation are internal
development surfaces. Its builder and strict reader accept only an
authoritative committed-D6 loader receipt, but it deliberately exposes no
full-design freeze, source-closure, admission, lifecycle, execution, result, or
promotion surface.

`spirallens.qualification.confirmation_execution_design` and
`spirallens.qualification.confirmation_crossed_development` are also internal.
The first requires a strict full parent-protocol load and constructs a
seed-slot execution draft; the second accepts only permanently excluded
development seeds and stops at sealed predictions. Neither module is exported
from `spirallens.qualification` or the package root. Their schemas and call
signatures may change while the D6-to-D7 structural-rebinding contract remains
unresolved. They expose no freeze, official seed supplier, admission, gate,
result, terminal writer, replay, or promotion API.

The package root deliberately does not re-export provisional scientific APIs.
Each provisional namespace maintains an explicit `__all__`; undocumented deep
module imports remain internal.

The ordinary `load_instrument_bundle()` API remains value-opaque: it exposes
manifest path metadata but retains no payload descriptor and returns no bytes
or decoded array. `open_numeric_payload_session()` is a separate explicit
value consumer with a trusted parent-policy digest, strict payload request,
and bounded session lifetime. This separation is part of the provisional
compatibility contract.

## Compatibility gates for PR #6 onward

Every PR that grows the research-to-library surface must include:

1. a typed Python entry point independent of `argparse`;
2. an exact schema and canonical round-trip/tamper test for persisted data;
   an intentionally in-memory-only record must instead declare that scope,
   expose no parser/writer, and test immutable fingerprint behavior;
3. an explicit `__all__` update and export snapshot test;
4. this document and the schema-change record updated for public changes;
5. a clean wheel installed into a fresh virtual environment;
6. an import and CLI smoke that proves the installed wheel, not another
   editable checkout, supplied the package;
7. confirmation that core/access import does not load Torch, Transformers,
   Hugging Face, Safetensors, or Faiss;
8. deterministic examples that require no model, network, or private data;
9. explicit failure and non-claim behavior.

Passing these gates does not establish multi-platform support. Supported
Python, operating-system, and backend matrices are updated only after those
environments actually pass.

## Promotion rule

A provisional symbol becomes stable only after at least two independent
consumers, full compatibility tests, user-facing documentation, and an
explicit reviewed promotion decision. Negative or inconclusive scientific
results do not block promotion of a generally useful software primitive.
