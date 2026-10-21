"""WorldSpec validation, provenance and scientifically guarded comparison.

A molecule's nuclear positions in angstrom and electronic quantum numbers are
specified independently of any quantum-chemistry package.
"""
import copy
import hashlib
import json
import math
from typing import Any
import numpy as np
from jsonschema import Draft202012Validator

SCHEMA_VERSION = "QW-WORLDSPEC-0.1"
ELEMENTS = {"H": 1, "He": 2, "Li": 3, "Be": 4, "B": 5, "C": 6,
            "N": 7, "O": 8, "F": 9, "Ne": 10}

SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "NARQUE QW-FOUNDATION-01 minimal WorldSpec",
    "type": "object", "required": ["version", "object_id", "epistemic_mode", "matter", "physics"],
    "additionalProperties": False,
    "properties": {
        "version": {"const": SCHEMA_VERSION},
        "object_id": {"type": "string", "minLength": 1, "maxLength": 100, "pattern": "^[A-Za-z0-9._-]+$"},
        "epistemic_mode": {"enum": ["GROUNDED", "EXTRAPOLATIVE", "MODEL_CHALLENGE"]},
        "matter": {
            "type": "object", "additionalProperties": False,
            "required": ["type", "atoms", "charge", "spin_2S", "periodic"],
            "properties": {
                "type": {"const": "molecule"},
                "atoms": {"type": "array", "minItems": 1, "maxItems": 16,
                    "items": {"type": "object", "additionalProperties": False,
                        "required": ["element", "xyz_angstrom"],
                        "properties": {"element": {"enum": sorted(ELEMENTS)},
                            "xyz_angstrom": {"type": "array", "minItems": 3, "maxItems": 3, "items": {"type": "number"}}}}},
                "bonds": {"type": "array", "items": {"type": "object", "required": ["i", "j", "order"], "additionalProperties": False,
                    "properties": {"i": {"type": "integer", "minimum": 0}, "j": {"type": "integer", "minimum": 0},
                        "order": {"enum": [1, 2, 3, 1.5]}}}},
                "charge": {"type": "integer", "minimum": -3, "maximum": 3},
                "spin_2S": {"type": "integer", "minimum": 0, "maximum": 16},
                "periodic": {"const": False},
                "source": {"type": "string", "maxLength": 300},
                "smiles": {"type": "string", "maxLength": 250},
            },
        },
        "physics": {"type": "object", "additionalProperties": False,
            "required": ["engine", "method", "observables"],
            "properties": {"engine": {"enum": ["rdkit", "pyscf", "ase-pyscf"]},
                "method": {"enum": ["MMFF94", "UFF", "RHF", "UHF", "RKS", "UKS"]},
                "basis": {"type": "string", "maxLength": 50},
                "xc": {"type": "string", "maxLength": 60},
                "observables": {"type": "array", "items": {"enum": ["energy", "forces"]}, "minItems": 1, "uniqueItems": True},
            }},
        "experiment": {"type": "object", "additionalProperties": False,
            "properties": {"action": {"const": "single_point"},
                "description": {"type": "string", "maxLength": 200}}},
    },
}


def canonical_json(data):
    return json.dumps(data, allow_nan=False, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(data):
    return hashlib.sha256(canonical_json(data).encode("utf8")).hexdigest()


def validate(spec):
    errors = sorted(Draft202012Validator(SCHEMA).iter_errors(spec), key=lambda e: list(map(str, e.path)))
    if errors:
        raise ValueError("SCHEMA_INVALID: " + "; ".join(str(e.message) for e in errors[:3]))
    if spec["epistemic_mode"] != "GROUNDED":
        raise ValueError("EPISTEMIC_MODE_NOT_EXECUTABLE_IN_FOUNDATION01")
    m, p = spec["matter"], spec["physics"]
    coords = np.array([a["xyz_angstrom"] for a in m["atoms"]], dtype=float)
    if not np.isfinite(coords).all():
        raise ValueError("NONFINITE_COORDINATES")
    if float(np.max(np.abs(coords))) > 1e5:
        raise ValueError("POSITION_OUTSIDE_BOUNDED_DOMAIN")
    if len(coords) > 1:
        from scipy.spatial.distance import pdist
        if float(pdist(coords).min()) < .35:
            raise ValueError("COINCIDENT_OR_UNPHYSICAL_NUCLEI")
    electrons = sum(ELEMENTS[a["element"]] for a in m["atoms"]) - m["charge"]
    spin = m["spin_2S"]
    if not (0 < electrons <= 120):
        raise ValueError("INVALID_ELECTRON_COUNT")
    if spin > electrons or (electrons - spin) % 2:
        raise ValueError("ELECTRON_SPIN_PARITY_MISMATCH")
    for b in m.get("bonds", []):
        if b["i"] == b["j"] or max(b["i"], b["j"]) >= len(coords):
            raise ValueError("INVALID_BOND_TOPOLOGY")
    if len({tuple(sorted((b["i"], b["j"]))) for b in m.get("bonds", [])}) != len(m.get("bonds", [])):
        raise ValueError("DUPLICATE_BOND")
    if p["engine"] == "rdkit":
        if p["method"] not in ("MMFF94", "UFF"):
            raise ValueError("ENGINE_METHOD_INCOMPATIBLE")
        if not m.get("bonds") and len(coords)>1:
            raise ValueError("RDKit_FORCEFIELD_NEEDS_BOND_TOPOLOGY")
        if m["spin_2S"]:
            raise ValueError("EMPIRICAL_FORCEFIELD_SPIN_DOMAIN_UNSUPPORTED")
    else:
        if p["method"] not in ("RHF", "UHF", "RKS", "UKS") or not p.get("basis"):
            raise ValueError("ENGINE_METHOD_OR_BASIS_INCOMPATIBLE")
        if (p["method"] in ("RHF", "RKS")) and spin != 0:
            raise ValueError("RESTRICTED_MEAN_FIELD_REQUIRES_ZERO_SPIN")
        # Restrict this W1 one-shot pilot to bounded, pre-registered calculations.
        # Later engines/methods require explicit additional capability qualification.
        if (len(coords) > 8 or electrons > 30 or p["basis"].lower() not in ("sto-3g", "cc-pvdz")
            or p["method"] not in ("RHF", "UHF")):
            raise ValueError("QUANTUM_ONE_SHOT_DOMAIN_LIMIT")
    return {"electron_count": electrons, "spin_2S": spin, "atomic_numbers": [ELEMENTS[a["element"]] for a in m["atoms"]],
            "model_scope": "molecular only; nonperiodic; finite element and size domain; not arbitrary matter"}


def displace(spec, atom_index, vector_angstrom, new_object_id):
    out = copy.deepcopy(spec)
    if not isinstance(atom_index, int) or not (0 <= atom_index < len(out["matter"]["atoms"])):
        raise ValueError("INVALID_ATOM_INDEX")
    if len(vector_angstrom) != 3 or not all(isinstance(x, (float, int)) and math.isfinite(x) for x in vector_angstrom):
        raise ValueError("INVALID_DISPLACEMENT")
    pos = out["matter"]["atoms"][atom_index]["xyz_angstrom"]
    out["matter"]["atoms"][atom_index]["xyz_angstrom"] = [round(float(a+b), 12) for a, b in zip(pos, vector_angstrom)]
    out["object_id"] = new_object_id
    validate(out)
    return out


def comparable(before, after):
    """Only compare within the same physical representation and composition."""
    a, b = before["spec"], after["spec"]
    fields = ["charge", "spin_2S", "periodic", "bonds"]
    if any(a["matter"].get(k) != b["matter"].get(k) for k in fields):
        return False, "MISMATCHED_CHARGE_SPIN_OR_BOND_GRAPH"
    if [v["element"] for v in a["matter"]["atoms"]] != [v["element"] for v in b["matter"]["atoms"]]:
        return False, "MISMATCHED_CHEMICAL_COMPOSITION"
    if a["physics"] != b["physics"]:
        return False, "MISMATCHED_MODEL_OR_OBSERVABLE_DEFINITION"
    if before.get("status") != "CALCULATED" or after.get("status") != "CALCULATED":
        return False, "UNVERIFIED_OR_MISSING_NUMERICAL_RESULT"
    return True, "SAME_COMPOSITION_AND_PHYSICAL_METHOD"


def compare(before, after):
    ok, why = comparable(before, after)
    if not ok:
        return {"status": "INCOMPARABLE", "reason": why, "energy_difference": None}
    a, b = before["observation"], after["observation"]
    if a.get("energy_unit") != b.get("energy_unit"):
        return {"status": "INCOMPARABLE", "reason": "ENERGY_UNIT_MISMATCH", "energy_difference": None}
    return {"status": "MODEL_INTERNAL_DIFFERENCE", "reason": why, "energy_difference": b["energy"] - a["energy"],
            "unit": a["energy_unit"], "physical_precision_qualified": False,
            "scope": "same-model geometry perturbation, NOT a reaction barrier, discovery, or independently certified energy"}
