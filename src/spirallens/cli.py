"""Command-line entry points for the auditable SpiralLens v0.1 pipeline."""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Sequence

from spirallens import __version__


def _write_json_atomic(
    path: Path,
    payload: dict[str, Any],
    *,
    overwrite: bool,
) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"refusing to overwrite {path}; pass --overwrite explicitly"
        )
    encoded = json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    )
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _print_json(payload: dict[str, Any]) -> None:
    print(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
    )


def _calibration_payload(report: Any, *, samples: int) -> dict[str, Any]:
    checks = [
        {
            "name": check.name,
            "category": check.category,
            "observed": check.observed,
            "expected": check.expected,
            "tolerance": check.tolerance,
            "absolute_error": check.absolute_error,
            "passed": check.passed,
            "details": dict(check.details),
        }
        for check in report.checks
    ]
    return {
        "schema_version": "spirallens.calibration-report.v0.1",
        "suite_name": report.suite_name,
        "samples": samples,
        "status": "passed" if report.passed else "failed",
        "summary": {
            "checks": len(checks),
            "passed": sum(check["passed"] for check in checks),
            "failed": len(report.failed),
        },
        "checks": checks,
    }


def _run_calibrate(args: argparse.Namespace) -> int:
    from spirallens.calibration import run_analytic_calibration

    report = run_analytic_calibration(samples=args.samples)
    payload = _calibration_payload(report, samples=args.samples)
    output = None
    if args.output is not None:
        output = args.output.resolve()
        _write_json_atomic(output, payload, overwrite=args.overwrite)
    _print_json(
        {
            "command": "calibrate",
            "status": payload["status"],
            **payload["summary"],
            "report": str(output) if output is not None else None,
        }
    )
    return 0 if report.passed else 1


def _automatic_device(torch: Any) -> str:
    if torch.cuda.is_available():
        return "cuda"
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return "mps"
    return "cpu"


def _run_atlas(args: argparse.Namespace) -> int:
    import torch

    from spirallens.adapters import PythiaAdapter
    from spirallens.atlas import SweepConfig, run_id_sweep

    if args.full_vocabulary and (
        args.subset is not None or args.max_tokens is not None
    ):
        raise ValueError(
            "--full-vocabulary cannot be combined with --subset or --max-tokens"
        )
    if (
        not args.full_vocabulary
        and args.subset is None
        and args.max_tokens is None
    ):
        raise ValueError(
            "choose --max-tokens/--subset for a bounded run, or explicitly pass "
            "--full-vocabulary"
        )

    device = _automatic_device(torch) if args.device == "auto" else args.device
    model_kwargs: dict[str, Any] = {}
    if args.dtype != "auto":
        model_kwargs["torch_dtype"] = {
            "float32": torch.float32,
            "float16": torch.float16,
            "bfloat16": torch.bfloat16,
        }[args.dtype]

    adapter = PythiaAdapter.from_pretrained(
        args.model,
        revision=args.revision,
        device=device,
        local_files_only=args.local_files_only,
        **model_kwargs,
    )
    manifest = run_id_sweep(
        adapter,
        SweepConfig(
            output_dir=args.output,
            context_ids=tuple(args.context_ids),
            position=args.position,
            batch_size=args.batch_size,
            subset=None if args.subset is None else tuple(args.subset),
            max_tokens=args.max_tokens,
            attention_mask=(
                None
                if args.attention_mask is None
                else tuple(args.attention_mask)
            ),
            resume=args.resume,
        ),
    )
    _print_json(
        {
            "command": "atlas",
            "status": manifest["status"],
            "run_id": manifest["run_id"],
            "model": manifest["model"]["model_id"],
            "device": device,
            "rows": manifest["progress"],
            "manifest": str((args.output / "manifest.json").resolve()),
        }
    )
    return 0


def _run_candidates(args: argparse.Namespace) -> int:
    from spirallens.metrics import (
        CandidateSearchConfig,
        extract_candidates_from_manifest,
        load_candidate_config_from_protocol,
    )

    if args.output.exists() and not args.overwrite:
        raise FileExistsError(
            f"refusing to overwrite {args.output.resolve()}; "
            "pass --overwrite explicitly"
        )

    protocol_binding: dict[str, Any]
    if args.protocol is not None:
        import yaml

        protocol_path = args.protocol.resolve()
        protocol_bytes = protocol_path.read_bytes()
        protocol_document = yaml.safe_load(protocol_bytes)
        if not isinstance(protocol_document, dict):
            raise ValueError("protocol must contain a YAML mapping")
        declared_id = protocol_document.get("protocol_id")
        declared_status = protocol_document.get("status")
        declared_ceiling = protocol_document.get("claim_ceiling")
        if not isinstance(declared_id, str) or not declared_id:
            raise ValueError("protocol.protocol_id must be a non-empty string")
        if not isinstance(declared_status, str) or not declared_status:
            raise ValueError("protocol.status must be a non-empty string")
        if (
            isinstance(declared_ceiling, bool)
            or not isinstance(declared_ceiling, int)
            or not 1 <= declared_ceiling <= 3
        ):
            raise ValueError("protocol.claim_ceiling must be an integer in [1, 3]")
        if args.protocol_id is not None and args.protocol_id != declared_id:
            raise ValueError(
                f"--protocol-id {args.protocol_id!r} does not match "
                f"protocol declaration {declared_id!r}"
            )
        protocol_id = declared_id
        protocol_claim_ceiling = declared_ceiling
        config = load_candidate_config_from_protocol(protocol_path)
        if protocol_path.read_bytes() != protocol_bytes:
            raise RuntimeError("protocol changed while it was being bound")
        protocol_binding = {
            "declared_id": declared_id,
            "declared_status": declared_status,
            "claim_ceiling": declared_ceiling,
            "path": str(protocol_path),
            "sha256": hashlib.sha256(protocol_bytes).hexdigest(),
        }
    else:
        protocol_id = args.protocol_id or "ad-hoc-v0.1"
        protocol_claim_ceiling = 1
        config = CandidateSearchConfig()
        protocol_binding = {
            "declared_id": protocol_id,
            "declared_status": "exploratory_ad_hoc",
            "claim_ceiling": 1,
            "path": None,
            "sha256": None,
        }
    overrides: dict[str, Any] = {}
    for name in (
        "cosine_min",
        "relative_norm_gap_max",
        "drift_relative_divergence_min",
        "drift_absolute_divergence_min",
        "min_state_norm",
        "min_drift_norm",
        "block_size",
        "max_pairwise_rows",
    ):
        value = getattr(args, name)
        if value is not None:
            overrides[name] = value
    if args.layers is not None:
        overrides["layer_indices"] = tuple(args.layers)
    if overrides:
        config = replace(config, **overrides)
    protocol_binding["candidate_search_overrides"] = {
        key: list(value) if isinstance(value, tuple) else value
        for key, value in overrides.items()
    }
    protocol_binding["execution_status"] = (
        "exploratory_override"
        if overrides
        else protocol_binding["declared_status"]
    )
    protocol_binding["deviates_from_declared_search"] = bool(overrides)

    summary = extract_candidates_from_manifest(
        args.manifest,
        args.output,
        config=config,
        protocol_id=protocol_id,
        verify_checksums=not args.skip_checksums,
        overwrite=args.overwrite,
        protocol_claim_ceiling=protocol_claim_ceiling,
        protocol_binding=protocol_binding,
    )
    _print_json(
        {
            "command": "candidates",
            "status": "complete",
            "candidate_count": summary.candidate_count,
            "ledger": str(summary.output_path.resolve()),
            "protocol_id": protocol_id,
            "execution_status": protocol_binding["execution_status"],
        }
    )
    return 0


def _add_calibrate_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "calibrate",
        help="run model-free winding and holonomy phantoms",
    )
    parser.add_argument("--samples", type=int, default=512)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace an existing report path",
    )
    parser.set_defaults(handler=_run_calibrate)


def _add_atlas_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "atlas",
        help="stream a fixed-context Pythia token-ID activation atlas",
    )
    parser.add_argument(
        "--model",
        default="EleutherAI/pythia-70m",
        help="Hugging Face model ID",
    )
    parser.add_argument("--revision")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--context-ids",
        type=int,
        nargs="+",
        required=True,
        metavar="ID",
        help="fixed token IDs; the ID at --position is replaced during the sweep",
    )
    parser.add_argument("--position", type=int, required=True)
    parser.add_argument("--attention-mask", type=int, nargs="+", metavar="BIT")
    parser.add_argument("--subset", type=int, nargs="+", metavar="ID")
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument(
        "--full-vocabulary",
        action="store_true",
        help="explicitly authorize all model token IDs",
    )
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--device", default="auto")
    parser.add_argument(
        "--dtype",
        choices=("auto", "float32", "float16", "bfloat16"),
        default="auto",
    )
    parser.add_argument(
        "--local-files-only",
        action="store_true",
        help="fail instead of downloading uncached model files",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="resume a matching interrupted atlas",
    )
    parser.set_defaults(handler=_run_atlas)


def _add_candidates_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "candidates",
        help="emit a structural, semantics-free candidate ledger",
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--protocol", type=Path)
    parser.add_argument(
        "--protocol-id",
        help="must match protocol_id when --protocol is supplied",
    )
    parser.add_argument("--layers", type=int, nargs="+", metavar="LAYER")
    parser.add_argument("--cosine-min", type=float)
    parser.add_argument("--relative-norm-gap-max", type=float)
    parser.add_argument("--drift-relative-divergence-min", type=float)
    parser.add_argument("--drift-absolute-divergence-min", type=float)
    parser.add_argument("--min-state-norm", type=float)
    parser.add_argument("--min-drift-norm", type=float)
    parser.add_argument("--block-size", type=int)
    parser.add_argument(
        "--max-pairwise-rows",
        type=int,
        help="fail loudly above this exact pairwise-search size",
    )
    parser.add_argument(
        "--skip-checksums",
        action="store_true",
        help="skip whole-file hashes (schema and batch journal remain validated)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace an existing ledger path",
    )
    parser.set_defaults(handler=_run_candidates)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spirallens",
        description=(
            "Auditable calibration, Pythia activation-atlas, and structural "
            "candidate instrumentation."
        ),
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--traceback",
        action="store_true",
        help="show a Python traceback when a command fails",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_calibrate_parser(subparsers)
    _add_atlas_parser(subparsers)
    _add_candidates_parser(subparsers)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
    except Exception as exc:
        if args.traceback:
            raise
        print(f"spirallens: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
