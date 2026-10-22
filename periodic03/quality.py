"""Three electron counts and bounded sensitivity; no material accuracy gate."""
import math
def electron_counts(occ,dm,overlap,weights,rho,grid_weights):
 import numpy as np
 occ=np.asarray(occ);dm=np.asarray(dm);overlap=np.asarray(overlap);w=np.asarray(weights)
 if len(w)!=len(dm) or len(w)!=len(occ) or not np.isclose(w.sum(),1):raise ValueError('WEIGHT_SHAPE_MISMATCH')
 traces=np.einsum('kij,kji->k',dm,overlap)
 return {'occupation_electrons':float(w@occ.sum(axis=1)),'density_overlap_trace_electrons':float(w@traces.real),'trace_imaginary_abs':float(abs(w@traces.imag)),'realspace_integrated_electrons':float(np.dot(rho,grid_weights)),'definitions':'Uniform k-weight sum of spin-summed occupations and Tr(D_k S_k); independent finite realspace quadrature of same final density. A quadrature mismatch does not change actual electron number.'}
def labels(converged):
 return ['NUMERICAL_CONVERGENCE_OBSERVED' if converged else 'NUMERICALLY_UNVERIFIED','QUADRATURE_SENSITIVITY_UNKNOWN','KPOINT_SENSITIVITY_UNKNOWN','BASIS_SENSITIVITY_UNKNOWN','MODEL_ACCURACY_NOT_CERTIFIED','INDEPENDENT_REFERENCE_NOT_TESTED']
def compare(a,b):
 if a.get('status')!='CALCULATED' or b.get('status')!='CALCULATED':return {'status':'UNVERIFIED','reason':'need two actual converged results'}
 if any(x.get('synthetic') or x.get('simulated') for x in (a,b)):return {'status':'UNVERIFIED','reason':'synthetic evidence is not a physical sensitivity measurement'}
 if any(x.get('observation',{}).get('SCF_converged') is not True or not math.isfinite(x['observation'].get('energy_Eh_per_cell',float('nan'))) for x in (a,b)):return {'status':'UNVERIFIED','reason':'finite converged SCF required'}
 from .contract import validate
 ma=validate(a['spec']);mb=validate(b['spec'])
 # Labels/source excluded only; geometry, chemistry, quantum numbers and base physics identical.
 sa=ma['base_spec'];sb=mb['base_spec']
 if sa['matter']!=sb['matter'] or sa['physics']!=sb['physics'] or ma['numerics']!=mb['numerics']:return {'status':'INCOMPARABLE','reason':'different state/model/numerics'}
 oa=a['observation'];ob=b['observation']
 if oa['energy_zero']!=ob['energy_zero']:return {'status':'INCOMPARABLE','reason':'energy reference'}
 if ma['method']!=mb['method']:kind='SOLVER_PATH_CONSISTENCY_DIFFERENCE'
 elif ma['sampling']!=mb['sampling']:kind='BOUNDED_KPOINT_SENSITIVITY_MEASURED'
 else:kind='SAME_SETTINGS_DIFFERENCE'
 return {'status':kind,'delta_Eh_per_cell':ob['energy_Eh_per_cell']-oa['energy_Eh_per_cell'],'changed':{'solver_paths':[ma['method'],mb['method']],'kmeshes':[ma['sampling']['mesh'],mb['sampling']['mesh']]},'grid_k_coupling':'Same nominal Becke setting, but self-consistent density and grid pruning can change; not pure isolated quadrature effect','KPOINT_CONVERGENCE_CERTIFIED':False,'QUADRATURE_SENSITIVITY':'UNKNOWN','physical_accuracy':'NOT_CERTIFIED'}
