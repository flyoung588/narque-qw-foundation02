"""Execute exact physically scoped world requests and preserve evidence."""
from datetime import datetime, timezone
import json
from pathlib import Path
from .contract import validate, digest, compare, SCHEMA


def run_world(spec):
    meta = validate(spec)
    backend = spec["physics"]["engine"]
    if backend == "rdkit":
        from .rdkit_bridge import solve
    elif backend in ("pyscf", "ase-pyscf"):
        from .pyscf_bridge import solve, solve_with_ase
        if backend == "ase-pyscf":
            solve = solve_with_ase
    else:
        raise ValueError("ENGINE_UNAVAILABLE")
    obs = solve(spec)
    status = obs.get("status", "CALCULATED")
    return {"record_kind": "QW_FOUNDATION01_OBSERVATION", "status": status,
            "model_precision_qualified": False, "scientific_novelty": "NOT_TESTED",
            "world_spec_sha256": digest(spec), "world_schema_sha256": digest(SCHEMA),
            "spec": spec, "matter_check": meta, "observation": obs,
            "truth_dimensions": {"numerical": "NOT_INDEPENDENTLY_CERTIFIED",
                                 "model_physics": "EMPIRICAL_FORCE_FIELD_ONLY" if backend == "rdkit" else "MEAN_FIELD_FINITE_BASIS",
                                 "scientific_novelty": "NOT_TESTED", "external_reality_engineering": "NOT_TESTED"},
            "publication_status": "LOCAL_ONLY_NOT_PUBLICLY_SUBMITTED"}


def save_json(path, data):
    p = Path(path);p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False, sort_keys=True)+"\n")
    return p
