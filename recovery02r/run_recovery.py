"""One feedback-selected WorldSpec, only the selected available engine; no optimizer."""
import json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from router import digest,save,physical_key
from recovery02r.isolated_router import run_isolated
def execute(request,out):
 out=pathlib.Path(out);prior=request['prior_observation'];decision=request['decision'];spec=decision['worldspec']
 assert prior['status']=='CALCULATED' and digest(prior)==decision['based_on_observation_sha256']
 assert decision['action']=='compute' and decision['analysis_after_observation'] and decision['prediction']
 assert spec['physics']['engine']=='pyscf' and physical_key(spec)!=physical_key(prior['spec'])
 save(out/'frozen_request.json',request)
 actual=run_isolated(spec,out/'pyscf',timeout=60);save(out/'ACTUAL_RETURN.json',actual)
 if actual['status']!='CALCULATED':return {'status':'UNVERIFIED','no_retry':True}
 a=physical_key(prior['spec']);b=physical_key(spec)
 atoms_a=a['matter'].pop('atoms');atoms_b=b['matter'].pop('atoms')
 assert a==b and [x['element'] for x in atoms_a]==[x['element'] for x in atoms_b]
 v=actual['observation'];v0=prior['observation']
 delta=v['energy_Eh']-v0['energy_Eh'];linear=decision['linear_tangent_prediction_Eh']
 comparison={'status':'SAME_MODEL_COMPOSITION_GEOMETRY_COMPARISON','old_energy_Eh':v0['energy_Eh'],'new_energy_Eh':v['energy_Eh'],'delta_energy_Eh':delta,'linear_tangent_prediction_Eh':linear,'finite_displacement_minus_tangent_Eh':delta-linear,'energy_lower_by_more_than_1e_6_Eh':delta< -1e-6,'old_forces_Eh_per_bohr':v0['forces_Eh_per_bohr'],'new_forces_Eh_per_bohr':v['forces_Eh_per_bohr'],'model_precision':'NOT_INDEPENDENTLY_CERTIFIED','meaning':'numeric comparison for AI post-run interpretation, not automatic W3 or stability certification'}
 save(out/'COMPARISON.json',comparison);return comparison
if __name__=='__main__':print(json.dumps(execute(json.loads(pathlib.Path(sys.argv[1]).read_text()),sys.argv[2]),indent=2))
