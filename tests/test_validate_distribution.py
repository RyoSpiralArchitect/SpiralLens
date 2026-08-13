from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

_VALIDATOR_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "validate_distribution.py"
)
_VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    "_spirallens_validate_distribution",
    _VALIDATOR_PATH,
)
assert _VALIDATOR_SPEC is not None
assert _VALIDATOR_SPEC.loader is not None
_VALIDATOR = importlib.util.module_from_spec(_VALIDATOR_SPEC)
_VALIDATOR_SPEC.loader.exec_module(_VALIDATOR)

DEFAULT_IMPORTS = _VALIDATOR.DEFAULT_IMPORTS
DEFAULT_SCIENTIFIC_IMPORTS = _VALIDATOR.DEFAULT_SCIENTIFIC_IMPORTS
ATLAS_PUBLIC_EXPORTS = _VALIDATOR.ATLAS_PUBLIC_EXPORTS
ATLAS_READER_FORBIDDEN_IMPORTS = _VALIDATOR.ATLAS_READER_FORBIDDEN_IMPORTS
ATLAS_READER_IMPORTS = _VALIDATOR.ATLAS_READER_IMPORTS
ATLAS_READER_SYMBOL_MODULES = _VALIDATOR.ATLAS_READER_SYMBOL_MODULES
DistributionValidationError = _VALIDATOR.DistributionValidationError
REPORT_SCHEMA_VERSION = _VALIDATOR.REPORT_SCHEMA_VERSION
REPOSITORY_EXPERIMENT_WHEEL_MEMBER_PREFIXES = (
    _VALIDATOR.REPOSITORY_EXPERIMENT_WHEEL_MEMBER_PREFIXES
)
REPOSITORY_EXPERIMENT_MODULES = _VALIDATOR.REPOSITORY_EXPERIMENT_MODULES
REPOSITORY_EXPERIMENT_SOURCE_PATHS = _VALIDATOR.REPOSITORY_EXPERIMENT_SOURCE_PATHS
REQUIRED_WHEEL_MEMBERS = _VALIDATOR.REQUIRED_WHEEL_MEMBERS
_classify_repository_experiment_members = (
    _VALIDATOR._classify_repository_experiment_members
)
_classify_repository_experiment_sdist_members = (
    _VALIDATOR._classify_repository_experiment_sdist_members
)
_library_separation_report = _VALIDATOR._library_separation_report
_load_public_package_exports = _VALIDATOR._load_public_package_exports
_parse_repository_experiment_absence_probe_output = (
    _VALIDATOR._parse_repository_experiment_absence_probe_output
)
_parse_atlas_reader_probe_output = _VALIDATOR._parse_atlas_reader_probe_output
_parse_probe_output = _VALIDATOR._parse_probe_output
_repository_experiment_source_report = _VALIDATOR._repository_experiment_source_report
_require_zero_repository_experiment_members = (
    _VALIDATOR._require_zero_repository_experiment_members
)
_sha256_file = _VALIDATOR._sha256_file

CURRENT_REPOSITORY_EXPERIMENT_WHEEL_MEMBERS = tuple(
    path.removeprefix("src/") for path in REPOSITORY_EXPERIMENT_SOURCE_PATHS
)

PRIVATE_HELD_FILE_WHEEL_MEMBER = "spirallens/_held_file.py"
PRIVATE_HELD_FILE_IMPORT = "spirallens._held_file"
PRIVATE_ATLAS_CAPTURE_STORE_WHEEL_MEMBER = "spirallens/atlas/_capture_store.py"
PRIVATE_STRICT_YAML_WHEEL_MEMBER = "spirallens/core/_strict_yaml.py"


def test_sha256_file_streams_exact_bytes(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.whl"
    payload = b"spirallens-wheel-fixture"
    artifact.write_bytes(payload)

    assert _sha256_file(artifact) == hashlib.sha256(payload).hexdigest()


def _write_synthetic_wheel(wheel: Path, members: tuple[str, ...]) -> None:
    with zipfile.ZipFile(wheel, mode="w") as archive:
        for member in members:
            archive.writestr(member, "")


def _write_synthetic_sdist(sdist: Path, members: tuple[str, ...]) -> None:
    with tarfile.open(sdist, mode="w:gz") as archive:
        for member in members:
            info = tarfile.TarInfo(member)
            info.size = 0
            archive.addfile(info, io.BytesIO())


def _write_source_inventory(root: Path, paths: tuple[str, ...]) -> None:
    for relative in paths:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# repository experiment\n", encoding="utf-8")


def test_repository_experiment_members_are_classified_from_wheel_paths(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "synthetic.whl"
    matching_members = (
        "spirallens/access/_pythia160_preobservation.py",
        "spirallens/qualification/confirmation_v1_records.py",
    )
    _write_synthetic_wheel(
        wheel,
        (
            "spirallens/qualification/public_surface.py",
            matching_members[1],
            "spirallens/access/pythia.py",
            matching_members[0],
        ),
    )

    assert _classify_repository_experiment_members(wheel) == tuple(
        sorted(matching_members)
    )


def test_new_matching_wheel_member_is_classified_without_an_allowlist(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "synthetic.whl"
    new_member = "spirallens/qualification/confirmation_v1_future_module.py"
    _write_synthetic_wheel(wheel, (new_member,))

    assert _classify_repository_experiment_members(wheel) == (new_member,)


def test_pep3147_matching_wheel_member_is_classified(tmp_path: Path) -> None:
    wheel = tmp_path / "synthetic.whl"
    member = (
        "spirallens/qualification/__pycache__/confirmation_v1_records.cpython-313.pyc"
    )
    _write_synthetic_wheel(wheel, (member,))

    assert _classify_repository_experiment_members(wheel) == (member,)


def test_repository_experiment_members_are_classified_from_sdist_paths(
    tmp_path: Path,
) -> None:
    sdist = tmp_path / "synthetic.tar.gz"
    matching = (
        "spirallens-0.1.0/src/spirallens/access/_pythia160_preobservation.py",
        "spirallens-0.1.0/src/spirallens/qualification/confirmation_v1_records.py",
    )
    _write_synthetic_sdist(
        sdist,
        (
            "spirallens-0.1.0/src/spirallens/access/contracts.py",
            matching[1],
            matching[0],
        ),
    )

    assert _classify_repository_experiment_sdist_members(sdist) == tuple(
        sorted(matching)
    )


def test_source_inventory_requires_the_exact_reviewed_regular_22_paths(
    tmp_path: Path,
) -> None:
    _write_source_inventory(tmp_path, REPOSITORY_EXPERIMENT_SOURCE_PATHS)

    assert _repository_experiment_source_report(tmp_path) == {
        "observation": "reviewed-exact-set-present",
        "count": 22,
        "all_regular_files": True,
        "total_lines": 22,
        "paths": list(REPOSITORY_EXPERIMENT_SOURCE_PATHS),
    }


def test_source_inventory_rejects_a_future_matching_prefix(tmp_path: Path) -> None:
    _write_source_inventory(tmp_path, REPOSITORY_EXPERIMENT_SOURCE_PATHS)
    future = tmp_path / "src/spirallens/qualification/confirmation_v1_future_module.py"
    future.write_text("# unreviewed\n", encoding="utf-8")

    with pytest.raises(DistributionValidationError, match="unexpected=.*future"):
        _repository_experiment_source_report(tmp_path)


def test_source_inventory_rejects_a_nonregular_reviewed_target(
    tmp_path: Path,
) -> None:
    _write_source_inventory(tmp_path, REPOSITORY_EXPERIMENT_SOURCE_PATHS[1:])
    nonregular = tmp_path / REPOSITORY_EXPERIMENT_SOURCE_PATHS[0]
    nonregular.mkdir(parents=True)

    with pytest.raises(DistributionValidationError, match="non-regular paths"):
        _repository_experiment_source_report(tmp_path)


def test_source_inventory_rejects_a_symlinked_package_ancestor(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside-access"
    for relative in REPOSITORY_EXPERIMENT_SOURCE_PATHS:
        if "/access/" not in relative:
            continue
        path = outside / Path(relative).name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# outside source\n", encoding="utf-8")
    (tmp_path / "src/spirallens").mkdir(parents=True)
    (tmp_path / "src/spirallens/access").symlink_to(outside)
    _write_source_inventory(
        tmp_path,
        tuple(
            path
            for path in REPOSITORY_EXPERIMENT_SOURCE_PATHS
            if "/qualification/" in path
        ),
    )

    with pytest.raises(
        DistributionValidationError,
        match="non-directory, or symlinked ancestors.*access",
    ):
        _repository_experiment_source_report(tmp_path)


def test_zero_artifact_members_is_bounded_absence_not_library_readiness() -> None:
    source_tree = {
        "observation": "reviewed-exact-set-present",
        "count": 22,
        "all_regular_files": True,
        "total_lines": 19190,
        "paths": list(REPOSITORY_EXPERIMENT_SOURCE_PATHS),
    }
    absent = _require_zero_repository_experiment_members((), artifact_kind="fixture")

    assert _library_separation_report(
        source_tree=source_tree,
        sdist=absent,
        direct_source_wheel=absent,
        sdist_derived_wheel=absent,
    ) == {
        "repository_experiment_separation": {
            "source_tree": source_tree,
            "sdist": absent,
            "direct_source_wheel": absent,
            "sdist_derived_wheel": absent,
            "source_prefixes": [
                "src/spirallens/access/_pythia160_",
                "src/spirallens/qualification/confirmation_v1_",
            ],
            "wheel_prefixes": list(REPOSITORY_EXPERIMENT_WHEEL_MEMBER_PREFIXES),
        },
        "closed_library_allowlist_established": False,
        "grants": {
            "authority": False,
            "library": False,
            "public_api": False,
            "scientific": False,
        },
    }


def test_private_held_file_is_an_explicit_non_experiment_wheel_import() -> None:
    assert PRIVATE_HELD_FILE_WHEEL_MEMBER in REQUIRED_WHEEL_MEMBERS
    assert PRIVATE_HELD_FILE_IMPORT in DEFAULT_IMPORTS
    assert not any(
        PRIVATE_HELD_FILE_WHEEL_MEMBER.startswith(prefix)
        for prefix in REPOSITORY_EXPERIMENT_WHEEL_MEMBER_PREFIXES
    )


def test_private_strict_yaml_factory_is_an_explicit_wheel_member() -> None:
    assert PRIVATE_STRICT_YAML_WHEEL_MEMBER in REQUIRED_WHEEL_MEMBERS
    assert not any(
        PRIVATE_STRICT_YAML_WHEEL_MEMBER.startswith(prefix)
        for prefix in REPOSITORY_EXPERIMENT_WHEEL_MEMBER_PREFIXES
    )


def test_atlas_reader_probe_is_separate_from_dependency_free_imports() -> None:
    assert REPORT_SCHEMA_VERSION == "spirallens.distribution-validation.v0.5"
    assert set(ATLAS_READER_IMPORTS).isdisjoint(DEFAULT_IMPORTS)
    assert ATLAS_READER_IMPORTS == (
        "spirallens.atlas",
        "spirallens.atlas.store",
        "spirallens.atlas.engineering_receipt",
    )
    assert ATLAS_READER_FORBIDDEN_IMPORTS == (
        "torch",
        "transformers",
        "huggingface_hub",
        "safetensors",
        "spirallens.adapters",
        "spirallens.atlas.id_sweep",
        "spirallens.atlas.engineering_run",
        "spirallens.atlas._capture_store",
    )
    assert PRIVATE_ATLAS_CAPTURE_STORE_WHEEL_MEMBER in REQUIRED_WHEEL_MEMBERS


def _probe(
    environment_root: Path,
    *,
    origins_root: Path | None = None,
    forbidden: list[str] | None = None,
    editable: bool = False,
) -> str:
    root = environment_root if origins_root is None else origins_root
    return json.dumps(
        {
            "distribution_root": str(root / "site-packages"),
            "direct_url": (
                {"dir_info": {"editable": True}}
                if editable
                else {"archive_info": {}, "url": "file:///artifact.whl"}
            ),
            "forbidden_imports_loaded": ([] if forbidden is None else forbidden),
            "help_exit_code": 0,
            "help_stderr": "",
            "help_stdout": "usage: spirallens [-h]\n",
            "module_origins": {
                name: str(
                    root / "site-packages" / Path(*name.split(".")) / "__init__.py"
                )
                for name in DEFAULT_IMPORTS
            },
            "package_version": "0.1.0",
        }
    )


def _atlas_reader_probe(
    environment_root: Path,
    *,
    origins_root: Path | None = None,
    forbidden: list[str] | None = None,
    public_exports: list[str] | None = None,
) -> str:
    root = environment_root if origins_root is None else origins_root
    return json.dumps(
        {
            "dependencies_loaded": ["numpy", "yaml"],
            "dir_includes_public_exports": True,
            "distribution_root": str(root / "site-packages"),
            "direct_url": {
                "archive_info": {},
                "url": "file:///artifact.whl",
            },
            "forbidden_imports_loaded": ([] if forbidden is None else forbidden),
            "module_origins": {
                name: str(
                    root / "site-packages" / Path(*name.split(".")) / "__init__.py"
                )
                for name in ATLAS_READER_IMPORTS
            },
            "package_version": "0.1.0",
            "public_exports": (
                list(ATLAS_PUBLIC_EXPORTS) if public_exports is None else public_exports
            ),
            "reader_symbol_identities": True,
            "reader_symbol_modules": ATLAS_READER_SYMBOL_MODULES,
        }
    )


def test_atlas_reader_probe_accepts_exact_non_editable_wheel_receipt(
    tmp_path: Path,
) -> None:
    environment_root = tmp_path / "scientific-venv"

    assert _parse_atlas_reader_probe_output(
        _atlas_reader_probe(environment_root),
        environment_root=environment_root,
        required_imports=ATLAS_READER_IMPORTS,
    ) == {
        "dependencies_loaded": ["numpy", "yaml"],
        "direct_url_editable": False,
        "dir_includes_public_exports": True,
        "distribution_root": "site-packages",
        "forbidden_imports_loaded": [],
        "module_origins": {
            name: ("site-packages/" + Path(*name.split("."), "__init__.py").as_posix())
            for name in ATLAS_READER_IMPORTS
        },
        "package_version": "0.1.0",
        "public_exports": list(ATLAS_PUBLIC_EXPORTS),
        "reader_symbol_identities": True,
        "reader_symbol_modules": dict(ATLAS_READER_SYMBOL_MODULES),
    }


def test_atlas_reader_probe_rejects_checkout_origin(tmp_path: Path) -> None:
    environment_root = tmp_path / "scientific-venv"
    checkout = tmp_path / "checkout"

    with pytest.raises(
        DistributionValidationError,
        match="outside the fresh Atlas reader environment",
    ):
        _parse_atlas_reader_probe_output(
            _atlas_reader_probe(environment_root, origins_root=checkout),
            environment_root=environment_root,
            required_imports=ATLAS_READER_IMPORTS,
        )


def test_atlas_reader_probe_rejects_forbidden_capture_import(
    tmp_path: Path,
) -> None:
    environment_root = tmp_path / "scientific-venv"

    with pytest.raises(
        DistributionValidationError,
        match="loaded forbidden capture modules",
    ):
        _parse_atlas_reader_probe_output(
            _atlas_reader_probe(
                environment_root,
                forbidden=["spirallens.atlas._capture_store"],
            ),
            environment_root=environment_root,
            required_imports=ATLAS_READER_IMPORTS,
        )


def test_atlas_reader_probe_rejects_public_export_reordering(
    tmp_path: Path,
) -> None:
    environment_root = tmp_path / "scientific-venv"
    reordered = list(reversed(ATLAS_PUBLIC_EXPORTS))

    with pytest.raises(
        DistributionValidationError,
        match="public export order differs",
    ):
        _parse_atlas_reader_probe_output(
            _atlas_reader_probe(
                environment_root,
                public_exports=reordered,
            ),
            environment_root=environment_root,
            required_imports=ATLAS_READER_IMPORTS,
        )


def _experiment_absence_probe(
    environment_root: Path,
    public_exports: dict[str, tuple[str, ...]],
    *,
    origins_root: Path | None = None,
    receipts: list[dict[str, str]] | None = None,
    editable: bool = False,
) -> str:
    root = environment_root if origins_root is None else origins_root
    if receipts is None:
        receipts = [
            {
                "exception_type": "ModuleNotFoundError",
                "module": name,
                "name": name,
            }
            for name in REPOSITORY_EXPERIMENT_MODULES
        ]
    return json.dumps(
        {
            "absence_receipts": receipts,
            "distribution_root": str(root / "site-packages"),
            "direct_url": (
                {"dir_info": {"editable": True}}
                if editable
                else {"archive_info": {}, "url": "file:///artifact.whl"}
            ),
            "module_origins": {
                name: str(
                    root / "site-packages" / Path(*name.split(".")) / "__init__.py"
                )
                for name in public_exports
            },
            "package_version": "0.1.0",
            "public_exports": {
                name: list(exports) for name, exports in public_exports.items()
            },
        }
    )


def test_repository_experiment_absence_probe_accepts_exact_22_receipts(
    tmp_path: Path,
) -> None:
    repository = Path(__file__).resolve().parents[1]
    exports = _load_public_package_exports(repository)
    environment_root = tmp_path / "venv"

    parsed = _parse_repository_experiment_absence_probe_output(
        _experiment_absence_probe(environment_root, exports),
        environment_root=environment_root,
        expected_modules=REPOSITORY_EXPERIMENT_MODULES,
        expected_public_exports=exports,
    )

    assert parsed["direct_url_editable"] is False
    assert parsed["exact_module_not_found_receipt_count"] == 22
    assert list(parsed["module_origins"]) == [
        "spirallens.access",
        "spirallens.qualification",
    ]
    assert all(
        len(receipt["ordered_sha256"]) == 64
        for receipt in parsed["public_package_exports"].values()
    )


def test_repository_experiment_absence_probe_rejects_transitive_missing_name(
    tmp_path: Path,
) -> None:
    repository = Path(__file__).resolve().parents[1]
    exports = _load_public_package_exports(repository)
    environment_root = tmp_path / "venv"
    receipts = [
        {
            "exception_type": "ModuleNotFoundError",
            "module": name,
            "name": name,
        }
        for name in REPOSITORY_EXPERIMENT_MODULES
    ]
    receipts[0]["name"] = "transitive_dependency"

    with pytest.raises(
        DistributionValidationError,
        match="exact requested ModuleNotFoundError.name",
    ):
        _parse_repository_experiment_absence_probe_output(
            _experiment_absence_probe(
                environment_root,
                exports,
                receipts=receipts,
            ),
            environment_root=environment_root,
            expected_modules=REPOSITORY_EXPERIMENT_MODULES,
            expected_public_exports=exports,
        )


def test_repository_experiment_absence_probe_rejects_editable_install(
    tmp_path: Path,
) -> None:
    repository = Path(__file__).resolve().parents[1]
    exports = _load_public_package_exports(repository)
    environment_root = tmp_path / "venv"

    with pytest.raises(DistributionValidationError, match="editable install"):
        _parse_repository_experiment_absence_probe_output(
            _experiment_absence_probe(environment_root, exports, editable=True),
            environment_root=environment_root,
            expected_modules=REPOSITORY_EXPERIMENT_MODULES,
            expected_public_exports=exports,
        )


def test_probe_rejects_import_from_an_editable_checkout(
    tmp_path: Path,
) -> None:
    environment_root = tmp_path / "venv"
    checkout = tmp_path / "checkout"

    with pytest.raises(
        DistributionValidationError,
        match="outside the fresh wheel environment",
    ):
        _parse_probe_output(
            _probe(environment_root, origins_root=checkout),
            environment_root=environment_root,
            required_imports=DEFAULT_IMPORTS,
        )


def test_probe_rejects_editable_direct_url(tmp_path: Path) -> None:
    environment_root = tmp_path / "venv"

    with pytest.raises(
        DistributionValidationError,
        match="editable SpiralLens install",
    ):
        _parse_probe_output(
            _probe(environment_root, editable=True),
            environment_root=environment_root,
            required_imports=DEFAULT_IMPORTS,
        )


def test_probe_rejects_forbidden_heavy_import(tmp_path: Path) -> None:
    environment_root = tmp_path / "venv"

    with pytest.raises(
        DistributionValidationError,
        match="loaded forbidden modules",
    ):
        _parse_probe_output(
            _probe(environment_root, forbidden=["torch"]),
            environment_root=environment_root,
            required_imports=DEFAULT_IMPORTS,
        )


def test_validator_emits_machine_readable_internal_diagnostic() -> None:
    repository = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            str(repository / "scripts" / "validate_distribution.py"),
            "--source-root",
            str(repository),
        ],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stderr == ""
    report = json.loads(completed.stdout)
    assert report["schema_version"] == REPORT_SCHEMA_VERSION
    assert report["status"] == "pass"
    absent = {"observation": "absent", "count": 0, "members": []}
    assert report["library_separation"] == {
        "repository_experiment_separation": {
            "source_tree": {
                "observation": "reviewed-exact-set-present",
                "count": 22,
                "all_regular_files": True,
                "total_lines": 19190,
                "paths": list(REPOSITORY_EXPERIMENT_SOURCE_PATHS),
            },
            "sdist": absent,
            "direct_source_wheel": absent,
            "sdist_derived_wheel": absent,
            "source_prefixes": [
                "src/spirallens/access/_pythia160_",
                "src/spirallens/qualification/confirmation_v1_",
            ],
            "wheel_prefixes": list(REPOSITORY_EXPERIMENT_WHEEL_MEMBER_PREFIXES),
        },
        "closed_library_allowlist_established": False,
        "grants": {
            "authority": False,
            "library": False,
            "public_api": False,
            "scientific": False,
        },
    }
    assert report["required_imports"] == list(DEFAULT_IMPORTS)
    assert report["required_atlas_reader_imports"] == list(ATLAS_READER_IMPORTS)
    assert report["required_scientific_imports"] == list(DEFAULT_SCIENTIFIC_IMPORTS)
    assert report["required_wheel_members"] == list(REQUIRED_WHEEL_MEMBERS)
    assert report["forbidden_imports"] == [
        "faiss",
        "huggingface_hub",
        "numpy",
        "safetensors",
        "scipy",
        "torch",
        "transformers",
        "yaml",
    ]
    assert report["build"] == {
        "direct_source_wheel_built": True,
        "frontend": "python-build",
        "isolation": True,
        "source_copy": True,
        "stale_build_outputs_fail_closed": True,
        "wheel_built_from_sdist": True,
    }
    assert report["installation"]["no_dependencies"] is True
    assert report["installation"]["system_site_packages"] is False
    assert report["installation"]["atlas_reader_system_site_packages"] is True
    assert report["installation"]["atlas_reader_user_site_packages"] is True
    assert report["installation"]["scientific_surface_system_site_packages"] is True
    assert report["installation"]["scientific_surface_user_site_packages"] is True
    assert report["installation"]["wheel_filename"].endswith(".whl")
    assert report["installation"]["direct_source_wheel_filename"].endswith(".whl")
    assert report["installation"]["repository_experiment_fresh_environment_count"] == 2
    assert report["repository_experiment_stale_build_rejection"] == {
        "observation": "rejected-before-wheel-publication",
        "seeded_target_count": 1,
        "skip_build": True,
        "wheel_artifact_count": 0,
    }
    source_import = report["repository_experiment_source_import_inspection"]
    assert source_import["forbidden_model_imports_loaded"] == []
    assert source_import["imported_module_count"] == 22
    assert source_import["module_origins"] == dict(
        zip(
            REPOSITORY_EXPERIMENT_MODULES,
            REPOSITORY_EXPERIMENT_SOURCE_PATHS,
            strict=True,
        )
    )
    assert set(report["repository_experiment_install_inspections"]) == {
        "direct_source_wheel",
        "sdist_derived_wheel",
    }
    for install_inspection in report[
        "repository_experiment_install_inspections"
    ].values():
        assert install_inspection["direct_url_editable"] is False
        assert install_inspection["exact_module_not_found_receipt_count"] == 22
        assert set(install_inspection["module_origins"]) == {
            "spirallens.access",
            "spirallens.qualification",
        }
        assert install_inspection["public_package_exports"] == {
            "spirallens.access": {
                "count": 37,
                "ordered_sha256": (
                    "1c1be6d21261935335e310c1cb665469f4934db40310d47dcbfe625e66d93600"
                ),
            },
            "spirallens.qualification": {
                "count": 115,
                "ordered_sha256": (
                    "4dab13d8a847400280682f61fcf0b03fdd9ad51c68d8909ab63a463d07579023"
                ),
            },
        }
    assert report["inspection"]["forbidden_imports_loaded"] == []
    assert report["inspection"]["direct_url_editable"] is False
    assert set(report["inspection"]["module_origins"]) == set(DEFAULT_IMPORTS)
    assert all(
        "site-packages/spirallens" in origin
        for origin in report["inspection"]["module_origins"].values()
    )
    assert report["atlas_reader_forbidden_imports"] == list(
        ATLAS_READER_FORBIDDEN_IMPORTS
    )
    assert report["atlas_reader_inspection"]["dependencies_loaded"] == [
        "numpy",
        "yaml",
    ]
    assert report["atlas_reader_inspection"]["dir_includes_public_exports"] is True
    assert report["atlas_reader_inspection"]["direct_url_editable"] is False
    assert report["atlas_reader_inspection"]["forbidden_imports_loaded"] == []
    assert set(report["atlas_reader_inspection"]["module_origins"]) == set(
        ATLAS_READER_IMPORTS
    )
    assert all(
        "site-packages/spirallens" in origin
        for origin in report["atlas_reader_inspection"]["module_origins"].values()
    )
    assert report["atlas_reader_inspection"]["public_exports"] == list(
        ATLAS_PUBLIC_EXPORTS
    )
    assert report["atlas_reader_inspection"]["reader_symbol_identities"] is True
    assert report["atlas_reader_inspection"]["reader_symbol_modules"] == (
        ATLAS_READER_SYMBOL_MODULES
    )
    assert set(report["scientific_surface_inspection"]["module_origins"]) == set(
        DEFAULT_SCIENTIFIC_IMPORTS
    )
    assert all(
        "site-packages/spirallens" in origin
        for origin in report["scientific_surface_inspection"]["module_origins"].values()
    )
    assert sorted(item["kind"] for item in report["artifacts"]) == [
        "direct-source-wheel",
        "sdist",
        "sdist-derived-wheel",
    ]
    for artifact in report["artifacts"]:
        assert len(artifact["sha256"]) == 64
        assert artifact["size_bytes"] > 0
