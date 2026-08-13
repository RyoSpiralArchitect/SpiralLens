# ruff: noqa: SIM905

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path


def test_readme_core_canonical_example_runs_from_current_source(tmp_path: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    readme = (repository / "README.md").read_text(encoding="utf-8")
    start = "<!-- spirallens-core-canonical-example:start -->"
    end = "<!-- spirallens-core-canonical-example:end -->"
    assert readme.count(start) == readme.count(end) == 1
    section = readme.split(start, 1)[1].split(end, 1)[0].strip()
    assert section.startswith("```python\n") and section.endswith("\n```")
    source = section.removeprefix("```python\n").removesuffix("\n```")
    output_start = "<!-- spirallens-core-canonical-example-output:start -->"
    output_end = "<!-- spirallens-core-canonical-example-output:end -->"
    assert readme.count(output_start) == readme.count(output_end) == 1
    output = readme.split(output_start, 1)[1].split(output_end, 1)[0].strip()
    output_prefix, output_suffix = "Expected output:\n\n```text\n", "\n```"
    assert output.startswith(output_prefix) and output.endswith(output_suffix)
    expected_output = output[len(output_prefix) : -len(output_suffix)] + "\n"
    exports = (
        "CanonicalJsonError JsonScalar JsonValue canonical_json_bytes "
        "canonical_json_sha256 parse_canonical_json sha256_bytes"
    ).split()
    imports = [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    assert len(imports) == 1
    imported = imports[0]
    assert isinstance(imported, ast.ImportFrom)
    assert (imported.module, imported.level) == ("spirallens.core", 0)
    assert tuple((alias.name, alias.asname) for alias in imported.names) == tuple(
        (name, None) for name in exports
    )
    used_exports = {
        node.id
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Name)
        and isinstance(node.ctx, ast.Load)
        and node.id in exports
    }
    assert used_exports == set(exports)
    source_root = repository / "src"
    origins = {
        "spirallens": source_root / "spirallens/__init__.py",
        "spirallens.core": source_root / "spirallens/core/__init__.py",
        "spirallens.core.canonical": source_root / "spirallens/core/canonical.py",
    }
    forbidden = (
        "faiss huggingface_hub numpy safetensors scipy torch transformers yaml"
    ).split()
    expected_origins = {name: str(path) for name, path in origins.items()}
    probe = (
        "import pathlib, sys\n"
        f"sys.path.insert(0, {str(source_root)!r})\n"
        f"exec(compile({source!r}, 'README.md#core-canonical-example', 'exec'))\n"
        "import spirallens.core as loaded_core\n"
        f"expected_origins = {expected_origins!r}\n"
        "for name, expected in expected_origins.items():\n"
        "    assert pathlib.Path(sys.modules[name].__file__).resolve() == pathlib.Path(expected)\n"
        f"assert all(globals()[name] is getattr(loaded_core, name) for name in {exports!r})\n"
        "loaded = sorted(name for name in sys.modules if name == 'spirallens' or name.startswith('spirallens.'))\n"
        f"assert loaded == {sorted(origins)!r}\n"
        f"assert not any(name in sys.modules for name in {forbidden!r})\n"
        "print('__probe__=ok')\n"
    )
    environment = dict(os.environ)
    for name in ("PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP", "VIRTUAL_ENV"):
        environment.pop(name, None)
    completed = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", probe],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == ""
    assert completed.stdout == expected_output + "__probe__=ok\n"
