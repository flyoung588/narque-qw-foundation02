"""ASE->PySCF electronic-structure bridge. Not executed in this chat environment.

No hardcoded molecules: any physically validated nonperiodic MatterSpec in
this prototype's bounded element/size domain can be submitted.
"""
import numpy as np
from .contract import validate

HARTREE_TO_EV = 27.211386245988
BOHR_TO_ANGSTROM = 0.529177210903


def solve(spec, stage_callback=None):
    stage = stage_callback or (lambda name: None)
    meta = validate(spec)
    request = spec["physics"]
    if request["engine"] not in ("pyscf", "ase-pyscf"):
        raise ValueError("WRONG_ENGINE")
    stage('IMPORT')
    try:
        import pyscf
        from pyscf import gto, scf, dft
    except ImportError as e:
        raise RuntimeError("ENGINE_UNAVAILABLE_PYSCF_NOT_INSTALLED") from e
    atoms = [(a["element"], a["xyz_angstrom"]) for a in spec["matter"]["atoms"]]
    stage('MOLECULE_BUILD')
    mol = gto.M(atom=atoms, unit="Angstrom", charge=spec["matter"]["charge"],
                spin=spec["matter"]["spin_2S"], basis=request["basis"],
                symmetry=False, verbose=0, max_memory=500)
    method = request["method"]
    if method == "RHF":
        mf = scf.RHF(mol)
    elif method == "UHF":
        mf = scf.UHF(mol)
    elif method == "RKS":
        mf = dft.RKS(mol);mf.xc = request.get("xc", "PBE")
    elif method == "UKS":
        mf = dft.UKS(mol);mf.xc = request.get("xc", "PBE")
    else:
        raise ValueError("MODEL_UNSUPPORTED")
    mf.conv_tol = 1e-10
    mf.max_cycle = 80
    stage('SCF_START')
    energy_eh = float(mf.kernel())
    stage('SCF_END')
    if not bool(mf.converged):
        return {"status": "UNVERIFIED", "reason": "SCF_NOT_CONVERGED", "energy_Eh_raw": energy_eh,
                "method": method, "basis": request["basis"]}
    if not np.isfinite(energy_eh):
        raise RuntimeError("NONFINITE_ELECTRONIC_ENERGY")
    stage('GRADIENT_START')
    grad = np.asarray(mf.nuc_grad_method().kernel(), dtype=float)
    stage('GRADIENT_END')
    if grad.shape != (len(atoms), 3) or not np.isfinite(grad).all():
        raise RuntimeError("NUMERICAL_GRADIENT_UNAVAILABLE")
    forces_eh_bohr = -grad
    values = {"energy": energy_eh, "energy_unit": "Eh", "energy_eV": energy_eh * HARTREE_TO_EV,
              "forces_Eh_per_bohr": forces_eh_bohr.tolist(),
              "forces_eV_per_angstrom": (forces_eh_bohr * HARTREE_TO_EV / BOHR_TO_ANGSTROM).tolist(),
              "engine": "PySCF", "engine_version": pyscf.__version__,
              "method": method, "basis": request["basis"], "converged": True,
              "orbital_basis_size": int(mol.nao_nr()), "SCF_convergence_threshold_Eh": mf.conv_tol,
              "SCF_max_iterations": mf.max_cycle,
              "nuclear_repulsion_Eh": float(mol.energy_nuc()),
              "electrons": mol.nelectron, "spin_2S": mol.spin,
              "electronic_structure_solved": True,
              "solver_equation": "single-determinant mean-field electronic Hamiltonian; approximate finite-basis solution",
              "physics_limit": "nonrelativistic fixed-nuclei Born-Oppenheimer; no nuclear dynamics, no correlated many-electron accuracy claim",
              "comparison_scope": "same composition/charge/spin/method/basis and geometry branch only"}
    return values


def ase_atoms(spec):
    """Use the actual mature ASE Atoms object; does not attach a forcefield."""
    validate(spec)
    try:
        from ase import Atoms
    except ImportError as e:
        raise RuntimeError("ENGINE_UNAVAILABLE_ASE_NOT_INSTALLED") from e
    m = spec["matter"]
    obj = Atoms([a["element"] for a in m["atoms"]],
                positions=[a["xyz_angstrom"] for a in m["atoms"]], pbc=False)
    obj.info.update(charge=m["charge"], spin_2S=m["spin_2S"], object_id=spec["object_id"])
    return obj


def ase_pyscf_calculator(spec):
    """A genuine ASE Calculator facade for the PySCF single-point backend.

    Avoids installing/unverified third-party ASE-PySCF adapters. The physical
    solver remains PySCF, and ASE only owns geometry / calculator invocation.
    """
    try:
        from ase.calculators.calculator import Calculator, all_changes
    except ImportError as e:
        raise RuntimeError("ENGINE_UNAVAILABLE_ASE_NOT_INSTALLED") from e
    from copy import deepcopy
    class _PySCF(Calculator):
        implemented_properties = ["energy", "forces"]
        def calculate(self, atoms=None, properties=("energy", "forces"), system_changes=all_changes):
            super().calculate(atoms, properties, system_changes)
            local = deepcopy(spec)
            local["physics"]["engine"] = "pyscf"
            for i, xyz in enumerate(atoms.positions):
                local["matter"]["atoms"][i]["xyz_angstrom"] = xyz.tolist()
            result = solve(local)
            if result.get("status") == "UNVERIFIED":
                raise RuntimeError("SCF_UNVERIFIED_NOT_AN_ASE_ENERGY")
            self.results = {"energy": result["energy_eV"], "forces": np.array(result["forces_eV_per_angstrom"])}
            self.pyscf_evidence = result
    return _PySCF()


def solve_with_ase(spec):
    atoms = ase_atoms(spec)
    atoms.calc = ase_pyscf_calculator(spec)
    ev = float(atoms.get_potential_energy())
    f = np.array(atoms.get_forces()).tolist()
    evidence = atoms.calc.pyscf_evidence
    assert abs(ev - evidence["energy_eV"]) < 1e-8
    return {**evidence, "ase_atoms_used": True, "ase_calculator_eV": ev, "ase_forces_eV_per_angstrom": f}
