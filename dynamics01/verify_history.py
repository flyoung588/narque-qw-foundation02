import pathlib,json,hashlib
import numpy as np
from .offline import setup
from .model import observe_arrays

def verify(out,history):
 out=pathlib.Path(out);w,b,s=setup(out/'history-check',history);records={}
 for key,h in s.items():
  if key not in ('initial','three_step_branch','final'):continue
  st=w.store.load(h);a=w.store.arrays(st);records[key]={'state_sha256':h,'array_sha256':st['payload']['arrays']['sha256'],'physical_time_au':st['payload']['time_au'],'observation':observe_arrays(a,st['payload'])}
 h=pathlib.Path(history);free=json.loads((h/'results/analytic_free_packet.json').read_text());closed=json.loads((h/'results/closed_system.json').read_text());conv=json.loads((h/'results/convergence.json').read_text());cap=json.loads((h/'results/cap_accounting.json').read_text())
 # Recompute summary from original trajectory rows, not from a stated PASS flag.
 drift=max(abs(v['energy_Eh']-closed['rows'][0]['energy_Eh']) for v in closed['rows']);norm=max(abs(v['norm']-1) for v in closed['rows']);center=float(np.max(abs(np.asarray(free['actual_center'])-free['analytic_center'])));cov=float(np.max(abs(np.asarray(free['actual_cov'])-free['analytic_cov'])))
 assert abs(drift-closed['energy_max_drift_Eh'])<1e-15 and abs(norm-closed['norm_max_error'])<1e-15
 for key in ('product_region','reactant_region','absorbed','energy_Eh'):
  c=conv[key];assert abs(abs(c['baseline']-c['dt_halved'])-c['dt_difference'])<1e-14;assert abs(abs(c['baseline']-c['grid_doubled'])-c['grid_difference'])<1e-14
 result={'mode':'HISTORICAL_ANALYSIS_NO_NEW_H3_SOLVE','restored_states':records,'historical_closed_norm_error':norm,'historical_closed_energy_drift_Eh':drift,'historical_free_gaussian_center_error_bohr':center,'historical_free_gaussian_covariance_error_bohr2':cov,'historical_product_dt_halved_difference':conv['product_region']['dt_difference'],'historical_product_grid_doubled_difference':conv['product_region']['grid_difference'],'CAP_original_accounting':cap,'scope':'short closed400au; reactive CAP2000au; regional convergences only. Not a global numerical error bound or independently certified reaction probability','array_identity':'Original NPZ psi and view_payload Hamiltonian used; no PES regeneration'}
 (out/'HISTORICAL_NUMERICAL_REVIEW.json').write_text(json.dumps(result,indent=2));return result
if __name__=='__main__':
 import sys
 verify(pathlib.Path(sys.argv[1]),pathlib.Path(sys.argv[2]))
