from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from spirallens.graphs.common import (
    GRAPH_PERSISTENCE_ROUND_TRIP_SUPPORTED,
    GRAPH_RECORD_SCOPE,
    GraphContractError,
    GraphFamily,
    GraphPurpose,
)
from spirallens.graphs.constructors import (
    construct_mutual_knn,
    construct_radius_graph,
    construct_shared_neighbor_graph,
)
from spirallens.graphs.contracts import (
    GraphConstructionReceipt,
    GraphInput,
    MutualKnnSpec,
    RadiusGraphSpec,
    SharedNeighborSpec,
)
from spirallens.graphs.diversity import measure_graph_diversity


def _grid_graphs() -> tuple[
    GraphConstructionReceipt,
    GraphConstructionReceipt,
    GraphConstructionReceipt,
]:
    states = np.array(
        [(x, y) for y in range(4) for x in range(4)],
        dtype="<f8",
    )
    graph_input = GraphInput(
        primary_unit_id="grid-diversity-unit",
        vertex_ids=np.arange(100, 116, dtype="<i8"),
        states=states,
    )
    purpose = GraphPurpose.CYCLE_CONSTRUCTION
    return (
        construct_mutual_knn(
            graph_input,
            MutualKnnSpec(
                spec_id="grid-mutual",
                purpose=purpose,
                neighbor_count=4,
            ),
        ),
        construct_radius_graph(
            graph_input,
            RadiusGraphSpec(
                spec_id="grid-radius",
                purpose=purpose,
                radius=1.01,
            ),
        ),
        construct_shared_neighbor_graph(
            graph_input,
            SharedNeighborSpec(
                spec_id="grid-shared",
                purpose=purpose,
                neighbor_count=5,
                minimum_shared_neighbors=1,
            ),
        ),
    )


def _two_vertex_graphs(
    *,
    purpose: GraphPurpose = GraphPurpose.FIELD_ESTIMATION,
    vertex_offset: int = 0,
) -> tuple[
    GraphConstructionReceipt,
    GraphConstructionReceipt,
    GraphConstructionReceipt,
]:
    graph_input = GraphInput(
        primary_unit_id=f"pair-diversity-unit-{vertex_offset}",
        vertex_ids=np.array(
            [vertex_offset + 10, vertex_offset + 20],
            dtype="<i8",
        ),
        states=np.array([[0.0], [2.0]], dtype="<f8"),
    )
    return (
        construct_mutual_knn(
            graph_input,
            MutualKnnSpec(
                spec_id="pair-mutual",
                purpose=purpose,
                neighbor_count=1,
            ),
        ),
        construct_radius_graph(
            graph_input,
            RadiusGraphSpec(
                spec_id="pair-radius",
                purpose=purpose,
                radius=0.5,
            ),
        ),
        construct_shared_neighbor_graph(
            graph_input,
            SharedNeighborSpec(
                spec_id="pair-shared",
                purpose=purpose,
                neighbor_count=1,
                minimum_shared_neighbors=1,
            ),
        ),
    )


def test_diversity_canonicalizes_three_families_and_measures_exact_edges(
    tmp_path: Path,
) -> None:
    mutual, radius, shared = _grid_graphs()

    receipt = measure_graph_diversity((shared, mutual, radius))

    assert tuple(graph.specification.family for graph in receipt.graphs) == (
        GraphFamily.MUTUAL_KNN,
        GraphFamily.FIXED_RADIUS,
        GraphFamily.SHARED_NEIGHBOR,
    )
    assert receipt.graph_input_fingerprint_sha256 == (
        mutual.graph_input.fingerprint_sha256
    )
    assert receipt.primary_unit_id == "grid-diversity-unit"
    assert receipt.vertex_order_sha256 == mutual.graph_input.vertex_order_sha256
    assert receipt.state_sha256 == mutual.graph_input.state_sha256
    assert receipt.purpose is GraphPurpose.CYCLE_CONSTRUCTION
    assert receipt.adjacency_fingerprints_pairwise_distinct

    mutual_radius = receipt.pairwise[0]
    assert mutual_radius.left_family is GraphFamily.MUTUAL_KNN
    assert mutual_radius.right_family is GraphFamily.FIXED_RADIUS
    assert mutual_radius.left_edge_count == 25
    assert mutual_radius.right_edge_count == 24
    assert mutual_radius.edge_intersection_count == 24
    assert mutual_radius.edge_union_count == 25
    assert not mutual_radius.edge_sets_equal
    assert mutual_radius.edge_jaccard_defined
    assert mutual_radius.edge_jaccard_reason == "ok"
    assert mutual_radius.edge_jaccard_similarity == pytest.approx(24 / 25)

    for comparison in receipt.pairwise:
        assert comparison.degree_pearson_defined
        assert comparison.degree_pearson_reason == "ok"
        assert comparison.degree_pearson_correlation is not None
        assert math.isfinite(comparison.degree_pearson_correlation)
        assert comparison.component_vertex_pair_count == 120
        assert comparison.component_pair_agreement_count == 120
        assert comparison.component_pair_agreement == 1.0
        assert comparison.component_pair_agreement_defined
        assert comparison.component_pair_agreement_reason == "ok"
        assert comparison.two_core_intersection_count == 16
        assert comparison.two_core_union_count == 16
        assert comparison.two_core_jaccard_similarity == 1.0
        assert comparison.two_core_jaccard_defined
        assert comparison.two_core_jaccard_reason == "ok"

    default_root = Path(__file__).resolve().parents[1] / "src"
    expected_root = Path(
        os.environ.get("SPIRALLENS_EXPECTED_IMPORT_ROOT", default_root)
    ).resolve(strict=True)
    numpy_root = Path(np.__file__).resolve(strict=True).parent.parent
    probe = """
import hashlib, importlib.abc, pathlib, sys
numpy_root, expected_root = [pathlib.Path(item).resolve(strict=True) for item in sys.argv[1:]]
sys.path[:0] = [str(expected_root), str(numpy_root)]; import numpy as np
assert pathlib.Path(np.__file__).resolve().is_relative_to(numpy_root)
blocked = 'scipy yaml torch transformers huggingface_hub safetensors faiss spirallens._repository_context spirallens.qualification'.split()
attempts = []
class Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == item or fullname.startswith(item + '.') for item in blocked):
            attempts.append(fullname)
            raise ModuleNotFoundError(fullname)
sys.meta_path.insert(0, Blocker())
import spirallens.graphs as graphs
expected_exports = 'BOUNDARY_CYCLE_CLASS_SPEC_RECEIPT_VERSION BOUNDARY_REFINEMENT_RULE_RECEIPT_VERSION CYCLE_CLASS_BINDING_RECEIPT_VERSION CYCLE_CLASS_MATCH_ATTEMPT_RECEIPT_VERSION DISCRETE_DOMAIN_RECEIPT_VERSION GRAPH_CLAIM_CEILING GRAPH_CLAIM_SCOPE GRAPH_CONSTRUCTION_RECEIPT_VERSION GRAPH_DIVERSITY_RECEIPT_VERSION GRAPH_FAMILY_IDENTITY_RECEIPT_VERSION GRAPH_INPUT_RECEIPT_VERSION GRAPH_PAIR_DIVERSITY_RECEIPT_VERSION GRAPH_PERSISTENCE_ROUND_TRIP_SUPPORTED GRAPH_RECORD_SCOPE GRAPH_SPEC_RECEIPT_VERSION MAX_DOMAIN_ESTIMATED_PEAK_BYTES MAX_GRAPH_ESTIMATED_PEAK_BYTES BoundaryCycleClassSpec BoundaryRefinementRule CycleClassBinding CycleClassMatchAttempt DiscreteDomainComplex GraphConstructionReceipt GraphContractError GraphDiversityReceipt GraphFamily GraphFamilyIdentity GraphInput GraphPairDiversity GraphPurpose GraphSpecValue MutualKnnSpec RadiusGraphSpec SharedNeighborSpec bind_cycle_class build_discrete_domain_complex construct_mutual_knn construct_radius_graph construct_shared_neighbor_graph define_boundary_cycle_class measure_graph_diversity'.split()
assert len(expected_exports) == 41 and graphs.__all__ == expected_exports
operations = {'bind_cycle_class': 'spirallens.graphs.domain', 'build_discrete_domain_complex': 'spirallens.graphs.domain', 'construct_mutual_knn': 'spirallens.graphs.constructors', 'construct_radius_graph': 'spirallens.graphs.constructors', 'construct_shared_neighbor_graph': 'spirallens.graphs.constructors', 'define_boundary_cycle_class': 'spirallens.graphs.domain', 'measure_graph_diversity': 'spirallens.graphs.diversity'}
assert len(operations) == 7
for name, module_name in operations.items():
    value = getattr(graphs, name); assert value is getattr(sys.modules[module_name], name) and value.__module__ == module_name
graph_input = graphs.GraphInput(primary_unit_id='wheel-probe', vertex_ids=np.array([10, 20], dtype='<i8'), states=np.array([[0.0], [1.0]], dtype='<f8'))
receipt = graphs.construct_radius_graph(graph_input, graphs.RadiusGraphSpec(spec_id='wheel-radius', purpose=graphs.GraphPurpose.FIELD_ESTIMATION, radius=1.0))
constructors = (expected_root / 'spirallens/graphs/constructors.py').resolve(strict=True)
assert receipt.family_identity.source_sha256 == hashlib.sha256(constructors.read_bytes()).hexdigest()
packages = set('spirallens spirallens.core spirallens.graphs'.split())
definitions = set('spirallens.core.canonical spirallens.graphs.common spirallens.graphs.constructors spirallens.graphs.contracts spirallens.graphs.diversity spirallens.graphs.domain'.split())
loaded = {name for name in sys.modules if name.split('.')[0] == 'spirallens'}; assert loaded == packages | definitions
for name in loaded:
    module = sys.modules[name]; path = pathlib.Path(*name.split('.'))
    relative = path / '__init__.py' if name in packages else path.with_suffix('.py')
    expected = (expected_root / relative).resolve(strict=True)
    assert {pathlib.Path(module.__file__).resolve(), pathlib.Path(module.__spec__.origin).resolve()} == {expected}
assert attempts == [] and not any(name == item or name.startswith(item + '.') for name in sys.modules for item in blocked)
"""
    subprocess.run(
        [sys.executable, "-I", "-B", "-c", probe, str(numpy_root), str(expected_root)],
        cwd=tmp_path,
        env={},
        check=True,
    )


def test_undefined_metrics_are_typed_as_none_and_never_nan() -> None:
    receipt = measure_graph_diversity(_two_vertex_graphs())
    mutual_radius, mutual_shared, radius_shared = receipt.pairwise

    assert not receipt.adjacency_fingerprints_pairwise_distinct
    for comparison in receipt.pairwise:
        assert comparison.degree_pearson_correlation is None
        assert not comparison.degree_pearson_defined
        assert comparison.degree_pearson_reason == "constant-degree-vector"
        assert comparison.two_core_jaccard_similarity is None
        assert not comparison.two_core_jaccard_defined
        assert comparison.two_core_jaccard_reason == "no-two-core-support"

    assert mutual_radius.edge_jaccard_similarity == 0.0
    assert mutual_radius.edge_jaccard_defined
    assert mutual_shared.edge_jaccard_similarity == 0.0
    assert mutual_shared.edge_jaccard_defined
    assert radius_shared.edge_sets_equal
    assert radius_shared.edge_jaccard_similarity is None
    assert not radius_shared.edge_jaccard_defined
    assert radius_shared.edge_jaccard_reason == "no-edges-in-pair"

    assert mutual_radius.component_pair_agreement == 0.0
    assert mutual_shared.component_pair_agreement == 0.0
    assert radius_shared.component_pair_agreement == 1.0

    encoded = json.dumps(receipt.to_dict(), allow_nan=False, sort_keys=True)
    assert "NaN" not in encoded


def test_receipt_is_measurement_only_and_in_memory_fingerprint_scoped() -> None:
    receipt = measure_graph_diversity(_grid_graphs())
    value = receipt.to_dict()

    assert value["record_scope"] == GRAPH_RECORD_SCOPE
    assert value["persistence_round_trip_supported"] is (
        GRAPH_PERSISTENCE_ROUND_TRIP_SUPPORTED
    )
    assert value["measurement_scope"] == (
        "three-family-adjacency-structural-diversity-only"
    )
    assert value["nonclaims"] == [
        (
            "declared-family-identity-does-not-establish-software-"
            "or-scientific-independence"
        ),
        ("structural-difference-does-not-establish-statistical-independence"),
        "no-field-core-holonomy-winding-or-charge-is-read",
        "no-qualification-or-d0-d8-decision-is-made",
    ]
    assert not hasattr(receipt, "to_json")
    assert not hasattr(receipt, "write")
    assert not hasattr(type(receipt), "from_dict")
    assert not hasattr(receipt, "pass_state")
    assert not hasattr(receipt, "threshold")
    assert not hasattr(receipt, "gate_state")


def test_equal_adjacencies_are_reported_without_rejection_or_decision() -> None:
    graphs = _two_vertex_graphs()
    receipt = measure_graph_diversity(graphs)
    reordered = measure_graph_diversity((graphs[2], graphs[0], graphs[1]))

    assert not receipt.adjacency_fingerprints_pairwise_distinct
    assert receipt.pairwise[2].edge_sets_equal
    assert receipt.pairwise[2].edge_jaccard_similarity is None
    assert reordered.fingerprint_sha256 == receipt.fingerprint_sha256


def test_diversity_rejects_missing_duplicate_or_mixed_contracts() -> None:
    mutual, radius, shared = _grid_graphs()

    with pytest.raises(
        GraphContractError,
        match="exactly three graph receipts",
    ):
        measure_graph_diversity((mutual, radius))
    with pytest.raises(
        GraphContractError,
        match="exactly one receipt from each canonical graph family",
    ):
        measure_graph_diversity((mutual, mutual, shared))
    with pytest.raises(TypeError, match="graphs must be a tuple"):
        measure_graph_diversity([mutual, radius, shared])  # type: ignore[arg-type]

    _, foreign_radius, _ = _two_vertex_graphs(vertex_offset=1000)
    with pytest.raises(GraphContractError, match="same GraphInput identity"):
        measure_graph_diversity((mutual, foreign_radius, shared))

    same_values_different_unit = GraphInput(
        primary_unit_id="different-primary-unit",
        vertex_ids=mutual.graph_input.vertex_ids,
        states=mutual.graph_input.states,
    )
    different_unit_radius = construct_radius_graph(
        same_values_different_unit,
        RadiusGraphSpec(
            spec_id="different-unit-radius",
            purpose=GraphPurpose.CYCLE_CONSTRUCTION,
            radius=1.01,
        ),
    )
    with pytest.raises(GraphContractError, match="same GraphInput identity"):
        measure_graph_diversity((mutual, different_unit_radius, shared))

    _, other_purpose_radius, _ = _two_vertex_graphs(
        purpose=GraphPurpose.CYCLE_CONSTRUCTION
    )
    pair_mutual, _, pair_shared = _two_vertex_graphs(
        purpose=GraphPurpose.FIELD_ESTIMATION
    )
    with pytest.raises(GraphContractError, match="same predeclared purpose"):
        measure_graph_diversity((pair_mutual, other_purpose_radius, pair_shared))


def test_pair_records_are_factory_only() -> None:
    receipt = measure_graph_diversity(_grid_graphs())
    comparison = receipt.pairwise[0]
    values = {
        name: getattr(comparison, name)
        for name in comparison.__dataclass_fields__
        if name != "receipt_version"
    }

    with pytest.raises(GraphContractError, match="must be produced"):
        type(comparison)(**values)
    receipt_values = {
        name: getattr(receipt, name)
        for name in receipt.__dataclass_fields__
        if name != "receipt_version"
    }
    with pytest.raises(GraphContractError, match="must be produced"):
        type(receipt)(**receipt_values)
