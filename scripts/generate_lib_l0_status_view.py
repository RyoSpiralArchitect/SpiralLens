#!/usr/bin/env python3
"""Render the non-authoritative generated LIB-L0 status/schema/digest view."""

import argparse
import ast
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path

VIEW_SCHEMA_VERSION = "spirallens.lib-l0-status-view.v0.1"
GENERATOR_VERSION = "spirallens.lib-l0-status-view-generator.v0.1"
CLAIM_CEILING = (
    "projection and navigation only; a successful check observes committed/rendered "
    "byte equality for the bounded input reads during that invocation, not a "
    "validation pass, installed behavior, "
    "compatibility, portability, public API, library maturity, LIB-L0 completion, "
    "release, scientific claim, authority, or D7 readiness or re-anchor"
)
GENERATOR_RELATIVE_PATH = "scripts/generate_lib_l0_status_view.py"
VIEW_RELATIVE_PATH = "docs/generated/lib_l0_status_v0_1.json"
POLICY_INPUTS = (
    "docs/FUNDAMENTAL_FRAME.md",
    "docs/EXPERIMENT_INTERPRETATION_LEDGER.md",
    "docs/ROADMAP.md",
)
VALIDATOR_RELATIVE_PATH = "scripts/validate_distribution.py"
VALIDATOR_SCHEMA_OWNER = "REPORT_SCHEMA_VERSION"
_DIST, _NS = "distribution/spirallens_", "spirallens."
MANIFEST_SCHEMAS = {
    _DIST + "installed_imports_v0_1.json": _NS + "installed-import-conformance.v0.1",
    _DIST + "ordered_exports_v0_1.json": _NS + "ordered-package-exports.v0.1",
    _DIST + "python_members_v0_1.json": _NS + "python-distribution-members.v0.1",
}
MANIFEST_INPUTS = tuple(MANIFEST_SCHEMAS)
OWNER_PATHS = POLICY_INPUTS + (VALIDATOR_RELATIVE_PATH,) + MANIFEST_INPUTS
OWNER_PATHS += (GENERATOR_RELATIVE_PATH,)
DOCUMENT_LIMIT, MACHINE_INPUT_LIMIT, VIEW_LIMIT = 512 * 1024, 64 * 1024, 16 * 1024


class ViewGenerationError(ValueError):
    pass


def _source_root(value: Path) -> Path:
    absolute = Path(os.path.abspath(value))
    try:
        is_directory = stat.S_ISDIR(value.lstat().st_mode)
        resolved = value.resolve(strict=True)
    except OSError as error:
        raise ViewGenerationError("source root is unavailable") from error
    if not is_directory or resolved != absolute:
        raise ViewGenerationError("source root must be an ordinary unaliased directory")
    return resolved


def _read_owned(root: Path, relative: str, *, limit: int) -> bytes:
    path = root / relative
    absolute = Path(os.path.abspath(path))
    try:
        before = path.lstat()
        resolved = path.resolve(strict=True)
        if not stat.S_ISREG(before.st_mode) or resolved != absolute:
            raise ViewGenerationError(f"owner is aliased or not a file: {relative}")
        if before.st_size > limit:
            raise ViewGenerationError(f"owner exceeds its byte limit: {relative}")
        with path.open("rb") as handle:
            descriptor_before = os.fstat(handle.fileno())
            source = handle.read(limit + 1)
            descriptor_after = os.fstat(handle.fileno())
        after = path.lstat()
    except ViewGenerationError:
        raise
    except OSError as error:
        raise ViewGenerationError(f"cannot read owner: {relative}") from error
    identities = {
        item[:7] + (item.st_mtime_ns, item.st_ctime_ns)
        for item in (before, descriptor_before, descriptor_after, after)
    }
    if len(source) > limit or len(identities) != 1:
        raise ViewGenerationError(f"owner changed while being read: {relative}")
    try:
        source.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ViewGenerationError(f"owner is not UTF-8: {relative}") from error
    return source


def _record(relative: str, source: bytes) -> dict[str, object]:
    return {
        "path": relative,
        "sha256": hashlib.sha256(source).hexdigest(),
        "size_bytes": len(source),
    }


def _roadmap_status(source: bytes) -> str:
    text = source.decode("utf-8")
    pattern = r"^\| Library \| `LIB-L0` through `LIB-L3` \| `LIB-L0` ([^`|\r\n]+) \|"
    table = list(re.finditer(pattern, text, flags=re.MULTILINE))
    start, end = '<a id="lib-l0"></a>', '<a id="lib-l1"></a>'
    heading = "\n#### LIB-L0 — Research-package consolidation\n"
    if len(table) != 1 or any(text.count(item) != 1 for item in (start, end, heading)):
        raise ViewGenerationError("Roadmap has ambiguous LIB-L0 status owners")
    begin, finish = text.index(start), text.index(end)
    if not table[0].start() < begin < finish or not text.startswith(
        heading, begin + len(start)
    ):
        raise ViewGenerationError("Roadmap LIB-L0 anchor has the wrong heading")
    section = text[begin + len(start) : finish]
    statuses = re.findall(r"^\*\*Status:\*\* ([^.\r\n]+)\.", section, re.MULTILINE)
    if len(statuses) != 1 or statuses[0] != table[0][1] or not statuses[0].strip():
        raise ViewGenerationError("Roadmap LIB-L0 status owners disagree")
    return statuses[0]


def _validator_schema(source: bytes) -> str:
    try:
        tree = ast.parse(source.decode("utf-8"))
    except SyntaxError as error:
        raise ViewGenerationError("validator source is not valid Python") from error
    assignments, bindings = [], 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == VALIDATOR_SCHEMA_OWNER:
            bindings += isinstance(node.ctx, (ast.Store, ast.Del))
        if isinstance(node, (ast.ExceptHandler, ast.MatchAs, ast.MatchStar)):
            bindings += node.name == VALIDATOR_SCHEMA_OWNER
        if isinstance(node, ast.MatchMapping):
            bindings += node.rest == VALIDATOR_SCHEMA_OWNER
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            bindings += sum(
                (item.asname or item.name.rsplit(".", 1)[-1]) == VALIDATOR_SCHEMA_OWNER
                for item in node.names
            )
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bindings += node.name == VALIDATOR_SCHEMA_OWNER
    for node in tree.body:
        if (
            type(node) is ast.Assign
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == VALIDATOR_SCHEMA_OWNER
        ):
            assignments.append(node)
    if len(assignments) != 1 or bindings != 1:
        raise ViewGenerationError("validator schema owner is not unique")
    value = assignments[0].value
    if (
        not isinstance(value, ast.Constant)
        or type(value.value) is not str
        or not value.value
    ):
        raise ViewGenerationError("validator schema owner is not a literal string")
    return value.value


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ViewGenerationError(f"manifest contains duplicate key: {key}")
        value[key] = item
    return value


def _manifest_schema(source: bytes, relative: str) -> str:
    def reject_constant(value: str) -> None:
        raise ViewGenerationError(f"manifest contains nonfinite constant: {value}")

    try:
        value = json.loads(
            source.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=reject_constant,
        )
    except json.JSONDecodeError as error:
        raise ViewGenerationError(f"manifest is not strict JSON: {relative}") from error
    schema = value.get("schema_version") if type(value) is dict else None
    if schema != MANIFEST_SCHEMAS[relative]:
        raise ViewGenerationError(f"manifest has the wrong schema: {relative}")
    return schema


def render_view(source_root: Path) -> bytes:
    root = _source_root(source_root)
    try:
        executing_owner = Path(__file__).samefile(root / GENERATOR_RELATIVE_PATH)
    except OSError as error:
        raise ViewGenerationError("cannot join executing generator to owner") from error
    if not executing_owner:
        raise ViewGenerationError("executing generator differs from its owner path")
    sources = {}
    for path in OWNER_PATHS:
        limit = (
            DOCUMENT_LIMIT
            if path in POLICY_INPUTS or path == VALIDATOR_RELATIVE_PATH
            else MACHINE_INPUT_LIMIT
        )
        sources[path] = _read_owned(root, path, limit=limit)
    owner_stats = [(root / path).stat() for path in OWNER_PATHS]
    inodes = [(item.st_dev, item.st_ino) for item in owner_stats]
    if len(set(inodes)) != len(inodes):
        raise ViewGenerationError("two declared owners alias the same file")
    validator = _record(VALIDATOR_RELATIVE_PATH, sources[VALIDATOR_RELATIVE_PATH])
    validator["kind"] = "declared-diagnostic-schema"
    validator["schema_version"] = _validator_schema(sources[VALIDATOR_RELATIVE_PATH])
    machine_views = [validator]
    for path in MANIFEST_INPUTS:
        record = _record(path, sources[path])
        record["kind"] = "manifest-schema"
        record["schema_version"] = _manifest_schema(sources[path], path)
        machine_views.append(record)
    generator = _record(GENERATOR_RELATIVE_PATH, sources[GENERATOR_RELATIVE_PATH])
    generator["version"] = GENERATOR_VERSION
    document = {
        "claim_ceiling": CLAIM_CEILING,
        "generator": generator,
        "library_lane": {
            "id": "LIB-L0",
            "owners": [
                "docs/ROADMAP.md#3-two-independent-maturity-axes",
                "docs/ROADMAP.md#lib-l0",
            ],
            "status": _roadmap_status(sources["docs/ROADMAP.md"]),
        },
        "machine_views": machine_views,
        "policy_inputs": [_record(path, sources[path]) for path in POLICY_INPUTS],
        "schema_version": VIEW_SCHEMA_VERSION,
        "view_role": "generated-read-only-non-authoritative",
    }
    rendered = (
        json.dumps(
            document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
        + b"\n"
    )
    if len(rendered) > VIEW_LIMIT:
        raise ViewGenerationError("generated view exceeds its byte limit")
    return rendered


def check_committed_view(source_root: Path) -> None:
    root = _source_root(source_root)
    expected = render_view(root)
    actual = _read_owned(root, VIEW_RELATIVE_PATH, limit=VIEW_LIMIT)
    view_stat = (root / VIEW_RELATIVE_PATH).stat()
    if any(os.path.samestat(view_stat, (root / path).stat()) for path in OWNER_PATHS):
        raise ViewGenerationError("generated view aliases an input owner")
    if actual != expected:
        raise ViewGenerationError("committed LIB-L0 generated view is stale")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        if arguments.check:
            check_committed_view(arguments.source_root)
        else:
            sys.stdout.buffer.write(render_view(arguments.source_root))
    except ViewGenerationError as error:
        print(f"LIB-L0 generated view error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
