from __future__ import annotations

import numpy as np
import pytest

from spirallens.graphs import domain as domain_module
from spirallens.graphs.common import GraphContractError
from spirallens.graphs.contracts import GraphInput
from spirallens.graphs.domain import (
    MAX_DOMAIN_ESTIMATED_PEAK_BYTES,
    build_discrete_domain_complex,
)


def _grid_input(side: int = 3) -> GraphInput:
    states = np.array(
        [(float(x), float(y)) for y in range(side) for x in range(side)],
        dtype="<f8",
    )
    return GraphInput(
        primary_unit_id="grid-unit",
        vertex_ids=np.arange(100, 100 + side * side, dtype="<i8"),
        states=states,
    )


def _grid_faces(side: int = 3) -> np.ndarray:
    faces: list[tuple[int, int, int]] = []
    for y in range(side - 1):
        for x in range(side - 1):
            lower_left = y * side + x
            lower_right = lower_left + 1
            upper_left = lower_left + side
            upper_right = upper_left + 1
            faces.extend(
                [
                    (lower_left, lower_right, upper_right),
                    (lower_left, upper_right, upper_left),
                ]
            )
    return np.asarray(faces, dtype="<i8")


def test_domain_builds_exact_integer_chain_complex_with_immutable_arrays() -> None:
    graph_input = _grid_input()
    domain = build_discrete_domain_complex(
        graph_input,
        _grid_faces(),
        domain_id="grid-domain",
        primary_unit_id="grid-unit",
    )

    assert domain.canonical_faces.shape == (8, 3)
    assert domain.canonical_edges.shape == (16, 2)
    assert domain.boundary_1.shape == (9, 16)
    assert domain.boundary_2.shape == (16, 8)
    assert np.array_equal(
        domain.boundary_1 @ domain.boundary_2,
        np.zeros((9, 8), dtype="<i8"),
    )
    assert domain.domain_boundary_directed_edges.shape == (8, 2)
    assert domain.estimated_peak_bytes <= MAX_DOMAIN_ESTIMATED_PEAK_BYTES
    assert domain.canonical_faces.flags.writeable is False
    assert domain.boundary_1.flags.writeable is False
    with pytest.raises(ValueError):
        domain.boundary_2.setflags(write=True)

    receipt = domain.to_dict()
    assert receipt["record_scope"] == "in-memory-fingerprint-only"
    assert receipt["persistence_round_trip_supported"] is False
    assert receipt["chain_identity"] == (
        "boundary_1-times-boundary_2-equals-zero-exactly"
    )
    assert receipt["latent_manifold_triangulation_claimed"] is False
    assert receipt["continuous_topology_claimed"] is False
    assert receipt["homology_claimed"] is False
    assert receipt["d0_d8_advanced"] is False


def test_face_canonicalization_rotates_without_reflecting_handedness() -> None:
    graph_input = _grid_input()
    faces = _grid_faces()
    rotated = np.asarray(
        [(face[1], face[2], face[0]) for face in reversed(faces)],
        dtype="<i8",
    )
    domain = build_discrete_domain_complex(
        graph_input,
        rotated,
        domain_id="rotated-domain",
        primary_unit_id="grid-unit",
    )
    reflected = build_discrete_domain_complex(
        graph_input,
        faces[:, ::-1],
        domain_id="reflected-domain",
        primary_unit_id="grid-unit",
    )
    original = build_discrete_domain_complex(
        graph_input,
        faces,
        domain_id="original-domain",
        primary_unit_id="grid-unit",
    )

    assert (
        np.array_equal(domain.canonical_faces, np.sort(domain.canonical_faces, axis=0))
        is False
    )
    assert np.array_equal(
        domain.canonical_faces,
        original.canonical_faces,
    )
    original_face_columns = {
        tuple(sorted(int(item) for item in face)): index
        for index, face in enumerate(original.canonical_faces)
    }
    for reflected_index, face in enumerate(reflected.canonical_faces):
        original_index = original_face_columns[
            tuple(sorted(int(item) for item in face))
        ]
        assert np.array_equal(
            reflected.boundary_2[:, reflected_index],
            -original.boundary_2[:, original_index],
        )


@pytest.mark.parametrize(
    "faces, message",
    [
        (
            np.array([(0, 1, 4), (0, 1, 3)], dtype="<i8"),
            "opposite orientations",
        ),
        (
            np.array([(0, 1, 4), (0, 1, 3), (0, 1, 2)], dtype="<i8"),
            "more than two",
        ),
        (
            np.array([(0, 1, 4), (4, 5, 8)], dtype="<i8"),
            "edge-connected",
        ),
        (
            np.array([(0, 1, 4), (4, 1, 0)], dtype="<i8"),
            "only once",
        ),
        (
            np.array([(0, 0, 1)], dtype="<i8"),
            "distinct",
        ),
        (
            np.array([(0, 1, 9)], dtype="<i8"),
            "outside",
        ),
    ],
)
def test_domain_rejects_invalid_incidence_orientation_and_rows(
    faces: np.ndarray,
    message: str,
) -> None:
    with pytest.raises(GraphContractError, match=message):
        build_discrete_domain_complex(
            _grid_input(),
            faces,
            domain_id="invalid-domain",
            primary_unit_id="grid-unit",
        )


def test_domain_rejects_non_integer_or_empty_face_contracts() -> None:
    graph_input = _grid_input()
    for faces in (
        np.empty((0, 3), dtype="<i8"),
        np.zeros((1, 4), dtype="<i8"),
        np.zeros((1, 3), dtype="<f8"),
    ):
        with pytest.raises(GraphContractError):
            build_discrete_domain_complex(
                graph_input,
                faces,
                domain_id="invalid-domain",
                primary_unit_id="grid-unit",
            )


def test_domain_preflights_resource_bound_and_primary_unit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph_input = _grid_input()
    with pytest.raises(GraphContractError, match="primary_unit_id"):
        build_discrete_domain_complex(
            graph_input,
            _grid_faces(),
            domain_id="wrong-unit-domain",
            primary_unit_id="different-unit",
        )

    monkeypatch.setattr(domain_module, "MAX_DOMAIN_ESTIMATED_PEAK_BYTES", 1)
    with pytest.raises(GraphContractError, match="resource cap"):
        build_discrete_domain_complex(
            graph_input,
            _grid_faces(),
            domain_id="oversized-domain",
            primary_unit_id="grid-unit",
        )
