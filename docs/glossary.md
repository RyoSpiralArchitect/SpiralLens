# SpiralLens glossary

SpiralLens keeps similarly named ideas separate in both prose and code.

- **Fundamental Frame**: The current project-wide ontology and admissible
  interpretation rules. It governs future labels and experiment design but
  cannot amend an earlier frozen protocol or artifact.
- **Experiment Interpretation Ledger**: The dated, append-oriented record that
  keeps an observation separate from its authorized interpretation and any
  later conceptual revision.
- **Interpretation amendment**: A dated ledger entry that narrows, partitions,
  or replaces an authorized reading without modifying the protocol, artifact,
  or earlier entry it discusses.
- **Outcome observation sidecar**: A compact, content-addressed witness to a
  separately persisted outcome artifact. It binds validated hashes and
  selected facts but is not a reconstruction, execution protocol, or promotion
  receipt.
- **Calibration evidence**: Evidence from an analytic or synthetic substrate
  with supplied ground truth. It qualifies conditional mathematics or
  instrument behavior and does not occupy a real-model claim-ladder rung.
- **State space**: the space in which an observed model state lives.
- **Observation substrate**: The explicitly declared discrete domain on which
  a field or transport quantity is evaluated. It includes observation identity,
  row universe, tensors, metric/preprocessing, and any field-estimation
  neighborhood. It does not imply a physical medium.
- **Substrate binding**: A future typed, content-addressed join between a
  substrate and its source artifacts. The term describes a design boundary;
  no stable public `SubstrateBinding` API exists yet.
- **Regime**: a metastable or operationally distinct region of a state space.
- **Support diagnostic**: A field-unbound scalar such as local anisotropy,
  effective rank, eigengap, projected norm, density, or coherence. It may
  diagnose identifiability but is not a core score, order parameter, phase, or
  singularity.
- **Core score**: A scalar that binds the exact order-parameter specification
  and field plus a frozen rule connecting the score to zero or unresolved
  amplitude/identifiability of that same field. It still is not a verified
  singularity or vortex core.
- **Order-parameter specification**: A declared construction, fit scope,
  target, transformation law, amplitude/identifiability rule, interpolation,
  and substrate binding for a candidate field.
- **Order-parameter field**: A replayable complex, oriented, director, or
  bundle-valued section created by an order-parameter specification. Its
  amplitude and phase-like direction belong to the same declared object.
- **Core candidate**: A candidate singular or unresolved set whose relation to
  an order-parameter field is explicit. It remains a candidate and cannot be
  localized by maximizing an observed winding after the fact.
- **Ground-truth anchor**: A supplied synthetic center used to qualify loop
  mathematics conditional on known geometry. It cannot be estimator input,
  cannot be serialized as an inferred core candidate, and cannot satisfy a
  localization gate.
- **Geometric field estimate**: A replayable projector, frame, or other
  geometry-branch estimate that may feed a connection and holonomy without
  claiming an order parameter or core.
- **Order-parameter angle**: The angular coordinate of a declared nonzero
  section under its stated gauge convention. The unqualified field name
  `phase` remains forbidden.
- **Transport angle**: a continuous angular observable associated with a chosen
  transport operator or local frame. It is not automatically semantic.
- **Holonomy**: the frame mismatch remaining after transport around a closed
  path. It is generally continuous.
- **Geometry branch**: The claim path for connections, transport, and holonomy.
  It does not require a singular core or quantized charge.
- **Defect branch**: The claim path for a substrate-bound order parameter,
  singular-set evidence, sampled charge, and topology-promotion controls.
- **Topology class**: a property invariant under the declared class of
  deformations.
- **Sampled winding**: the principal-branch phase increment around a declared
  discrete loop, divided by \(2\pi\). It can alias unresolved turns between
  samples and is not, by itself, the winding of an unknown continuous field.
- **Topology promotion**: a later claim requiring explicit sampling or
  smoothness assumptions, multi-resolution controls, deformation tests,
  matched graph-construction families, and independently defined core support.
  It corresponds to Level 2T. SpiralLens v0.1 does not emit this claim.
- **Graph construction family**: A preregistered set of genuinely distinct
  adjacency mechanisms on the same declared substrate, such as mutual-kNN,
  fixed-radius, and shared-neighbor graphs.
- **Graph-family invariance null**: A worst-case comparison of the same matched
  support or cycle class across required graph constructions. Determinism under
  one graph is not this null.
- **Matched cycle class**: A support, anchor, or homology rule that identifies
  the comparison object across graph families without choosing whichever cycle
  preserves the desired result.
- **Crossed graph design**: Evaluation over field-estimation graph
  \(G_A\) by cycle-construction graph \(G_B\). Diagonal-only agreement can be a
  shared-construction artifact.
- **Graph dependence failure**: An outcome where adequately supported required
  graph families disagree on the frozen matched quantity.
- **Core-estimation graph**: The graph, if any, used by a core estimator. It
  must be graph-free, explicitly inherit the field-estimation graph, or appear
  as its own nuisance axis in the crossed design.
- **Calibration selection decision**: The content-addressed artifact that
  freezes advanced hypotheses, required cells, estimators, thresholds,
  coverage, abstention, and aggregation before hidden confirmation is opened.
- **Subject prepare-only**: A future metadata-only validation boundary that
  cannot load subject activation values, construct a graph, inspect support,
  or localize a candidate. It is not subject execution authorization.
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

The evolution referent must also remain explicit:

- `token_position`: movement through a sequence;
- `layer_index`: transport through model depth;
- `training_step`: movement through model training.
- `synthetic_lattice`: a representation-shaped development lattice, accepted
  only for `instrument_dev` and never a model token-position claim.

No unqualified field named `phase` or `time` should be added to a persisted
artifact.
