"""Dynamics branch of existing ExecutionFabric. Shared reservation/recovery journal.
Offline entry denies all new science. Future enabling requires source-bound gate,
real model invocation and a supported, resource-admitted isolated transport.
"""
import copy,json,pathlib
from router import digest
from interactive01.world import freeze
from world01.session import publish_bytes,filehash
from live_fabric01.fabric import ExecutionFabric,require,LIMITS,SCOPE
from .model import SCHEMA,validate_operation,OBS
from .adapter import is_dynamic
class DynamicsExecutionFabric(ExecutionFabric):
 def resolve(self,i):
  if i.get('model')!='dynamics':return super().resolve(i)
  require(all(i.get(k) not in (None,'',[]) for k in ('research_session','world_session','goal','candidate','model','operation','input_state','prediction','falsifier','observables','resource_ref','authorization_ref','stop_condition','mode')),'INCOMPLETE_PHYSICAL_INTENT');require(i['world_session'] in (str(self.world.root.resolve()),digest(str(self.world.root.resolve()))),'WORLD_SESSION_MISMATCH')
  parent=self.world.store.load(i['input_state']);self.world.load(i['input_state']);require(is_dynamic(parent),'DYNAMIC_PARENT_REQUIRED');require(i['operation']['source_state_sha256']==parent['sha256'],'STALE_PHYSICAL_PARENT');validate_operation(parent['payload'],i['operation']);require(not set(i['observables'])-set(OBS),'OBSERVABLE_OUT_OF_DOMAIN')
  require(i['mode']=='NEW_SCIENTIFIC_EXECUTION','USE_HASH_PINNED_HISTORY_IMPORT_NOT_SYNTHETIC_EXECUTION');return {'model':'dynamics','worker':'dynamics01.worker.execute'}
 def authorize(self,i,provider_record=None,raw_decision=None):
  if i.get('model')!='dynamics':return super().authorize(i,provider_record,raw_decision)
  require(self.grant_path is not None and self.grant_sha256 is not None,'NEW_DYNAMICS_EXECUTION_AUTHORIZATION_REQUIRED');require(filehash(self.grant_path)==self.grant_sha256,'GRANT_PIN_MISMATCH');g=json.loads(self.grant_path.read_text());require(g.get('release')=='QW-DYNAMICS-01' and g.get('status')=='HUMAN_GRANTED' and g.get('human_reference') and g.get('scope')==SCOPE,'NEW_DYNAMICS_EXECUTION_AUTHORIZATION_REQUIRED');require(g.get('source_sha256')==self.source_hash and g.get('limits')==LIMITS,'SOURCE_RESOURCE_BINDING_MISMATCH');require(i['authorization_ref']==self.grant_sha256 and i['resource_ref']==digest(LIMITS) and i['experiment_ref']==g['preregistration_sha256'],'INTENT_SCOPE_MISMATCH');require(i['operation']['type'] in g['operations'],'DYNAMICS_ACTION_NOT_GRANTED')
  require(provider_record and raw_decision and self.model_budget,'REAL_MODEL_AND_SHARED_BUDGET_REQUIRED')
  from explorer01.l1_audit import verify_invocation
  if provider_record.get('source')=='OPENCLAW_AGENT_RAW_RECORDS':
   from explorer01.openclaw_evidence import verify_openclaw,CONTRACT
   require(g.get('model_evidence_contract')==CONTRACT,'OPENCLAW_EVIDENCE_CONTRACT_NOT_GRANTED')
   require(g.get('max_new_scientific_jobs')==1 and not any(e['data']['new_science'] for e in self.j.query('ExecutionReserved')),'OPENCLAW_SINGLE_EXECUTION_ONLY')
   require(g.get('exact_operation')==i['operation'],'OPENCLAW_EXACT_OPERATION_NOT_GRANTED')
   proof=verify_openclaw(provider_record['records_path'],g['model_evidence_pins'],i,bindings=g.get('model_intent_bindings'),grant_sha256=self.grant_sha256)
   require(json.loads(raw_decision)==proof['decision_original'],'OPENCLAW_RAW_DECISION_MISMATCH')
   require(hasattr(self.model_budget,'snapshot'),'EXISTING_XREM_BUDGET_VIEW_REQUIRED')
   snapshot=self.model_budget.snapshot()
   require(g.get('shared_budget_ledger_sha256')==snapshot['ledger_sha256'],'SHARED_BUDGET_BINDING_MISMATCH')
  else:
   d=json.loads(raw_decision);bound=copy.deepcopy(d['operation']['parameters']['intent']);bound['model_request_hash']=d['request_hash']
   if bound==i:
    verify_invocation(pathlib.Path(provider_record['transcript_path']).parent,expected_request_hash=i['model_request_hash'],expected_decision_raw=raw_decision)
   else:
    require(i.get('delegation_ref') and g.get('continuation'),'MODEL_INTENT_MISMATCH')
    from .continuation import validate_execution_delegation
    validate_execution_delegation(self,i,g,provider_record,raw_decision)
  require(i['research_session']==g['research_session'] and i['world_session']==digest(str(self.world.root.resolve())),'SESSION_SCOPE_MISMATCH')
  returned=[e['data']['state'] for e in self.j.query('ExecutionReturned') if e['data']['new_science']];require(i['input_state'] in g.get('initial_states',[])+returned,'UNAUTHORIZED_PHYSICAL_PARENT')
  from .model import LIVE_BOUNDS,screen_live_action
  require(g.get('dynamics_bounds')==LIVE_BOUNDS,'DYNAMICS_BOUNDS_NOT_GRANTED');used=sum(e['data']['new_science'] for e in self.j.query('ExecutionReserved'));screen_live_action(self.world.store.load(i['input_state'])['payload'],i['operation'],used)
  if used:require(bool(returned) and i['input_state']==returned[-1],'LATEST_DYNAMIC_OBSERVATION_REQUIRED')
  es=self.model_budget.j.events();require(es[0]['data']['max_calls']-len(self.model_budget.j.query('CallReserved'))>=1,'POSTOBSERVATION_MODEL_BUDGET_REQUIRED');return g
