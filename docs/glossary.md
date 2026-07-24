# SpiralLens glossary

SpiralLens keeps similarly named ideas separate in both prose and code.

- **State space**: the space in which an observed model state lives.
- **Regime**: a metastable or operationally distinct region of a state space.
- **Transport angle**: a continuous angular observable associated with a chosen
  transport operator or local frame. It is not automatically semantic.
- **Holonomy**: the frame mismatch remaining after transport around a closed
  path. It is generally continuous.
- **Topology class**: a property invariant under the declared class of
  deformations.
- **Sampled winding**: the principal-branch phase increment around a declared
  discrete loop, divided by \(2\pi\). It can alias unresolved turns between
  samples and is not, by itself, the winding of an unknown continuous field.
- **Topology promotion**: a later claim requiring explicit sampling or
  smoothness assumptions, multi-resolution controls, and deformation tests.
  SpiralLens v0.1 does not emit this claim.
- **Angular spectrum**: a Fourier decomposition around a preregistered loop.
  “OAM” is reserved for the motivating optical analogy.
- **Candidate**: an observation that passed the stated structural gates. A
  candidate is not a verified semantic feature or vortex.
- **Neighbor proposal**: a canonical unordered pair of global atlas row indices
  retrieved from unprojected states. It is not a candidate until the shared
  exact state-and-drift reranker passes it.
- **Candidate-boundary recall**: the fraction of bounded exact candidates that
  remain after a subject backend's proposals are exactly reranked. This, not
  generic recall@k, is the initial approximate-backend promotion metric.
- **Frozen recall-gate methodology**: the outcome-independent rules for
  query-local incidence, relative-density ranking, cosine-boundary strata,
  support, and worst-case reduction. Freezing it does not freeze an
  atlas/layer execution and does not assert that a backend passed.
- **Query-local candidate recall**: candidate-boundary recall restricted to
  exact reference candidates incident to one selected query row. A pair whose
  endpoints are both selected belongs to both query-local denominators.
- **Relative-density stratum**: a deterministic equal-count rank stratum of
  evaluable queries, ordered by exact-reference retrieval degree and then
  global row index. It is not derived from ANN hits or projected coordinates.
- **Cosine-boundary shell**: exact reranked reference candidates whose canonical
  float64 cosine slack lies from zero through the frozen shell width,
  inclusively. Subject-backend scores cannot determine shell membership.
- **Insufficient audit**: an audit whose exact reference contains too few
  candidates, evaluable queries, or required stratum members to evaluate the
  frozen recall gate. In particular, a zero denominator is not assigned recall
  1.0.
- **Prepared index build receipt**: a typed binding between actual serialized
  index bytes and the full ordered state matrix, row identity, layer group,
  dtype, shape, backend configuration, and runtime that produced them.
- **Receipt-gated candidate protocol**: the v0.2 candidate declaration that
  permits approximate proposals only through a verified same-input/index/group
  receipt followed by the shared exact reranker. The older v0.1 declaration is
  exact-only; changing its status does not grant ANN authorization.
- **Built-in Faiss audit runner**: the exact in-tree `FaissHNSWBackend` Python
  implementation used for a promotion-eligible audit. Subclasses, wrappers,
  and custom backends remain measurable but non-promotable.
- **Neighbor audit receipt**: a protocol-verified record authorizing one
  identical full input/index/group for approximate proposal persistence after a
  frozen, deviation-free audit pass. It is loaded against trusted external
  audit and protocol digests; a self-constructed receipt record is not
  authorization.
- **Full-index/subset-query audit**: an audit that builds the approximate index
  on every discovery row while bounding only the exact reference query rows.
  It is not an audit of a separately indexed subset.

Three evolution axes must also remain explicit:

- `token_position`: movement through a sequence;
- `layer_index`: transport through model depth;
- `training_step`: movement through model training.

No unqualified field named `phase` or `time` should be added to a persisted
artifact.
