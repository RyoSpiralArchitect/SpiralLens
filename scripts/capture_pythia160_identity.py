#!/usr/bin/env -S python3 -I -S
"""Capture the fixed, metadata-only Pythia-160M identity inputs.

This source-only entry point is intentionally not registered as a package CLI.
It fetches only provider model metadata and ``config.json``; it never imports a
model framework, loads a tokenizer or model, consults a cache, or reads weights.
"""

# The isolated-runtime and OpenSSL-environment gates intentionally precede
# every import that can initialize TLS.
# ruff: noqa: E402

from __future__ import annotations

import sys

_ISOLATED_RUNTIME = bool(
    sys.flags.isolated
    and sys.flags.ignore_environment
    and sys.flags.no_user_site
    and sys.flags.no_site
    and sys.flags.safe_path
)
if __name__ == "__main__" and not _ISOLATED_RUNTIME:
    raise SystemExit("Pythia-160M identity capture requires isolated `python3 -I -S`")

# Python isolation does not suppress OpenSSL's own process environment.  On
# the supported interpreter ``os`` is frozen, so this check cannot be shadowed
# by the script directory and runs before importing ``ssl`` or ``urllib``.
import os

_FORBIDDEN_OPENSSL_ENVIRONMENT = frozenset(
    {
        "OPENSSL_CONF",
        "OPENSSL_CONF_INCLUDE",
        "OPENSSL_ENGINES",
        "OPENSSL_MODULES",
    }
)
if __name__ == "__main__" and any(
    value and name.upper() in _FORBIDDEN_OPENSSL_ENVIRONMENT
    for name, value in os.environ.items()
):
    raise SystemExit(
        "Pythia-160M identity capture refuses ambient OpenSSL configuration"
    )

import ctypes
from dataclasses import dataclass, field
import errno
import hashlib
from importlib.machinery import ModuleSpec
from pathlib import Path
import ssl
import stat
import subprocess
from types import ModuleType
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, unquote, urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    ProxyHandler,
    Request,
    build_opener,
)


_MODEL_ID = "EleutherAI/pythia-160m"
_HF_HOST = "huggingface.co"
_REPOSITORY_URL = "https://github.com/RyoSpiralArchitect/SpiralLens.git"
_DEFAULT_INFO_URL = f"https://{_HF_HOST}/api/models/{_MODEL_ID}?blobs=true"
_MAX_MODEL_INFO_BYTES = 4 * 1024 * 1024
_MAX_CONFIG_BYTES = 1024 * 1024
_MAX_REDIRECTS = 1
_TIMEOUT_SECONDS = 30
_FIXED_CA_BUNDLE = Path("/private/etc/ssl/cert.pem")
_MAX_CA_BUNDLE_BYTES = 4 * 1024 * 1024

_REPOSITORY = Path(os.path.abspath(__file__)).parent.parent
_SCRIPT_REPOSITORY_PATH = "scripts/capture_pythia160_identity.py"
_KERNEL_REPOSITORY_PATH = "src/spirallens/access/_pythia160_identity_acquisition.py"
_OUTPUT_PARENT = _REPOSITORY / "experiments/pythia/model_identity"
_OUTPUT_DIRECTORY = _OUTPUT_PARENT / "pythia160-v0.1"
_STAGE_DIRECTORY = _OUTPUT_PARENT / ".pythia160-v0.1.stage"
_DEFAULT_MODEL_INFO_OUTPUT = _OUTPUT_DIRECTORY / "provider-default-model-info.json"
_EXACT_MODEL_INFO_OUTPUT = _OUTPUT_DIRECTORY / "provider-exact-model-info.json"
_CONFIG_OUTPUT = _OUTPUT_DIRECTORY / "config.json"
_RECEIPT_OUTPUT = _OUTPUT_DIRECTORY / "identity-receipt.json"
_OUTPUT_NAMES = (
    _DEFAULT_MODEL_INFO_OUTPUT.name,
    _EXACT_MODEL_INFO_OUTPUT.name,
    _CONFIG_OUTPUT.name,
    _RECEIPT_OUTPUT.name,
)

_FAILURE_PHASES = frozenset(
    {
        "preflight",
        "acquisition_reservation",
        "provider_acquisition",
        "stage_publication",
        "post_publication_verification",
    }
)

_FORBIDDEN_ENVIRONMENT = frozenset(
    {
        "ALL_PROXY",
        "GIT_ASKPASS",
        "HF_API_TOKEN",
        "HF_AUTH_TOKEN",
        "HF_HUB_TOKEN",
        "HF_TOKEN",
        "HF_TOKEN_PATH",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "HUGGINGFACEHUB_API_TOKEN",
        "HUGGINGFACE_HUB_TOKEN",
        "HUGGING_FACE_HUB_TOKEN",
        "NETRC",
        "NO_PROXY",
        *_FORBIDDEN_OPENSSL_ENVIRONMENT,
        "REQUESTS_CA_BUNDLE",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "SSLKEYLOGFILE",
    }
)

_FORBIDDEN_LOCAL_GIT_PREFIXES = (
    "credential.",
    "filter.",
    "http.",
    "https.",
    "include.",
    "includeif.",
    "url.",
)


class _CaptureError(RuntimeError):
    """Raised when the fixed metadata-only acquisition cannot stay exact."""

    def __init__(
        self,
        message: str,
        *,
        phase: str = "preflight",
        stage_retained: bool | None = False,
        publication_visible: bool | None = False,
    ) -> None:
        if (
            type(message) is not str
            or not message
            or phase not in _FAILURE_PHASES
            or type(stage_retained) not in {bool, type(None)}
            or type(publication_visible) not in {bool, type(None)}
        ):
            raise TypeError("identity capture failure facts are invalid")
        super().__init__(message)
        self.phase = phase
        self.stage_retained = stage_retained
        self.publication_visible = publication_visible
        self.cleanup_authorized = False
        self.resume_authorized = False
        self.retry_authorized = False


def _publication_outcome() -> tuple[bool | None, bool | None]:
    def visible(path: Path) -> bool | None:
        try:
            path.lstat()
        except FileNotFoundError:
            return False
        except OSError:
            return None
        return True

    return visible(_STAGE_DIRECTORY), visible(_OUTPUT_DIRECTORY)


def _owned_publication_outcome(
    owned: "_OwnedOutputStage",
) -> tuple[bool | None, bool | None]:
    try:
        _require_live_directory_anchor(_OUTPUT_PARENT, owned.parent_fd)
        held = _stat_identity(os.fstat(owned.stage_fd))
        staged = _entry_metadata(owned.parent_fd, _STAGE_DIRECTORY.name)
        published = _entry_metadata(owned.parent_fd, _OUTPUT_DIRECTORY.name)
    except (OSError, _CaptureError):
        return None, None
    staged_matches = staged is not None and _stat_identity(staged) == held
    published_matches = published is not None and _stat_identity(published) == held
    if staged_matches and published is None:
        return True, False
    if published_matches and staged is None:
        return False, True
    if staged is None and published is None:
        return False, False
    return None, None


def _capture_failure(
    *, phase: str, owned_stage: "_OwnedOutputStage | None" = None
) -> _CaptureError:
    if owned_stage is None:
        stage, published = _publication_outcome()
    else:
        stage, published = _owned_publication_outcome(owned_stage)
    return _CaptureError(
        f"Pythia-160M identity capture failed during {phase}",
        phase=phase,
        stage_retained=stage,
        publication_visible=published,
    )


def _refuse_ambient_network_authority() -> None:
    present = sorted(
        name
        for name, value in os.environ.items()
        if value and name.upper() in _FORBIDDEN_ENVIRONMENT
    )
    if present:
        raise _CaptureError(
            "Pythia-160M identity capture refuses credential, proxy, and "
            f"ambient TLS environment variables: {present}"
        )


def _safe_fixed_ca_metadata(metadata: os.stat_result) -> bool:
    return bool(
        stat.S_ISREG(metadata.st_mode)
        and metadata.st_nlink == 1
        and metadata.st_uid == 0
        and stat.S_IMODE(metadata.st_mode) & 0o022 == 0
        and 0 < metadata.st_size <= _MAX_CA_BUNDLE_BYTES
    )


def _fixed_ca_metadata_fingerprint(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _read_fixed_ca_bundle() -> bytes:
    """Read the root-owned fixed CA bundle through no-symlink path anchors."""

    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise _CaptureError("fixed TLS CA bundle requires no-symlink open support")
    try:
        parent_fd = _open_absolute_directory(_FIXED_CA_BUNDLE.parent)
    except OSError as error:
        raise _CaptureError("fixed TLS CA bundle parent is unavailable") from error
    descriptor = -1
    try:
        _require_live_directory_anchor(_FIXED_CA_BUNDLE.parent, parent_fd)
        try:
            before = os.stat(
                _FIXED_CA_BUNDLE.name,
                dir_fd=parent_fd,
                follow_symlinks=False,
            )
        except OSError as error:
            raise _CaptureError("fixed TLS CA bundle is unavailable") from error
        if not _safe_fixed_ca_metadata(before):
            raise _CaptureError(
                "fixed TLS CA bundle is not one bounded root-owned ordinary file"
            )

        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        try:
            descriptor = os.open(
                _FIXED_CA_BUNDLE.name,
                flags,
                dir_fd=parent_fd,
            )
        except OSError as error:
            raise _CaptureError(
                "fixed TLS CA bundle cannot be opened safely"
            ) from error
        held_before = os.fstat(descriptor)
        if _fixed_ca_metadata_fingerprint(
            held_before
        ) != _fixed_ca_metadata_fingerprint(before) or not _safe_fixed_ca_metadata(
            held_before
        ):
            raise _CaptureError("fixed TLS CA bundle changed before its read")
        chunks: list[bytes] = []
        remaining = _MAX_CA_BUNDLE_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        source = b"".join(chunks)
        held_after = os.fstat(descriptor)
        try:
            after = os.stat(
                _FIXED_CA_BUNDLE.name,
                dir_fd=parent_fd,
                follow_symlinks=False,
            )
        except OSError as error:
            raise _CaptureError(
                "fixed TLS CA bundle disappeared after its read"
            ) from error
        _require_live_directory_anchor(_FIXED_CA_BUNDLE.parent, parent_fd)
        if (
            len(source) < 1
            or len(source) > _MAX_CA_BUNDLE_BYTES
            or len(source) != held_before.st_size
            or not _safe_fixed_ca_metadata(held_after)
            or _fixed_ca_metadata_fingerprint(held_after)
            != _fixed_ca_metadata_fingerprint(held_before)
            or not _safe_fixed_ca_metadata(after)
            or _fixed_ca_metadata_fingerprint(after)
            != _fixed_ca_metadata_fingerprint(held_after)
        ):
            raise _CaptureError("fixed TLS CA bundle changed during its bounded read")
        return source
    except OSError as error:
        raise _CaptureError("fixed TLS CA bundle read failed") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        os.close(parent_fd)


def _require_usable_tls_context(context: ssl.SSLContext) -> None:
    try:
        statistics = context.cert_store_stats()
    except (AttributeError, ssl.SSLError) as error:
        raise _CaptureError(
            "fixed TLS context cannot report its trust store"
        ) from error
    if (
        type(context) is not ssl.SSLContext
        or context.protocol != ssl.PROTOCOL_TLS_CLIENT
        or context.verify_mode != ssl.CERT_REQUIRED
        or context.check_hostname is not True
        or context.minimum_version < ssl.TLSVersion.TLSv1_2
        or type(statistics) is not dict
        or type(statistics.get("x509_ca")) is not int
        or statistics["x509_ca"] < 1
    ):
        raise _CaptureError("fixed TLS context is not a usable verified client context")


def _build_fixed_tls_context() -> ssl.SSLContext:
    """Build the sole HTTPS trust context from the fixed local CA bundle."""

    source = _read_fixed_ca_bundle()
    try:
        cadata = source.decode("ascii")
    except UnicodeDecodeError as error:
        raise _CaptureError("fixed TLS CA bundle is not ASCII PEM text") from error
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = True
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_verify_locations(cadata=cadata)
    except (OSError, ssl.SSLError, ValueError) as error:
        raise _CaptureError("fixed TLS CA bundle could not establish trust") from error
    _require_usable_tls_context(context)
    return context


def _require_isolated_runtime() -> None:
    if _ISOLATED_RUNTIME is not True:
        raise _CaptureError(
            "identity capture requires isolated `python3 -I -S` execution"
        )


def _git(*arguments: str, binary: bool = False) -> bytes | str:
    environment = {
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": "/usr/bin:/bin",
    }
    completed = subprocess.run(
        [
            "/usr/bin/git",
            "--no-replace-objects",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.untrackedCache=false",
            *arguments,
        ],
        cwd=_REPOSITORY,
        env=environment,
        check=False,
        capture_output=True,
        text=not binary,
    )
    if completed.returncode != 0:
        stderr = completed.stderr
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        raise _CaptureError(f"sanitized Git check failed: {stderr.strip()}")
    if binary:
        assert isinstance(completed.stdout, bytes)
        return completed.stdout
    assert isinstance(completed.stdout, str)
    return completed.stdout.rstrip("\n")


def _full_lower_hex(value: str, length: int, *, label: str) -> str:
    if (
        len(value) != length
        or value.lower() != value
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise _CaptureError(f"{label} must be exactly {length} lowercase hex digits")
    return value


def _read_head_blob(repository_path: str) -> tuple[str, bytes]:
    live_path = _REPOSITORY / repository_path
    metadata = live_path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise _CaptureError(f"{repository_path} must be one ordinary live file")

    index_flag = _git("ls-files", "-v", "--", repository_path)
    if index_flag != f"H {repository_path}":
        raise _CaptureError(
            f"{repository_path} has assume-unchanged or skip-worktree state"
        )
    attributes = _git(
        "check-attr",
        "filter",
        "working-tree-encoding",
        "--",
        repository_path,
    )
    assert isinstance(attributes, str)
    if any(not line.endswith(": unspecified") for line in attributes.splitlines()):
        raise _CaptureError(
            f"{repository_path} is subject to unreviewed Git transformations"
        )
    index_line = _git("ls-files", "-s", "--", repository_path)
    assert isinstance(index_line, str)
    fields = index_line.split()
    if (
        len(fields) != 4
        or fields[0] not in {"100644", "100755"}
        or fields[2] != "0"
        or fields[3] != repository_path
    ):
        raise _CaptureError(f"{repository_path} is not one stage-zero ordinary blob")
    blob_id = _full_lower_hex(fields[1], 40, label=f"{repository_path} blob")
    object_type = _git("cat-file", "-t", f"HEAD:{repository_path}")
    if object_type != "blob":
        raise _CaptureError(f"HEAD:{repository_path} is not a Git blob")
    committed = _git("cat-file", "blob", f"HEAD:{repository_path}", binary=True)
    assert isinstance(committed, bytes)
    live = live_path.read_bytes()
    if committed != live:
        raise _CaptureError(f"live {repository_path} differs from HEAD")
    header = f"blob {len(live)}\0".encode("ascii")
    if hashlib.sha1(header + live).hexdigest() != blob_id:  # noqa: S324
        raise _CaptureError(f"{repository_path} Git blob identity differs")
    return blob_id, live


def _verified_source(*, allow_owned_stage: bool = False) -> tuple[str, bytes, bytes]:
    top = _git("rev-parse", "--show-toplevel")
    if top != str(_REPOSITORY):
        raise _CaptureError("script is not running from its fixed repository")
    if _git("rev-parse", "--show-object-format") != "sha1":
        raise _CaptureError("identity capture requires the fixed SHA-1 Git format")
    local_config = _git("config", "--local", "--name-only", "--list")
    assert isinstance(local_config, str)
    if any(
        name.lower().startswith(_FORBIDDEN_LOCAL_GIT_PREFIXES)
        for name in local_config.splitlines()
    ):
        raise _CaptureError("identity capture rejects active Git routing or filters")
    head = _git("rev-parse", "--verify", "HEAD^{commit}")
    assert isinstance(head, str)
    head = _full_lower_hex(head, 40, label="repository HEAD")
    origin_main = _git("rev-parse", "--verify", "refs/remotes/origin/main^{commit}")
    if origin_main != head:
        raise _CaptureError(
            "identity capture requires HEAD equal to the local origin/main "
            "tracking candidate"
        )
    index_records = _git("ls-files", "-v", "-z", "--", ".")
    assert isinstance(index_records, str)
    if any(
        record and not record.startswith("H ") for record in index_records.split("\0")
    ):
        raise _CaptureError(
            "identity capture rejects assume-unchanged or skip-worktree state"
        )
    status = _git("status", "--porcelain=v1", "--untracked-files=all")
    assert isinstance(status, str)
    status_lines = status.splitlines()
    if allow_owned_stage:
        owned_prefix = "?? experiments/pythia/model_identity/.pythia160-v0.1.stage/"
        status_lines = [
            line for line in status_lines if not line.startswith(owned_prefix)
        ]
    if status_lines:
        raise _CaptureError("identity capture requires an exactly clean worktree")
    if _git("remote", "get-url", "origin") != _REPOSITORY_URL:
        raise _CaptureError("identity capture requires the fixed repository remote")
    _script_blob, script_source = _read_head_blob(_SCRIPT_REPOSITORY_PATH)
    _kernel_blob, kernel_source = _read_head_blob(_KERNEL_REPOSITORY_PATH)
    return head, kernel_source, script_source


def _allowed_config_urls(revision: str) -> frozenset[str]:
    return frozenset(
        {
            f"https://{_HF_HOST}/{_MODEL_ID}/resolve/{revision}/config.json",
            (
                f"https://{_HF_HOST}/api/resolve-cache/models/"
                f"{_MODEL_ID}/{revision}/config.json"
            ),
        }
    )


def _validate_https_url(url: str, allowed_urls: frozenset[str]) -> None:
    parsed = urlsplit(url)
    try:
        port = parsed.port
    except ValueError as error:
        raise _CaptureError("provider URL contains an invalid port") from error
    exact_url = url in allowed_urls
    cache_redirect = False
    malformed_percent_escape = any(
        character == "%"
        and (
            index + 2 >= len(parsed.query)
            or any(
                digit not in "0123456789abcdefABCDEF"
                for digit in parsed.query[index + 1 : index + 3]
            )
        )
        for index, character in enumerate(parsed.query)
    )
    if (
        not exact_url
        and parsed.query
        and len(parsed.query) <= 4096
        and not malformed_percent_escape
    ):
        cache_bases = {
            allowed
            for allowed in allowed_urls
            if "/api/resolve-cache/models/" in allowed
        }
        cache_redirect = any(
            urlsplit(allowed)._replace(query="").geturl()
            == parsed._replace(query="").geturl()
            for allowed in cache_bases
        )
        if cache_redirect:
            try:
                pairs = parse_qsl(
                    parsed.query,
                    keep_blank_values=True,
                    strict_parsing=True,
                    max_num_fields=16,
                )
            except ValueError as error:
                raise _CaptureError("provider cache query is invalid") from error
            cache_redirect = (
                bool(pairs)
                and len({key for key, _ in pairs}) == len(pairs)
                and all(
                    key
                    and len(key.encode("utf-8")) <= 512
                    and len(value.encode("utf-8")) <= 1024
                    for key, value in pairs
                )
            )
    if (
        parsed.scheme != "https"
        or parsed.hostname != _HF_HOST
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 443}
        or parsed.fragment
        or not (exact_url or cache_redirect)
        or unquote(parsed.path) != parsed.path
    ):
        raise _CaptureError("provider URL escaped the fixed HTTPS model route")


class _PinnedRedirectHandler(HTTPRedirectHandler):
    def __init__(self, allowed_urls: frozenset[str]) -> None:
        super().__init__()
        self._allowed_urls = allowed_urls
        self._redirects = 0

    def redirect_request(  # type: ignore[override]
        self,
        request: Request,
        file_pointer: object,
        code: int,
        message: str,
        headers: object,
        new_url: str,
    ) -> Request | None:
        del file_pointer
        self._redirects += 1
        if self._redirects > _MAX_REDIRECTS:
            raise _CaptureError("provider redirect count exceeds the fixed bound")
        _validate_https_url(new_url, self._allowed_urls)
        return super().redirect_request(request, None, code, message, headers, new_url)


def _fetch_bytes(
    url: str,
    *,
    allowed_urls: frozenset[str],
    maximum_bytes: int,
    tls_context: ssl.SSLContext,
) -> bytes:
    _validate_https_url(url, allowed_urls)
    _require_usable_tls_context(tls_context)
    opener = build_opener(
        ProxyHandler({}),
        HTTPSHandler(context=tls_context),
        _PinnedRedirectHandler(allowed_urls),
    )
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "User-Agent": "SpiralLens-pythia160-identity/0.1",
        },
        method="GET",
    )
    try:
        with opener.open(request, timeout=_TIMEOUT_SECONDS) as response:
            final_url = response.geturl()
            _validate_https_url(final_url, allowed_urls)
            if response.status != 200:
                raise _CaptureError(f"provider returned HTTP {response.status}")
            encoding = response.headers.get("Content-Encoding", "identity")
            if encoding.lower() != "identity":
                raise _CaptureError("compressed provider responses are forbidden")
            declared = response.headers.get("Content-Length")
            if declared is not None:
                try:
                    declared_bytes = int(declared, 10)
                except ValueError as error:
                    raise _CaptureError("provider Content-Length is invalid") from error
                if declared_bytes < 0 or declared_bytes > maximum_bytes:
                    raise _CaptureError("provider response exceeds the byte bound")
            source = response.read(maximum_bytes + 1)
    except _CaptureError:
        raise
    except (HTTPError, URLError, OSError) as error:
        raise _CaptureError("bounded provider request failed") from error
    if len(source) > maximum_bytes:
        raise _CaptureError("provider response exceeds the byte bound")
    if declared is not None and len(source) != declared_bytes:
        raise _CaptureError("provider response length differs from its declaration")
    return source


def _directory_flags() -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    return flags


def _stat_identity(metadata: os.stat_result) -> tuple[int, int, int]:
    return metadata.st_dev, metadata.st_ino, stat.S_IFMT(metadata.st_mode)


def _open_absolute_directory(path: Path) -> int:
    if not path.is_absolute():
        raise _CaptureError("directory anchor must be absolute")
    descriptor = os.open("/", _directory_flags())
    try:
        for component in path.parts[1:]:
            child = os.open(component, _directory_flags(), dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _require_live_directory_anchor(path: Path, descriptor: int) -> None:
    live = _open_absolute_directory(path)
    try:
        if _stat_identity(os.fstat(live)) != _stat_identity(os.fstat(descriptor)):
            raise _CaptureError("live output ancestor differs from its held directory")
    finally:
        os.close(live)


def _entry_metadata(parent_fd: int, name: str) -> os.stat_result | None:
    try:
        return os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None


def _require_output_namespace_absent() -> None:
    pythia = _REPOSITORY / "experiments/pythia"
    pythia_fd = _open_absolute_directory(pythia)
    try:
        try:
            parent_fd = os.open(
                _OUTPUT_PARENT.name, _directory_flags(), dir_fd=pythia_fd
            )
        except FileNotFoundError:
            return
        try:
            metadata = os.fstat(parent_fd)
            if stat.S_IMODE(metadata.st_mode) != 0o700:
                raise _CaptureError("fixed output parent mode differs")
            _require_live_directory_anchor(_OUTPUT_PARENT, parent_fd)
            entries = set(os.listdir(parent_fd))
            if entries:
                raise _CaptureError("fixed identity output parent is not empty")
        finally:
            os.close(parent_fd)
    finally:
        os.close(pythia_fd)


@dataclass(slots=True)
class _OwnedOutputStage:
    parent_fd: int
    stage_fd: int
    file_fds: dict[str, int] = field(default_factory=dict)

    def close(self) -> None:
        for descriptor in self.file_fds.values():
            try:
                os.close(descriptor)
            except OSError:
                pass
        self.file_fds.clear()
        for name in ("stage_fd", "parent_fd"):
            descriptor = getattr(self, name)
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
                setattr(self, name, -1)


def _reserve_output_directory() -> _OwnedOutputStage:
    pythia = _REPOSITORY / "experiments/pythia"
    pythia_fd = _open_absolute_directory(pythia)
    parent_fd = -1
    stage_fd = -1
    try:
        try:
            os.mkdir(_OUTPUT_PARENT.name, 0o700, dir_fd=pythia_fd)
        except FileExistsError:
            pass
        else:
            os.fsync(pythia_fd)
        parent_fd = os.open(_OUTPUT_PARENT.name, _directory_flags(), dir_fd=pythia_fd)
        metadata = os.fstat(parent_fd)
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o700
        ):
            raise _CaptureError("fixed output parent is unsafe")
        _require_live_directory_anchor(_OUTPUT_PARENT, parent_fd)
        if os.listdir(parent_fd):
            raise _CaptureError("fixed output parent must be empty")
        os.mkdir(_STAGE_DIRECTORY.name, 0o700, dir_fd=parent_fd)
        os.fsync(parent_fd)
        stage_fd = os.open(_STAGE_DIRECTORY.name, _directory_flags(), dir_fd=parent_fd)
        stage_metadata = os.fstat(stage_fd)
        live_stage = _entry_metadata(parent_fd, _STAGE_DIRECTORY.name)
        if (
            live_stage is None
            or _stat_identity(live_stage) != _stat_identity(stage_metadata)
            or stat.S_IMODE(stage_metadata.st_mode) != 0o700
        ):
            raise _CaptureError("owned identity stage differs after creation")
        owned = _OwnedOutputStage(parent_fd=parent_fd, stage_fd=stage_fd)
        parent_fd = -1
        stage_fd = -1
        return owned
    finally:
        os.close(pythia_fd)
        if stage_fd >= 0:
            os.close(stage_fd)
        if parent_fd >= 0:
            os.close(parent_fd)


def _read_held_file(descriptor: int) -> bytes:
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    while True:
        chunk = os.read(descriptor, 1024 * 1024)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _write_exclusive(stage: _OwnedOutputStage, name: str, source: bytes) -> None:
    if type(source) is not bytes:
        raise _CaptureError("identity output must be exact bytes")
    if name not in _OUTPUT_NAMES or name in stage.file_fds:
        raise _CaptureError("identity output member name differs")
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    descriptor = os.open(name, flags, 0o600, dir_fd=stage.stage_fd)
    try:
        view = memoryview(source)
        while view:
            written = os.write(descriptor, view)
            if written < 1:
                raise _CaptureError("identity output write made no progress")
            view = view[written:]
        os.fsync(descriptor)
        metadata = os.fstat(descriptor)
        live = _entry_metadata(stage.stage_fd, name)
        if (
            live is None
            or _stat_identity(live) != _stat_identity(metadata)
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or _read_held_file(descriptor) != source
        ):
            raise _CaptureError("identity output re-read differs after durable write")
        stage.file_fds[name] = descriptor
        descriptor = -1
        os.fsync(stage.stage_fd)
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _reverify_owned_stage(
    stage: _OwnedOutputStage,
    expected: dict[str, bytes],
    *,
    published: bool,
) -> None:
    _require_live_directory_anchor(_OUTPUT_PARENT, stage.parent_fd)
    live_name = _OUTPUT_DIRECTORY.name if published else _STAGE_DIRECTORY.name
    absent_name = _STAGE_DIRECTORY.name if published else _OUTPUT_DIRECTORY.name
    held_stage = os.fstat(stage.stage_fd)
    live_stage = _entry_metadata(stage.parent_fd, live_name)
    if (
        live_stage is None
        or _stat_identity(live_stage) != _stat_identity(held_stage)
        or not stat.S_ISDIR(held_stage.st_mode)
        or stat.S_IMODE(held_stage.st_mode) != 0o700
        or _entry_metadata(stage.parent_fd, absent_name) is not None
        or set(os.listdir(stage.parent_fd)) != {live_name}
        or set(os.listdir(stage.stage_fd)) != set(_OUTPUT_NAMES)
        or set(stage.file_fds) != set(_OUTPUT_NAMES)
        or set(expected) != set(_OUTPUT_NAMES)
    ):
        raise _CaptureError("owned identity stage namespace differs")
    for name in _OUTPUT_NAMES:
        descriptor = stage.file_fds[name]
        held = os.fstat(descriptor)
        live = _entry_metadata(stage.stage_fd, name)
        if (
            live is None
            or _stat_identity(live) != _stat_identity(held)
            or not stat.S_ISREG(held.st_mode)
            or held.st_nlink != 1
            or stat.S_IMODE(held.st_mode) != 0o600
            or held.st_size != len(expected[name])
            or _read_held_file(descriptor) != expected[name]
        ):
            raise _CaptureError(f"owned identity member {name!r} differs")
    _require_live_directory_anchor(_OUTPUT_PARENT, stage.parent_fd)


def _native_publish_stage_no_replace(
    stage: _OwnedOutputStage, expected: dict[str, bytes]
) -> None:
    _reverify_owned_stage(stage, expected, published=False)
    libc = ctypes.CDLL(None, use_errno=True)
    source = os.fsencode(_STAGE_DIRECTORY.name)
    destination = os.fsencode(_OUTPUT_DIRECTORY.name)
    if sys.platform == "darwin":
        try:
            function = libc.renameatx_np
        except AttributeError as error:
            raise _CaptureError("Darwin exclusive rename is unavailable") from error
        flag = 0x00000004  # RENAME_EXCL
    elif sys.platform.startswith("linux"):
        try:
            function = libc.renameat2
        except AttributeError as error:
            raise _CaptureError("Linux exclusive rename is unavailable") from error
        flag = 0x00000001  # RENAME_NOREPLACE
    else:
        raise _CaptureError("no supported exclusive rename for this platform")
    function.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    function.restype = ctypes.c_int
    ctypes.set_errno(0)
    if (
        function(
            stage.parent_fd,
            source,
            stage.parent_fd,
            destination,
            flag,
        )
        != 0
    ):
        observed_errno = ctypes.get_errno() or errno.EIO
        raise _CaptureError(
            f"exclusive identity publication failed with errno {observed_errno}"
        )
    os.fsync(stage.parent_fd)
    _reverify_owned_stage(stage, expected, published=True)


def _kernel(source: bytes) -> ModuleType:
    module_name = "_spirallens_pythia160_identity_acquisition_authenticated"
    if module_name in sys.modules:
        raise _CaptureError("authenticated identity kernel is already loaded")
    module = ModuleType(module_name)
    module.__file__ = str(_REPOSITORY / _KERNEL_REPOSITORY_PATH)
    module.__package__ = ""
    module.__spec__ = ModuleSpec(module_name, loader=None, origin=module.__file__)
    sys.modules[module_name] = module
    try:
        code = compile(source, module.__file__, "exec", dont_inherit=True)
        exec(code, module.__dict__)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    if module.__dict__.get("__all__") != ():
        sys.modules.pop(module_name, None)
        raise _CaptureError("authenticated identity kernel exported public symbols")
    return module


def _provider_revision(kernel: object, source: bytes) -> str:
    """Use the private pure kernel for the pre-network revision join."""

    revision = kernel._resolved_revision_from_model_info(source)
    return _full_lower_hex(revision, 40, label="provider revision")


def _main() -> int:
    preflight_failure: _CaptureError | None = None
    try:
        _require_isolated_runtime()
        if len(sys.argv) != 1:
            raise _CaptureError("identity capture accepts no arguments")
        _refuse_ambient_network_authority()
        source_commit, kernel_source, script_source = _verified_source()
        _require_output_namespace_absent()
        kernel = _kernel(kernel_source)
        tls_context = _build_fixed_tls_context()
    except BaseException:
        preflight_failure = _capture_failure(phase="preflight")
    if preflight_failure is not None:
        raise preflight_failure from None

    owned_stage: _OwnedOutputStage | None = None
    reservation_failure: _CaptureError | None = None
    try:
        # This durable empty reservation precedes the first provider request.
        # If anything later fails, the retained stage makes the one-shot
        # operation mechanically non-retryable without an unreviewed cleanup.
        owned_stage = _reserve_output_directory()
    except BaseException:
        reservation_failure = _capture_failure(phase="acquisition_reservation")
    if reservation_failure is not None:
        raise reservation_failure from None

    provider_failure: _CaptureError | None = None
    try:
        default_source = _fetch_bytes(
            _DEFAULT_INFO_URL,
            allowed_urls=frozenset({_DEFAULT_INFO_URL}),
            maximum_bytes=_MAX_MODEL_INFO_BYTES,
            tls_context=tls_context,
        )
        revision = _provider_revision(kernel, default_source)
        exact_info_path = f"/api/models/{_MODEL_ID}/revision/{revision}"
        exact_info_url = f"https://{_HF_HOST}{exact_info_path}?blobs=true"
        exact_source = _fetch_bytes(
            exact_info_url,
            allowed_urls=frozenset({exact_info_url}),
            maximum_bytes=_MAX_MODEL_INFO_BYTES,
            tls_context=tls_context,
        )
        config_path = f"/{_MODEL_ID}/resolve/{revision}/config.json"
        config_source = _fetch_bytes(
            f"https://{_HF_HOST}{config_path}",
            allowed_urls=_allowed_config_urls(revision),
            maximum_bytes=_MAX_CONFIG_BYTES,
            tls_context=tls_context,
        )
        source_binding = {
            "repository": _REPOSITORY_URL,
            "source_commit": source_commit,
            "members": [
                {
                    "repository_path": _SCRIPT_REPOSITORY_PATH,
                    "byte_count": len(script_source),
                    "sha256": hashlib.sha256(script_source).hexdigest(),
                },
                {
                    "repository_path": _KERNEL_REPOSITORY_PATH,
                    "byte_count": len(kernel_source),
                    "sha256": hashlib.sha256(kernel_source).hexdigest(),
                },
            ],
        }
        receipt = kernel._build_pythia160_identity_acquisition_receipt(
            default_model_info_source=default_source,
            exact_model_info_source=exact_source,
            config_source=config_source,
            source_binding=source_binding,
        )
        receipt_source = receipt.canonical_bytes
        if type(receipt_source) is not bytes:
            raise _CaptureError(
                "identity receipt did not provide exact canonical bytes"
            )
        post_commit, post_kernel, post_script = _verified_source()
        if (
            post_commit != source_commit
            or post_kernel != kernel_source
            or post_script != script_source
        ):
            raise _CaptureError("source-bound candidate changed during acquisition")
    except BaseException:
        provider_failure = _capture_failure(
            phase="provider_acquisition",
            owned_stage=owned_stage,
        )
        assert owned_stage is not None
        owned_stage.close()
    if provider_failure is not None:
        raise provider_failure from None

    outputs = {
        _DEFAULT_MODEL_INFO_OUTPUT.name: default_source,
        _EXACT_MODEL_INFO_OUTPUT.name: exact_source,
        _CONFIG_OUTPUT.name: config_source,
        _RECEIPT_OUTPUT.name: receipt_source,
    }
    stage_failure: _CaptureError | None = None
    try:
        assert owned_stage is not None
        for name in _OUTPUT_NAMES:
            _write_exclusive(owned_stage, name, outputs[name])
        _reverify_owned_stage(owned_stage, outputs, published=False)
        staged_commit, staged_kernel, staged_script = _verified_source(
            allow_owned_stage=True
        )
        if (
            staged_commit != source_commit
            or staged_kernel != kernel_source
            or staged_script != script_source
        ):
            raise _CaptureError("source-bound candidate changed before publication")
        _reverify_owned_stage(owned_stage, outputs, published=False)
        _native_publish_stage_no_replace(owned_stage, outputs)
    except BaseException:
        stage_failure = _capture_failure(
            phase="stage_publication",
            owned_stage=owned_stage,
        )
        if owned_stage is not None:
            owned_stage.close()
    if stage_failure is not None:
        raise stage_failure from None

    post_publication_failure: _CaptureError | None = None
    try:
        assert owned_stage is not None
        _reverify_owned_stage(owned_stage, outputs, published=True)
    except BaseException:
        post_publication_failure = _capture_failure(
            phase="post_publication_verification",
            owned_stage=owned_stage,
        )
        owned_stage.close()
    if post_publication_failure is not None:
        raise post_publication_failure from None
    owned_stage.close()
    return 0


def main() -> int:
    """Run the fixed acquisition with a closed, non-retryable failure surface."""

    return _main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except _CaptureError as error:
        print(
            "Pythia-160M identity capture blocked: "
            f"phase={error.phase}; "
            f"stage_retained={error.stage_retained}; "
            f"publication_visible={error.publication_visible}; "
            "cleanup_authorized=false; resume_authorized=false; "
            "retry_authorized=false",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
