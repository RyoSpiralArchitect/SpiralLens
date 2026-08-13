from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import sys
from urllib.parse import unquote, urlsplit
from urllib.request import url2pathname

EXPORTS = (
    "CanonicalJsonError JsonScalar JsonValue canonical_json_bytes "
    "canonical_json_sha256 parse_canonical_json sha256_bytes"
).split()
VERSIONS = dict(
    item.split("==", 1)
    for item in (
        "build==1.5.0 iniconfig==2.3.0 numpy==2.4.6 packaging==26.3 "
        "pip==26.2.1 pluggy==1.6.0 pygments==2.20.0 pyproject-hooks==1.2.0 "
        "pytest==9.1.1 pyyaml==6.0.3 scipy==1.17.1 setuptools==84.0.0 "
        "spirallens==0.1.0 wheel==0.48.0"
    ).split()
)
FORBIDDEN = set(
    "faiss huggingface_hub numpy safetensors scipy torch transformers yaml".split()
)


def _normalized_distribution_name(value: str) -> str:
    return value.lower().replace("_", "-").replace(".", "-")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-packages", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--expected-python", required=True)
    parser.add_argument("--tested-sha", required=True)
    parser.add_argument("--runner-image", required=True)
    arguments = parser.parse_args()
    site_packages = arguments.site_packages.resolve(strict=True)
    wheel = arguments.wheel.resolve(strict=True)
    workspace = arguments.workspace.resolve(strict=True)

    assert sys.prefix != sys.base_prefix
    assert platform.python_implementation() == "CPython"
    assert platform.python_version() == arguments.expected_python
    assert platform.machine() == "x86_64"
    assert sum(Path(item).resolve() == site_packages for item in sys.path) == 1
    workspace_entries = [
        item
        for item in sys.path
        if item
        and (
            Path(item).resolve() == workspace
            or workspace in Path(item).resolve().parents
        )
    ]
    assert workspace_entries == []
    assert not list(site_packages.glob("*.egg-link"))
    assert all(
        str(workspace) not in item.read_text(encoding="utf-8")
        for item in site_packages.glob("*.pth")
    )
    distributions = {
        _normalized_distribution_name(item.metadata["Name"]): item.version
        for item in metadata.distributions()
    }
    assert distributions == VERSIONS

    distribution = metadata.distribution("spirallens")
    assert Path(distribution.locate_file("")).resolve() == site_packages
    direct_url = json.loads(distribution.read_text("direct_url.json") or "null")
    assert isinstance(direct_url, dict)
    assert set(direct_url) == {"archive_info", "url"}
    parsed_url = urlsplit(direct_url["url"])
    assert parsed_url.scheme == "file" and parsed_url.netloc in {"", "localhost"}
    installed_from = Path(url2pathname(unquote(parsed_url.path))).resolve(strict=True)
    assert installed_from == wheel
    wheel_sha256 = hashlib.sha256(wheel.read_bytes()).hexdigest()
    archive_info = direct_url["archive_info"]
    assert set(archive_info) == {"hash", "hashes"}
    assert archive_info["hashes"] == {"sha256": wheel_sha256}
    assert archive_info["hash"] == f"sha256={wheel_sha256}"

    import spirallens.core as core
    from spirallens.core import canonical

    origins = {
        "spirallens": site_packages / "spirallens/__init__.py",
        "spirallens.core": site_packages / "spirallens/core/__init__.py",
        "spirallens.core.canonical": site_packages / "spirallens/core/canonical.py",
    }
    assert {
        name: Path(sys.modules[name].__file__).resolve() for name in origins
    } == origins
    assert {
        name: Path(sys.modules[name].__spec__.origin).resolve() for name in origins
    } == origins
    assert core.__all__ == EXPORTS
    assert all(getattr(core, name) is getattr(canonical, name) for name in EXPORTS)
    loaded = sorted(
        name
        for name in sys.modules
        if name == "spirallens" or name.startswith("spirallens.")
    )
    assert loaded == sorted(origins)
    assert FORBIDDEN.isdisjoint(sys.modules)

    print(
        json.dumps(
            {
                "direct_url_editable": False,
                "distributions": distributions,
                "forbidden_imports_loaded": [],
                "machine": platform.machine(),
                "module_origins": {
                    name: path.relative_to(site_packages).as_posix()
                    for name, path in origins.items()
                },
                "ordered_exports": EXPORTS,
                "platform": platform.platform(),
                "python_implementation": platform.python_implementation(),
                "python": platform.python_version(),
                "runner_image": arguments.runner_image,
                "status": "pass",
                "tested_sha": arguments.tested_sha,
                "wheel": {"filename": wheel.name, "sha256": wheel_sha256},
                "workspace_sys_path_entries": [],
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
