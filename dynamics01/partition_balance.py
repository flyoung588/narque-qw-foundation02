"""One source-bound diagnostic measurement contract, not a new propagator."""
import copy,json,pathlib,numpy as np
from router import digest
from live_fabric01.fabric import require,LIMITS
SCHEMA='PARTITION_BALANCE_STRANG_V1'
REQUEST_SHA='126229e291a2efcd612dbaeb70b10180b009198248a5b8c2e4f177d11660b827'
PARENT='2a83343f29210b4ff8af5430c64a2e1d28eb92655a9cab08e50608a6b8ea98c7'
ORIGINAL_INTENT='37fd4f87ae993f2a92fc46b14682dd4e74073b7df4c44b839747872621c8c98a'
CONTRACT={'schema':SCHEMA,'source_state':PARENT,'time_start_au':2000,'time_end_au':2200,'dt_au':0.25,'steps':800,'regions':['x>3,y<3','x<3,y>3','x<3,y<3','complement'],'measurements':['CAP_first','CAP_second','kinetic_probability_transfer','substep_populations'],'model_calls':0,'review':'LOCAL_DETERMINISTIC_AUDIT','max_new_dispatches':1,'auto_retry':False}
def validate(i,g=None,p=None):
 require(i.get('request')==CONTRACT,'DIAGNOSTIC_CONTRACT_NOT_EXACT')
 require(i.get('model')=='dynamics' and i.get('input_state')==PARENT,'DIAGNOSTIC_PARENT_MISMATCH')
 require(i.get('operation')=={'type':'EVOLVE_WAVEPACKET','source_state_sha256':PARENT,'dt_au':.25,'steps':800},'DIAGNOSTIC_OPERATION_MISMATCH')
 if p is not None:require(p['time_au']==2000 and p['model']['grid']['n']==256,'DIAGNOSTIC_DOMAIN_MISMATCH')
 if g is not None:
  require(g.get('authorization_mode')=='DIAGNOSTIC_NO_MODEL_REVIEW' and g.get('approved_request_sha256')==REQUEST_SHA and g.get('measurement_contract')==CONTRACT and g.get('model_calls')==0 and g.get('max_new_scientific_jobs')==1 and g.get('auto_retry') is False,'DIAGNOSTIC_AUTHORITY_SCOPE_MISMATCH')
  require(g.get('exact_operation')==i['operation'] and g.get('initial_states')==[PARENT],'DIAGNOSTIC_EXACT_ACTION_NOT_GRANTED')
 return True
def authorize(broker,i,g):
 p=broker.world.store.load(i['input_state'])['payload'];validate(i,g,p)
 require(i['research_session']==g.get('research_session') and i['world_session']==g.get('world_session'),'DIAGNOSTIC_SESSION_MISMATCH')
 require(i['world_session']==digest(str(broker.world.root.resolve())),'DIAGNOSTIC_WORLD_MISMATCH')
 require(broker.model_budget is not None,'EXISTING_SHARED_MODEL_LEDGER_REQUIRED')
 snapshot=broker.model_budget.snapshot();require(snapshot['ledger_sha256']==g.get('shared_budget_ledger_sha256') and snapshot['max_calls']==snapshot['used_calls']==3 and snapshot['remaining_calls']==0,'DIAGNOSTIC_MODEL_LEDGER_NOT_PRESERVED')
 events=broker.j.events();require(len(events)>=2 and events[1]['sha256']==g.get('inherited_execution_head') and any(e['kind']=='ExecutionReturned' and e['data']['intent_hash']==ORIGINAL_INTENT for e in events),'DIAGNOSTIC_REAL_INHERITED_JOURNAL_REQUIRED')
 previous=[e for e in broker.j.query('ExecutionReserved') if e['data']['intent'].get('request',{}).get('schema')==SCHEMA];require(not previous,'DIAGNOSTIC_SINGLE_ATTEMPT_CONSUMED')
 from .model import LIVE_BOUNDS,screen_live_action
 require(g.get('dynamics_bounds')==LIVE_BOUNDS,'DYNAMICS_BOUNDS_NOT_GRANTED');screen_live_action(p,i['operation'],1)
 return g
class Recorder:
 def __init__(self,axis,dx):
  x,y=np.meshgrid(axis,axis,indexing='ij');self.masks=[(x>3)&(y<3),(x<3)&(y>3),(x<3)&(y<3)];self.masks.append(~np.logical_or.reduce(self.masks));self.dx=dx;self.rows=[];self.times=[]
 def record(self,psi,middle,a,decay,dt,t):
  phi=a*psi;end=a*middle;weight=self.dx**2
  start_r=abs(psi)**2*weight;phi_r=abs(phi)**2*weight;mid_r=abs(middle)**2*weight;end_r=abs(end)**2*weight
  row=[]
  for m in self.masks:
   row.append([float(start_r[m].sum()),float(phi_r[m].sum()),float(mid_r[m].sum()),float(end_r[m].sum()),float((start_r*decay)[m].sum()),float((mid_r*decay)[m].sum()),float((mid_r-phi_r)[m].sum())])
  self.rows.append(row);self.times.append([t,t+dt])
 def export(self,io):
  io=pathlib.Path(io);r=np.asarray(self.rows);require(r.shape==(800,4,7),'DIAGNOSTIC_ROWS_INCOMPLETE');loss=r[:,:,4]+r[:,:,5];transfer=r[:,:,6];delta=r[:,:,3]-r[:,:,0];res=delta-transfer+loss
  total_delta=r[-1,:,3]-r[0,:,0];L=loss.sum(axis=0);F=transfer.sum(axis=0)
  checks={'step_closure_max':float(abs(res).max()),'cumulative_closure_max':float(abs(total_delta-F+L).max()),'kinetic_step_conservation_max':float(abs(transfer.sum(axis=1)).max()),'kinetic_cumulative_conservation':float(abs(F.sum())),'min_halfstep_loss':float(min(r[:,:,4].min(),r[:,:,5].min())),'interaction_loss':float(L[2])}
  require(all(v<=1e-10 for k,v in checks.items() if k!='min_halfstep_loss') and checks['min_halfstep_loss']>=-1e-10,'DIAGNOSTIC_BALANCE_FAILURE')
  np.savez_compressed(io/'partition_balance.npz',rows=r,times=np.asarray(self.times))
  summary={'schema':SCHEMA,'regions':['product','reactant','interaction','other'],'columns':['P_start','P_after_first','P_after_kinetic','P_end','CAP_first','CAP_second','F_kinetic'],'L':L.tolist(),'F':F.tolist(),'DeltaP':total_delta.tolist(),'checks':checks,'data_sha256':__import__('hashlib').sha256((io/'partition_balance.npz').read_bytes()).hexdigest(),'claim':'fixed Strang substep accounting, not CAP-removal counterfactual'}
  require((io/'partition_balance.npz').stat().st_size<4194304,'DIAGNOSTIC_OUTPUT_LIMIT')
  (io/'partition_balance.json').write_text(json.dumps(summary,indent=2));return summary
