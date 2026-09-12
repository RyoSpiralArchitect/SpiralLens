"""Local, deterministic development controls; no campaign or remote launcher."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import scipy

import prototype_p4_bounded_observation_v0_1 as kernel
import prototype_p4_center_resolution_v0_1 as predecessor
from spirallens.core.canonical import canonical_json_bytes

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "docs/P4_BOUNDED_OBSERVATION_PLAN.md"
PROTOCOL_SHA256 = "3a0d0a3dd1b9d7b7a74da21e2ac5e1ffcc9b294c27af97f223b3347412e1bbdb"
FIXTURES = (
    "double",
    "pair-d080",
    "pair-d160",
    "reverse-d160",
    "zero",
    "constant",
    "linear",
    "dipole",
    "cubic",
)
MODES = ("none", "constant", "linear", "shared-constant")
EPSILONS = (0.0, 1e-7, 1e-5, 1e-3)
PLACEMENTS = (0.5, 1.0)
WITNESS_EPSILON = 1e-6
SEED, TAG = 7, 0x5034424F


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_lock():
    paths = sorted((ROOT / "src").rglob("*.py"))
    paths += sorted((ROOT / "scripts").glob("*p4*.py"))
    paths += [ROOT / PROTOCOL, ROOT / "pyproject.toml"]
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}


def disk_draw(count, role):
    rng = np.random.default_rng(np.random.SeedSequence([SEED, TAG, role]))
    angle = rng.uniform(0, 2 * np.pi, count)
    radius = np.sqrt(rng.uniform(0, 1, count))
    return np.column_stack((np.cos(angle), np.sin(angle))) * radius[:, None]


def observe_background(h, role):
    coords = kernel.witness.witness_stencil(h)
    probes = predecessor.prior.background_probes(coords)
    frames = np.broadcast_to(kernel.spatial.FRAME, (5, 3, 2))
    moments = kernel.spatial.DenseMomentAdapter().moments(frames, probes)
    result = {}
    for hypothesis, clean in moments.items():
        values = clean + WITNESS_EPSILON * disk_draw(5, role)
        fit = kernel.witness.fit_affine_witness(
            coords, values, np.full(5, WITNESS_EPSILON)
        )
        result[hypothesis] = {
            "coords": coords.tolist(),
            "moments": values.tolist(),
            "clean_probe_sha256": kernel.HASH(probes),
            "fit": fit,
        }
    return result


def bias(mode):
    result = np.zeros((3, 2))
    if mode in ("constant", "shared-constant"):
        result[0] = kernel.base.cv(5e-4 * np.exp(1j * np.pi / 7))
    elif mode == "linear":
        result[1] = kernel.base.cv(5e-4 * np.exp(1j * np.pi / 7))
        result[2] = kernel.base.cv(5e-4 * np.exp(1j * (np.pi / 7 + np.pi / 3)))
    elif mode != "none":
        raise ValueError("registered coefficient stress required")
    return result


def score(
    readout, truth, reference, witness_coefficients, witness_radii, *, witness_consumed
):
    """Truth and ideal background appear only after the inference seal exists."""
    body = {k: v for k, v in readout.items() if k != "readout_seal_sha256"}
    if kernel.SEAL(body) != readout["readout_seal_sha256"]:
        raise ValueError("readout changed before truth scoring")
    valid = truth["fixture"] == "double" or truth["fixture"].startswith(
        ("pair-", "reverse-")
    )
    available = readout["center"] is not None
    center_error = (
        float(np.linalg.norm(np.asarray(readout["center"]) - truth["center"]))
        if valid and available
        else None
    )
    return {
        "truth_read_after_inference": True,
        "truth_quadratic_family": valid,
        "witness_bound_holds": bool(
            np.all(
                np.linalg.norm(witness_coefficients - kernel.spatial.IDEAL, axis=1)
                <= witness_radii
            )
        )
        if witness_consumed
        else None,
        "reference_error_rows": np.linalg.norm(
            reference - kernel.spatial.IDEAL, axis=1
        ).tolist(),
        "center_covered": center_error <= readout["center_radius"]
        if center_error is not None
        else None,
        "separation_covered": readout["separation_lower"]
        <= truth["separation"]
        <= readout["separation_upper"]
        if valid and available
        else None,
        "single_false_two": truth["fixture"] == "double"
        and readout["status"] == "two_required_in_family",
        "center_error": center_error,
    }


def summary(rows):
    result = []
    for placement in PLACEMENTS:
        for mode in MODES:
            for epsilon in EPSILONS:
                for witness_mode in ("bounded", "absent"):
                    selected = [
                        r
                        for r in rows
                        if (r["placement"], r["mode"], r["epsilon"], r["witness_mode"])
                        == (placement, mode, epsilon, witness_mode)
                    ]
                    scored = [r["score"] for r in selected]
                    result.append(
                        {
                            "placement": placement,
                            "mode": mode,
                            "epsilon": epsilon,
                            "witness_mode": witness_mode,
                            "records": len(selected),
                            "statuses": dict(
                                sorted(
                                    Counter(
                                        r["readout"]["status"] for r in selected
                                    ).items()
                                )
                            ),
                            "center_available": sum(
                                s["center_covered"] is not None for s in scored
                            ),
                            "center_misses": sum(
                                s["center_covered"] is False for s in scored
                            ),
                            "separation_misses": sum(
                                s["separation_covered"] is False for s in scored
                            ),
                            "single_false_two": sum(
                                s["single_false_two"] for s in scored
                            ),
                            "witness_contract_violations": sum(
                                s["witness_bound_holds"] is False for s in scored
                            ),
                        }
                    )
    return result


def demo():
    if sha(ROOT / PROTOCOL) != PROTOCOL_SHA256:
        raise ValueError("committed development specification changed")
    before = source_lock()
    references = observe_background(1.0, 1)
    witnesses = {str(h): observe_background(h, 2) for h in PLACEMENTS}
    observations, truths = {}, {}
    for fixture in FIXTURES:
        truth = predecessor.geometry(SEED, fixture)
        truths[fixture] = truth
        probes, clean = predecessor.observe(kernel.SUPPORT, truth, 0.1)
        for epsilon in EPSILONS:
            for hypothesis in kernel.spatial.HYPOTHESES:
                key = f"{fixture}/{epsilon}/{hypothesis}"
                measured = clean[hypothesis] + epsilon * disk_draw(25, 3)
                observations[key] = {
                    "moments": measured.tolist(),
                    "clean_probe_sha256": kernel.HASH(probes),
                    "point_bounds": np.full(25, epsilon).tolist(),
                }
    rows = []
    for placement in PLACEMENTS:
        for mode in MODES:
            for epsilon in EPSILONS:
                for fixture in FIXTURES:
                    for hypothesis in kernel.spatial.HYPOTHESES:
                        rf = references[hypothesis]["fit"]
                        wf = witnesses[str(placement)][hypothesis]["fit"]
                        reference = np.asarray(rf["coefficients"]) + bias(mode)
                        observed_witness = np.asarray(wf["coefficients"]).copy()
                        if mode == "shared-constant":
                            observed_witness += bias(mode)
                        for witness_mode in ("bounded", "absent"):
                            budget = kernel.witness.reference_budget(reference)
                            if witness_mode == "bounded":
                                budget = kernel.witness.reference_budget(
                                    reference,
                                    observed_witness,
                                    wf["radii"],
                                    witness_independent=True,
                                    witness_id=f"synthetic-witness/h={placement}/{hypothesis}",
                                )
                            key = f"{fixture}/{epsilon}/{hypothesis}"
                            observed = observations[key]
                            readout = kernel.infer(
                                observed["moments"],
                                reference,
                                budget,
                                observed["point_bounds"],
                            )
                            rows.append(
                                {
                                    "placement": placement,
                                    "mode": mode,
                                    "epsilon": epsilon,
                                    "fixture": fixture,
                                    "hypothesis": hypothesis,
                                    "witness_mode": witness_mode,
                                    "observation_key": key,
                                    "reference": reference.tolist(),
                                    "budget": budget,
                                    "readout": readout,
                                    "score": score(
                                        readout,
                                        truths[fixture],
                                        reference,
                                        observed_witness,
                                        np.asarray(wf["radii"]),
                                        witness_consumed=witness_mode == "bounded",
                                    ),
                                }
                            )
    if len(rows) != 1152 or source_lock() != before:
        raise ValueError("development denominator or source changed")
    body = kernel.json_values(
        {
            "schema_version": kernel.SCHEMA + ".development-demo",
            "protocol_sha256": PROTOCOL_SHA256,
            "source_sha256": before,
            "environment": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "scipy": scipy.__version__,
            },
            "record_count": len(rows),
            "independent_trials": None,
            "evaluation_geometry_seeds": [SEED],
            "noise_seed_namespace": TAG,
            "geometry_generator": "inherited center-resolution geometry, development seed 7; not a new cohort",
            "campaign_status": "not_frozen_not_run",
            "scope": "synthetic-deterministic-development-controls",
            "scientific_authority": False,
            "calibrated_confidence_region": False,
            "noise_location": "post-adapter-moment-space",
            "pairing": "shared bounded draws across scales fixtures placements and F2/F4; no independent F2/F4 performance comparison",
            "references": references,
            "witnesses": witnesses,
            "observations": observations,
            "truth": truths,
            "records": rows,
            "summary": summary(rows),
        }
    )
    return {**body, "report_seal_sha256": kernel.SEAL(body)}


def verify_demo(report):
    if type(report) is not dict or canonical_json_bytes(report) != canonical_json_bytes(
        demo()
    ):
        raise ValueError("development report does not replay from frozen inputs/source")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument(
        "--output", type=Path, help="exclusive-create local development JSON"
    )
    action.add_argument(
        "--verify", type=Path, help="replay an existing report without writing"
    )
    args = parser.parse_args()
    if args.verify is not None:
        verify_demo(json.loads(args.verify.read_text()))
        print("Development report replay verified; no campaign/model execution.")
    else:
        if args.output.exists():
            raise FileExistsError("development output already exists")
        report = demo()
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(
                json.dumps(
                    report,
                    ensure_ascii=False,
                    sort_keys=True,
                    indent=2,
                    allow_nan=False,
                )
                + "\n"
            )
        print(
            json.dumps(
                {
                    "records": report["record_count"],
                    "report_seal_sha256": report["report_seal_sha256"],
                    "campaign_status": report["campaign_status"],
                }
            )
        )


if __name__ == "__main__":
    main()
