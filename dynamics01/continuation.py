"""One original Decision, separate execution authority; no model/science caller.
Preserves the stopped journal. Delegates only the first scientifically identical
operation into a new DynamicsExplorer using the existing World/Fabric ingress.
"""
import copy,json,pathlib
from router import digest
from world01.session import filehash
from explorer01.memory import Journal
from explorer01.l1_audit import verify_invocation
from live_fabric01.fabric import require,LIMITS
from .runtime import DynamicsExplorer
ALLOWED_REBIND=('research_session','world_session','authorization_ref','resource_ref')

def load_binding(root,path='CONTINUATION_BINDING.json',pin=None):
 root=pathlib.Path(root);require(path=='CONTINUATION_BINDING.json','DELEGATION_MANIFEST_PATH_INVALID');p=root/path
 require(p.is_file() and (pin is None or filehash(p)==pin),'DELEGATION_MANIFEST_PIN_MISMATCH');m=json.loads(p.read_text())
 require(m.get('mode')=='ENGINEERING_RECOVERED_CONTINUATION','DELEGATION_MODE_INVALID')
 for rel,expected in m['evidence_files'].items():
  parts=pathlib.PurePosixPath(rel);require(not parts.is_absolute() and '..' not in parts.parts,'DELEGATION_EVIDENCE_PATH_INVALID')
  require((root/rel).is_file() and filehash(root/rel)==expected,'DELEGATION_EVIDENCE_CHANGED')
 call=root/m['original_call'];raw=(call/'response.txt').read_text();d=json.loads(raw);original=copy.deepcopy(d['operation']['parameters']['intent']);original['model_request_hash']=d['request_hash']
 require(digest(original)==m['original_intent_hash'] and original==m['original_intent'],'DELEGATION_ORIGINAL_INTENT_MISMATCH')
 verify_invocation(call,expected_request_hash=original['model_request_hash'],expected_decision_raw=raw)
 research=Journal(root/'inherited/research').events();broker=Journal(root/'inherited/broker').events();budget=Journal(root/'inherited/model_budget').events()
 require(any(e['sha256']==m['original_decision_event'] and e['kind']=='DecisionAccepted' and e['data']['decision']==d for e in research),'DELEGATION_DECISION_EVENT_MISSING')
 require(any(e['sha256']==m['original_stop_event'] and e['kind']=='Stopped' and e['data']['reason']=='SYSTEM_SCIENCE_FAILURE_NO_RETRY_NOT_MODEL_STOP' for e in research),'DELEGATION_OLD_STOP_MISSING')
 require(any(e['sha256']==m['original_reservation_event'] and e['kind']=='ExecutionReserved' and e['data']['intent']==original for e in broker),'DELEGATION_OLD_RESERVATION_MISSING')
 require(any(e['sha256']==m['original_failure_event'] and e['kind']=='ExecutionFailed' and e['data']['reason']=='REMOTE_STAGED_BYTES_MISMATCH' for e in broker),'DELEGATION_OLD_FAILURE_MISSING')
 require(budget[0]['data']['max_calls']==6 and sum(e['kind']=='CallReserved' for e in budget)==2,'DELEGATION_INHERITED_MODEL_BUDGET_INVALID')
 return m,original,raw,json.loads((call/'invocation_receipt.json').read_text())

def derive_intent(original,*,research_session,world_session,grant_sha256,binding_sha256):
 result=copy.deepcopy(original);result.update(research_session=research_session,world_session=world_session,authorization_ref=grant_sha256,resource_ref=digest(LIMITS),delegation_ref=binding_sha256);return result

def validate_execution_delegation(fabric,intent,grant,provider_record,raw_decision):
 delegation=grant.get('continuation',{});require(delegation.get('mode')=='ENGINEERING_RECOVERED_CONTINUATION','EXPLICIT_CONTINUATION_AUTHORITY_REQUIRED')
 m,original,raw,receipt=load_binding(fabric.grant_path.parent,delegation.get('manifest_path'),delegation.get('manifest_sha256'))
 require(delegation.get('original_intent_hash')==m['original_intent_hash'] and delegation.get('original_response_sha256')==m['original_response_sha256'],'DELEGATION_AUTHORITY_SCOPE_MISMATCH')
 require(raw_decision==raw and provider_record==receipt,'DELEGATION_ORIGINAL_MODEL_EVIDENCE_MISMATCH')
 require(not fabric.j.query('ExecutionReserved'),'DELEGATION_FIRST_ATTEMPT_ONLY')
 expected=derive_intent(original,research_session=grant['research_session'],world_session=digest(str(fabric.world.root.resolve())),grant_sha256=fabric.grant_sha256,binding_sha256=delegation['manifest_sha256'])
 require(intent==expected and digest(intent)==digest(expected),'DELEGATION_SCIENTIFIC_FIELDS_CHANGED')
 require(fabric.model_budget.j.root.resolve()==(fabric.grant_path.parent/'live/model_budget').resolve(),'DELEGATION_BUDGET_LEDGER_PATH_MISMATCH')
 budget=fabric.model_budget.j.events();inherited=Journal(fabric.grant_path.parent/'inherited/model_budget').events()
 require(budget[:len(inherited)]==inherited and budget[0]['data']['max_calls']==6 and sum(e['kind']=='CallReserved' for e in budget)>=2,'DELEGATION_MODEL_BUDGET_RESET')
 require(grant.get('new_independent_science_tranche')=={'max_new_jobs':2,'old_reservation_preserved':1,'old_reservation_refunded':False,'old_actual_jobs':0},'EXPLICIT_NEW_JOB_BUDGET_REQUIRED')
 return {'mode':'ENGINEERING_RECOVERED_CONTINUATION','original_intent_hash':m['original_intent_hash'],'binding_sha256':delegation['manifest_sha256'],'scientific_fields_unchanged':True,'model_calls_charged_for_reuse':0,'old_STOP_preserved':True}

class ContinuationResearchSession(DynamicsExplorer):
 def __init__(self,*args,binding_root,**kwargs):
  self.binding_root=pathlib.Path(binding_root);self.binding_pin=filehash(self.binding_root/'CONTINUATION_BINDING.json');self.binding,self.original_intent,self.original_raw,self.original_provider=load_binding(self.binding_root,pin=self.binding_pin)
  super().__init__(*args,**kwargs)
  with self.j.lock():
   starts=self.j.query('ContinuationStarted')
   if starts:require(len(starts)==1 and starts[0]['data']['binding_sha256']==self.binding_pin,'CONTINUATION_BINDING_CHANGED')
   else:self.j.append('ContinuationStarted',{'mode':'ENGINEERING_RECOVERED_CONTINUATION','binding_sha256':self.binding_pin,'original_research_session':self.binding['original_research_session'],'original_decision_event':self.binding['original_decision_event'],'original_stop_event':self.binding['original_stop_event'],'old_broker_reservation_preserved':1,'model_calls_inherited':2,'execution_authority':'NOT_GRANTED_BY_SESSION_CREATION'});self.j.checkpoint()
 def context(self):
  c=super().context();c['continuation']={'mode':'ENGINEERING_RECOVERED_CONTINUATION','original_session':self.binding['original_research_session'],'original_intent_hash':self.binding['original_intent_hash'],'original_model_response_sha256':self.binding['original_response_sha256'],'original_prediction':self.original_intent['prediction'],'original_falsifier':self.original_intent['falsifier'],'old_STOP':'PRESERVED','historical_model_calls':2,'old_failed_reservation':1,'uninterrupted_execution':False};return c
 def execute_original_decision(self):
  self._open();require(not self.j.query('OriginalDecisionDelegated'),'CONTINUATION_ALREADY_ATTEMPTED_NO_RETRY')
  require(self.execution.grant_path is not None,'CONTINUATION_NEW_HUMAN_GRANT_REQUIRED')
  g=json.loads(self.execution.grant_path.read_text());i=derive_intent(self.original_intent,research_session=self.id,world_session=digest(str(self.world.root.resolve())),grant_sha256=self.execution.grant_sha256,binding_sha256=self.binding_pin)
  # All original and current authority checks precede any irreversible reservation.
  self.execution.resolve(i);self.execution.authorize(i,self.original_provider,self.original_raw)
  with self.j.lock():
   require(not self.j.query('OriginalDecisionDelegated'),'CONTINUATION_ALREADY_ATTEMPTED_NO_RETRY')
   self.j.append('OriginalDecisionDelegated',{'mode':'ENGINEERING_RECOVERED_CONTINUATION','original_intent_hash':digest(self.original_intent),'original_response_sha256':self.binding['original_response_sha256'],'derived_intent':i,'derived_intent_hash':digest(i),'changed_fields':list(ALLOWED_REBIND)+['delegation_ref'],'model_call':False,'new_model_decision':False});self.j.checkpoint()
  try:
   result=self.world.execute_physics(i,provider_record=self.original_provider,raw_decision=self.original_raw)
   o=result.get('observation') or self.world.observe(result['state']);require(o['source_state_hash']==result['state'],'OBSERVATION_STATE_MISMATCH')
   with self.j.lock():
    ref=self._record(o,result['status']);self.j.append('DelegatedOperationCompleted',{'original_intent_hash':digest(self.original_intent),'derived_intent_hash':digest(i),'state':result['state'],'observation_hash':ref,'new_scientific_executions':result['new_scientific_executions'],'automatic_observation_ingress':True});self.j.checkpoint()
   return {'status':'COMPLETED','state':result['state'],'observation_hash':ref,'mode':'ENGINEERING_RECOVERED_CONTINUATION'}
  except BaseException as e:
   with self.j.lock():self.j.append('Stopped',{'reason':'SYSTEM_SCIENCE_FAILURE_NO_RETRY_NOT_MODEL_STOP','detail':getattr(e,'code',type(e).__name__),'original_STOP_also_preserved':True});self.j.checkpoint()
   raise
