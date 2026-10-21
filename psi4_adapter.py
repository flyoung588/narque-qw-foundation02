"""Psi4 conventional RHF/UHF, midpoint-free Cartesian geometry, analytic gradient."""
def solve(spec,out):
 import psi4
 import numpy as np
 p=spec['physics'];m=spec['matter'];psi4.core.clean();psi4.core.clean_options();psi4.set_num_threads(1);psi4.set_memory('400 MiB')
 psi4.core.IOManager.shared_object().set_default_path('/tmp')
 psi4.set_output_file(str(out/'psi4.log'),False)
 lines=[f"{m['charge']} {m['spin_2S']+1}"]+[a['element']+' '+' '.join(format(float(v),'.15g') for v in a['xyz_angstrom']) for a in m['atoms']]+['units angstrom','symmetry c1','no_reorient','no_com']
 mol=psi4.geometry('\n'.join(lines));mol.update_geometry()
 opts={'basis':p['basis'],'reference':p['method'].lower(),'scf_type':'pk','puream':True,'e_convergence':1e-10,'d_convergence':1e-8,'maxiter':80,'fail_on_maxiter':True,'guess':'sad'}
 psi4.set_options(opts)
 gradient,wfn=psi4.gradient('scf',molecule=mol,return_wfn=True)
 g=np.asarray(gradient);energy=float(wfn.energy());assert g.shape==(len(m['atoms']),3) and np.isfinite(g).all() and np.isfinite(energy)
 b=wfn.basisset();shells=[]
 for i in range(b.nshell()):
  s=b.shell(i);shells.append({'center':s.ncenter,'l':s.am,'exponents':[s.exp(j) for j in range(s.nprimitive)],'original_coefficients':[s.original_coef(j) for j in range(s.nprimitive)]})
 return {'engine':'Psi4','engine_version':psi4.__version__,'model':'nonrelativistic all-electron fixed-nuclei BO conventional HF','method':p['method'],'basis':p['basis'],'basis_AO_count':b.nbf(),'basis_shells':shells,'basis_coefficient_convention':'Psi4 original_coef; not assumed identical normalization to PySCF','settings':opts,'status':'CALCULATED','SCF_converged':'successful fail_on_maxiter gradient return','energy_Eh':energy,'energy_unit':'Eh','energy_zero':'total BO electronic-structure energy including nuclear repulsion','gradient_Eh_per_bohr':g.tolist(),'forces_Eh_per_bohr':(-g).tolist(),'force_definition':'negative analytic Cartesian nuclear gradient in original input frame','nuclear_repulsion_Eh':mol.nuclear_repulsion_energy(),'geometry_bohr':np.asarray(mol.geometry()).tolist(),'electrons':int(wfn.nalpha()+wfn.nbeta()),'numerical_threads':1,'limitations':'mean-field finite-basis; no correlation, relativity, nuclear dynamics or stability proof'}
