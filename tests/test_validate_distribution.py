from __future__ import annotations

import ast
import builtins
import hashlib
import importlib.util
import io
import json
import runpy
import stat
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

_VALIDATOR_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "validate_distribution.py"
)
_INSTALLED_IMPORT_POLICY_PATH = (
    Path(__file__).resolve().parents[1] / "distribution" / "_installed_import_policy.py"
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
PYTHON_MEMBER_CLASSIFICATION_PATH = _VALIDATOR.PYTHON_MEMBER_CLASSIFICATION_PATH
ORDERED_EXPORT_CLASSIFICATION_PATH = _VALIDATOR.ORDERED_EXPORT_CLASSIFICATION_PATH
ORDERED_EXPORT_CLASSIFICATION_SCHEMA_VERSION = (
    _VALIDATOR.ORDERED_EXPORT_CLASSIFICATION_SCHEMA_VERSION
)
INSTALLED_IMPORT_CLASSIFICATION_PATH = _VALIDATOR.INSTALLED_IMPORT_CLASSIFICATION_PATH
INSTALLED_IMPORT_CLASSIFICATION_SCHEMA_VERSION = (
    _VALIDATOR.INSTALLED_IMPORT_CLASSIFICATION_SCHEMA_VERSION
)
INSTALLED_IMPORT_DENIED_AUDIT_EVENTS = _VALIDATOR.INSTALLED_IMPORT_DENIED_AUDIT_EVENTS
_classify_source_python_members = _VALIDATOR._classify_source_python_members
_classify_sdist_python_members = _VALIDATOR._classify_sdist_python_members
_classify_wheel_python_members = _VALIDATOR._classify_wheel_python_members
_extract_sdist = _VALIDATOR._extract_sdist
_require_absent_sdist_test_surface = _VALIDATOR._require_absent_sdist_test_surface
_load_python_member_classification = _VALIDATOR._load_python_member_classification
_load_literal_ordered_exports = _VALIDATOR._load_literal_ordered_exports
_load_ordered_export_classification = _VALIDATOR._load_ordered_export_classification
_load_installed_import_classification = _VALIDATOR._load_installed_import_classification
_parse_installed_import_probe_output = _VALIDATOR._parse_installed_import_probe_output
_normalize_installed_import_explicit_roots = (
    _VALIDATOR._normalize_installed_import_explicit_roots
)
_normalize_installed_requires_dist = _VALIDATOR._normalize_installed_requires_dist
_require_minimum_release_version = _VALIDATOR._require_minimum_release_version
_require_installed_import_outcome_equality = (
    _VALIDATOR._require_installed_import_outcome_equality
)
_parse_installed_python_member_probe_output = (
    _VALIDATOR._parse_installed_python_member_probe_output
)
_parse_installed_ordered_export_probe_output = (
    _VALIDATOR._parse_installed_ordered_export_probe_output
)
_require_ordered_export_state = _VALIDATOR._require_ordered_export_state
_require_sdist_exact_file = _VALIDATOR._require_sdist_exact_file
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


def _classification() -> dict[str, object]:
    return _load_python_member_classification(Path(__file__).resolve().parents[1])


def _export_classification() -> dict[str, object]:
    repository = Path(__file__).resolve().parents[1]
    return _load_ordered_export_classification(
        repository,
        python_member_classification=_classification(),
    )


def _source_initializer_bytes() -> dict[str, bytes]:
    repository = Path(__file__).resolve().parents[1]
    classification = _export_classification()
    return {
        initializer: (repository / "src" / initializer).read_bytes()
        for initializer in classification["initializers"]
    }


def _write_export_manifest(root: Path, document: object) -> None:
    path = root / ORDERED_EXPORT_CLASSIFICATION_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _installed_import_classification() -> dict[str, object]:
    repository = Path(__file__).resolve().parents[1]
    return _load_installed_import_classification(
        repository,
        python_member_classification=_classification(),
        ordered_export_classification=_export_classification(),
    )


def _copy_installed_import_classification_inputs(destination: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    for relative in (
        "pyproject.toml",
        PYTHON_MEMBER_CLASSIFICATION_PATH,
        ORDERED_EXPORT_CLASSIFICATION_PATH,
        INSTALLED_IMPORT_CLASSIFICATION_PATH,
    ):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((repository / relative).read_bytes())


def test_installed_import_policy_is_stdlib_only_pure_metadata_projection() -> None:
    source = _INSTALLED_IMPORT_POLICY_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(_INSTALLED_IMPORT_POLICY_PATH))
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            assert node.module is not None
            imported_roots.add(node.module.split(".", 1)[0])

    assert imported_roots <= set(sys.stdlib_module_names) | {"__future__"}
    assert imported_roots.isdisjoint(
        {
            "ast",
            "configparser",
            "csv",
            "importlib",
            "io",
            "json",
            "marshal",
            "os",
            "packaging",
            "pathlib",
            "pickle",
            "setuptools",
            "shutil",
            "socket",
            "spirallens",
            "subprocess",
            "tarfile",
            "tempfile",
            "tomllib",
            "urllib",
            "xml",
            "yaml",
            "zipfile",
        }
    )
    forbidden_calls = {
        "Popen",
        "__import__",
        "compile",
        "dump",
        "dumps",
        "eval",
        "exec",
        "load",
        "loads",
        "lstat",
        "open",
        "parse",
        "read_bytes",
        "read_text",
        "run",
        "stat",
        "write_bytes",
        "write_text",
        "urlopen",
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            called = node.func.id
        elif isinstance(node.func, ast.Attribute):
            called = node.func.attr
        else:
            continue
        assert called not in forbidden_calls

    def reject_io(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("policy module attempted I/O")

    restricted_builtins = dict(vars(builtins))
    restricted_builtins["open"] = reject_io
    namespace: dict[str, object] = {
        "__builtins__": restricted_builtins,
        "__name__": "_installed_import_policy_test",
    }
    exec(compile(source, str(_INSTALLED_IMPORT_POLICY_PATH), "exec"), namespace)
    projection = namespace["worker_policy_projection"]
    assert callable(projection)
    first = projection()
    second = projection()
    assert isinstance(first, dict)
    assert first == second
    assert first is not second
    assert json.loads(json.dumps(first, sort_keys=True)) == first
    blocked = first["blocked_optional_prefixes"]
    assert isinstance(blocked, list)
    blocked.append("rogue")
    assert second == projection()


def test_installed_import_manifest_parsers_remain_independent_of_policy() -> None:
    repository = Path(__file__).resolve().parents[1]
    policy_source = _INSTALLED_IMPORT_POLICY_PATH.read_text(encoding="utf-8")
    setup_source = (repository / "setup.py").read_text(encoding="utf-8")
    validator_source = _VALIDATOR_PATH.read_text(encoding="utf-8")

    assert "def _load_installed_import_classification(" not in policy_source
    assert "def _reject_import_duplicate_json_keys(" not in policy_source
    assert "def _load_installed_import_classification(" in setup_source
    assert "def _reject_import_duplicate_json_keys(" in setup_source
    assert "def _load_installed_import_classification(" in validator_source
    assert "def _reject_duplicate_json_object(" in validator_source


@pytest.mark.parametrize(
    ("mutation", "exception", "match"),
    [
        ("missing", RuntimeError, "cannot load installed import policy"),
        ("symlink", RuntimeError, "cannot load installed import policy"),
        ("oversize", RuntimeError, "cannot load installed import policy"),
        ("import_failure", ValueError, "policy import failed"),
    ],
)
def test_validator_policy_load_fails_closed(
    tmp_path: Path,
    mutation: str,
    exception: type[BaseException],
    match: str,
) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    validator_path = scripts / "validate_distribution.py"
    validator_path.write_bytes(_VALIDATOR_PATH.read_bytes())
    distribution = tmp_path / "distribution"
    distribution.mkdir()
    policy = distribution / "_installed_import_policy.py"
    if mutation == "symlink":
        target = tmp_path / "policy-target.py"
        target.write_text("SCHEMA = 'untrusted'\n", encoding="utf-8")
        policy.symlink_to(target)
    elif mutation == "oversize":
        policy.write_bytes(b"#" * (1024 * 1024 + 1))
    elif mutation == "import_failure":
        policy.write_text(
            "raise ValueError('policy import failed')\n",
            encoding="utf-8",
        )
    elif mutation != "missing":  # pragma: no cover - parameter table is exhaustive
        raise AssertionError(mutation)

    with pytest.raises(exception, match=match):
        runpy.run_path(str(validator_path))


def test_installed_import_manifest_freezes_exact_132_outcomes() -> None:
    classification = _installed_import_classification()

    assert classification["schema_version"] == (
        INSTALLED_IMPORT_CLASSIFICATION_SCHEMA_VERSION
    )
    assert classification["manifest_sha256"] == (
        "eebf61d097db980fd9d239f002729386e9890ce3495022ddc453bf14bc63fa9d"
    )
    assert len(classification["outcomes"]["base_import_success"]) == 127
    assert classification["outcomes"]["models_extra_missing_torch"] == (
        "spirallens.adapters",
        "spirallens.adapters.pythia",
        "spirallens.atlas._capture_store",
        "spirallens.atlas.engineering_run",
        "spirallens.atlas.id_sweep",
    )
    assert classification["successful_package_modules"] == tuple(
        package["module"]
        for package in _export_classification()["packages"]
        if package["module"] != "spirallens.adapters"
    )
    assert classification["successful_runtime_export_count"] == 554
    assert classification["unavailable_package_modules"] == ("spirallens.adapters",)
    assert classification["unavailable_runtime_export_count"] == 5
    requires_dist = classification["requires_dist_contract"]
    assert len(requires_dist) == 13
    assert [record for record in requires_dist if record["name"] == "cryptography"] == [
        {"extra": "dev", "name": "cryptography", "specifier": ">=42"},
        {"extra": "witness", "name": "cryptography", "specifier": ">=42"},
    ]


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        ("unknown_top_key", "unexpected top-level keys"),
        ("wrong_scope", "wrong scope"),
        ("reorder_success", "sorted and unique"),
        ("overlap", "overlap"),
        ("missing_module", "exact shipped module set"),
        ("wrong_negative", "overlap"),
        ("extra_dependency", "base dependencies differ"),
    ],
)
def test_installed_import_manifest_rejects_drift(
    tmp_path: Path,
    mutation: str,
    match: str,
) -> None:
    _copy_installed_import_classification_inputs(tmp_path)
    path = tmp_path / INSTALLED_IMPORT_CLASSIFICATION_PATH
    document = json.loads(path.read_text(encoding="utf-8"))
    if mutation == "unknown_top_key":
        document["unknown"] = True
    elif mutation == "wrong_scope":
        document["classification_scope"] = "broader"
    elif mutation == "reorder_success":
        document["outcomes"]["base_import_success"][0:2] = reversed(
            document["outcomes"]["base_import_success"][0:2]
        )
    elif mutation == "overlap":
        document["outcomes"]["base_import_success"].append(
            document["outcomes"]["models_extra_missing_torch"][0]
        )
        document["outcomes"]["base_import_success"].sort()
    elif mutation == "missing_module":
        document["outcomes"]["base_import_success"].pop()
    elif mutation == "wrong_negative":
        document["outcomes"]["models_extra_missing_torch"][-1] = (
            "spirallens.synthetic.generators"
        )
        document["outcomes"]["models_extra_missing_torch"].sort()
    elif mutation == "extra_dependency":
        document["base_dependencies"].append(
            {
                "distribution": "rogue",
                "import_name": "rogue",
                "requirement": "rogue>=1",
            }
        )
    else:  # pragma: no cover - parameter table is exhaustive
        raise AssertionError(mutation)
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(DistributionValidationError, match=match):
        _load_installed_import_classification(
            tmp_path,
            python_member_classification=_classification(),
            ordered_export_classification=_export_classification(),
        )


def test_installed_import_manifest_accepts_pyproject_dependency_reordering(
    tmp_path: Path,
) -> None:
    _copy_installed_import_classification_inputs(tmp_path)
    pyproject = tmp_path / "pyproject.toml"
    source = pyproject.read_text(encoding="utf-8")
    source = source.replace(
        '  "numpy>=1.26",\n  "scipy>=1.11",',
        '  "scipy>=1.11",\n  "numpy>=1.26",',
    )
    pyproject.write_text(source, encoding="utf-8")

    classification = _load_installed_import_classification(
        tmp_path,
        python_member_classification=_classification(),
        ordered_export_classification=_export_classification(),
    )

    assert classification["manifest_sha256"] == (
        "eebf61d097db980fd9d239f002729386e9890ce3495022ddc453bf14bc63fa9d"
    )


@pytest.mark.parametrize(
    "replacement",
    [
        '  "numpy>=1.25",\n  "scipy>=1.11",',
        '  "numpy>=1.26",',
        '  "numpy>=1.26",\n  "numpy>=1.26",\n  "scipy>=1.11",',
        '  "numpy>=1.26",\n  "scipy>=1.11",\n  "rogue>=1",',
        '  "NUMPY>=1.26",\n  "scipy>=1.11",',
    ],
)
def test_installed_import_manifest_rejects_pyproject_dependency_drift(
    tmp_path: Path,
    replacement: str,
) -> None:
    _copy_installed_import_classification_inputs(tmp_path)
    pyproject = tmp_path / "pyproject.toml"
    source = pyproject.read_text(encoding="utf-8")
    source = source.replace(
        '  "numpy>=1.26",\n  "scipy>=1.11",',
        replacement,
    )
    pyproject.write_text(source, encoding="utf-8")

    with pytest.raises(
        DistributionValidationError,
        match="project dependencies differ",
    ):
        _load_installed_import_classification(
            tmp_path,
            python_member_classification=_classification(),
            ordered_export_classification=_export_classification(),
        )


@pytest.mark.parametrize(
    "mutation", ["symlink", "oversize", "invalid_utf8", "invalid_toml"]
)
def test_installed_import_manifest_rejects_unsafe_pyproject(
    tmp_path: Path,
    mutation: str,
) -> None:
    _copy_installed_import_classification_inputs(tmp_path)
    pyproject = tmp_path / "pyproject.toml"
    if mutation == "symlink":
        original = tmp_path / "pyproject-original.toml"
        pyproject.rename(original)
        pyproject.symlink_to(original)
    elif mutation == "oversize":
        pyproject.write_bytes(b"x" * (1024 * 1024 + 1))
    elif mutation == "invalid_utf8":
        pyproject.write_bytes(b"\xff")
    elif mutation == "invalid_toml":
        pyproject.write_text("[project\n", encoding="utf-8")
    else:  # pragma: no cover - parameter table is exhaustive
        raise AssertionError(mutation)

    with pytest.raises(DistributionValidationError):
        _load_installed_import_classification(
            tmp_path,
            python_member_classification=_classification(),
            ordered_export_classification=_export_classification(),
        )


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ('  "cryptography>=42",\n  "pytest>=8",', '  "pytest>=8",'),
        (
            '  "cryptography>=42",\n  "pytest>=8",',
            '  "Cryptography>=42",\n  "pytest>=8",',
        ),
        (
            '  "cryptography>=42",\n  "pytest>=8",',
            '  "cryptography>=43",\n  "pytest>=8",',
        ),
        ("witness = [", "review = ["),
    ],
)
def test_installed_import_manifest_rejects_optional_dependency_drift(
    tmp_path: Path,
    old: str,
    new: str,
) -> None:
    _copy_installed_import_classification_inputs(tmp_path)
    pyproject = tmp_path / "pyproject.toml"
    source = pyproject.read_text(encoding="utf-8")
    assert old in source
    pyproject.write_text(source.replace(old, new, 1), encoding="utf-8")

    with pytest.raises(
        DistributionValidationError,
        match="project .*dependencies",
    ):
        _load_installed_import_classification(
            tmp_path,
            python_member_classification=_classification(),
            ordered_export_classification=_export_classification(),
        )


@pytest.mark.parametrize(
    "mutation",
    [
        'rogue>=1; python_version >= "3.11"',
        'torch>=2.3; extra == "models"',
        'Torch>=2.2; extra == "models"',
        'torch>=2.2; extra == "dev"',
        'torch>=2.2; extra == "models" and python_version >= "3.11"',
    ],
)
def test_installed_requires_dist_rejects_full_metadata_drift(
    tmp_path: Path,
    mutation: str,
) -> None:
    document = _installed_import_probe_document(tmp_path)
    raw = list(document["spirallens_requires_dist"])
    if mutation.startswith("rogue"):
        raw.append(mutation)
    else:
        raw[raw.index('torch>=2.2; extra == "models"')] = mutation

    with pytest.raises(DistributionValidationError):
        _normalize_installed_requires_dist(
            raw,
            expected=_installed_import_classification()["requires_dist_contract"],
            label="synthetic wheel",
        )


def _installed_import_probe_document(
    environment_root: Path,
    *,
    denied_count: int = 0,
    module_origin: Path | None = None,
) -> dict[str, object]:
    origin = module_origin or (
        environment_root / "lib/python3.13/site-packages/spirallens/core/canonical.py"
    )
    origin.parent.mkdir(parents=True, exist_ok=True)
    origin.touch(exist_ok=True)
    distribution_root = environment_root / "lib/python3.13/site-packages"
    return {
        "audit_denied_event_count": denied_count,
        "audit_denied_events": ([] if denied_count == 0 else ["subprocess.Popen"]),
        "blocked_optional_prefixes_loaded": [],
        "blocked_undeclared_import_attempts": [],
        "dependency_runtime_modules_without_file_origin": [],
        "dependency_runtime_module_aliases": [],
        "explicit_import_roots": [str(distribution_root)],
        "failure_message": None,
        "failure_type": None,
        "missing_name": None,
        "module": "spirallens.core.canonical",
        "module_origin": str(origin),
        "runtime_exports": None,
        "runtime_exports_sha256": None,
        "spirallens_requires_dist": [
            "numpy>=1.26",
            "scipy>=1.11",
            "PyYAML>=6.0",
            'faiss-cpu==1.14.3; extra == "ann"',
            'build>=1.2.2; extra == "dev"',
            'cryptography>=42; extra == "dev"',
            'pytest>=8; extra == "dev"',
            'ruff>=0.9; extra == "dev"',
            'huggingface-hub>=0.34; extra == "models"',
            'torch>=2.2; extra == "models"',
            'transformers>=4.40; extra == "models"',
            'safetensors>=0.4; extra == "models"',
            'cryptography>=42; extra == "witness"',
        ],
        "spirallens_distribution_root": str(distribution_root),
        "site_initialization_enabled": False,
        "status": "base_import_success",
        "third_party_distributions": {},
        "pth_startup_executed": False,
    }


def test_installed_import_probe_parser_accepts_bounded_success(
    tmp_path: Path,
) -> None:
    document = _installed_import_probe_document(tmp_path)

    parsed = _parse_installed_import_probe_output(
        json.dumps(document),
        module="spirallens.core.canonical",
        expected_member="spirallens/core/canonical.py",
        expected_outcome="base_import_success",
        expected_initializer_exports=None,
        environment_root=tmp_path,
        explicit_import_roots=(str(tmp_path / "lib/python3.13/site-packages"),),
        expected_dependencies=(),
        expected_requires_dist=_installed_import_classification()[
            "requires_dist_contract"
        ],
    )

    assert parsed["status"] == "base_import_success"
    assert parsed["module_origin"].endswith("spirallens/core/canonical.py")
    assert parsed["explicit_import_roots"] == [
        "fresh-environment/lib/python3.13/site-packages"
    ]


def test_installed_import_probe_receipt_normalizes_distinct_fresh_roots(
    tmp_path: Path,
) -> None:
    receipts = []
    for name in ("direct", "sdist"):
        environment_root = tmp_path / name
        document = _installed_import_probe_document(environment_root)
        receipts.append(
            _parse_installed_import_probe_output(
                json.dumps(document),
                module="spirallens.core.canonical",
                expected_member="spirallens/core/canonical.py",
                expected_outcome="base_import_success",
                expected_initializer_exports=None,
                environment_root=environment_root,
                explicit_import_roots=(
                    str(environment_root / "lib/python3.13/site-packages"),
                ),
                expected_dependencies=(),
                expected_requires_dist=_installed_import_classification()[
                    "requires_dist_contract"
                ],
            )
        )

    assert receipts[0] == receipts[1]


def test_installed_import_startup_roots_normalize_across_distinct_environments(
    tmp_path: Path,
) -> None:
    host_root = tmp_path.parent / "host/site-packages"
    normalized = []
    for name in ("direct", "sdist"):
        environment_root = tmp_path / name
        fresh_root = environment_root / "lib/python3.13/site-packages"
        normalized.append(
            _normalize_installed_import_explicit_roots(
                (str(fresh_root), str(host_root)),
                environment_root=environment_root,
            )
        )

    assert normalized == [
        ["fresh-environment/lib/python3.13/site-packages", str(host_root.resolve())],
        ["fresh-environment/lib/python3.13/site-packages", str(host_root.resolve())],
    ]


def test_installed_import_equality_includes_normalized_startup() -> None:
    receipt = {
        "outcome_manifest_sha256": "a" * 64,
        "modules": [],
        "third_party_dependencies": {},
        "startup": {
            "explicit_import_roots": ["fresh-environment/lib/python3.13/site-packages"]
        },
    }

    assert _require_installed_import_outcome_equality(receipt, dict(receipt)) == {
        "direct_source_to_sdist_derived_install": True,
        "direct_source_to_sdist_derived_startup": True,
    }
    drifted = {**receipt, "startup": {"explicit_import_roots": ["absolute-drift"]}}
    with pytest.raises(DistributionValidationError, match="outcomes differ"):
        _require_installed_import_outcome_equality(receipt, drifted)


def test_installed_import_probe_parser_rejects_denied_audit_event(
    tmp_path: Path,
) -> None:
    document = _installed_import_probe_document(tmp_path, denied_count=1)

    with pytest.raises(DistributionValidationError, match="denied audit event"):
        _parse_installed_import_probe_output(
            json.dumps(document),
            module="spirallens.core.canonical",
            expected_member="spirallens/core/canonical.py",
            expected_outcome="base_import_success",
            expected_initializer_exports=None,
            environment_root=tmp_path,
            explicit_import_roots=(str(tmp_path / "lib/python3.13/site-packages"),),
            expected_dependencies=(),
            expected_requires_dist=_installed_import_classification()[
                "requires_dist_contract"
            ],
        )


def test_installed_import_probe_parser_rejects_origin_outside_environment(
    tmp_path: Path,
) -> None:
    outside = tmp_path.parent / "shadow/spirallens/core/canonical.py"
    document = _installed_import_probe_document(
        tmp_path,
        module_origin=outside,
    )

    with pytest.raises(DistributionValidationError, match="outside"):
        _parse_installed_import_probe_output(
            json.dumps(document),
            module="spirallens.core.canonical",
            expected_member="spirallens/core/canonical.py",
            expected_outcome="base_import_success",
            expected_initializer_exports=None,
            environment_root=tmp_path,
            explicit_import_roots=(str(tmp_path / "lib/python3.13/site-packages"),),
            expected_dependencies=(),
            expected_requires_dist=_installed_import_classification()[
                "requires_dist_contract"
            ],
        )


@pytest.mark.parametrize(
    ("version", "accepted"),
    [
        ("1.26", True),
        ("1.26.0", True),
        ("2.0.0", True),
        ("1.25.9", False),
        ("1.26rc1", False),
    ],
)
def test_minimum_release_version_is_fail_closed(
    version: str,
    accepted: bool,
) -> None:
    if accepted:
        _require_minimum_release_version(
            version,
            minimum=(1, 26),
            label="numpy",
        )
    else:
        with pytest.raises(DistributionValidationError):
            _require_minimum_release_version(
                version,
                minimum=(1, 26),
                label="numpy",
            )


def test_installed_import_probe_script_compiles_and_policy_is_bounded() -> None:
    compile(_VALIDATOR._INSTALLED_IMPORT_MODULE_PROBE, "installed probe", "exec")
    compile(
        _VALIDATOR._INSTALLED_IMPORT_ROOT_DISCOVERY_PROBE,
        "installed root discovery",
        "exec",
    )
    assert "subprocess.Popen" in INSTALLED_IMPORT_DENIED_AUDIT_EVENTS
    assert "os.fork" in INSTALLED_IMPORT_DENIED_AUDIT_EVENTS
    assert "ctypes.dlopen" not in INSTALLED_IMPORT_DENIED_AUDIT_EVENTS
    assert "os.putenv" not in INSTALLED_IMPORT_DENIED_AUDIT_EVENTS


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_field",
        "extra_field",
        "blocked_not_list",
        "denied_not_list",
        "missing_torch_not_list",
        "empty_blocked",
        "empty_denied",
        "empty_missing_torch",
        "empty_schema",
        "empty_dependency_value",
        "outcome_mismatch",
    ],
)
def test_installed_import_worker_rejects_policy_projection_tamper(
    tmp_path: Path,
    mutation: str,
) -> None:
    policy = json.loads(_VALIDATOR._INSTALLED_IMPORT_WORKER_POLICY)
    module = "spirallens.core.canonical"
    outcome = "base_import_success"
    if mutation == "missing_field":
        policy.pop("schema_version")
    elif mutation == "extra_field":
        policy["fallback"] = True
    elif mutation == "blocked_not_list":
        policy["blocked_optional_prefixes"] = "torch"
    elif mutation == "denied_not_list":
        policy["denied_audit_events"] = "subprocess.Popen"
    elif mutation == "missing_torch_not_list":
        policy["models_extra_missing_torch"] = "spirallens.adapters"
    elif mutation == "empty_blocked":
        policy["blocked_optional_prefixes"] = []
    elif mutation == "empty_denied":
        policy["denied_audit_events"] = []
    elif mutation == "empty_missing_torch":
        policy["models_extra_missing_torch"] = []
    elif mutation == "empty_schema":
        policy["schema_version"] = ""
    elif mutation == "empty_dependency_value":
        policy["base_dependencies"][0]["requirement"] = ""
    elif mutation == "outcome_mismatch":
        module = "spirallens.adapters"
    else:  # pragma: no cover - parameter table is exhaustive
        raise AssertionError(mutation)

    completed = subprocess.run(
        (
            sys.executable,
            "-I",
            "-S",
            "-B",
            "-c",
            _VALIDATOR._INSTALLED_IMPORT_MODULE_PROBE,
            module,
            outcome,
            "null",
            json.dumps(policy),
            json.dumps([str(tmp_path.resolve())]),
            module.replace(".", "/") + ".py",
        ),
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert completed.returncode != 0
    assert "installed import probe received invalid policy" in completed.stderr


def test_installed_import_worker_receives_projection_without_importing_policy() -> None:
    probe = _VALIDATOR._INSTALLED_IMPORT_MODULE_PROBE
    projected = json.loads(_VALIDATOR._INSTALLED_IMPORT_WORKER_POLICY)

    assert projected == _VALIDATOR._POLICY["worker_policy_projection"]()
    assert "_installed_import_policy" not in probe
    assert "runpy" not in probe
    assert "worker_policy = json.loads(sys.argv[4])" in probe
    assert "blocked_optional_prefixes = tuple(json.loads(sys.argv[4]))" not in probe


def test_installed_import_probe_has_no_site_no_preload_and_exact_owner_join() -> None:
    probe = _VALIDATOR._INSTALLED_IMPORT_MODULE_PROBE
    discovery = _VALIDATOR._INSTALLED_IMPORT_ROOT_DISCOVERY_PROBE

    assert "sys.flags.isolated != 1 or sys.flags.no_site != 1" in probe
    assert "sys.flags.isolated != 1 or sys.flags.no_site != 1" in discovery
    assert 'environment_root / "Lib/site-packages"' in discovery
    assert 'environment_root\n            / f"lib/python' in discovery
    assert "baseline_modules = frozenset(sys.modules)" in probe
    assert probe.index("baseline_modules = frozenset(sys.modules)") < probe.index(
        "module = importlib.import_module(module_name)"
    )
    assert 'for import_name in ("numpy", "yaml", "scipy")' not in probe
    assert "owner_top_level_stems" not in probe
    assert "len(mapped_distributions) != 1" in probe
    assert '"_cyutility": ("scipy._cyutility", "scipy")' in probe
    assert "stdlib_internal_modules = {sysconfig._get_sysconfigdata_name()}" in probe
    assert "packaging" not in probe
    assert "packaging" not in discovery
    assert 'if ";" not in requirement' not in probe
    assert 'if ";" not in requirement' not in discovery
    assert 'site_initialization_enabled": False' in probe
    assert 'pth_startup_executed": False' in probe


def test_packaging_parser_stays_in_parent_build_validator_only() -> None:
    source = _VALIDATOR_PATH.read_text(encoding="utf-8")

    assert "`build>=1.2.2` requires packaging" in source
    assert (
        "from packaging.requirements import InvalidRequirement, Requirement" in source
    )
    assert "packaging" not in _VALIDATOR._INSTALLED_IMPORT_ROOT_DISCOVERY_PROBE
    assert "packaging" not in _VALIDATOR._INSTALLED_IMPORT_MODULE_PROBE


def test_ordered_export_manifest_freezes_exact_24_package_559_name_state() -> None:
    classification = _export_classification()

    assert classification["schema_version"] == (
        "spirallens.ordered-package-exports.v0.1"
    )
    assert classification["package_count"] == 24
    assert classification["export_count"] == 559
    assert classification["manifest_sha256"] == (
        "cb9d58ba50c3ead9551da17a7b3d31180157c0b0f7b005aff2df4c5f05effe3e"
    )
    assert classification["initializers"] == tuple(
        package["initializer"] for package in classification["packages"]
    )


def test_source_ordered_export_inventory_is_exact_and_static() -> None:
    repository = Path(__file__).resolve().parents[1]
    receipt = _classify_source_python_members(
        repository,
        classification=_classification(),
        ordered_export_classification=_export_classification(),
    )["ordered_export_inventory"]

    assert receipt["observation"] == "exact-literal-ordered-set"
    assert receipt["package_count"] == 24
    assert receipt["export_count"] == 559
    assert receipt["initializer_bytes_sha256"] == (
        "6f4556d990e93b4b82b857a872c25f7efd0b40a9e2131ee818832946137a7efa"
    )
    assert receipt["ordered_exports_sha256"] == (
        "e2c947c30f0323c54c1713274dac0117fd74dc86cd576279c44a040dfc0ae798"
    )


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        ("reorder_packages", "sorted and unique"),
        ("duplicate_package", "sorted and unique"),
        ("missing_package", "initializer topology"),
        ("extra_package", "initializer topology"),
        ("wrong_topology", "module/initializer topology"),
        ("duplicate_export", "ordered unique ASCII identifiers"),
        ("nonstring_export", "ordered unique ASCII identifiers"),
        ("empty_export", "ordered unique ASCII identifiers"),
    ],
)
def test_ordered_export_manifest_rejects_drift(
    tmp_path: Path,
    mutation: str,
    match: str,
) -> None:
    repository = Path(__file__).resolve().parents[1]
    document = json.loads(
        (repository / ORDERED_EXPORT_CLASSIFICATION_PATH).read_text(encoding="utf-8")
    )
    packages = document["packages"]
    if mutation == "reorder_packages":
        packages[0], packages[1] = packages[1], packages[0]
    elif mutation == "duplicate_package":
        packages[1] = json.loads(json.dumps(packages[0]))
    elif mutation == "missing_package":
        packages.pop()
    elif mutation == "extra_package":
        packages.append(
            {
                "module": "spirallens.rogue",
                "initializer": "spirallens/rogue/__init__.py",
                "exports": ["Rogue"],
            }
        )
        packages.sort(key=lambda package: package["module"])
    elif mutation == "wrong_topology":
        packages[0]["initializer"] = "spirallens/rogue/__init__.py"
    elif mutation == "duplicate_export":
        packages[0]["exports"].append(packages[0]["exports"][0])
    elif mutation == "nonstring_export":
        packages[0]["exports"][0] = 1
    elif mutation == "empty_export":
        packages[0]["exports"] = []
    else:  # pragma: no cover - parameter table is exhaustive
        raise AssertionError(mutation)
    _write_export_manifest(tmp_path, document)

    with pytest.raises(DistributionValidationError, match=match):
        _load_ordered_export_classification(
            tmp_path,
            python_member_classification=_classification(),
        )


def test_ordered_export_manifest_rejects_duplicate_json_key(tmp_path: Path) -> None:
    path = tmp_path / ORDERED_EXPORT_CLASSIFICATION_PATH
    path.parent.mkdir(parents=True)
    path.write_text(
        '{"schema_version":"x","schema_version":"y",'
        '"classification_scope":"x","claim_boundary":"x","packages":[]}\n',
        encoding="utf-8",
    )

    with pytest.raises(DistributionValidationError, match="duplicate-free JSON"):
        _load_ordered_export_classification(
            tmp_path,
            python_member_classification=_classification(),
        )


@pytest.mark.parametrize(
    "source",
    [
        b"__all__ = ['alpha', 'alpha']\n",
        b"__all__ = ['alpha', 1]\n",
        b"__all__ = []\n",
        b"__all__ = tuple(['alpha'])\n",
        b"__all__ = ['alpha']\n__all__ = ['alpha']\n",
        b"__all__ = ['alpha']\n__all__ += ['beta']\n",
        b"__all__ = ['alpha']\ndel __all__\n",
        b"__all__ = ['alpha']\ndef mutate():\n    __all__ = ['beta']\n",
        b"__all__ = ['alpha']\n__all__.append('beta')\n",
        b"__all__ = ['alpha']\n__all__.extend(['beta'])\n",
        b"__all__ = ['alpha']\n__all__[0] = 'beta'\n",
        b"__all__ = ['alpha']\ndel __all__[0]\n",
        b"__all__ = ['alpha']\n__all__.metadata = 'beta'\n",
        b"__all__ = ['alpha']\ndel __all__.metadata\n",
    ],
)
def test_literal_ordered_exports_rejects_nonliteral_or_direct_mutation(
    source: bytes,
) -> None:
    with pytest.raises(DistributionValidationError):
        _load_literal_ordered_exports(source, label="initializer fixture")


def test_ordered_export_state_rejects_reorder_add_remove_and_extra_initializer() -> (
    None
):
    classification = _export_classification()
    sources = _source_initializer_bytes()
    package = classification["packages"][1]
    initializer = package["initializer"]
    exports = list(package["exports"])
    assert len(exports) > 1

    for changed in (
        [exports[1], exports[0], *exports[2:]],
        [*exports, "RogueExport"],
        exports[:-1],
    ):
        drifted = dict(sources)
        drifted[initializer] = ("__all__ = " + repr(changed) + "\n").encode("utf-8")
        with pytest.raises(DistributionValidationError, match="ordered exports differ"):
            _require_ordered_export_state(
                drifted,
                classification=classification,
                artifact_kind="fixture",
            )

    extra = dict(sources)
    extra["spirallens/rogue/__init__.py"] = b"__all__ = ['Rogue']\n"
    missing = dict(sources)
    missing.pop(initializer)
    for changed_sources in (missing, extra):
        with pytest.raises(DistributionValidationError, match="initializer topology"):
            _require_ordered_export_state(
                changed_sources,
                classification=classification,
                artifact_kind="fixture",
            )


def _synthetic_shipped_sources(
    initializer_sources: dict[str, bytes],
) -> dict[str, bytes]:
    return {
        member: initializer_sources.get(member, b"# classified Python member\n")
        for member in _classification()["shipped_members"]
        if not member.endswith("/__init__.py") or member in initializer_sources
    }


def _write_synthetic_export_wheel(
    path: Path,
    initializer_sources: dict[str, bytes],
) -> None:
    with zipfile.ZipFile(path, mode="w") as archive:
        for member, source in _synthetic_shipped_sources(initializer_sources).items():
            archive.writestr(member, source)
        archive.writestr("spirallens-0.1.0.dist-info/METADATA", b"metadata")


def _write_synthetic_export_sdist(
    path: Path,
    initializer_sources: dict[str, bytes],
    *,
    manifest_bytes: bytes | None = None,
) -> None:
    prefix = "spirallens-0.1.0/src/"
    with tarfile.open(path, mode="w:gz") as archive:
        for member, source in _synthetic_shipped_sources(initializer_sources).items():
            info = tarfile.TarInfo(prefix + member)
            info.size = len(source)
            archive.addfile(info, io.BytesIO(source))
        if manifest_bytes is not None:
            info = tarfile.TarInfo(
                "spirallens-0.1.0/" + ORDERED_EXPORT_CLASSIFICATION_PATH
            )
            info.size = len(manifest_bytes)
            archive.addfile(info, io.BytesIO(manifest_bytes))


def test_wheel_and_sdist_ordered_export_classifiers_preserve_exact_bytes(
    tmp_path: Path,
) -> None:
    classification = _export_classification()
    shipped_members = _classification()["shipped_members"]
    sources = _source_initializer_bytes()
    wheel = tmp_path / "synthetic.whl"
    sdist = tmp_path / "synthetic.tar.gz"
    _write_synthetic_export_wheel(wheel, sources)
    _write_synthetic_export_sdist(sdist, sources)

    wheel_receipt = _classify_wheel_python_members(
        wheel,
        expected_members=shipped_members,
        ordered_export_classification=classification,
    )["ordered_export_inventory"]
    sdist_receipt = _classify_sdist_python_members(
        sdist,
        expected_members=shipped_members,
        ordered_export_classification=classification,
    )["ordered_export_inventory"]
    assert wheel_receipt == sdist_receipt
    assert wheel_receipt["package_count"] == 24
    assert wheel_receipt["export_count"] == 559


def test_ordered_export_archive_classifiers_reject_topology_and_nonregular(
    tmp_path: Path,
) -> None:
    classification = _export_classification()
    shipped_members = _classification()["shipped_members"]
    sources = _source_initializer_bytes()
    missing_sources = dict(sources)
    missing_sources.pop(next(iter(missing_sources)))
    wheel = tmp_path / "missing.whl"
    _write_synthetic_export_wheel(wheel, missing_sources)
    with pytest.raises(
        DistributionValidationError, match="Python member classification"
    ):
        _classify_wheel_python_members(
            wheel,
            expected_members=shipped_members,
            ordered_export_classification=classification,
        )

    sdist = tmp_path / "linked.tar.gz"
    prefix = "spirallens-0.1.0/src/"
    target = next(iter(sources))
    with tarfile.open(sdist, mode="w:gz") as archive:
        for initializer, source in sources.items():
            info = tarfile.TarInfo(prefix + initializer)
            if initializer == target:
                info.type = tarfile.SYMTYPE
                info.linkname = "elsewhere.py"
                archive.addfile(info)
            else:
                info.size = len(source)
                archive.addfile(info, io.BytesIO(source))
    with pytest.raises(DistributionValidationError, match="non-regular"):
        _classify_sdist_python_members(
            sdist,
            expected_members=shipped_members,
            ordered_export_classification=classification,
        )


def test_sdist_ordered_export_manifest_requires_byte_identity(tmp_path: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    manifest_bytes = (repository / ORDERED_EXPORT_CLASSIFICATION_PATH).read_bytes()
    sdist = tmp_path / "synthetic.tar.gz"
    _write_synthetic_export_sdist(
        sdist,
        _source_initializer_bytes(),
        manifest_bytes=manifest_bytes,
    )

    receipt = _require_sdist_exact_file(
        sdist,
        relative=ORDERED_EXPORT_CLASSIFICATION_PATH,
        expected_bytes=manifest_bytes,
        label="ordered export classification manifest",
    )
    assert receipt["byte_identical_to_source"] is True

    with pytest.raises(DistributionValidationError, match="differs from source"):
        _require_sdist_exact_file(
            sdist,
            relative=ORDERED_EXPORT_CLASSIFICATION_PATH,
            expected_bytes=manifest_bytes + b" ",
            label="ordered export classification manifest",
        )


def test_sdist_installed_import_policy_requires_one_regular_exact_file(
    tmp_path: Path,
) -> None:
    policy_relative = "distribution/_installed_import_policy.py"
    policy_bytes = _INSTALLED_IMPORT_POLICY_PATH.read_bytes()

    def write_archive(
        path: Path, *, duplicate: bool = False, symlink: bool = False
    ) -> None:
        with tarfile.open(path, mode="w:gz") as archive:
            for _index in range(2 if duplicate else 1):
                info = tarfile.TarInfo(f"spirallens-0.1.0/{policy_relative}")
                if symlink:
                    info.type = tarfile.SYMTYPE
                    info.linkname = "outside-policy.py"
                    archive.addfile(info)
                else:
                    info.size = len(policy_bytes)
                    archive.addfile(info, io.BytesIO(policy_bytes))

    valid = tmp_path / "valid.tar.gz"
    write_archive(valid)
    receipt = _require_sdist_exact_file(
        valid,
        relative=policy_relative,
        expected_bytes=policy_bytes,
        label="installed import policy",
    )
    assert receipt == {
        "path": policy_relative,
        "sha256": hashlib.sha256(policy_bytes).hexdigest(),
        "size_bytes": len(policy_bytes),
        "byte_identical_to_source": True,
    }

    with pytest.raises(DistributionValidationError, match="differs from source"):
        _require_sdist_exact_file(
            valid,
            relative=policy_relative,
            expected_bytes=policy_bytes + b" ",
            label="installed import policy",
        )
    for name, options in (
        ("duplicate", {"duplicate": True}),
        ("symlink", {"symlink": True}),
    ):
        invalid = tmp_path / f"{name}.tar.gz"
        write_archive(invalid, **options)
        with pytest.raises(
            DistributionValidationError,
            match="must contain one regular installed import policy",
        ):
            _require_sdist_exact_file(
                invalid,
                relative=policy_relative,
                expected_bytes=policy_bytes,
                label="installed import policy",
            )


def _installed_ordered_export_probe(
    environment_root: Path,
    *,
    sources: dict[str, bytes] | None = None,
    loaded: list[str] | None = None,
) -> str:
    if sources is None:
        sources = _source_initializer_bytes()
    return json.dumps(
        {
            "distribution_root": str(environment_root / "site-packages"),
            "initializer_sources_base64": {
                initializer: __import__("base64").b64encode(source).decode("ascii")
                for initializer, source in sources.items()
            },
            "spirallens_modules_loaded": [] if loaded is None else loaded,
        }
    )


def test_installed_ordered_export_probe_accepts_static_bytes_without_import(
    tmp_path: Path,
) -> None:
    environment_root = tmp_path / "venv"
    receipt = _parse_installed_ordered_export_probe_output(
        _installed_ordered_export_probe(environment_root),
        environment_root=environment_root,
        classification=_export_classification(),
        artifact_kind="fresh install",
    )

    assert receipt["package_count"] == 24
    assert receipt["export_count"] == 559
    assert receipt["spirallens_modules_imported"] is False
    assert receipt["distribution_root"] == "site-packages"


def test_installed_ordered_export_probe_rejects_import_and_outside_origin(
    tmp_path: Path,
) -> None:
    environment_root = tmp_path / "venv"
    classification = _export_classification()
    with pytest.raises(DistributionValidationError, match="imported SpiralLens"):
        _parse_installed_ordered_export_probe_output(
            _installed_ordered_export_probe(
                environment_root,
                loaded=["spirallens"],
            ),
            environment_root=environment_root,
            classification=classification,
            artifact_kind="fresh install",
        )
    outside = tmp_path / "outside"
    with pytest.raises(DistributionValidationError, match="outside its fresh"):
        _parse_installed_ordered_export_probe_output(
            _installed_ordered_export_probe(outside),
            environment_root=environment_root,
            classification=classification,
            artifact_kind="fresh install",
        )


def test_python_member_manifest_freezes_exact_roles_and_partition() -> None:
    classification = _classification()
    roles = classification["roles"]

    assert {name: len(members) for name, members in roles.items()} == {
        "package_initializer": 24,
        "console_entrypoint_runtime": 2,
        "shipped_runtime": 106,
        "repository_only": 49,
    }
    assert len(classification["shipped_members"]) == 132
    assert len(classification["source_members"]) == 181
    assert classification["manifest_sha256"] == (
        "81c7efba9d3084aafe3c49783ef5c338bc80ea303ab12ac730d99f1316e854d1"
    )


def test_exact_27_confirmation_modules_remain_source_but_not_artifacts() -> None:
    classification = _classification()
    all_confirmation_members = {
        member
        for member in classification["source_members"]
        if member.startswith("spirallens/qualification/confirmation_")
    }
    newly_repository_only_members = {
        member
        for member in all_confirmation_members
        if not member.startswith("spirallens/qualification/confirmation_v1_")
    }

    assert len(all_confirmation_members) == 47
    assert len(newly_repository_only_members) == 27
    assert all_confirmation_members <= set(classification["repository_only_members"])
    assert all_confirmation_members.isdisjoint(classification["shipped_members"])
    assert "spirallens/qualification/__init__.py" in classification["shipped_members"]

    repository = Path(__file__).resolve().parents[1]
    assert all(
        (repository / "src" / member).is_file()
        for member in newly_repository_only_members
    )

    installable_modules = set().union(
        *_installed_import_classification()["outcomes"].values()
    )
    newly_repository_only_modules = {
        member.removesuffix(".py").replace("/", ".")
        for member in newly_repository_only_members
    }
    assert newly_repository_only_modules.isdisjoint(installable_modules)


def test_source_python_inventory_is_exact_181_equals_132_plus_49_partition() -> None:
    repository = Path(__file__).resolve().parents[1]
    classification = _classification()

    receipt = _classify_source_python_members(
        repository,
        classification=classification,
    )

    assert receipt["count"] == 181
    assert receipt["shipped_count"] == 132
    assert receipt["repository_only_count"] == 49
    assert receipt["manifest_sha256"] == (
        "2a5e9db9541bb500829f555afd9ecc9307b6141f9fa49b9e9cf4b01b567d8e9a"
    )
    assert receipt["shipped_manifest_sha256"] == (
        "c8ddc9f9ae4c79e2b814f1da77faf61586ac75541c39b675bcc1c7ccc8e4b09a"
    )


def test_source_python_inventory_rejects_rogue_top_level_package(
    tmp_path: Path,
) -> None:
    classification = _classification()
    for member in classification["source_members"]:
        path = tmp_path / "src" / member
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# classified\n", encoding="utf-8")
    rogue = tmp_path / "src/roguepkg/__init__.py"
    rogue.parent.mkdir(parents=True)
    rogue.write_text("# unclassified\n", encoding="utf-8")

    with pytest.raises(DistributionValidationError, match="unclassified=.*roguepkg"):
        _classify_source_python_members(tmp_path, classification=classification)


def test_source_python_inventory_rejects_python_inside_egg_info(
    tmp_path: Path,
) -> None:
    classification = _classification()
    for member in classification["source_members"]:
        path = tmp_path / "src" / member
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# classified\n", encoding="utf-8")
    metadata = tmp_path / "src/spirallens.egg-info/PKG-INFO"
    metadata.parent.mkdir()
    metadata.write_text("Metadata-Version: 2.4\n", encoding="utf-8")
    rogue = metadata.parent / "rogue.py"
    rogue.write_text("# unclassified\n", encoding="utf-8")

    with pytest.raises(
        DistributionValidationError,
        match=r"unclassified=.*spirallens\.egg-info/rogue\.py",
    ):
        _classify_source_python_members(tmp_path, classification=classification)


def test_source_python_inventory_fails_closed_on_walk_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = Path(__file__).resolve().parents[1]
    classification = _classification()

    def failing_walk(
        _root: Path,
        *,
        followlinks: bool,
        onerror: object,
    ) -> object:
        assert followlinks is False
        assert callable(onerror)
        onerror(PermissionError("enumeration denied"))
        raise AssertionError("onerror must raise before os.walk can continue")

    monkeypatch.setattr(_VALIDATOR.os, "walk", failing_walk)

    with pytest.raises(
        DistributionValidationError,
        match="cannot enumerate the Python member source inventory",
    ) as raised:
        _classify_source_python_members(
            repository,
            classification=classification,
        )
    assert isinstance(raised.value.__cause__, PermissionError)


def test_source_python_inventory_rejects_rogue_python_under_pycache(
    tmp_path: Path,
) -> None:
    classification = _classification()
    for member in classification["source_members"]:
        path = tmp_path / "src" / member
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# classified\n", encoding="utf-8")
    rogue = tmp_path / "src/spirallens/core/__pycache__/rogue.py"
    rogue.parent.mkdir()
    rogue.write_text("# unclassified\n", encoding="utf-8")

    with pytest.raises(DistributionValidationError, match="unclassified=.*rogue"):
        _classify_source_python_members(tmp_path, classification=classification)


def test_exact_wheel_classifier_ignores_dist_info_but_rejects_extra_python(
    tmp_path: Path,
) -> None:
    members = _classification()["shipped_members"]
    wheel = tmp_path / "synthetic.whl"
    _write_synthetic_wheel(
        wheel,
        (*members, "spirallens-0.1.0.dist-info/METADATA"),
    )
    receipt = _classify_wheel_python_members(wheel, expected_members=members)
    assert receipt["count"] == 132

    rogue = tmp_path / "rogue.whl"
    _write_synthetic_wheel(rogue, (*members, "roguepkg/__init__.py"))
    with pytest.raises(DistributionValidationError, match="unclassified=.*roguepkg"):
        _classify_wheel_python_members(rogue, expected_members=members)

    policy = tmp_path / "policy.whl"
    _write_synthetic_wheel(
        policy,
        (*members, "distribution/_installed_import_policy.py"),
    )
    with pytest.raises(DistributionValidationError, match="unclassified=.*policy"):
        _classify_wheel_python_members(policy, expected_members=members)


def test_exact_wheel_classifier_rejects_duplicate_unsafe_and_symlink(
    tmp_path: Path,
) -> None:
    members = _classification()["shipped_members"]
    duplicate = tmp_path / "duplicate.whl"
    with zipfile.ZipFile(duplicate, mode="w") as archive:
        archive.writestr(members[0], "")
        with pytest.warns(UserWarning, match="Duplicate name"):
            archive.writestr(members[0], "")
    with pytest.raises(DistributionValidationError, match="duplicate"):
        _classify_wheel_python_members(duplicate, expected_members=members)

    unsafe = tmp_path / "unsafe.whl"
    _write_synthetic_wheel(unsafe, (*members, "../rogue.py"))
    with pytest.raises(DistributionValidationError, match="unsafe path"):
        _classify_wheel_python_members(unsafe, expected_members=members)

    symlink = tmp_path / "symlink.whl"
    target = "spirallens/core/canonical.py"
    with zipfile.ZipFile(symlink, mode="w") as archive:
        for member in members:
            if member != target:
                archive.writestr(member, "")
        info = zipfile.ZipInfo(target)
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, "elsewhere.py")
    with pytest.raises(DistributionValidationError, match="non-regular"):
        _classify_wheel_python_members(symlink, expected_members=members)


def test_exact_wheel_classifier_rejects_dist_info_symlink(
    tmp_path: Path,
) -> None:
    members = _classification()["shipped_members"]
    wheel = tmp_path / "metadata-symlink.whl"
    with zipfile.ZipFile(wheel, mode="w") as archive:
        for member in members:
            archive.writestr(member, "")
        info = zipfile.ZipInfo("spirallens-0.1.0.dist-info/METADATA")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, "outside-metadata")

    with pytest.raises(
        DistributionValidationError,
        match=r"non-regular archive members: .*\.dist-info/METADATA",
    ):
        _classify_wheel_python_members(wheel, expected_members=members)


@pytest.mark.parametrize(
    "noncanonical",
    [
        "spirallens/./cli.py",
        "spirallens//cli.py",
    ],
)
def test_exact_wheel_classifier_rejects_noncanonical_member_spelling(
    tmp_path: Path,
    noncanonical: str,
) -> None:
    members = _classification()["shipped_members"]
    wheel = tmp_path / "noncanonical.whl"
    _write_synthetic_wheel(
        wheel,
        tuple(
            noncanonical if member == "spirallens/cli.py" else member
            for member in members
        ),
    )

    with pytest.raises(DistributionValidationError, match="unsafe path"):
        _classify_wheel_python_members(wheel, expected_members=members)


@pytest.mark.parametrize(
    "extra",
    [
        "spirallens/data.json",
        "spirallens/native.so",
        "spirallens/core/__pycache__/canonical.cpython-313.pyc",
    ],
)
def test_exact_wheel_classifier_rejects_package_data(
    tmp_path: Path,
    extra: str,
) -> None:
    members = _classification()["shipped_members"]
    wheel = tmp_path / "synthetic.whl"
    _write_synthetic_wheel(wheel, (*members, extra))
    with pytest.raises(DistributionValidationError, match="non-Python"):
        _classify_wheel_python_members(wheel, expected_members=members)


def test_exact_sdist_classifier_ignores_egg_info_and_rejects_partial_package(
    tmp_path: Path,
) -> None:
    members = _classification()["shipped_members"]
    prefix = "spirallens-0.1.0/src/"
    sdist = tmp_path / "synthetic.tar.gz"
    _write_synthetic_sdist(
        sdist,
        tuple(prefix + member for member in members)
        + (prefix + "spirallens.egg-info/SOURCES.txt",),
    )
    assert (
        _classify_sdist_python_members(
            sdist,
            expected_members=members,
        )["count"]
        == 132
    )

    partial = tmp_path / "partial.tar.gz"
    _write_synthetic_sdist(
        partial,
        tuple(prefix + member for member in members) + (prefix + "newpkg/module.py",),
    )
    with pytest.raises(DistributionValidationError, match="unclassified=.*newpkg"):
        _classify_sdist_python_members(partial, expected_members=members)


@pytest.mark.parametrize("link_type", [tarfile.SYMTYPE, tarfile.LNKTYPE])
def test_exact_sdist_classifier_rejects_duplicate_unsafe_and_links(
    tmp_path: Path,
    link_type: bytes,
) -> None:
    members = _classification()["shipped_members"]
    prefix = "spirallens-0.1.0/src/"
    duplicate = tmp_path / "duplicate.tar.gz"
    _write_synthetic_sdist(
        duplicate,
        (prefix + members[0], prefix + members[0]),
    )
    with pytest.raises(DistributionValidationError, match="duplicate"):
        _classify_sdist_python_members(duplicate, expected_members=members)

    unsafe = tmp_path / "unsafe.tar.gz"
    _write_synthetic_sdist(unsafe, (*tuple(prefix + m for m in members), "../x.py"))
    with pytest.raises(DistributionValidationError, match="unsafe path"):
        _classify_sdist_python_members(unsafe, expected_members=members)

    linked = tmp_path / "linked.tar.gz"
    target = "spirallens/core/canonical.py"
    with tarfile.open(linked, mode="w:gz") as archive:
        for member in members:
            if member == target:
                continue
            info = tarfile.TarInfo(prefix + member)
            info.size = 0
            archive.addfile(info, io.BytesIO())
        info = tarfile.TarInfo(prefix + target)
        info.type = link_type
        info.linkname = "elsewhere.py"
        archive.addfile(info)
    with pytest.raises(DistributionValidationError, match="non-regular"):
        _classify_sdist_python_members(linked, expected_members=members)


@pytest.mark.parametrize(
    "noncanonical_suffix",
    [
        "src/./spirallens/cli.py",
        "src//spirallens/cli.py",
    ],
)
def test_exact_sdist_classifier_rejects_noncanonical_member_spelling(
    tmp_path: Path,
    noncanonical_suffix: str,
) -> None:
    members = _classification()["shipped_members"]
    top_level = "spirallens-0.1.0/"
    prefix = top_level + "src/"
    sdist = tmp_path / "noncanonical.tar.gz"
    _write_synthetic_sdist(
        sdist,
        tuple(
            top_level + noncanonical_suffix
            if member == "spirallens/cli.py"
            else prefix + member
            for member in members
        ),
    )

    with pytest.raises(DistributionValidationError, match="unsafe path"):
        _classify_sdist_python_members(sdist, expected_members=members)


def test_exact_sdist_classifier_rejects_regular_file_with_trailing_slash(
    tmp_path: Path,
) -> None:
    members = _classification()["shipped_members"]
    prefix = "spirallens-0.1.0/src/"
    target = "spirallens/core/canonical.py"
    sdist = tmp_path / "regular-file-trailing-slash.tar.gz"
    with tarfile.open(sdist, mode="w:gz") as archive:
        for member in members:
            name = prefix + member + ("/" if member == target else "")
            info = tarfile.TarInfo(name)
            info.type = tarfile.REGTYPE
            info.size = 0
            archive.addfile(info, io.BytesIO())

    with pytest.raises(
        DistributionValidationError,
        match=r"unsafe path: .*canonical\.py/",
    ):
        _classify_sdist_python_members(sdist, expected_members=members)


@pytest.mark.parametrize(
    "unsafe_member",
    [
        "spirallens-0.1.0/src/./spirallens/cli.py",
        "spirallens-0.1.0/src/spirallens/cli.py/",
    ],
)
def test_sdist_extractor_independently_rejects_noncanonical_regular_files(
    tmp_path: Path,
    unsafe_member: str,
) -> None:
    sdist = tmp_path / "unsafe-extraction.tar.gz"
    with tarfile.open(sdist, mode="w:gz") as archive:
        for name in ("spirallens-0.1.0/pyproject.toml", unsafe_member):
            info = tarfile.TarInfo(name)
            info.type = tarfile.REGTYPE
            info.size = 0
            archive.addfile(info, io.BytesIO())

    with pytest.raises(DistributionValidationError, match="unsafe path"):
        _extract_sdist(sdist, tmp_path / "extracted")


def test_sdist_test_surface_absence_receipt_ignores_similar_path(
    tmp_path: Path,
) -> None:
    extracted_source = tmp_path / "spirallens-0.1.0"
    extracted_source.mkdir()
    (extracted_source / "tests_backup").mkdir()
    (extracted_source / "tests_backup" / "retained.py").write_text(
        "# not the top-level tests path\n",
        encoding="utf-8",
    )

    assert _require_absent_sdist_test_surface(extracted_source) == {
        "observation": "absent",
        "count": 0,
        "members": [],
    }


@pytest.mark.parametrize("observed_kind", ["directory", "file", "symlink"])
def test_sdist_test_surface_rejects_every_observed_top_level_tests_path(
    tmp_path: Path,
    observed_kind: str,
) -> None:
    extracted_source = tmp_path / "spirallens-0.1.0"
    extracted_source.mkdir()
    tests_path = extracted_source / "tests"
    if observed_kind == "directory":
        tests_path.mkdir()
    elif observed_kind == "file":
        tests_path.write_text("# misplaced test surface\n", encoding="utf-8")
    else:
        tests_path.symlink_to(tmp_path / "missing-tests-target")

    with pytest.raises(
        DistributionValidationError,
        match="extracted sdist contains top-level tests path",
    ):
        _require_absent_sdist_test_surface(extracted_source)


def test_sdist_test_surface_gate_rejects_tests_extracted_from_archive(
    tmp_path: Path,
) -> None:
    sdist = tmp_path / "synthetic.tar.gz"
    _write_synthetic_sdist(
        sdist,
        (
            "spirallens-0.1.0/pyproject.toml",
            "spirallens-0.1.0/tests/test_publication.py",
        ),
    )

    extracted_source = _extract_sdist(sdist, tmp_path / "extracted")
    with pytest.raises(
        DistributionValidationError,
        match="extracted sdist contains top-level tests path",
    ):
        _require_absent_sdist_test_surface(extracted_source)


def test_installed_member_probe_excludes_metadata_and_rejects_pyc() -> None:
    members = _classification()["shipped_members"]
    output = json.dumps({"package_members": list(members)})
    assert (
        _parse_installed_python_member_probe_output(
            output,
            expected_members=members,
            artifact_kind="fixture install",
        )["count"]
        == 132
    )

    bad = json.dumps(
        {
            "package_members": sorted(
                (*members, "spirallens/__pycache__/cli.cpython-313.pyc")
            )
        }
    )
    with pytest.raises(DistributionValidationError, match="non-Python"):
        _parse_installed_python_member_probe_output(
            bad,
            expected_members=members,
            artifact_kind="fixture install",
        )


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
        "spirallens/qualification/confirmation_attempt_records.py",
        "spirallens/qualification/confirmation_v1_records.py",
    )
    _write_synthetic_wheel(
        wheel,
        (
            "spirallens/qualification/public_surface.py",
            matching_members[2],
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
    new_member = "spirallens/qualification/confirmation_future_module.py"
    _write_synthetic_wheel(wheel, (new_member,))

    assert _classify_repository_experiment_members(wheel) == (new_member,)


def test_pep3147_matching_wheel_member_is_classified(tmp_path: Path) -> None:
    wheel = tmp_path / "synthetic.whl"
    member = "spirallens/qualification/__pycache__/confirmation_attempt_records.cpython-313.pyc"
    _write_synthetic_wheel(wheel, (member,))

    assert _classify_repository_experiment_members(wheel) == (member,)


def test_repository_experiment_members_are_classified_from_sdist_paths(
    tmp_path: Path,
) -> None:
    sdist = tmp_path / "synthetic.tar.gz"
    matching = (
        "spirallens-0.1.0/src/spirallens/access/_pythia160_preobservation.py",
        "spirallens-0.1.0/src/spirallens/qualification/confirmation_attempt_records.py",
        "spirallens-0.1.0/src/spirallens/qualification/confirmation_v1_records.py",
    )
    _write_synthetic_sdist(
        sdist,
        (
            "spirallens-0.1.0/src/spirallens/access/contracts.py",
            matching[2],
            matching[1],
            matching[0],
        ),
    )

    assert _classify_repository_experiment_sdist_members(sdist) == tuple(
        sorted(matching)
    )


def test_source_inventory_requires_the_exact_reviewed_regular_49_paths(
    tmp_path: Path,
) -> None:
    _write_source_inventory(tmp_path, REPOSITORY_EXPERIMENT_SOURCE_PATHS)

    assert _repository_experiment_source_report(tmp_path) == {
        "observation": "reviewed-exact-set-present",
        "count": 49,
        "all_regular_files": True,
        "total_lines": 49,
        "paths": list(REPOSITORY_EXPERIMENT_SOURCE_PATHS),
    }


def test_source_inventory_rejects_a_future_matching_prefix(tmp_path: Path) -> None:
    _write_source_inventory(tmp_path, REPOSITORY_EXPERIMENT_SOURCE_PATHS)
    future = tmp_path / "src/spirallens/qualification/confirmation_future_module.py"
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
        "count": 49,
        "all_regular_files": True,
        "total_lines": 55912,
        "paths": list(REPOSITORY_EXPERIMENT_SOURCE_PATHS),
    }
    absent = _require_zero_repository_experiment_members((), artifact_kind="fixture")

    assert _library_separation_report(
        source_tree=source_tree,
        sdist=absent,
        direct_source_wheel=absent,
        sdist_derived_wheel=absent,
        python_module_inventory={"fixture": True},
        ordered_package_export_inventory={"fixture": True},
    ) == {
        "repository_experiment_separation": {
            "source_tree": source_tree,
            "sdist": absent,
            "direct_source_wheel": absent,
            "sdist_derived_wheel": absent,
            "source_prefixes": [
                "src/spirallens/access/_pythia160_",
                "src/spirallens/qualification/confirmation_",
            ],
            "wheel_prefixes": list(REPOSITORY_EXPERIMENT_WHEEL_MEMBER_PREFIXES),
        },
        "python_module_inventory": {"fixture": True},
        "ordered_package_export_inventory": {"fixture": True},
        "closed_wheel_python_module_inventory_established": True,
        "closed_ordered_package_export_inventory_established": True,
        "closed_installed_module_import_outcome_inventory_established": True,
        "closed_public_api_contract_established": False,
        "runtime_successful_package_export_values_established": True,
        "runtime_export_values_established": False,
        "all_package_runtime_export_values_established": False,
        "export_symbol_importability_established": False,
        "side_effect_free_imports_established": False,
        "closed_library_allowlist_established": False,
        "grants": {
            "authority": False,
            "lib_l0": False,
            "library": False,
            "portability": False,
            "public_api": False,
            "scientific": False,
        },
    }


def test_private_held_file_is_an_explicit_non_experiment_wheel_import() -> None:
    classification = _load_python_member_classification(Path(__file__).parents[1])
    assert PRIVATE_HELD_FILE_WHEEL_MEMBER in classification["shipped_members"]
    assert PRIVATE_HELD_FILE_IMPORT in DEFAULT_IMPORTS
    assert not any(
        PRIVATE_HELD_FILE_WHEEL_MEMBER.startswith(prefix)
        for prefix in REPOSITORY_EXPERIMENT_WHEEL_MEMBER_PREFIXES
    )


def test_private_strict_yaml_factory_is_an_explicit_wheel_member() -> None:
    classification = _load_python_member_classification(Path(__file__).parents[1])
    assert PRIVATE_STRICT_YAML_WHEEL_MEMBER in classification["shipped_members"]
    assert not any(
        PRIVATE_STRICT_YAML_WHEEL_MEMBER.startswith(prefix)
        for prefix in REPOSITORY_EXPERIMENT_WHEEL_MEMBER_PREFIXES
    )


def test_atlas_reader_probe_is_separate_from_dependency_free_imports() -> None:
    assert REPORT_SCHEMA_VERSION == "spirallens.distribution-validation.v0.9"
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
    classification = _load_python_member_classification(Path(__file__).parents[1])
    assert PRIVATE_ATLAS_CAPTURE_STORE_WHEEL_MEMBER in classification["shipped_members"]


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


def test_repository_experiment_absence_probe_accepts_exact_49_receipts(
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
    assert parsed["exact_module_not_found_receipt_count"] == 49
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
    assert report["sdist_test_surface"] == absent
    separation = report["library_separation"]
    assert separation["repository_experiment_separation"] == {
        "source_tree": {
            "observation": "reviewed-exact-set-present",
            "count": 49,
            "all_regular_files": True,
            "total_lines": 55912,
            "paths": list(REPOSITORY_EXPERIMENT_SOURCE_PATHS),
        },
        "sdist": absent,
        "direct_source_wheel": absent,
        "sdist_derived_wheel": absent,
        "source_prefixes": [
            "src/spirallens/access/_pythia160_",
            "src/spirallens/qualification/confirmation_",
        ],
        "wheel_prefixes": list(REPOSITORY_EXPERIMENT_WHEEL_MEMBER_PREFIXES),
    }
    assert separation["closed_wheel_python_module_inventory_established"] is True
    assert separation["closed_ordered_package_export_inventory_established"] is True
    assert separation["closed_public_api_contract_established"] is False
    assert separation["runtime_export_values_established"] is False
    assert separation["export_symbol_importability_established"] is False
    assert separation["closed_library_allowlist_established"] is False
    assert separation["grants"] == {
        "authority": False,
        "lib_l0": False,
        "library": False,
        "portability": False,
        "public_api": False,
        "scientific": False,
    }
    python_inventory = separation["python_module_inventory"]
    assert python_inventory["classification"]["role_counts"] == {
        "package_initializer": 24,
        "console_entrypoint_runtime": 2,
        "shipped_runtime": 106,
        "repository_only": 49,
    }
    assert python_inventory["source_tree"]["count"] == 181
    newly_repository_only_confirmation_members = {
        member
        for member in python_inventory["source_tree"]["members"]
        if member.startswith("spirallens/qualification/confirmation_")
        and not member.startswith("spirallens/qualification/confirmation_v1_")
    }
    assert len(newly_repository_only_confirmation_members) == 27
    for artifact_kind in (
        "sdist",
        "direct_source_wheel",
        "sdist_derived_wheel",
        "direct_source_install",
        "sdist_derived_install",
    ):
        assert python_inventory[artifact_kind]["count"] == 132
        assert newly_repository_only_confirmation_members.isdisjoint(
            python_inventory[artifact_kind]["members"]
        )
        assert python_inventory[artifact_kind]["manifest_sha256"] == (
            "c8ddc9f9ae4c79e2b814f1da77faf61586ac75541c39b675bcc1c7ccc8e4b09a"
        )
    assert all(python_inventory["equality"].values())
    export_inventory = separation["ordered_package_export_inventory"]
    assert export_inventory["classification"] == {
        "claim_boundary": (
            "classification grants no public API, stability, compatibility, "
            "authority, scientific claim, or library maturity"
        ),
        "classification_scope": (
            "literal ordered __all__ values for every classified package initializer"
        ),
        "export_count": 559,
        "manifest_path": ORDERED_EXPORT_CLASSIFICATION_PATH,
        "manifest_sha256": (
            "cb9d58ba50c3ead9551da17a7b3d31180157c0b0f7b005aff2df4c5f05effe3e"
        ),
        "package_count": 24,
        "schema_version": ORDERED_EXPORT_CLASSIFICATION_SCHEMA_VERSION,
        "sdist_manifest": {
            "path": ORDERED_EXPORT_CLASSIFICATION_PATH,
            "sha256": (
                "cb9d58ba50c3ead9551da17a7b3d31180157c0b0f7b005aff2df4c5f05effe3e"
            ),
            "size_bytes": len(
                (repository / ORDERED_EXPORT_CLASSIFICATION_PATH).read_bytes()
            ),
            "byte_identical_to_source": True,
        },
    }
    for artifact_kind in (
        "source_tree",
        "sdist",
        "direct_source_wheel",
        "sdist_derived_wheel",
        "direct_source_install",
        "sdist_derived_install",
    ):
        receipt = export_inventory[artifact_kind]
        assert receipt["observation"] == "exact-literal-ordered-set"
        assert receipt["package_count"] == 24
        assert receipt["export_count"] == 559
        assert receipt["initializer_bytes_sha256"] == (
            "6f4556d990e93b4b82b857a872c25f7efd0b40a9e2131ee818832946137a7efa"
        )
        assert receipt["ordered_exports_sha256"] == (
            "e2c947c30f0323c54c1713274dac0117fd74dc86cd576279c44a040dfc0ae798"
        )
    for artifact_kind in ("direct_source_install", "sdist_derived_install"):
        assert export_inventory[artifact_kind]["spirallens_modules_imported"] is False
    assert all(export_inventory["equality"].values())
    assert report["required_imports"] == list(DEFAULT_IMPORTS)
    assert report["required_atlas_reader_imports"] == list(ATLAS_READER_IMPORTS)
    assert report["required_scientific_imports"] == list(DEFAULT_SCIENTIFIC_IMPORTS)
    assert report["required_wheel_members"] == list(
        _classification()["shipped_members"]
    )
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
    assert source_import["imported_module_count"] == 49
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
        assert install_inspection["exact_module_not_found_receipt_count"] == 49
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
