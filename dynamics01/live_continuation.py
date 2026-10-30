"""Source-pinned gated host entry. Never invoked by preparation or tests.
Original first scientific choice is delegated, not requested from a new model.
"""
import pathlib,json,copy
from router import digest
from world01.session import filehash
from live_fabric01.fabric import LIMITS,SCOPE,require
from live_fabric01.github_transport import GithubFabricTransport
from explorer01.codex_invocation import InvocationBudget,CodexGateway
from explorer01.l1_audit import verify_invocation
from .adapter import DynamicsWorldSession
from .fabric import DynamicsExecutionFabric
from .continuation import ContinuationResearchSession,load_binding
from .decision import DynamicsModelAdapter

def run(root,grant_pin,model_pin):
 r=pathlib.Path(root).resolve();gp=r/'LIVE_SCIENCE_AUTHORITY.json';mp=r/'LIVE_MODEL_AUTHORITY.json'
 require(gp.is_file() and filehash(gp)==grant_pin,'CONTINUATION_SCIENCE_GRANT_PIN_REQUIRED');g=json.loads(gp.read_text());require(g.get('status')=='HUMAN_GRANTED' and g.get('human_reference') and g.get('release')=='QW-DYNAMICS-01' and g.get('scope')==SCOPE and g.get('limits')==LIMITS,'NEW_CONTINUATION_HUMAN_AUTHORITY_REQUIRED')
 require(mp.is_file() and filehash(mp)==model_pin,'CONTINUATION_MODEL_GRANT_PIN_REQUIRED');m=json.loads(mp.read_text());require(m.get('status')=='HUMAN_GRANTED_MODEL_TRANSFER' and m.get('human_reference')==g['human_reference'] and m.get('source_sha256')==g.get('source_sha256') and m.get('model')=='gpt-6.1-sol' and m.get('effort')=='low' and m.get('max_calls')==6 and m.get('max_new_calls')==4 and m.get('new_purchases')==0,'CONTINUATION_MODEL_AUTHORITY_REQUIRED')
 require(g.get('zero_additional_cost_verified') is True and g.get('cost_evidence_ref'),'CURRENT_FREE_RUNNER_COST_EVIDENCE_REQUIRED')
 source={str(p.relative_to(r/'repo')):filehash(p) for p in (r/'repo').rglob('*') if p.is_file() and p.suffix in ('.py','.json','.f90','.npz') and '__pycache__' not in p.parts and '.git' not in p.parts};require(digest(source)==g['source_sha256'],'SOURCE_CHANGED')
 pr=json.loads((r/'LIVE_PREREGISTRATION.json').read_text());require(filehash(r/'LIVE_PREREGISTRATION.json')==g['preregistration_sha256']=='4c040e7ba961dc91ee69f0be10e54d1b13e892937f13c1966415f780d83eb69a','PREREGISTRATION_CHANGED')
 man={'local_base':'CORE01_PINNED_ORIGINAL_OUTPUTS_20261017','files':{str(p.relative_to(r/'history')):filehash(p) for p in (r/'history').rglob('*') if p.is_file()}};w=DynamicsWorldSession(r/'live/world',r/'history',man,pr['goal']);states=w.import_core_history(view_path='results/view_payload.json',trajectory_path='results/experiment-0.6.json',state_path='results/experiment-0.6-state.npz');initial=states['initial']
 budget=InvocationBudget(r/'live/model_budget',6);transport=GithubFabricTransport(r/'live/remote',runtime_enabled=True);b=DynamicsExecutionFabric(r/'live/broker',w,grant_path=gp,grant_sha256=grant_pin,source_hash=g['source_sha256'],transport=transport,model_budget=budget);w.attach(b)
 research=ContinuationResearchSession(r/'live/research',w,{initial:{'path':'dynamics:'+initial,'domain':'dynamics'}},pr['goal'],max_decisions=3,execution=b,model_budget=budget,binding_root=r);require(research.id==g['research_session'],'CONTINUATION_SESSION_NOT_GRANTED');require(not research.j.query('OriginalDecisionDelegated') and not b.j.query('ExecutionReserved'),'NO_AUTOMATIC_CONTINUATION_RETRY')
 if not research.j.query('PhysicalEvidence'):research.seed(initial)
 (r/'model_workspace').mkdir(exist_ok=True);gateway=CodexGateway(r/'live/model_gateway',r/'model_workspace',budget);outcomes=[]
 try:
  gateway.admission();thread=gateway.start_thread();h=digest({'purpose':'CONTINUATION_IDENTITY_ONLY','source':g['source_sha256'],'session':research.id})
  from .scan import secret_scan
  prompt='Identity only. No tools or research. Return {"ready":true}.';schema={'type':'object','properties':{'ready':{'type':'boolean'}},'required':['ready'],'additionalProperties':False};secret_scan(prompt);secret_scan(schema)
  (r/'IDENTITY_OUTBOUND_PREFLIGHT.json').write_text(json.dumps({'status':'PASS','request_hash':h,'model':'gpt-6.1-sol','effort':'low','purpose':'IDENTITY_ONLY'},indent=2))
  raw=gateway.invoke(thread,prompt,schema,request_hash=h,observation_digest=digest([]),research_session=research.id,purpose='CONTINUATION_IDENTITY_INCLUDED_IN_CUMULATIVE_SIX',timeout=90);verify_invocation(pathlib.Path(gateway.last_receipt['transcript_path']).parent,expected_request_hash=h);require(json.loads(raw).get('ready') is True,'MODEL_IDENTITY_NOT_READY')
  first=research.execute_original_decision();outcomes.append(first)
  # Stage only actual authenticated first-return bytes, never a second condition.
  from .stage_successor import stage
  g=stage(r,w,first['state'],g,transport);gp.write_text(json.dumps(g,indent=2));b.grant_sha256=filehash(gp);b.source_hash=g['source_sha256'];m['source_sha256']=g['source_sha256'];mp.write_text(json.dumps(m,indent=2));(r/'SECOND_JOB_GRANT.json').write_bytes(gp.read_bytes())
  adapter=DynamicsModelAdapter(gateway,thread,mp,filehash(mp),g['source_sha256'],research)
  for _ in range(3):
   out=research.run_one(adapter,{'model':'gpt-6.1-sol','effort':'low','gateway':'existing ChatGPT subscription'});outcomes.append(out);(r/'LIVE_OUTCOMES.json').write_text(json.dumps(outcomes,indent=2))
   if out['status'] in ('STOPPED','MODEL_TRANSPORT_FAILED','MODEL_RESPONSE_PENDING') or research.j.query('Stopped'):break
  if not research.j.query('Stopped'):
   with research.j.lock():research.j.append('Stopped',{'reason':'AUTHORIZED_BOUND_REACHED_NO_AUTOMATIC_SUCCESSOR','model_STOP':False});research.j.checkpoint()
 except BaseException as e:
  (r/'LIVE_FAILURE.json').write_text(json.dumps({'code':getattr(e,'code',type(e).__name__),'detail':str(e),'automatic_retry':False},indent=2));raise
 finally:
  gateway.close();(r/'LIVE_COUNTS.json').write_text(json.dumps({'cumulative_model_calls':len(budget.j.query('CallReserved')),'historical_model_calls':2,'new_job_reservations':len(b.j.query('ExecutionReserved')),'old_reservation_preserved':1,'verified_returns':len(b.j.query('ExecutionReturned')),'recovery_mode':'ENGINEERING_RECOVERED_CONTINUATION'},indent=2))
 return outcomes
if __name__=='__main__':
 import sys
 print(json.dumps(run(sys.argv[1],sys.argv[2],sys.argv[3]),indent=2))
