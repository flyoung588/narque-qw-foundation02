"""Reuse frozen Foundation01 solver, add common observation semantics and basis provenance."""
def solve(spec,out):
 import numpy as np
 from pyscf import lib,gto
 from foundation01.pyscf_bridge import solve as direct,solve_with_ase
 lib.num_threads(1)
 v=(solve_with_ase if spec['physics']['engine']=='ase-pyscf' else direct)(spec)
 if v.get('status')=='UNVERIFIED':return v
 mol=gto.M(atom=[(a['element'],a['xyz_angstrom']) for a in spec['matter']['atoms']],unit='Angstrom',charge=spec['matter']['charge'],spin=spec['matter']['spin_2S'],basis=spec['physics']['basis'],cart=False,verbose=0)
 shells=[{'center':mol.bas_atom(i),'l':mol.bas_angular(i),'exponents':mol.bas_exp(i).tolist(),'contraction_coefficients':mol.bas_ctr_coeff(i).tolist()} for i in range(mol.nbas)]
 return {**v,'engine':'PySCF','model':'nonrelativistic all-electron fixed-nuclei BO conventional HF','energy_Eh':v['energy'],'energy_zero':'total BO electronic-structure energy including nuclear repulsion','gradient_Eh_per_bohr':(-np.array(v['forces_Eh_per_bohr'])).tolist(),'force_definition':'negative analytic Cartesian nuclear gradient in original input frame','basis_AO_count':mol.nao_nr(),'basis_shells':shells,'basis_coefficient_convention':'PySCF bas_ctr_coeff; normalization review required versus Psi4','settings':{'density_fitting':False,'cartesian':False,'conv_tol':1e-10,'max_cycle':80},'geometry_bohr':mol.atom_coords().tolist(),'numerical_threads':lib.num_threads(1)}
