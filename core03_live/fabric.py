"""New model authority branch; unchanged reservations, transports and molecular gates."""
import json,copy,pathlib
from router import digest
from live_fabric01.fabric import LIMITS,SCOPE,require
from dynamics01.fabric import DynamicsExecutionFabric
from world01.session import filehash
from .model import DOMAIN,SCHEMA,OBS,validate_action,system

RELEASE='QW-LIVE-CORE03-01'
class CoupledExecutionFabric(DynamicsExecutionFabric):
 def resolve(self,i):
  if i.get('model')!=DOMAIN:return super().resolve(i)
  require(all(i.get(k) not in (None,'',[]) for k in ('research_session','world_session','goal','candidate','model','operation','input_state','prediction','falsifier','observables','resource_ref','authorization_ref','stop_condition','mode')),'INCOMPLETE_CORE03_INTENT')
  require(i['world_session']==digest(str(self.world.root.resolve())) and i['mode']=='NEW_SCIENTIFIC_EXECUTION','CORE03_SESSION_MODE_MISMATCH')
  p=self.world.store.load(i['input_state']);self.world.load(i['input_state']);require(p['payload']['schema']==SCHEMA and i['operation']['source_state_sha256']==p['sha256'],'CORE03_PARENT_INVALID');validate_action(p['payload'],i['operation']);require(not set(i['observables'])-set(OBS),'CORE03_OBSERVABLE_OUT_OF_DOMAIN')
  return {'model':DOMAIN,'worker':'core03_live.worker.execute'}
 def authorize(self,i,provider_record=None,raw_decision=None):
  if i.get('model')!=DOMAIN:return super().authorize(i,provider_record,raw_decision)
  require(self.grant_path is not None and self.grant_sha256 is not None,'NEW_CORE03_EXECUTION_AUTHORIZATION_REQUIRED')
  require(filehash(self.grant_path)==self.grant_sha256,'GRANT_PIN_MISMATCH');g=json.loads(self.grant_path.read_text())
  require(g.get('release')==RELEASE and g.get('status')=='HUMAN_GRANTED' and g.get('human_reference') and g.get('scope')==SCOPE,'NEW_CORE03_EXECUTION_AUTHORIZATION_REQUIRED')
  require(g.get('source_sha256')==self.source_hash and g.get('limits')==LIMITS and g.get('domains')==[DOMAIN],'CORE03_SOURCE_OR_DOMAIN_MISMATCH')
  require(i['authorization_ref']==self.grant_sha256 and i['resource_ref']==digest(LIMITS) and i['experiment_ref']==g['preregistration_sha256'] and i['research_session']==g['research_session'],'CORE03_SCOPE_MISMATCH')
  returned=[e['data']['state'] for e in self.j.query('ExecutionReturned') if e['data']['new_science']];require(i['input_state'] in g.get('initial_states',[])+returned,'CORE03_PARENT_NOT_GRANTED')
  # This task permits a B-Work engineering experiment. It is not a gateway model trial.
  if g.get('decision_mode')=='BWORK_FROZEN_ENGINEERING':
   require(i['operation'] in g.get('frozen_operations',[]),'CORE03_OPERATION_NOT_GRANTED')
   require(g.get('frozen_decision_sha256') and i.get('decision_ref')==g['frozen_decision_sha256'],'CORE03_FROZEN_DECISION_MISSING')
  elif g.get('decision_mode')=='REAL_GATEWAY_MODEL':
   require(i['operation']['type'] in g.get('operations',[]) and g.get('original_domain_sha256')==digest(system().allowed()),'CORE03_MODEL_CONTROL_DOMAIN_NOT_GRANTED')
   require(provider_record and raw_decision and self.model_budget,'CORE03_REAL_MODEL_EVIDENCE_REQUIRED')
   from explorer01.l1_audit import verify_invocation
   d=json.loads(raw_decision);bound=copy.deepcopy(d['operation']['parameters']['intent']);bound['model_request_hash']=d['request_hash'];require(bound==i,'MODEL_INTENT_MISMATCH');verify_invocation(pathlib.Path(provider_record['transcript_path']).parent,expected_request_hash=i['model_request_hash'],expected_decision_raw=raw_decision)
   events=self.model_budget.j.events();require(events[0]['data']['max_calls']-len(self.model_budget.j.query('CallReserved'))>=1,'POSTOBSERVATION_MODEL_BUDGET_REQUIRED')
  else:require(False,'CORE03_DECISION_MODE_NOT_GRANTED')
  require(len(self.j.query('ExecutionReserved'))<g.get('max_new_jobs',0)<=2,'CORE03_JOB_BUDGET_EXHAUSTED')
  return g
