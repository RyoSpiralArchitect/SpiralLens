# Graph and discrete-domain foundation

## Status

This document specifies the provisional, model-free `spirallens.graphs`
foundation. The records in this namespace are immutable in-memory
fingerprints. They are not persistence schemas: they have no parser, loader,
writer, or canonical round-trip authority.

This foundation measures graph construction and proves one narrow,
graph-independent combinatorial relation. It does not run a field estimator,
locate a core, construct holonomy, read winding, or advance D0-D8.

## Why the graph is not the domain

A nearest-neighbor graph records adjacency selected by one construction rule.
It does not say which triangles are filled, which support has been excluded,
or which closed walks bound the same two-dimensional support. Treating each
graph as its own topological domain would change the space whenever the graph
family changed and would make graph invariance circular.

SpiralLens therefore keeps two identities separate:

1. `GraphConstructionReceipt` records one deterministic, exhaustive
   canonical-coordinate-order float64 adjacency on a bound ordered numerical
   input.
2. `DiscreteDomainComplex` records an independently declared oriented
   triangular complex on the same row domain.

The first PR supporting this distinction accepts only exact identity of the
input and domain fingerprints. It does not compare different discretizations,
infer a latent-manifold triangulation, or manufacture a refinement map from a
shared vertex set.

## Deterministic graph input and constructions

`GraphInput` binds one explicit primary statistical-unit identity, an ordered,
unique int64 vertex-identity vector, and a finite float64 state matrix. Graph
construction sees no field, core, loop, winding, charge, semantic label, SAE
label, or model-derived outcome.

All three constructors use:

- an exhaustive Euclidean norm whose absolute coordinates are stably sorted
  before a fixed float64 `hypot` reduction;
- identity preprocessing;
- canonical row-index edges with `left < right`;
- deterministic ordering;
- a conservative 256 MiB estimated working-set limit; and
- fail-closed detection of non-finite distance arithmetic and nonzero
  separations that underflow to zero.

The metric is deterministic over the supplied float64 values and bit-identical
under signed coordinate permutations, but it is not exact real arithmetic.
Distinct real distances may round to the same float64 value; the declared
vertex-identity tie rule then applies. Radius comparison uses the canonical
norm directly rather than squaring it, avoiding a known near-underflow
threshold alias.

The parameter-aware bounded resource estimate includes conservative Python
container and dense-output terms and runs before the pairwise allocation. It
protects against parameter-induced runaway allocation. It is not an
operating-system OOM guarantee.

The three mechanisms are:

### Mutual k-nearest neighbor

For every row \(i\), rank every other row by

\[
(\operatorname{fl}_{64}(\lVert x_i-x_j\rVert_2),\
\text{vertex-id}_j,\ j).
\]

An undirected edge \(\{i,j\}\) exists exactly when \(j\) is in the first
\(k\) rows for \(i\) and \(i\) is in the first \(k\) rows for \(j\).

### Inclusive fixed radius

An undirected edge \(\{i,j\}\) exists exactly when

\[
\operatorname{fl}_{64}(\lVert x_i-x_j\rVert_2) \leq \epsilon.
\]

The equality case is included.

### Shared neighbor

First form each directed \(k\)-nearest-neighbor set \(N_k(i)\) with the same
tie rule. For every unordered row pair, including pairs that are not mutual
neighbors, create an edge exactly when

\[
\lvert N_k(i)\cap N_k(j)\rvert \geq m.
\]

Adding mutual-neighbor eligibility to this rule would collapse it toward the
first mechanism and is forbidden.

Each construction receipt recomputes and binds the canonical edge list,
Euclidean edge distances, degree, connected-component labels, and two-core
mask. A declared family and a different adjacency fingerprint establish
structural difference only. They do not prove software independence,
independent failure modes, or stochastic independence.

## Graph-diversity measurement

`GraphDiversityReceipt` requires one receipt from each of the three declared
families over the identical `GraphInput`. It records, for every family pair:

- edge counts, intersection, union, equality, and Jaccard similarity;
- degree-vector correlation when both variances are nonzero;
- agreement of the same-component relation across all unordered vertex
  pairs; and
- two-core intersection, union, and Jaccard similarity.

Undefined ratios or correlations are represented by a typed reason and
`value=None`, never NaN. The receipt records whether the three adjacency
fingerprints are pairwise distinct, but has no threshold and emits no
`pass`, `fail`, `insufficient`, or D-gate state. A later frozen qualification
protocol must decide what diversity is adequate.

Graph cells over one generator instance are repeated measurements of one
primary unit. Relabeling or duplicating graph cells cannot increase the
inferential sample size.

## Exact oriented discrete domain

`DiscreteDomainComplex` binds oriented triangular faces expressed in
`GraphInput` row indices. Cyclic rotations of a triangle are canonicalized
without reversing its handedness. The constructor rejects duplicate faces,
degenerate faces, out-of-range vertices, edges incident to more than two
faces, and shared edges whose incident faces traverse them in the same
direction.

Using the canonical edge basis \((\min i,\max j)\), it constructs exact int64
matrices

\[
C_2 \xrightarrow{\partial_2} C_1
\xrightarrow{\partial_1} C_0
\]

and verifies

\[
\partial_1\partial_2=0
\]

by exact integer arithmetic. This proves internal consistency of the supplied
finite chain complex only. It does not prove that the cells triangulate a
continuous representation manifold.

The builder accepts no field or loop observable. It does not, however, verify
when or why the caller selected the triangle domain or face support. A later
qualification protocol must seal that provenance before observable access.
The exterior boundary and any face-support boundary are combinatorial support
facts, not evidence of a field zero, singularity, vortex core, or missing
observation.

## Same induced support-boundary class

`BoundaryCycleClassSpec` declares an exact set of faces in one
`DiscreteDomainComplex`. The selected faces must be connected and their
oriented boundary must form one simple cycle. The resulting equivalence
relation is deliberately named `same-induced-support-boundary`.

It is not generic homology, homotopy equivalence, or a claim that two cycles
enclose an inferred core. In particular, the exterior boundary of a filled
disk is a boundary chain; this foundation does not call it a nontrivial
\(H_1\) class.

`BoundaryRefinementRule` permits one graph edge to represent a bounded,
forward-contiguous arc of that exact common boundary. `bind_cycle_class()`
searches without reading any field or loop value. A valid graph cycle must:

1. use graph edges from the supplied construction receipt;
2. preserve the domain-induced orientation;
3. partition the common boundary exactly once;
4. use at least three distinct graph vertices; and
5. respect the declared maximum domain-edge span.

Every orientation-preserving cyclic cut is searched, so a valid coarse edge
may cross the canonical minimum-row cut. When multiple refinements are
possible, selection maximizes graph-edge count and then uses canonical
lexicographic cycle-vertex order. If no refinement covers the boundary, the
function returns a typed unmatched attempt. Unmatched is a measurement result,
not an `insufficient` gate result; the D4 protocol that consumes it has not yet
been implemented.

Each binding carries `primary_unit_id`, `matched_set_id`, graph-cell identity,
representative identity, orientation relation, traversal multiplicity, and a
content-equivalence group. These full-digest identities expose lineage so a
later validator can detect combinatorial multiplicity. This foundation does
not implement an aggregator, prevent misuse by a caller, or establish
stochastic independence. The content-equivalence digest excludes declaration,
matched-set, and domain display IDs; relabeling the same ordered input,
oriented domain structure, support, and boundary therefore cannot manufacture
a new content group.

Binding three graph families to the same finest available boundary establishes
common-boundary availability only. It is not yet graph-family cycle invariance:
the later crossed design must show graph-dependent representative consumption
or another non-vacuous nuisance test. Mapping a graph chord to a declared
boundary arc also proves neither the chord's geometric realization nor its
homotopy class.

## Frozen non-claims

The graph/domain foundation:

- does not establish a triangulation of a latent manifold;
- does not establish continuous-domain topology;
- does not treat shared vertex support as general cycle-class equivalence;
- does not treat a cycle-basis index as cross-graph identity;
- does not claim homology or homotopy equivalence;
- does not identify a domain boundary or hole with a field zero or core;
- does not identify missing support with a singular set;
- does not treat a graph-family label as construction independence;
- does not treat structural diversity as software independence;
- does not erase orientation under reflection;
- does not treat combinatorial multiplicity as statistical replication;
- does not certify caller-side outcome-blind support or rule selection;
- does not turn common-boundary availability into graph-family invariance;
- does not treat a boundary-arc mapping as geometric or homotopy evidence;
- does not read a field, holonomy, winding, charge, semantics, or a subject;
- does not authorize Level 2T; and
- does not pass or advance D0-D8.

## Deferred work

A later payload-backed schema may persist graph/domain receipts after their
parser and round-trip contracts exist. A later qualification layer may bind
field, cycle, and optional core graphs into a preregistered crossed matrix and
classify coverage as `pass`, `fail`, or `insufficient`. Comparison between
different domain discretizations requires explicit chain maps and ambiguity
handling and is outside this foundation.
