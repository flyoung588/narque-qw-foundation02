"""Future one-command model→Fabric→worker→observation→model controller.
No current Human grant, image or external execution is silently supplied."""
import pathlib,json,sys
from router import digest
from world01.session import filehash
from .fabric import FabricWorldSession,ExecutionFabric,LIMITS,require,SCOPE
from .runtime import FabricExplorer
from .transport import DockerTransport

def run(root,grant_pin,transfer_pin):
 r=pathlib.Path(root).resolve();repo=r/'repo';grant=r/'LIVE_SCIENCE_AUTHORITY.json';transfer=r/'LIVE_MODEL_AUTHORITY.json'
 require(grant.is_file() and filehash(grant)==grant_pin,'LIVE_SCIENCE_GRANT_REQUIRED');g=json.loads(grant.read_text())
 require(g.get('scope')==SCOPE and g.get('status')=='HUMAN_GRANTED' and g.get('limits')==LIMITS,'LIVE_SCIENCE_GRANT_REQUIRED')
 require(transfer.is_file() and filehash(transfer)==transfer_pin,'LIVE_MODEL_TRANSFER_APPROVAL_REQUIRED');t=json.loads(transfer.read_text())
 require(t.get('scope')==SCOPE and t.get('status')=='HUMAN_GRANTED_MODEL_TRANSFER' and t.get('source_sha256')==g.get('source_sha256'),'LIVE_MODEL_TRANSFER_APPROVAL_REQUIRED')
 require(t.get('max_calls')==4 and t.get('model')=='gpt-6.1-sol' and t.get('effort')=='low' and t.get('new_purchases')==0,'MODEL_APPROVAL_ENVELOPE_MISMATCH')
 source={str(p.relative_to(repo)):filehash(p) for p in repo.rglob('*') if p.is_file() and p.suffix in ('.py','.json') and '__pycache__' not in p.parts and '.git' not in p.parts};require(digest(source)==g['source_sha256'],'SOURCE_CHANGED')
 spec=json.loads((r/'LIVE_PREREGISTRATION.json').read_text());require(filehash(r/'LIVE_PREREGISTRATION.json')==g.get('preregistration_sha256'),'PREREGISTRATION_CHANGED')
 world=FabricWorldSession(r/'live/world',repo,json.loads((r/'SOURCE_BASELINE_SHA256.json').read_text()),spec['goal'])
 if g.get('transport')=='github':
  from .github_transport import GithubFabricTransport
  transport=GithubFabricTransport(r/'live/remote',runtime_enabled=True)
 else:transport=DockerTransport(repo,g['container_image'],runtime_enabled=True)
 broker=ExecutionFabric(r/'live/broker',world,grant_path=grant,grant_sha256=grant_pin,source_hash=g['source_sha256'],transport=transport);world.attach(broker)
 parent=world.create(spec['world_spec']);ident=parent['source_state_hash'];require(ident in g['initial_states'],'INITIAL_STATE_NOT_GRANTED')
 initial_path='initial:'+ident;catalog={ident:{'path':initial_path,'domain':'molecular'}}
 # create() has already stored this structural state; explicit reference shim is local only.
 original=world.reference
 world.reference=lambda rel,*a,**k:world.load(rel.split(':',1)[1]) if rel.startswith('initial:') else original(rel,*a,**k)
 research=FabricExplorer(r/'live/research',world,catalog,spec['goal'],max_decisions=4,execution=broker)
 from explorer01.codex_invocation import CodexGateway,InvocationBudget,MODEL,EFFORT
 from .model_adapter import FabricModelAdapter
 # Gate is checked BEFORE construction of the existing external model client.
 require(t.get('human_reference') and g.get('human_reference'),'HUMAN_REFERENCE_REQUIRED')
 gateway=CodexGateway(r/'live/model_gateway',r/'model_workspace',InvocationBudget(r/'live/model_budget',4))
 try:
  gateway.admission();thread=gateway.start_thread()
  # Identity-only turn counts inside the same maximum four calls. No science question yet.
  identity_request=digest({'scope':SCOPE,'source':g['source_sha256'],'purpose':'IDENTITY_ONLY_BEFORE_SUBSTANTIVE_WORK'})
  gateway.invoke(thread,'Identity-only check. No tools or research. Return {"ready":true}.',{'type':'object','properties':{'ready':{'type':'boolean'}},'required':['ready'],'additionalProperties':False},request_hash=identity_request,observation_digest=digest([]),research_session=research.id,purpose='IDENTITY_ONLY_PRECHECK',timeout=90)
  from explorer01.l1_audit import verify_invocation
  verify_invocation(pathlib.Path(gateway.last_receipt['transcript_path']).parent,expected_request_hash=identity_request)
  adapter=FabricModelAdapter(gateway,thread,transfer,transfer_pin,g['source_sha256'],research)
  return research.run(adapter,{'model':MODEL,'effort':EFFORT,'gateway':'existing ChatGPT subscription'},max_steps=4)
 finally:gateway.close()
if __name__=='__main__':
 try:print(json.dumps(run(sys.argv[1],sys.argv[2],sys.argv[3]),ensure_ascii=False,indent=2))
 except Exception as e:print(json.dumps({'status':'NOT_EXECUTED_OR_FAILED_NO_RETRY','reason':getattr(e,'code',type(e).__name__),'detail':str(e)}));raise SystemExit(2)
