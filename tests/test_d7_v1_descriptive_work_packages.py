from __future__ import annotations

import ast
from collections.abc import Iterator
import importlib
import importlib.util
import inspect
import os
from pathlib import Path
import shutil
import sys
from types import ModuleType

import pytest

import spirallens
import spirallens.qualification as qualification
from spirallens.core.canonical import canonical_json_bytes, sha256_bytes
from spirallens.qualification import confirmation_v1_materialization as materialization
from spirallens.qualification import (
    confirmation_v1_post_d6_descriptive as descriptive,
)
from spirallens.qualification import confirmation_v1_records as records
from spirallens.qualification.common import QualificationContractError


REPOSITORY = Path(__file__).resolve().parents[1]
FACADE_REPOSITORY_PATH = (
    "src/spirallens/qualification/confirmation_v1_post_d6_descriptive.py"
)
WORK_PACKAGE_STEMS = (
    "confirmation_v1_descriptive_common",
    "confirmation_v1_descriptive_d1",
    "confirmation_v1_descriptive_d2",
    "confirmation_v1_descriptive_d3",
    "confirmation_v1_descriptive_d4",
    "confirmation_v1_descriptive_d5_inputs",
    "confirmation_v1_descriptive_d5_outputs",
    "confirmation_v1_descriptive_independence",
)
WORK_PACKAGE_REPOSITORY_PATHS = tuple(
    f"src/spirallens/qualification/{stem}.py" for stem in WORK_PACKAGE_STEMS
)
MATERIALIZATION_HELPER_ALIASES = (
    "descriptive_common",
    "descriptive_d1",
    "descriptive_d2",
    "descriptive_d3",
    "descriptive_d4",
    "descriptive_d5_inputs",
    "descriptive_d5_outputs",
    "descriptive_independence",
)
MATERIALIZATION_REPOSITORY_PATH = (
    "src/spirallens/qualification/confirmation_v1_materialization.py"
)
RESULT_PUBLICATION_REPOSITORY_PATH = (
    "src/spirallens/qualification/confirmation_v1_result_publication.py"
)
OFFICIAL_PATHS = (
    REPOSITORY / "experiments" / "qualification" / "d7_spectral_moment_confirmation_v1",
    Path("/Users/ryohiga/SpiralReality/.spirallens-d7-v1-store.staging"),
    Path("/Users/ryohiga/SpiralReality/spirallens-d7-v1-store"),
)

EXPECTED_RESULT_BYTE_COUNT = 5_308_075
EXPECTED_RESULT_SHA256 = (
    "bc8b324794a096e915ac4cde57446c2d912e7c94bda68e2d4a0584bff7515680"
)
EXPECTED_RESULT_ID = "d7-v1-post-d6-descriptive-9d75fb73d554f171bd92009a"
EXPECTED_ROOT_ALL_SHA256 = (
    "a67ce5620fe4a53824cc2b3e0e0b4d46a452298a72fdaa8974ace14e97f13b7c"
)
EXPECTED_QUALIFICATION_ALL_SHA256 = (
    "4dab13d8a847400280682f61fcf0b03fdd9ad51c68d8909ab63a463d07579023"
)


def _restore_authenticated_referent_documents_origin() -> None:
    loaded = sys.modules.get(
        "spirallens.qualification.confirmation_v1_design_referent_documents"
    )
    referents = sys.modules.get(
        "spirallens.qualification.confirmation_v1_full_design_referents"
    )
    authenticated = getattr(
        referents,
        "_AUTHENTICATED_REFERENT_DOCUMENTS_MODULE",
        None,
    )
    if loaded is not None and loaded is authenticated:
        workspace_leaf = REPOSITORY / (
            "src/spirallens/qualification/confirmation_v1_design_referent_documents.py"
        )
        loaded.__file__ = str(workspace_leaf)
        if loaded.__spec__ is not None:
            loaded.__spec__.origin = str(workspace_leaf)


@pytest.fixture(autouse=True)
def _isolate_authenticated_referent_documents(tmp_path: Path) -> Iterator[None]:
    _restore_authenticated_referent_documents_origin()
    try:
        yield
    finally:
        _restore_authenticated_referent_documents_origin()
        shutil.rmtree(tmp_path, ignore_errors=True)


def _load_test_module(repository_name: str, module_name: str) -> ModuleType:
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    path = REPOSITORY / "tests" / repository_name
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load test helpers from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    return module


def _descriptive_test_helpers() -> ModuleType:
    return _load_test_module(
        "test_d7_v1_descriptive_and_entrypoints.py",
        "_spirallens_pr49_descriptive_test_helpers",
    )


def _materialization_test_helpers() -> ModuleType:
    return _load_test_module(
        "test_d7_v1_materialization.py",
        "_spirallens_pr49_materialization_test_helpers",
    )


def _work_package_modules() -> tuple[ModuleType, ...]:
    return tuple(
        importlib.import_module(f"spirallens.qualification.{stem}")
        for stem in WORK_PACKAGE_STEMS
    )


def _local_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name.rsplit(".", 1)[-1] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                result.add(node.module.rsplit(".", 1)[-1])
            if node.level and node.module is None:
                result.update(alias.name for alias in node.names)
    return result


def _imported_modules(tree: ast.AST) -> set[str]:
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                result.add(node.module)
            elif node.level:
                result.update(alias.name for alias in node.names)
    return result


@pytest.fixture(scope="module")
def descriptive_case() -> tuple[
    ModuleType, tuple[bytes, ...], tuple[object, object], object
]:
    helpers = _descriptive_test_helpers()
    sources = helpers.historical_sources.__wrapped__()
    parents = helpers._attempt_and_receipt()
    result = helpers._derive_result(sources, parents)
    return helpers, sources, parents, result


def test_facade_preserves_the_exact_pre_refactor_result_bytes(
    descriptive_case: tuple[
        ModuleType,
        tuple[bytes, ...],
        tuple[object, object],
        object,
    ],
) -> None:
    helpers, sources, parents, result = descriptive_case
    assert isinstance(result, records.D7V1PostselectionDescriptiveResult)
    assert result.to_dict()["record_id"] == EXPECTED_RESULT_ID
    assert result.byte_count == EXPECTED_RESULT_BYTE_COUNT
    assert result.canonical_sha256 == EXPECTED_RESULT_SHA256
    assert result.to_dict()["payload"]["status"] == "insufficient"
    assert helpers._verify_result(result, sources, parents) is result


def test_work_packages_are_private_and_facade_signatures_remain_stable() -> None:
    modules = _work_package_modules()
    assert descriptive.__all__ == ()
    assert all(module.__all__ == () for module in modules)
    assert not set(WORK_PACKAGE_STEMS) & set(qualification.__all__)
    assert sha256_bytes(canonical_json_bytes(spirallens.__all__)) == (
        EXPECTED_ROOT_ALL_SHA256
    )
    assert sha256_bytes(canonical_json_bytes(qualification.__all__)) == (
        EXPECTED_QUALIFICATION_ALL_SHA256
    )

    derive = inspect.signature(
        descriptive._derive_d7_v1_post_d6_descriptive_result
    ).parameters
    verify = inspect.signature(
        descriptive._verify_d7_v1_post_d6_descriptive_result
    ).parameters
    sources = (
        "historical_plan_source",
        "parent_protocol_source",
        "parent_result_source",
        "parent_manifest_source",
        "parent_consumption_source",
        "parent_d6_decision_source",
        "parent_attempt",
        "chronology_receipt",
    )
    assert tuple(derive) == sources
    assert all(item.kind is inspect.Parameter.KEYWORD_ONLY for item in derive.values())
    assert tuple(verify) == ("candidate", *sources)
    assert verify["candidate"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert all(verify[name].kind is inspect.Parameter.KEYWORD_ONLY for name in sources)


def test_documentation_projects_only_the_pre_s_internal_refactor() -> None:
    projections = {
        "README.md": (
            "4,699-line descriptive implementation",
            "287-line facade",
            "source-S blob",
            "commit S has not been selected",
        ),
        "docs/ROADMAP.md": (
            "4,699-line module",
            "287-line facade",
            "C1 member tuple",
            "S remains unselected",
        ),
        "docs/EXPERIMENT_INTERPRETATION_LEDGER.md": (
            "### 3.21 D7 v1 descriptive work-package split",
            "5,308,075 canonical bytes",
            EXPECTED_RESULT_SHA256,
            "This refactor creates no source closure and selects no S",
        ),
        "docs/SCHEMA_CHANGELOG.md": (
            "D7 v1 descriptive private work-package split",
            "canonical 5,308,075-byte result remain unchanged",
            "S remains unselected",
            "no schema, artifact, authority, public API",
        ),
    }
    for repository_path, required in projections.items():
        source = (REPOSITORY / repository_path).read_text(encoding="utf-8")
        normalized = " ".join(source.split())
        assert all(item in normalized for item in required)


def test_work_packages_have_no_io_model_legacy_or_import_side_effects() -> None:
    helpers = _materialization_test_helpers()
    before = {path: helpers._filesystem_snapshot(path) for path in OFFICIAL_PATHS}
    for module in (descriptive, *_work_package_modules()):
        importlib.reload(module)
    assert {path: helpers._filesystem_snapshot(path) for path in OFFICIAL_PATHS} == (
        before
    )

    allowed_imports = {
        "__future__",
        "collections",
        "collections.abc",
        "dataclasses",
        "math",
        "spirallens.core.canonical",
        "common",
        "confirmation_v1_records",
        *WORK_PACKAGE_STEMS,
    }
    forbidden_calls = {
        "Popen",
        "__import__",
        "compile",
        "eval",
        "exec",
        "from_pretrained",
        "getattr",
        "load_model",
        "mkdir",
        "open",
        "read_bytes",
        "read_text",
        "remove",
        "rename",
        "rmdir",
        "rmtree",
        "run",
        "system",
        "unlink",
        "write_bytes",
        "write_text",
    }
    for repository_path in (FACADE_REPOSITORY_PATH, *WORK_PACKAGE_REPOSITORY_PATHS):
        path = REPOSITORY.joinpath(*repository_path.split("/"))
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        assert _imported_modules(tree) <= allowed_imports
        called = {
            node.func.id if isinstance(node.func, ast.Name) else node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, (ast.Name, ast.Attribute))
        }
        assert forbidden_calls.isdisjoint(called)
        assert not any(name.startswith("_git") for name in called)


def test_facade_and_materialization_are_the_only_work_package_consumers() -> None:
    helper_set = set(WORK_PACKAGE_STEMS)
    facade_stem = Path(FACADE_REPOSITORY_PATH).stem
    facade_imports = _local_imports(
        REPOSITORY.joinpath(*FACADE_REPOSITORY_PATH.split("/"))
    )
    assert facade_imports & helper_set == helper_set

    consumers: dict[str, set[str]] = {}
    excluded = {FACADE_REPOSITORY_PATH, *WORK_PACKAGE_REPOSITORY_PATHS}
    for path in (REPOSITORY / "src" / "spirallens").rglob("*.py"):
        repository_path = path.relative_to(REPOSITORY).as_posix()
        if repository_path in excluded:
            continue
        direct = _local_imports(path) & helper_set
        if direct:
            consumers[repository_path] = direct
    assert consumers == {MATERIALIZATION_REPOSITORY_PATH: helper_set}

    materialization_path = REPOSITORY.joinpath(
        *MATERIALIZATION_REPOSITORY_PATH.split("/")
    )
    materialization_tree = ast.parse(
        materialization_path.read_text(encoding="utf-8"),
        filename=str(materialization_path),
    )
    registry = next(
        node.value
        for node in materialization_tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "_DESCRIPTIVE_HELPER_MODULES"
            for target in node.targets
        )
    )
    registry_names = {
        node.id
        for node in ast.walk(registry)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }
    assert registry_names == set(MATERIALIZATION_HELPER_ALIASES)
    for alias in MATERIALIZATION_HELPER_ALIASES:
        assert (
            sum(
                isinstance(node, ast.Name)
                and isinstance(node.ctx, ast.Load)
                and node.id == alias
                for node in ast.walk(materialization_tree)
            )
            == 1
        )

    for repository_path in (
        MATERIALIZATION_REPOSITORY_PATH,
        RESULT_PUBLICATION_REPOSITORY_PATH,
    ):
        imports = _local_imports(REPOSITORY.joinpath(*repository_path.split("/")))
        assert facade_stem in imports


def test_work_packages_are_c1_bound_and_fail_closed_on_origin_or_source_drift(
    tmp_path: Path,
) -> None:
    helpers = _materialization_test_helpers()
    try:
        case = helpers._build_case(tmp_path / "joined")
        joined = helpers._load_stage(case)
        assert joined.source_commit == case.source_commit
        c1 = case.records_by_role[records.D7V1C1SourceSetRecord.artifact_role]
        member_paths = {
            item["repository_path"]
            for item in c1.to_dict()["payload"]["source_members"]
        }
        assert materialization._DESCRIPTIVE_HELPER_PATHS == (
            WORK_PACKAGE_REPOSITORY_PATHS
        )
        assert set(WORK_PACKAGE_REPOSITORY_PATHS) <= member_paths

        modules_by_path = {
            repository_path: module
            for module, repository_path, _label in (
                materialization._DESCRIPTIVE_HELPER_MODULES
            )
        }
        for repository_path in WORK_PACKAGE_REPOSITORY_PATHS:
            target = case.repository.joinpath(*repository_path.split("/"))
            imported = Path(modules_by_path[repository_path].__file__)
            source = target.read_bytes()
            assert target.samefile(imported)

            target.unlink()
            target.write_bytes(source)
            with pytest.raises(QualificationContractError, match="import origin"):
                materialization._require_import_origins(case.context)

            target.write_bytes(source + b"\n")
            with pytest.raises(QualificationContractError, match="reviewed source S"):
                materialization._require_executing_sources_match_commit(
                    case.context,
                    case.source_commit,
                )

            target.unlink()
            os.link(imported, target)

        def omit_first_helper(
            members: tuple[records.D7V1SourceMember, ...],
        ) -> tuple[records.D7V1SourceMember, ...]:
            omitted = WORK_PACKAGE_REPOSITORY_PATHS[0]
            return tuple(
                member for member in members if member.repository_path != omitted
            )

        omitted_case = helpers._build_case(
            tmp_path / "omitted",
            mutate_source_member=omit_first_helper,
        )
        with pytest.raises(
            QualificationContractError,
            match="C1 source members differ from the exact choice-free Git tree",
        ):
            helpers._load_stage(omitted_case)
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)
