from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from spirallens._repository_context import RepositoryContext
from spirallens.atlas.engineering_run import (
    PublicExamplePlumbingRunError,
    run_public_example_plumbing,
)
from spirallens.atlas.engineering_protocol import (
    load_public_example_plumbing_protocol,
)
from spirallens.qualification import QualificationContractError
from spirallens.qualification.preparation import (
    build_current_qualification_engine_binding,
)

REPOSITORY = Path(__file__).resolve().parents[1]


def test_repository_context_is_absolute_and_authority_free(
    tmp_path: Path,
) -> None:
    context = RepositoryContext(root=tmp_path.resolve())

    assert context.root == tmp_path.resolve()
    with pytest.raises(ValueError, match="must be absolute"):
        RepositoryContext(root=Path("relative"))
    with pytest.raises(TypeError, match="must be a Path"):
        RepositoryContext(root="/not-a-path")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="lexically normalized"):
        RepositoryContext(root=tmp_path / "nested" / "..")


def test_repository_context_compares_physical_import_identity(
    tmp_path: Path,
) -> None:
    root = tmp_path / "declared"
    expected = root / "src/spirallens/example.py"
    expected.parent.mkdir(parents=True)
    expected.write_text("VALUE = 1\n", encoding="utf-8")
    copy = tmp_path / "adjacent" / "src/spirallens/example.py"
    copy.parent.mkdir(parents=True)
    copy.write_bytes(expected.read_bytes())
    alias = tmp_path / "same-file-alias.py"
    alias.symlink_to(expected)
    context = RepositoryContext(root=root.resolve())

    assert context.matches_imported_file(
        imported_file=alias,
        repository_path="src/spirallens/example.py",
    )
    assert not context.matches_imported_file(
        imported_file=copy,
        repository_path="src/spirallens/example.py",
    )
    with pytest.raises(ValueError, match="repository-relative"):
        context.matches_imported_file(
            imported_file=expected,
            repository_path="../example.py",
        )


@pytest.mark.parametrize(
    "consumer",
    (
        build_current_qualification_engine_binding,
        run_public_example_plumbing,
    ),
)
def test_repository_bound_consumers_require_explicit_root(
    consumer: object,
) -> None:
    parameter = inspect.signature(consumer).parameters["repository_root"]

    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is inspect.Parameter.empty


def _write_adjacent_source_copy(root: Path, repository_path: str) -> None:
    current = REPOSITORY / repository_path
    target = root / repository_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(current.read_bytes())


def _link_current_source(root: Path, repository_path: str) -> None:
    target = root / repository_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(REPOSITORY / repository_path)


def test_public_example_runner_rejects_an_adjacent_checkout(
    tmp_path: Path,
) -> None:
    adjacent = tmp_path / "adjacent"
    _write_adjacent_source_copy(
        adjacent,
        "src/spirallens/atlas/engineering_run.py",
    )
    _write_adjacent_source_copy(adjacent, "src/spirallens/adapters/pythia.py")

    with pytest.raises(PublicExamplePlumbingRunError, match="import origin"):
        run_public_example_plumbing(
            repository_root=adjacent,
            protocol_path=tmp_path / "unused-protocol.yaml",
            output_dir=tmp_path / "unused-output",
            receipt_path=tmp_path / "unused-receipt.json",
            expected_protocol_source_sha256="a" * 64,
            expected_protocol_canonical_sha256="b" * 64,
        )


def test_public_example_runner_rejects_adjacent_adapter_after_runner_join(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adjacent = tmp_path / "adjacent"
    _link_current_source(
        adjacent,
        "src/spirallens/atlas/engineering_run.py",
    )
    _link_current_source(
        adjacent,
        "src/spirallens/atlas/engineering_protocol.py",
    )
    _write_adjacent_source_copy(adjacent, "src/spirallens/adapters/pythia.py")
    protocol_path = (
        REPOSITORY / "protocols/pythia70_public_example_plumbing_v0_1.yaml"
    )
    loaded = load_public_example_plumbing_protocol(protocol_path)
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("HUGGING_FACE_HUB_TOKEN", raising=False)

    with pytest.raises(PublicExamplePlumbingRunError, match="Pythia adapter"):
        run_public_example_plumbing(
            repository_root=adjacent,
            protocol_path=protocol_path,
            output_dir=tmp_path / "unused-output",
            receipt_path=tmp_path / "unused-receipt.json",
            expected_protocol_source_sha256=loaded.source_sha256,
            expected_protocol_canonical_sha256=loaded.canonical_sha256,
        )


def test_public_example_runner_rejects_adjacent_protocol_after_runner_join(
    tmp_path: Path,
) -> None:
    adjacent = tmp_path / "adjacent"
    _link_current_source(
        adjacent,
        "src/spirallens/atlas/engineering_run.py",
    )
    _write_adjacent_source_copy(
        adjacent,
        "src/spirallens/atlas/engineering_protocol.py",
    )

    with pytest.raises(
        PublicExamplePlumbingRunError,
        match="engineering protocol import origin",
    ):
        run_public_example_plumbing(
            repository_root=adjacent,
            protocol_path=tmp_path / "unused-protocol.yaml",
            output_dir=tmp_path / "unused-output",
            receipt_path=tmp_path / "unused-receipt.json",
            expected_protocol_source_sha256="a" * 64,
            expected_protocol_canonical_sha256="b" * 64,
        )


def test_current_engine_binding_rejects_an_adjacent_checkout(
    tmp_path: Path,
) -> None:
    adjacent = tmp_path / "adjacent"
    _write_adjacent_source_copy(
        adjacent,
        "src/spirallens/qualification/preparation.py",
    )
    _write_adjacent_source_copy(
        adjacent,
        "src/spirallens/qualification/runner.py",
    )

    with pytest.raises(QualificationContractError, match="import origin"):
        build_current_qualification_engine_binding(
            engine_commit="a" * 40,
            repository_root=adjacent,
        )


def test_current_engine_binding_rejects_adjacent_runner_after_preparation_join(
    tmp_path: Path,
) -> None:
    adjacent = tmp_path / "adjacent"
    _link_current_source(
        adjacent,
        "src/spirallens/qualification/preparation.py",
    )
    _write_adjacent_source_copy(
        adjacent,
        "src/spirallens/qualification/runner.py",
    )

    with pytest.raises(QualificationContractError, match="runner closure"):
        build_current_qualification_engine_binding(
            engine_commit="a" * 40,
            repository_root=adjacent,
        )
