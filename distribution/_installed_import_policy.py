"""Private immutable metadata for the installed-import build policy."""

SCHEMA = "spirallens.installed-import-conformance.v0.1"
SCOPE = (
    "fresh non-editable SpiralLens wheel module-import outcomes with "
    "host-projected declared base dependencies, blocked optional-import "
    "prefixes, and a bounded denied-audit-event policy"
)
CLAIM = (
    "classification grants no export-symbol importability, behavior, operation "
    "safety, side-effect freedom, stability, compatibility, dependency closure, "
    "portability, public API, authority, scientific claim, or library maturity"
)
DEPENDENCIES = (
    ("numpy", "numpy", "numpy>=1.26"),
    ("PyYAML", "yaml", "PyYAML>=6.0"),
    ("scipy", "scipy", "scipy>=1.11"),
)
PROJECT_DEPENDENCIES = tuple(
    sorted((values[2] for values in DEPENDENCIES), key=str.casefold)
)
BLOCKED = (
    "cryptography",
    "faiss",
    "huggingface_hub",
    "safetensors",
    "torch",
    "transformers",
)
OUTCOMES = ("base_import_success", "models_extra_missing_torch")
MISSING_TORCH = (
    "spirallens.adapters",
    "spirallens.adapters.pythia",
    "spirallens.atlas.engineering_run",
)
DENIED_AUDIT_EVENTS = tuple(
    (
        "builtins/open-write http.client.connect os.chdir os.chmod os.chown "
        "os.exec os.fork os.forkpty os.kill os.link os.mkdir os.remove os.rename "
        "os.rmdir os.posix_spawn os.symlink os.system os.truncate os.utime "
        "shutil.copyfile smtplib.connect socket.__new__ socket.bind "
        "socket.connect socket.getaddrinfo subprocess.Popen urllib.Request"
    ).split()
)


def dependency_records() -> list[dict[str, str]]:
    keys = ("distribution", "import_name", "requirement")
    return [dict(zip(keys, values, strict=True)) for values in DEPENDENCIES]


def worker_policy_projection() -> dict[str, object]:
    return {
        "base_dependencies": dependency_records(),
        "blocked_optional_prefixes": list(BLOCKED),
        "denied_audit_events": list(DENIED_AUDIT_EVENTS),
        "models_extra_missing_torch": list(MISSING_TORCH),
        "schema_version": SCHEMA,
    }
