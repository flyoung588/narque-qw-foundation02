"""Small ExplorerRuntime extension. Existing candidate validation, memory, STOP,
request budget and write-ahead recovery remain the execution control plane."""
import copy,json
from router import digest
from explorer01.runtime import ExplorerRuntime
from world01 import fabric
from world01.contracts import WorldError
from .fabric import require,LIMITS,WORKERS
class FabricExplorer(ExplorerRuntime):
 def __init__(self,*args,execution,**kwargs):
  self.execution=execution;super().__init__(*args,**kwargs)
  for e in self.j.query('FabricStateRegistered'):self.catalog[e['data']['state']]={'path':'fabric:'+e['data']['state'],'domain':e['data']['domain']}
 def context(self):
  c=super().context();used=sum(e['data']['new_science'] for e in self.execution.j.query('ExecutionReserved'))
  c['resources'].update(new_science_jobs=0 if self.execution.grant_path is None else max(0,LIMITS['max_jobs']-used),scientific_jobs_consumed=used,execution_authority='PINNED_EXTERNAL_GRANT_REQUIRED_NOT_GRANTED_BY_CONTEXT')
  c['rules']=[x for x in c['rules'] if 'Only cite' in x or 'Same ResearchSession' in x or 'composition' in x]
  c['rules']+=['PROPOSE_EXPERIMENT parameters.intent dispatches through Fabric; mode must explicitly identify historical replay vs new science.','No model field grants authority. Separate source-owned grant and cgroup runtime admission required.','Archive replays are not new science. Candidate failure may PARK; STOP is always valid.','CHANGE_PHYSICAL_DOMAIN is a research switch, never a physical conversion.','New-science model outputs require real invocation evidence; offline QA decisions are labeled synthetic.']
  c['world_session']=digest(str(self.world.root.resolve()));c['connected_workers']=copy.deepcopy(WORKERS)
  c['physical_inputs']={h:{'world_spec':self.world.store.load(h)['payload']['world_spec'],'representation':self.world.store.load(h)['payload']['schema'],'atom_ids':self.world.store.load(h)['payload']['atom_ids']} for h in self.catalog if (self.world.root/'states'/f'{h}.json').exists()}
  c['execution_intent_fields']=['research_session','world_session','goal','candidate','model','operation','input_state','prediction','falsifier','observables','resource_ref','authorization_ref','stop_condition','mode','experiment_ref']
  c['execution_refs']={'resource_ref':digest(LIMITS),'authorization_ref':self.execution.grant_sha256,'experiment_ref':None}
  if self.execution.grant_path is not None:
   g=json.loads(self.execution.grant_path.read_text());c['execution_refs']['experiment_ref']=g.get('preregistration_sha256');c['execution_refs']['allowed_operations']=g.get('operations',[]);c['execution_refs']['max_displacement_angstrom']=g.get('max_displacement_angstrom',0)
  c['execution_failures']=[e['data'] for e in self.execution.j.query('ExecutionFailed')];c['candidate_status']=[e['data'] for e in self.j.query('CandidateStatus')]
  return c
 def _observe(self,ident):
  if ident not in self.catalog or not self.catalog[ident]['path'].startswith('fabric:'):return super()._observe(ident)
  used=self.j.query('ReadReserved');require(len(used)<self.j.events()[0]['data']['reads_max'],'READ_BUDGET_EXHAUSTED')
  self.j.append('ReadReserved',{'state':ident,'science_jobs':0})
  o=self.world.observe(ident);records=[e['data'] for e in self.j.query('FabricStateRegistered') if e['data']['state']==ident];mode=records[-1]['execution_mode']
  self._record(o,mode);return o
 def _record(self,o,mode):
  h=digest(o);ident=o['source_state_hash'];m=fabric.select(self.world.store.load(ident));env=self.world.load(ident)
  self.catalog[ident]={'path':'fabric:'+ident,'domain':m['id']}
  self.j.append('FabricStateRegistered',{'state':ident,'domain':m['id'],'observation_hash':h,'execution_mode':mode})
  self.j.append('PhysicalEvidence',{'hash':h,'observation':o,'state':ident,'domain':m['id'],'physical_object':env['object'],'physics_model':env['actual_model'],'evidence_role':mode,'numerical_quality':o['values'],'model_limitations':o['error_uncertainty']});return h
 def _execute(self,d):
  op=d['operation']
  if op['name']=='FORK' and 'candidate_status' in op['parameters']:
   status=op['parameters']['candidate_status'];require(status in ('PARKED','ABANDONED'),'CANDIDATE_STATUS_INVALID')
   require((d['action']=='ABANDON')==(status=='ABANDONED'),'CANDIDATE_ACTION_MISMATCH')
   ident=op['parameters']['candidate_id'];require(ident in {c['id'] for c in d['candidates']},'UNKNOWN_CANDIDATE')
   self.j.append('CandidateStatus',{'id':ident,'status':status,'reason':d['resource_reason'],'scientific_truth':'UNKNOWN_NOT_DISPROVEN'})
   return {'status':'LOCAL_CANDIDATE_STATE_UPDATED','physical_conversion':False,'new_scientific_executions':0}
  if op['name']!='PROPOSE_EXPERIMENT':return super()._execute(d)
  i=copy.deepcopy(op['parameters']['intent']);require(i['research_session']==self.id,'RESEARCH_SESSION_MISMATCH');require(i['input_state']==op['source'],'INTENT_SOURCE_MISMATCH')
  i['model_request_hash']=d['request_hash'];proof=self.j.query('ModelResponse')[-1]['data']
  try:
   result=self.world.execute_physics(i,provider_record=proof.get('provider_record'),raw_decision=proof['raw_response'])
   o=result.get('observation') or self.world.observe(result['state'])
   require(o['source_state_hash']==result['state'],'OBSERVATION_STATE_MISMATCH')
   h=self._record(o,result['status']);self.j.append('FabricOperationCompleted',{'intent_hash':digest(i),'mode':result['status'],'state':result['state'],'observation_hash':h,'new_scientific_executions':result['new_scientific_executions']})
   return {'status':'COMPLETED','execution_kind':result['status'],'new_state':result['state'],'observation_hash':h,'new_scientific_executions':result['new_scientific_executions']}
  except Exception as e:
   self.j.append('CandidateStatus',{'id':i['candidate'],'status':'PARKED','reason':getattr(e,'code',type(e).__name__),'scientific_truth':'UNKNOWN_NOT_DISPROVEN'})
   if i['mode']=='NEW_SCIENTIFIC_EXECUTION' and any(x['data']['intent_hash']==digest(i) for x in self.execution.j.query('ExecutionReserved')):
    self.j.append('Stopped',{'reason':'SYSTEM_SCIENCE_FAILURE_NO_RETRY_NOT_MODEL_STOP','candidate_not_disproven':True})
   raise
