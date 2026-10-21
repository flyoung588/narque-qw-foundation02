"""Same frozen HF request, no process DATA cap, total cgroup protection retained."""
import json,pathlib
from router import digest,save
from recovery02r.isolated_router import run_isolated
def execute(out):
 out=pathlib.Path(out);request=json.loads((pathlib.Path(__file__).parents[1]/'recovery02r/request.json').read_text());prior=request['prior_observation'];decision=request['decision']
 assert digest(prior)==decision['based_on_observation_sha256']
 save(out/'frozen_request.json',request)
 actual=run_isolated(decision['worldspec'],out/'pyscf',timeout=90,worker_path=pathlib.Path(__file__).with_name('native_worker.py'))
 save(out/'ACTUAL_RETURN.json',actual)
 if actual['status']!='CALCULATED':raise RuntimeError('FROZEN_EXPERIMENT_FAILED_NO_REPAIR_OR_RERUN')
 v=actual['observation'];p=prior['observation'];delta=v['energy_Eh']-p['energy_Eh']
 save(out/'NUMERIC_COMPARISON.json',{'old_energy_Eh':p['energy_Eh'],'new_energy_Eh':v['energy_Eh'],'delta_energy_Eh':delta,'frozen_tangent_prediction_Eh':decision['linear_tangent_prediction_Eh'],'nonlinear_remainder_Eh':delta-decision['linear_tangent_prediction_Eh'],'old_forces_Eh_per_bohr':p['forces_Eh_per_bohr'],'new_forces_Eh_per_bohr':v['forces_Eh_per_bohr'],'prediction_supported':delta< -1e-6,'meaning':'same composition/charge/spin/RHF/cc-pVDZ, not discovery or stability; actual AI analysis follows after this numeric receipt'})
