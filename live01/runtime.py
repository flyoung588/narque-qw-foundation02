import copy,json
from router import digest
from world01.contracts import WorldError,OperationRequest
from explorer01.runtime import ExplorerRuntime
from explorer01.l1_audit import verify_invocation
from .contracts import successor,require,LIMITS
class LiveExplorerRuntime(ExplorerRuntime):
 def __init__(self,*args,broker,**kwargs):
  self.broker=broker;super().__init__(*args,**kwargs)
  for e in self.j.query('LiveStateRegistered'):self.catalog[e['data']['state']]={'path':'live:'+e['data']['state'],'domain':'molecular'}
 def context(self):
  v=super().context();used=len(self.broker.j.query('JobReserved'));v['resources'].update(new_science_jobs=max(0,LIMITS['max_jobs']-used) if self.broker.grant.get('status')=='HUMAN_GRANTED_E01' else 0,scientific_jobs_consumed=used,live_grant_scope='QW-EXPLORER-E01',balance_timing='model-request count includes the current request before its reservation')
  v['rules']=['Only a source-owned Human E01 grant can authorize new science.','Past archive permissions never authorize a new Job.','Only broker-admitted molecular RHF/UHF/cc-pVDZ, bounded WorldSpec and mature operations can execute.','The model may nominate other physical domains but they are NOT executable in this live pipeline.','New Observation values are model outputs with error limits, not discoveries or materials certification.','No composition/energy-zero mismatch ranking, synthetic promotion, automatic retry or budget extension.','STOP is always allowed.']
  return v
 def record_live(self,observation):
  h=digest(observation);ident=observation['source_state_hash']
  from world01 import fabric
  require(observation['observables']==fabric.observation_values(self.world.store.load(ident)),'LIVE_OBSERVATION_CONTENT_MISMATCH')
  self.catalog[ident]={'path':'live:'+ident,'domain':'molecular'}
  self.j.append('LiveStateRegistered',{'state':ident,'observation_hash':h})
  env=self.world.load(ident);self.j.append('PhysicalEvidence',{'hash':h,'observation':observation,'state':ident,'domain':observation['model_domain'],'physical_object':env['object'],'physics_model':env['actual_model'],'evidence_role':'NEW_REMOTE_E01_OBSERVATION_NOT_ARCHIVE','numerical_quality':observation['values'],'model_limitations':observation['error_uncertainty']});return h
 def first_frozen(self,plan,receipt_verified):
  self.broker.authorize();require(receipt_verified,'INITIAL_MODEL_RECEIPT_REQUIRED')
  require(plan['world_spec']==self.broker.prereg['first_world_spec'],'INITIAL_SPEC_NOT_FROZEN')
  with self.j.lock():
   self._open();require(not self.j.query('InitialLiveAttempt'),'INITIAL_EXPERIMENT_ALREADY_ATTEMPTED');self.j.append('InitialLiveAttempt',{'plan_hash':digest(plan),'model_decision_hash':plan['model_decision_hash']});self.j.checkpoint()
  parent=self.world.create(plan['world_spec']);request=OperationRequest('MEASURE_OBSERVABLE',parent['source_state_hash'],{'model_decision_hash':plan['model_decision_hash']},('energy','forces'))
  try:o=self.world.act(request)
  except BaseException as e:
   with self.j.lock():self.j.append('Stopped',{'reason':'Initial science failure, no retry','detail':str(e)});self.j.checkpoint()
   raise
  with self.j.lock():self.record_live(o);self.j.checkpoint()
  return o
 def _execute(self,d):
  if d['operation']['name']!='PROPOSE_EXPERIMENT':return super()._execute(d)
  try:
   self.broker.authorize();source=d['operation']['source'];known=self.j.query('PhysicalEvidence');require(bool(known) and source==known[-1]['data']['state'],'STALE_PARENT')
   # The actual provider output, not a self-asserted actor flag, must bind the action.
   response=self.j.query('ModelResponse')[-1]['data'];proof=response.get('provider_record') or {};path=proof.get('transcript_path')
   require(bool(path),'AUTOMATIC_MODEL_INVOCATION_REQUIRED');verify_invocation(__import__('pathlib').Path(path).parent,expected_request_hash=d['request_hash'],expected_decision_raw=response['raw_response'])
   state=self.world.store.load(source);spec=successor(state,d['operation']['parameters'],d['action']);candidate=self.world.create(spec)
   o=self.world.act(OperationRequest('MEASURE_OBSERVABLE',candidate['source_state_hash'],{'model_decision_hash':digest(d)},('energy','forces')))
   return {'status':'COMPLETED','observation_hash':self.record_live(o),'new_state':o['source_state_hash']}
  except BaseException as e:
   self.j.append('Stopped',{'reason':'Scientific/admission failure, no automatic retry','detail':str(e)});raise
