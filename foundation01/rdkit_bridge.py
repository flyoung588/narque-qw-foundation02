"""Local mature molecular-mechanics probe.

RDKit MMFF/UFF is NOT a quantum electronic solver or PySCF replacement.
It is used only to exercise MatterSpec -> energy/forces -> branch/compare.
"""
import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem
from .contract import validate

HARTREE_TO_KCALMOL = 627.5094740631
BOHR_TO_ANGSTROM = 0.529177210903
KCALMOL_TO_EV = 0.0433641153087705


def from_smiles(smiles, object_id, method="MMFF94", seed=20261020):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError("SMILES_PARSE_FAILED")
    mol = Chem.AddHs(mol)
    if mol.GetNumAtoms() > 16:
        raise ValueError("PILOT_EXCEEDS_16_ATOMS")
    code = AllChem.EmbedMolecule(mol, randomSeed=seed)
    if code != 0:
        raise ValueError("CONFORMER_GENERATION_FAILED")
    if any(a.GetNumRadicalElectrons() != 0 for a in mol.GetAtoms()):
        raise ValueError("RADICAL_NOT_SUPPORTED_BY_RDKit_PILOT")
    conf = mol.GetConformer()
    spec = {
        "version": "QW-WORLDSPEC-0.1", "object_id": object_id, "epistemic_mode": "GROUNDED",
        "matter": {"type": "molecule", "periodic": False,
                   "atoms": [{"element": a.GetSymbol(), "xyz_angstrom": [float(x) for x in conf.GetAtomPosition(a.GetIdx())]}
                             for a in mol.GetAtoms()],
                   "bonds": [{"i": b.GetBeginAtomIdx(), "j": b.GetEndAtomIdx(),
                              "order": float(b.GetBondTypeAsDouble())} for b in mol.GetBonds()],
                   "charge": Chem.GetFormalCharge(mol), "spin_2S": 0,
                   "source": "RDKit SMILES->ETKDGv3 embedding, geometry not optimized", "smiles": smiles},
        "physics": {"engine": "rdkit", "method": method, "observables": ["energy", "forces"]},
        "experiment": {"action": "single_point", "description": "Empirical force field at submitted unrelaxed geometry"},
    }
    validate(spec)
    return spec


def rdkit_molecule_from_matter(matter):
    rw = Chem.RWMol()
    for atom in matter["atoms"]:
        rw.AddAtom(Chem.Atom(atom["element"]))
    for bond in matter.get("bonds", []):
        orders = {1.: Chem.BondType.SINGLE, 2.: Chem.BondType.DOUBLE, 3.: Chem.BondType.TRIPLE, 1.5: Chem.BondType.AROMATIC}
        rw.AddBond(bond["i"], bond["j"], orders[float(bond["order"])])
    mol = rw.GetMol()
    Chem.SanitizeMol(mol)
    conf = Chem.Conformer(len(matter["atoms"]))
    for i, atom in enumerate(matter["atoms"]):
        conf.SetAtomPosition(i, atom["xyz_angstrom"])
    mol.AddConformer(conf)
    return mol


def solve(spec):
    meta = validate(spec)
    if spec["physics"]["engine"] != "rdkit":
        raise ValueError("WRONG_ENGINE")
    m = rdkit_molecule_from_matter(spec["matter"])
    method = spec["physics"]["method"]
    if method == "MMFF94":
        if not AllChem.MMFFHasAllMoleculeParams(m):
            raise ValueError("OUT_OF_DOMAIN_MMFF_PARAMETERS")
        properties = AllChem.MMFFGetMoleculeProperties(m, mmffVariant="MMFF94")
        ff = AllChem.MMFFGetMoleculeForceField(m, properties, ignoreInterfragInteractions=False)
    elif method == "UFF":
        if not AllChem.UFFHasAllMoleculeParams(m):
            raise ValueError("OUT_OF_DOMAIN_UFF_PARAMETERS")
        ff = AllChem.UFFGetMoleculeForceField(m, ignoreInterfragInteractions=False)
    else:
        raise ValueError("WRONG_RDKit_METHOD")
    energy_kcal = float(ff.CalcEnergy())
    gradient_kcal_ang = np.array(ff.CalcGrad(), dtype=float).reshape((-1, 3))
    if not (np.isfinite(energy_kcal) and np.isfinite(gradient_kcal_ang).all()):
        raise ValueError("NONFINITE_RESULT")
    force_eva = (-gradient_kcal_ang * KCALMOL_TO_EV).tolist()
    return {"energy": energy_kcal * KCALMOL_TO_EV, "energy_unit": "eV", "forces_eV_per_angstrom": force_eva,
            "energy_kcal_per_mol": energy_kcal,
            "engine": "RDKit", "method": method, "rdkit_version": __import__('rdkit').__version__,
            "electronic_structure_solved": False, "solver_equation": "empirical molecular mechanics forcefield",
            "physics_limit": "fixed chemical bond graph; no electronic wavefunction, photophysics, bond-breaking, or quantum dynamics",
            "coordinate_frame": "molecular Cartesian angstrom; energy zero and parameterization specific to forcefield"}
