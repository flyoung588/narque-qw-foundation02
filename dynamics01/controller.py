"""Prepared gated entry over the EXISTING gateway, budget, broker and Explorer.
No invocation occurs unless separately pinned science/model grants are present.
"""
import pathlib,json
from router import digest
from world01.session import filehash
from live_fabric01.fabric import require,LIMITS,SCOPE
from .offline import setup
from .adapter import DynamicsWorldSession
from .fabric import DynamicsExecutionFabric
from .runtime import DynamicsExplorer

def run(root,grant_pin,transfer_pin):
 r=pathlib.Path(root).resolve();repo=r/'repo';gp=r/'LIVE_SCIENCE_AUTHORITY.json';mp=r/'LIVE_MODEL_AUTHORITY.json'
 require(gp.is_file() and filehash(gp)==grant_pin,'NEW_DYNAMICS_EXECUTION_AUTHORIZATION_REQUIRED');g=json.loads(gp.read_text());require(g.get('release')=='QW-DYNAMICS-01' and g.get('status')=='HUMAN_GRANTED' and g.get('limits')==LIMITS and g.get('scope')==SCOPE and g.get('human_reference'),'NEW_DYNAMICS_EXECUTION_AUTHORIZATION_REQUIRED')
 require(mp.is_file() and filehash(mp)==transfer_pin,'NEW_DYNAMICS_MODEL_AUTHORIZATION_REQUIRED');m=json.loads(mp.read_text());require(m.get('release')=='QW-DYNAMICS-01' and m.get('status')=='HUMAN_GRANTED_MODEL_TRANSFER' and m.get('max_calls')==6 and m.get('model')=='gpt-6.1-sol' and m.get('effort')=='low' and m.get('human_reference') and m.get('source_sha256')==g.get('source_sha256'),'NEW_DYNAMICS_MODEL_AUTHORIZATION_REQUIRED')
 source={str(p.relative_to(repo)):filehash(p) for p in repo.rglob('*') if p.is_file() and p.suffix in ('.py','.json','.f90','.npz') and '__pycache__' not in p.parts and '.git' not in p.parts};require(digest(source)==g['source_sha256'],'SOURCE_CHANGED');pr=json.loads((r/'LIVE_PREREGISTRATION.json').read_text());require(filehash(r/'LIVE_PREREGISTRATION.json')==g['preregistration_sha256'],'PREREGISTRATION_CHANGED')
 # Initial state is an explicitly pinned real Core output. No hidden regeneration.
 man=json.loads((r/'CORE_HISTORY_SOURCE.json').read_text());w=DynamicsWorldSession(r/'live/world',r/'history',man,pr['goal']);states=w.import_core_history(view_path='results/view_payload.json',trajectory_path='results/experiment-0.6.json',state_path='results/experiment-0.6-state.npz')
 initial=states['initial'];require(g['initial_states']==[initial],'INITIAL_STATE_NOT_GRANTED')
 from explorer01.codex_invocation import InvocationBudget,CodexGateway,MODEL,EFFORT
 from live_fabric01.transport import DockerTransport
 from live_fabric01.github_transport import GithubFabricTransport
 budget=InvocationBudget(r/'live/model_budget',6);transport=GithubFabricTransport(r/'live/remote',runtime_enabled=True) if g.get('transport')=='github' else DockerTransport(repo,g['container_image'],runtime_enabled=True)
 b=DynamicsExecutionFabric(r/'live/broker',w,grant_path=gp,grant_sha256=grant_pin,source_hash=g['source_sha256'],transport=transport,model_budget=budget);w.attach(b);cat={initial:{'path':'dynamics:'+initial,'domain':'dynamics'}}
 research=DynamicsExplorer(r/'live/research',w,cat,pr['goal'],max_decisions=5,execution=b,model_budget=budget);require(g['research_session']==research.id,'RESEARCH_SESSION_NOT_GRANTED')
 from .decision import DynamicsModelAdapter
 gateway=CodexGateway(r/'live/model_gateway',r/'model_workspace',budget)
 try:
  gateway.admission();thread=gateway.start_thread();h=digest({'scope':'QW-DYNAMICS-01','source':g['source_sha256'],'purpose':'IDENTITY_ONLY'})
  gateway.invoke(thread,'Identity-only check. No tools or research. Return {"ready":true}.',{'type':'object','properties':{'ready':{'type':'boolean'}},'required':['ready'],'additionalProperties':False},request_hash=h,observation_digest=digest([]),research_session=research.id,purpose='IDENTITY_ONLY_PRECHECK',timeout=90)
  from explorer01.l1_audit import verify_invocation
  verify_invocation(pathlib.Path(gateway.last_receipt['transcript_path']).parent,expected_request_hash=h)
  a=DynamicsModelAdapter(gateway,thread,mp,transfer_pin,g['source_sha256'],research);return research.run(a,{'model':MODEL,'effort':EFFORT,'gateway':'existing ChatGPT subscription'},max_steps=5)
 finally:gateway.close()
if __name__=='__main__':
 import sys
 print(json.dumps(run(sys.argv[1],sys.argv[2],sys.argv[3]),indent=2))
