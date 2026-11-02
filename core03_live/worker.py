"""Executed only by existing resource-admitted live_fabric01.worker."""
from types import SimpleNamespace
from router import digest
from interactive01.world import freeze
from birth01.preparation import runtime_probe,resource_check
from live_fabric01.fabric import require
from .model import SCHEMA,validate_arrays,transition,observe
from .session import save
def execute(io,intent,store):
 facts=runtime_probe();resource_check(facts);require(facts['memory.swap.max']=='0','SWAP_NOT_ZERO');parent=store.load(intent['input_state']);p=parent['payload'];require(p['schema']==SCHEMA and intent['operation']['source_state_sha256']==parent['sha256'],'CORE03_WORKER_PARENT_MISMATCH');a=store.arrays(parent);validate_arrays(a,p)
 action=intent['operation'];world=SimpleNamespace(root=store.root,store=store)
 if action['type'] in ('EVOLVE_COUPLED_STATE','PULSE_AND_EVOLVE_COUPLED_STATE') and action['steps']>=2:
  # Save/reload a genuine intermediate complete state before continuing. Total
  # time/field/steps are unchanged; this is not another experiment or a retry.
  import copy,json,numpy as np
  from state_space01.state import blob
  from world01.session import filehash
  first=copy.deepcopy(action);first['steps']=action['steps']//2
  mid,fields=transition(a,p,first);ref=blob(store.root,mid);mp={'model':p['model'],**fields}
  freeze(io/'intermediate_checkpoint.json',{'arrays':ref,'state_fields':mp,'source_state_sha256':parent['sha256'],'mode':'NEW_PROPAGATION_INTERMEDIATE_NOT_HISTORICAL'})
  raw=json.loads((io/'intermediate_checkpoint.json').read_text());require(filehash(store.root/ref['path'])==ref['sha256'],'CORE03_INTERMEDIATE_CHECKPOINT_CHANGED')
  with np.load(store.root/ref['path'],allow_pickle=False) as z:restored={k:z[k].copy() for k in z.files}
  require(all(np.array_equal(mid[k],restored[k]) for k in mid),'CORE03_INTERMEDIATE_ARRAY_RESTORE_MISMATCH')
  tail={'type':'EVOLVE_COUPLED_STATE','source_state_sha256':parent['sha256'],'dt_au':action['dt_au'],'steps':action['steps']-first['steps']}
  b,fields=transition(restored,raw['state_fields'],tail)
  freeze(io/'CHECKPOINT_RESTORE_PROBE.json',{'status':'EXACT_BYTES_RESTORED_AND_CONTINUED','checkpoint_array_sha256':ref['sha256'],'checkpoint_time_au':mp['time_au'],'continued_to_au':fields['time_au'],'total_requested_steps':action['steps'],'initial_fields_and_active_pulse_restored':True,'extra_steps':0})
 else:b,fields=transition(a,p,action)
 s=save(world,b,fields,parent=parent['sha256'],provenance={'mode':'NEW_SCIENTIFIC_EXECUTION','intent_sha256':digest(intent),'resources':facts})
 out=observe(b,s['payload']);before=observe(a,p);work_delta=out['work_input_Eh']-before['work_input_Eh'];energy_delta=out['energy_Eh']-before['energy_Eh'];quality={'norm_error':abs(out['norm']-1),'work_energy_residual_Eh':energy_delta-work_delta,'original_norm_limit':1e-9,'original_work_limit_Eh':1e-5,'physical_accuracy':'NOT_CERTIFIED'}
 # Preserve computed result even on a quality failure, then fail without retry.
 receipt={'source_state_sha256':parent['sha256'],'new_state_sha256':s['sha256'],'action':intent['operation'],'action_sha256':digest(intent['operation']),'time_before_au':p['time_au'],'time_after_au':s['payload']['time_au'],'array_sha256':s['payload']['arrays']['sha256'],'result_sha256':digest(out)}
 freeze(io/'worker_result.json',{'state':s['sha256'],'intent_hash':digest(intent),'receipt':receipt,'observation':out,'quality':quality,'new_scientific_executions':1,'mode':'NEW_SCIENTIFIC_EXECUTION'})
 freeze(io/'resources_after.json',runtime_probe());require(quality['norm_error']<=1e-9 and abs(quality['work_energy_residual_Eh'])<=1e-5,'CORE03_NUMERICAL_QUALITY_FAILED_NO_RETRY')
