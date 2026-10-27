"""Actual future controller. Default gate closes BEFORE model or science access."""
import pathlib,json,sys,hashlib
from router import digest
from explorer01.codex_invocation import CodexGateway,InvocationBudget,MODEL,EFFORT
from explorer01.l1_audit import verify_invocation
from .contracts import admission
from .broker import LiveBroker
from .session import LiveWorldSession
from .runtime import LiveExplorerRuntime
from .model_adapter import LiveModelAdapter
from .transport import GithubTransport

def run(root):
 r=pathlib.Path(root).resolve();grant=json.loads((r/'HUMAN_EXECUTION_AUTHORITY.json').read_text());prereg=json.loads((r/'SCIENTIFIC_PREREGISTRATION.json').read_text());review=json.loads((r/'L1_INDEPENDENT_ACCEPTANCE.json').read_text());source_hash=hashlib.sha256((r/'EXECUTION_SOURCE_SHA256.json').read_bytes()).hexdigest()
 admission(grant,prereg,review,source_hash)
 for name,h in json.loads((r/'EXECUTION_SOURCE_SHA256.json').read_text()).items():
  if hashlib.sha256((r/name).read_bytes()).hexdigest()!=h:raise __import__('world01.contracts',fromlist=['WorldError']).WorldError('EXECUTION_SOURCE_CHANGED')
 if grant.get('model_io_authorized') is not True:raise __import__('world01.contracts',fromlist=['WorldError']).WorldError('LIVE_MODEL_DATA_TRANSFER_NOT_AUTHORIZED')
 attempt=r/'LIVE_CONTROLLER_ATTEMPT';attempt.mkdir(exist_ok=False)
 plan=json.loads((r/'INITIAL_MODEL_PLAN.json').read_text());proof=pathlib.Path(plan['invocation_receipt_path']).parent;verify_invocation(proof,expected_request_hash=plan['request_hash'])
 body=json.loads((proof/'response.txt').read_text());assert json.loads(body['world_spec_json'])==prereg['first_world_spec'];assert hashlib.sha256((proof/'invocation_receipt.json').read_bytes()).hexdigest()==prereg['initial_model_receipt_sha256']
 broker=LiveBroker(r/'live_run/science',grant,prereg,review,source_hash,GithubTransport(r/'live_run/remote_logs'))
 man=json.loads((r/'SOURCE_BASELINE_SHA256.json').read_text());world=LiveWorldSession(r/'live_run/world',r/'repo',man,'E01 admitted new observations',broker=broker)
 runtime=LiveExplorerRuntime(r/'live_run/research',world,{},prereg['research_goal'],max_decisions=4,max_reads=6,wall_seconds=3600,broker=broker)
 g=None
 try:
  runtime.first_frozen({'world_spec':prereg['first_world_spec'],'model_decision_hash':digest(body)},receipt_verified=True)
  g=CodexGateway(r/'execution_model_gateway',r/'model_workspace',InvocationBudget(r/'execution_model_budget',4))
  old=json.loads((proof/'invocation_receipt.json').read_text());assert all(x['model']==MODEL and x['effort']==EFFORT for x in old['persisted_turn_context'])
  t=g.rpc('thread/resume',{'threadId':old['thread_id'],'model':MODEL,'modelProvider':'openai','config':{'model_reasoning_effort':EFFORT},'cwd':str(r/'model_workspace'),'approvalPolicy':'never','sandbox':'read-only'});assert t['model']==MODEL and t['reasoningEffort']==EFFORT
  result=runtime.run(LiveModelAdapter(g,t,prereg),{'provider':'official Codex OpenAI gateway','model':MODEL,'effort':EFFORT},max_steps=4)
  (r/'LIVE_CONTROLLER_RESULT.json').write_text(json.dumps({'status':'COMPLETED_OR_BOUNDED_STOP','results':result,'scientific_jobs':len(broker.j.query('JobReserved')),'novelty':'NOT_PROVEN'},indent=2));return result
 finally:
  if g:g.close()
if __name__=='__main__':
 try:run(sys.argv[1])
 except Exception as e:print(json.dumps({'status':'E01_NOT_EXECUTED_OR_STOPPED','reason_code':getattr(e,'code',type(e).__name__),'detail':str(e)}));sys.exit(2)
