from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

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
DistributionValidationError = _VALIDATOR.DistributionValidationError
REPORT_SCHEMA_VERSION = _VALIDATOR.REPORT_SCHEMA_VERSION
_parse_probe_output = _VALIDATOR._parse_probe_output
_sha256_file = _VALIDATOR._sha256_file


def test_sha256_file_streams_exact_bytes(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.whl"
    payload = b"spirallens-wheel-fixture"
    artifact.write_bytes(payload)

    assert _sha256_file(artifact) == hashlib.sha256(payload).hexdigest()


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
    assert report["required_imports"] == list(DEFAULT_IMPORTS)
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
        "frontend": "python-build",
        "isolation": True,
        "source_copy": True,
        "wheel_built_from_sdist": True,
    }
    assert report["installation"]["no_dependencies"] is True
    assert report["installation"]["system_site_packages"] is False
    assert report["installation"]["wheel_filename"].endswith(".whl")
    assert report["inspection"]["forbidden_imports_loaded"] == []
    assert report["inspection"]["direct_url_editable"] is False
    assert set(report["inspection"]["module_origins"]) == set(DEFAULT_IMPORTS)
    assert all(
        "site-packages/spirallens" in origin
        for origin in report["inspection"]["module_origins"].values()
    )
    assert sorted(item["kind"] for item in report["artifacts"]) == [
        "sdist",
        "wheel",
    ]
    for artifact in report["artifacts"]:
        assert len(artifact["sha256"]) == 64
        assert artifact["size_bytes"] > 0
