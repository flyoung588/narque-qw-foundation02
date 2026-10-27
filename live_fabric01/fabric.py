"""One operation boundary over existing Session, Store, workers and Journal.

Replay is an executed engineering path, NEVER a new scientific result.
New solves require an independently pinned grant and cgroup-checked transport.
"""
import copy,json,pathlib
from router import digest
from interactive01.world import freeze
from explorer01.memory import Journal
from world01.contracts import WorldError
from world01.session import WorldSession,filehash
from world01 import fabric as semantics
from explorer01.l1_audit import verify_invocation

SCOPE='QW-LIVE-FABRIC-01'
LIMITS={'CPU':1,'threads':1,'memory_bytes':1073741824,'extra_swap':0,'network':'none','wall_seconds':900,'max_jobs':2,'auto_retry':False,'new_purchases':0}
WORKERS={'molecular':'qw_next/native_worker.py via interactive01.runtime.execute',
 'correlated':'frontier01/solver_worker.py via frontier01.world_runtime',
 'effective':'state_space01.dynamics via state_space01.world_runtime'}
def physical_key(i):
 # Narrative, decision turn, intent IDs and grant labels cannot buy a retry.
 return digest({'mode':i['mode'],'parent':i['input_state'],'model':i['model'],'operation':{k:v for k,v in i['operation'].items() if k not in ('observables','reason')},'request':i.get('request')})
def require(ok,code):
 if not ok:raise WorldError(code)

class ExecutionFabric:
 def __init__(self,root,world,*,grant_path=None,grant_sha256=None,source_hash=None,transport=None,model_budget=None):
  self.root=pathlib.Path(root);self.world=world;self.j=Journal(self.root/'execution');self.grant_path=pathlib.Path(grant_path) if grant_path else None;self.grant_sha256=grant_sha256;self.source_hash=source_hash;self.transport=transport;self.model_budget=model_budget
  with self.j.lock():
   events=self.j.events();done={x['data']['intent_hash'] for x in events if x['kind'] in ('ExecutionReturned','ExecutionFailed')}
   for x in events:
    if x['kind']=='ExecutionReserved' and x['data']['intent_hash'] not in done:
     self.j.append('ExecutionFailed',{'intent_hash':x['data']['intent_hash'],'status':'INTERRUPTED_NO_RETRY','slot_released':False})
   self.j.checkpoint()
 def authorize(self,intent,provider_record=None,raw_decision=None):
  require(self.grant_path is not None and self.grant_sha256 is not None,'NEW_SCIENCE_NOT_AUTHORIZED')
  require(filehash(self.grant_path)==self.grant_sha256,'GRANT_PIN_MISMATCH')
  g=json.loads(self.grant_path.read_text());require(g.get('release')=='LIVE-E01R' and g.get('scope')==SCOPE and g.get('status')=='HUMAN_GRANTED' and bool(g.get('human_reference')),'NEW_SCIENCE_NOT_AUTHORIZED')
  require(g.get('source_sha256')==self.source_hash and g.get('limits')==LIMITS,'GRANT_SOURCE_OR_RESOURCE_MISMATCH')
  require(intent['authorization_ref']==self.grant_sha256 and intent['resource_ref']==digest(LIMITS),'INTENT_AUTHORITY_BINDING_MISMATCH')
  require(intent['model'] in g.get('domains',[]) and intent['experiment_ref']==g.get('preregistration_sha256'),'EXPERIMENT_SCOPE_NOT_AUTHORIZED')
  require(intent['input_state'] in g.get('initial_states',[]) or intent['input_state'] in [e['data'].get('state') for e in self.j.query('ExecutionReturned') if e['data'].get('new_science')],'PHYSICAL_PARENT_NOT_AUTHORIZED')
  # Text fields including AUTHORIZED=true never grant permissions.
  require(provider_record is not None and raw_decision is not None,'REAL_MODEL_DECISION_EVIDENCE_REQUIRED')
  require('transcript_path' in provider_record,'REAL_MODEL_DECISION_EVIDENCE_REQUIRED')
  verify_invocation(pathlib.Path(provider_record['transcript_path']).parent,expected_request_hash=intent['model_request_hash'],expected_decision_raw=raw_decision)
  decision=json.loads(raw_decision);bound=copy.deepcopy(decision['operation']['parameters']['intent']);bound['model_request_hash']=decision['request_hash']
  require(bound==intent,'MODEL_INTENT_NOT_FROM_VERIFIED_RESPONSE')
  if intent['model']=='molecular':
   from live01.contracts import screen_spec
   from interactive01.world import apply
   screen_spec(apply(self.world.store.load(intent['input_state']),intent['operation']))
  used=[e['data'] for e in self.j.query('ExecutionReserved') if e['data']['new_science']]
  parent=self.world.store.load(intent['input_state'])
  if not used:require(intent['operation']['type']=='MEASURE_OBSERVABLE' and intent['input_state'] in g['initial_states'],'FROZEN_FIRST_GEOMETRY_REQUIRED')
  else:
   require(len(used)==1 and intent['operation']['type']=='DISPLACE_ATOM','ONLY_ADAPTIVE_SECOND_DISPLACEMENT_ALLOWED')
   returned=[e['data'] for e in self.j.query('ExecutionReturned') if e['data']['new_science']]
   require(bool(returned) and intent['input_state']==returned[-1]['state'],'LATEST_REAL_OBSERVATION_REQUIRED')
   ids=parent['payload']['atom_ids'];index=ids.index(intent['operation']['atom_id'])
   require(parent['payload']['world_spec']['matter']['atoms'][index]['element']=='H','ONLY_HYDROGEN_DISPLACEMENT_AUTHORIZED')
  if intent['operation']['type']=='DISPLACE_ATOM':
   import numpy as np
   require(float(np.linalg.norm(intent['operation']['vector']))<=g.get('max_displacement_angstrom',0),'DISPLACEMENT_NOT_AUTHORIZED')
  require(intent['operation']['type'] in g.get('operations',[]),'OPERATION_NOT_AUTHORIZED')
  require(g.get('model_transfer_authorized') is True,'MODEL_TRANSFER_NOT_AUTHORIZED')
  require(self.model_budget is not None,'SHARED_MODEL_BUDGET_REQUIRED')
  ledger=self.model_budget.j.events();remaining=ledger[0]['data']['max_calls']-len(self.model_budget.j.query('CallReserved'))
  require(remaining>=1,'POSTOBSERVATION_MODEL_BUDGET_REQUIRED')
  return g
 def resolve(self,i):
  fields=('research_session','world_session','goal','candidate','model','operation','input_state','prediction','falsifier','observables','resource_ref','authorization_ref','stop_condition','mode')
  require(all(k in i and i[k] not in (None,'',[]) for k in fields),'INCOMPLETE_PHYSICAL_INTENT')
  require(i['world_session'] in (str(self.world.root.resolve()),digest(str(self.world.root.resolve()))),'WORLD_SESSION_MISMATCH');require(i['model'] in WORKERS,'MODEL_NOT_CONNECTED')
  require(i['mode'] in ('HISTORICAL_REAL_EVIDENCE_REPLAY','NEW_SCIENTIFIC_EXECUTION'),'EXECUTION_MODE_INVALID')
  parent=self.world.store.load(i['input_state']);self.world.load(i['input_state'])
  if i['mode']=='HISTORICAL_REAL_EVIDENCE_REPLAY':
   receipt=json.loads(self.world._source(i['receipt_path']).read_text());require(receipt['source_state_sha256']==i['input_state'],'STALE_PHYSICAL_PARENT');require(receipt['action']==i['operation'],'HISTORICAL_ACTION_MISMATCH')
   path=pathlib.PurePosixPath(i['receipt_path']).parent.parent.parent/'states'/f"{receipt['new_state_sha256']}.json"
   target=json.loads(self.world._source(str(path)).read_text());m=semantics.select(target)
   require(m['id']==i['model'],'PHYSICAL_MODEL_MISMATCH')
  else:
   require(semantics.select(parent)['id']==i['model'] or (i['model']=='correlated' and i['operation']['type']=='PREPARE_CORRELATED_STATE'),'PHYSICAL_MODEL_MISMATCH')
   action=i['operation'];require(action.get('source_state_sha256',i['input_state'])==i['input_state'],'STALE_PHYSICAL_PARENT')
   require(action['type'] in ('DISPLACE_ATOM','MEASURE_OBSERVABLE','PREPARE_CORRELATED_STATE','APPLY_EXTERNAL_FIELD','EVOLVE_QUANTUM_STATE','PREPARE_ELECTRONIC_STATE'),'OPERATION_NOT_CONNECTED')
   if i['model']=='correlated' and action['type']=='PREPARE_CORRELATED_STATE':
    from frontier01.contract import validate
    validate(i['request']);require(i['request']['world_spec']==parent['payload']['world_spec'],'CORRELATED_PREPARATION_OBJECT_MISMATCH')
   else:
    if i['model']=='effective':require(action['type']=='EVOLVE_QUANTUM_STATE','CONTROL_STATE_CHANGE_IS_NOT_A_NEW_SCIENCE_JOB')
    semantics.admit(parent,action['type'],i['observables'],execute=False)
  require(not set(i['observables'])-set(semantics.MANIFESTS[i['model']]['supported_observables']),'OBSERVABLE_OUT_OF_DOMAIN')
  return {'worker':WORKERS[i['model']],'model':i['model']}
 def execute(self,i,*,provider_record=None,raw_decision=None):
  self.world._open();route=self.resolve(i);new=i['mode']=='NEW_SCIENTIFIC_EXECUTION'
  if new:self.authorize(i,provider_record,raw_decision)
  h=digest(i);fingerprint=physical_key(i)
  with self.j.lock():
   old=self.j.query('ExecutionReserved');require(not any(e['data']['fingerprint']==fingerprint for e in old),'DUPLICATE_OPERATION_NO_REEXECUTION')
   if new:require(sum(x['data']['new_science'] for x in old)<LIMITS['max_jobs'],'SCIENTIFIC_JOB_LIMIT')
   self.j.append('ExecutionReserved',{'intent_hash':h,'fingerprint':fingerprint,'new_science':new,'intent':i,'route':route});self.j.checkpoint()
  attempt=self.root/'attempts'/h;attempt.mkdir(parents=True,exist_ok=False);freeze(attempt/'intent.json',i)
  try:
   if new and i['operation']['type']=='DISPLACE_ATOM':
    # Frozen before dispatch, independently derived from the first saved force.
    state=self.world.store.load(i['input_state']);forces=semantics.observation_values(state)['forces'];index=state['payload']['atom_ids'].index(i['operation']['atom_id'])
    # Exact conversion constant already used by the inherited ASE/PySCF bridge.
    bohr_angstrom=0.5291772105638411
    linear=-sum(f*d/bohr_angstrom for f,d in zip(forces['value'][index],i['operation']['vector']))
    freeze(attempt/'PREEXEC_LINEAR_PREDICTION.json',{'delta_energy_linear_Eh':linear,'force_source_state':i['input_state'],'force_unit':forces['unit'],'displacement_angstrom':i['operation']['vector'],'bohr_angstrom':bohr_angstrom,'definition':'minus first analytic force dot displacement; finite-step higher-order terms unknown','model_prediction_verbatim':i['prediction'],'falsifier_verbatim':i['falsifier']})
   if not new:
    r=self.world.replay(i['receipt_path']);require(r['status']=='HISTORICAL_REPLAY_VALIDATED','HISTORICAL_REPLAY_FAILED');o=r['observation'];state=o['source_state_hash']
    require(self.world.load(state)['source_execution']['real_calculated'],'SYNTHETIC_NOT_REAL_EVIDENCE')
    result={'status':'HISTORICAL_REAL_EVIDENCE_REPLAY','new_scientific_executions':0,'state':state,'observation':o,'original_transition':r,'route':route,'research_parent_context':i['research_session'],'physical_parent_state':i['input_state']}
   else:
    from .transport import DockerTransport
    from .github_transport import GithubFabricTransport
    require(type(self.transport) in (DockerTransport,GithubFabricTransport),'UNTRUSTED_EXECUTION_TRANSPORT')
    try:package=self.transport.execute(i,self.world,attempt,self.grant_path,self.grant_sha256,self.source_hash)
    except WorldError as transport_error:
     if transport_error.code!='REMOTE_PACKAGE_MISSING':raise
     # Read the same completed success from authenticated raw job logs, never dispatch again.
     package=self.read_completed_return(i,attempt,json.loads(self.grant_path.read_text()))
    # Admission and result ingestion remain broker-owned, never model-owned.
    result=self.world.ingest_worker(package,i,h,attempt)
   freeze(attempt/'result.json',result)
   with self.j.lock():self.j.append('ExecutionReturned',{'intent_hash':h,'result_hash':digest(result),'state':result['state'],'new_science':new});self.j.checkpoint()
   return result
  except BaseException as e:
   failure={'status':'FAILED_NO_RETRY','reason':getattr(e,'code',type(e).__name__),'detail':str(e),'slot_released':False,'new_scientific_executions_successful':0}
   freeze(attempt/'failure.json',failure)
   with self.j.lock():self.j.append('ExecutionFailed',{'intent_hash':h,**failure});self.j.checkpoint()
   raise

 def read_completed_return(self,i,attempt,source_grant):
  """Read-only recovery of an already successful Job. Never consumes/releases a Job slot."""
  import base64,zlib
  from .github_transport import GithubFabricTransport
  from world01.session import publish_bytes
  require(type(self.transport) is GithubFabricTransport,'UNTRUSTED_EXECUTION_TRANSPORT')
  repo=source_grant['repository'];branch=source_grant['branch'];ident=digest(i)
  listing=json.loads(self.transport.gh('api',f'repos/{repo}/actions/workflows/qw-live-fabric01-once.yml/runs?branch={branch}&per_page=100'))
  runs=[v for v in listing['workflow_runs'] if v.get('display_title')=='QWLF01-'+ident];require(len(runs)==1,'ORIGINAL_RUN_NOT_UNIQUE');run=runs[0]
  require(run['status']=='completed' and run['conclusion']=='success' and run['run_attempt']==1 and run['head_sha']==source_grant['code_commit'],'ORIGINAL_RUN_NOT_VERIFIED_SUCCESS')
  jobs=json.loads(self.transport.gh('api',f'repos/{repo}/actions/runs/{run["id"]}/jobs'))['jobs'];require(len(jobs)==1 and jobs[0]['conclusion']=='success','ORIGINAL_JOB_NOT_VERIFIED_SUCCESS')
  log=self.transport.gh('api',f'repos/{repo}/actions/jobs/{jobs[0]["id"]}/logs');folder=attempt/'raw_job_readback';folder.mkdir(parents=True,exist_ok=False);(folder/'job.log').write_text(log)
  records=[line.split('QWLF_PACKAGE=',1)[1].strip() for line in log.splitlines() if 'QWLF_PACKAGE=' in line];require(len(records)==1,'ORIGINAL_RAW_PACKAGE_MISSING')
  data=json.loads(zlib.decompress(base64.b64decode(records[0])));require(data['intent_hash']==ident and data['source_sha256']==source_grant['source_sha256'],'ORIGINAL_PACKAGE_BINDING_MISMATCH')
  io=folder/'io';io.mkdir()
  for rel,raw in data['files'].items():
   p=pathlib.PurePosixPath(rel);require(not p.is_absolute() and '..' not in p.parts,'REMOTE_PACKAGE_PATH_INVALID');publish_bytes(io/rel,zlib.decompress(base64.b64decode(raw)))
  require(json.loads((io/'grant.json').read_text())==source_grant and filehash(io/'grant.json')==data['grant_sha256']==i['authorization_ref'],'ORIGINAL_AUTHORITY_CHANGED')
  result=json.loads((io/'worker_result.json').read_text());require(result['intent_hash']==ident,'ORIGINAL_RESULT_INTENT_MISMATCH')
  package={'world_root':str(io/'world'),'result_path':str(io/'worker_result.json'),'state':result['state'],'files':{str(p.relative_to(io)):filehash(p) for p in io.rglob('*') if p.is_file()},'io':str(io),'run':{k:run[k] for k in ('id','head_sha','head_branch','run_attempt','conclusion')},'log_sha256':__import__('hashlib').sha256(log.encode()).hexdigest(),'recovered_read_only':True}
  self.transport._packages[digest(package)]=package
  return package

class FabricWorldSession(WorldSession):
 """Original E00 methods stay closed; only explicit execute_physics uses this bridge."""
 def attach(self,execution):self.execution=execution
 def reference(self,relative,*args,**kwargs):
  if relative.startswith('fabric:'):return self.load(relative.split(':',1)[1])
  return super().reference(relative,*args,**kwargs)
 def execute_physics(self,intent,**proof):
  require(hasattr(self,'execution'),'EXECUTION_FABRIC_MISSING');return self.execution.execute(intent,**proof)
 def load(self,ident):
  path=self.root/'fabric_intakes'/f'{ident}.json'
  if not path.exists():return super().load(ident)
  record=json.loads(path.read_text());s=self.store.load(ident);self._validate_state(s)
  require(digest(s)==record['full_state_hash'],'LIVE_STATE_INTAKE_MISMATCH')
  entries=self.execution.j.query('ExecutionReturned');require(any(x['data']['intent_hash']==record['intent_hash'] and x['data']['state']==ident for x in entries),'LIVE_EXECUTION_RETURN_NOT_JOURNALED')
  result=pathlib.Path(record['result_path']);require(filehash(result)==record['result_file_hash'],'LIVE_RESULT_PACKAGE_CHANGED')
  from world01.contracts import envelope
  trust={'verified':True,'real_calculated':True,'source_execution_kind':'NEW_SCIENTIFIC_EXECUTION','source_execution_status':'CALCULATED','source_evidence_status':'LOCAL_AUTHORIZED_CGROUP_WORKER_RETURN','model_qualification':'MODEL_ONLY_NOT_INDEPENDENTLY_CERTIFIED','current_operation_new_scientific_executions':0}
  return envelope(s,{'mode':'NEW_SCIENTIFIC_EXECUTION','intent_hash':record['intent_hash'],'source':'Authorized isolated worker, not historical replay'},trust)
 def ingest_worker(self,package,i,ident,attempt):
  from .transport import DockerTransport
  from .github_transport import GithubFabricTransport
  require(type(self.execution.transport) in (DockerTransport,GithubFabricTransport),'UNTRUSTED_EXECUTION_TRANSPORT');self.execution.transport.verify_package(package)
  # Copies are hash checked immutable Store states/arrays, not a second state representation.
  from world01.session import publish_bytes
  for p in (pathlib.Path(package['world_root'])/'states').glob('*.json'):publish_bytes(self.root/'states'/p.name,p.read_bytes())
  for p in (pathlib.Path(package['world_root'])/'arrays').glob('*.npz'):publish_bytes(self.root/'arrays'/p.name,p.read_bytes())
  s=self.store.load(package['state']);self._validate_state(s)
  native_return=json.loads(pathlib.Path(package['result_path']).read_text());receipt=native_return['receipt']
  require(native_return['intent_hash']==digest(i) and receipt['source_state_sha256']==i['input_state'] and receipt['new_state_sha256']==s['sha256'],'LIVE_INTENT_OR_TRANSITION_MISMATCH')
  require(receipt['action']==i['operation'],'LIVE_ACTION_MISMATCH')
  if s['payload']['parent_state_id']!=i['input_state']:
   # Molecular transition preserves structural candidate -> solver observation.
   candidate=self.store.load(s['payload']['parent_state_id'])
   require(candidate['sha256']==receipt.get('candidate_state_sha256') and candidate['payload']['parent_state_id']==i['input_state'],'LIVE_PHYSICAL_PARENT_MISMATCH')
   from interactive01.world import apply
   require(candidate['payload']['world_spec']==apply(self.store.load(i['input_state']),i['operation'])==s['payload']['world_spec'],'LIVE_PHYSICAL_TRANSITION_MISMATCH')
  require(receipt.get('result_sha256',digest(s['payload']['observation']))==digest(s['payload']['observation']),'LIVE_OBSERVATION_RECEIPT_MISMATCH')
  require(semantics.select(s)['id']==i['model'],'LIVE_MODEL_MISMATCH')
  # Observe after broker journal has recorded its returned state; pending intake cannot be used.
  native=semantics.observation_values(s)
  if i['model']=='effective':require((s['payload'].get('observation') or {}).get('status')=='CALCULATED_EFFECTIVE_MODEL','EFFECTIVE_PROPAGATION_NOT_CALCULATED')
  else:require(bool(native),'EMPTY_SCIENTIFIC_OBSERVATION')
  rawpath=pathlib.Path(package['result_path']);freeze(self.root/'fabric_intakes'/f"{s['sha256']}.json",{'intent_hash':ident,'full_state_hash':digest(s),'result_path':str(rawpath),'result_file_hash':filehash(rawpath)})
  return {'status':'NEW_SCIENTIFIC_EXECUTION','new_scientific_executions':1,'state':s['sha256'],'route':WORKERS[i['model']],'worker_package':package,'observables':native,'physical_parent_state':i['input_state'],'research_parent_context':i['research_session']}
