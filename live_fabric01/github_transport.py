"""Reuse existing authenticated GH command/log transport; different scope,
workers and output format. This module is prepared, not remotely executed."""
import pathlib,json,base64,zlib,time,hashlib,subprocess
from live01.transport import GithubTransport
from world01.session import filehash,publish_bytes
from router import digest
from .fabric import require,SCOPE,LIMITS
class GithubFabricTransport(GithubTransport):
 def __init__(self,root,*,runtime_enabled=False):super().__init__(root,timeout=950);self.enabled=runtime_enabled;self._packages={}
 def execute(self,intent,world,attempt,grant_path,grant_sha,source_sha):
  require(self.enabled,'RUNTIME_TRANSPORT_DISABLED');g=json.loads(pathlib.Path(grant_path).read_text())
  require(g.get('status')=='HUMAN_GRANTED' and g.get('scope')==SCOPE and g.get('zero_additional_cost_verified') is True and bool(g.get('cost_evidence_ref')),'REMOTE_COST_OR_AUTHORITY_UNCONFIRMED')
  repo=g['repository'];branch=g['branch'];wf='qw-dynamics01-once.yml' if intent['model']=='dynamics' else 'qw-live-fabric01-once.yml'
  meta=json.loads(self.gh('api',f'repos/{repo}'));require(meta.get('private') is False and not meta.get('disabled'),'PUBLIC_STANDARD_RUNNER_REQUIRED')
  ref=json.loads(self.gh('api',f'repos/{repo}/git/ref/heads/{branch}'));require(ref['object']['sha']==g['code_commit'],'FROZEN_REMOTE_COMMIT_MISMATCH')
  # Send only immutable current states/arrays required by this Session, never credentials.
  files={str(p.relative_to(world.root)):base64.b64encode(zlib.compress(p.read_bytes())).decode() for folder,glob in [('states','*.json'),('arrays','*.npz')] for p in (world.root/folder).glob(glob)}
  references={}
  if intent['model']=='dynamics':
   from dynamics01.transfer import staged_references
   references=staged_references(world,intent['input_state'],g);files={}
  payload={'intent':intent,'grant':g,'grant_file_b64':base64.b64encode(pathlib.Path(grant_path).read_bytes()).decode(),'grant_sha256':grant_sha,'source_sha256':source_sha,'world_files':files,'world_references':references}
  ident=digest(intent);encoded=base64.b64encode(zlib.compress(json.dumps(payload).encode())).decode();require(len(encoded)<50000,'REMOTE_INPUT_TOO_LARGE')
  history=json.loads(self.gh('api',f'repos/{repo}/actions/workflows/{wf}/runs?branch={branch}&per_page=100'))
  require(history.get('total_count',101)<=100,'REMOTE_HISTORY_UNBOUNDED')
  previous=[r for r in history['workflow_runs'] if r.get('head_sha')==g['code_commit']]
  require(len(previous)<LIMITS['max_jobs'] and not any(r.get('display_title')=='QWLF01-'+ident for r in previous),'REMOTE_BUDGET_OR_ATTEMPT_ALREADY_CONSUMED')
  if intent['model']=='dynamics':self._verify_staged_source(world,intent,g,attempt)
  # Marked reserved by broker before this non-idempotent dispatch. Never retry POST.
  self.gh('api','--method','POST',f'repos/{repo}/actions/workflows/{wf}/dispatches','-f',f'ref={branch}','-f',f'inputs[intent_id]={ident}','-f',f'inputs[request_b64]={encoded}','-F','inputs[enabled]=true')
  end=time.monotonic()+self.timeout;run=None
  while time.monotonic()<end:
   rows=json.loads(self.gh('api',f'repos/{repo}/actions/workflows/{wf}/runs?branch={branch}&per_page=100'))['workflow_runs'];matches=[r for r in rows if r.get('display_title')=='QWLF01-'+ident];require(len(matches)<=1,'DUPLICATE_REMOTE_JOB')
   if matches:
    run=matches[0]
    if run['status']=='completed':break
   time.sleep(5)
  require(run and run['status']=='completed','REMOTE_JOB_TIMEOUT_NO_RETRY')
  log='' if intent['model']=='dynamics' else self.gh('run','view',str(run['id']),'--repo',repo,'--log');(attempt/'remote.log').write_text(log)
  proof=None
  if intent['model']=='dynamics':
   run,result,proof=self._verified_dynamics_return(repo,wf,run['id'],intent,g,source_sha,grant_sha,grant_path,attempt)
  else:
   parts=[x.split('QWLF_PACKAGE=',1)[1].strip() for x in log.splitlines() if 'QWLF_PACKAGE=' in x];require(bool(parts),'REMOTE_PACKAGE_MISSING')
   result=json.loads(zlib.decompress(base64.b64decode(parts[-1])))
  require(result['intent_hash']==ident and run['head_sha']==g['code_commit'] and run['head_branch']==branch and run['run_attempt']==1 and run['status']=='completed' and run['conclusion']=='success','REMOTE_RUN_NOT_SUCCESSFUL')
  package=self._publish_verified_return(result,proof,run,intent,g,source_sha,grant_sha,grant_path,world,attempt,log)
  self._packages[digest(package)]=package;return package

 def _publish_verified_return(self,result,proof,run,intent,g,source_sha,grant_sha,grant_path,world,attempt,log=''):
  ident=digest(intent)
  require(result['source_sha256']==source_sha and result['grant_sha256']==grant_sha,'REMOTE_RETURN_BINDING')
  io=attempt/'remote_io';io.mkdir()
  for rel,v in result['files'].items():
   p=pathlib.PurePosixPath(rel);require(not p.is_absolute() and '..' not in p.parts,'REMOTE_PACKAGE_PATH_INVALID');publish_bytes(io/rel,zlib.decompress(base64.b64decode(v)))
  raw=json.loads((io/'worker_result.json').read_text());require(raw['intent_hash']==ident,'REMOTE_INTENT_MISMATCH')
  if intent['model']=='dynamics':
   self._verify_dynamics_bundle(io,world,intent,g,grant_path,grant_sha,source_sha)
   from dynamics01.adapter import verify_return_files
   verify_return_files(world,io/'world',raw,intent)
   from dynamics01.adapter import compare_observations
   from dynamics01.model import observe_arrays
   from frontier01.state import CorrelatedStore
   store=CorrelatedStore(io/'world');state=store.load(raw['state']);check=compare_observations(observe_arrays(store.arrays(state),state['payload']),raw['observation']);(io/'engineering_readback_check.json').write_text(json.dumps(check,indent=2))
  package={'world_root':str(io/'world'),'result_path':str(io/'worker_result.json'),'state':raw['state'],'files':{str(p.relative_to(io)):filehash(p) for p in io.rglob('*') if p.is_file()},'io':str(io),'run':{k:run[k] for k in ('id','head_sha','head_branch','run_attempt','conclusion')},'log_sha256':hashlib.sha256(log.encode()).hexdigest()}
  if proof is not None:
   package['verified_run']=proof;package['log_sha256']=proof['raw_log_sha256']
   package['acquisition_evidence_files']={str(p.resolve()):filehash(p) for p in attempt.iterdir() if p.is_file() and (p.suffix=='.json' or p.name=='raw_remote.log.bin')}
  return package
 def verify_package(self,p):
  require(digest(p) in self._packages,'UNAUTHENTICATED_WORKER_PACKAGE');require(all(filehash(pathlib.Path(p['io'])/rel)==h for rel,h in p['files'].items()),'WORKER_PACKAGE_BYTES_CHANGED')
  if p.get('verified_run'):require(all(pathlib.Path(rel).is_file() and filehash(pathlib.Path(rel))==h for rel,h in p.get('acquisition_evidence_files',{}).items()) and bool(p.get('acquisition_evidence_files')),'ACQUISITION_EVIDENCE_BYTES_CHANGED')

 def _get(self,path,attempt,label):
  """Only this method acquires production metadata: authenticated official GET.
  Tests monkeypatch gh explicitly; fixture replies are not independent evidence.
  No caller-supplied 'verified' JSON or success flag is an input to execution.
  """
  raw=self.gh('api',path);(attempt/(label+'.json')).write_text(raw)
  try:return json.loads(raw)
  except (ValueError,TypeError):require(False,'GITHUB_METADATA_INVALID_JSON')
 def gh_bytes(self,*argv):
  # Preserve exact bytes of the authenticated Job logs response, not CLI pretty output.
  p=subprocess.run(['gh',*argv],capture_output=True,timeout=60,check=False);self._calls+=1
  (self.root/f'gh_raw_{self._calls:04d}.json').write_text(json.dumps({'argv':['gh',*argv],'returncode':p.returncode,'stdout_sha256':hashlib.sha256(p.stdout).hexdigest(),'stderr':p.stderr.decode('utf-8',errors='replace'),'credentials_requested':False}))
  require(p.returncode==0,'GITHUB_RAW_LOG_READ_FAILED');return p.stdout
 def _metadata_binding(self,repo,wf,run_id,ident,g,attempt,label):
  require(repo=='flyoung588/narque-qw-foundation02' and type(run_id) is int and run_id>0,'REMOTE_REPOSITORY_OR_RUN_INVALID')
  meta=self._get(f'repos/{repo}',attempt,label+'_repository');require(meta.get('full_name')==repo and meta.get('id')==g.get('repository_id') and type(meta.get('id')) is int,'REMOTE_REPOSITORY_ID_MISMATCH')
  workflow=self._get(f'repos/{repo}/actions/workflows/{wf}',attempt,label+'_workflow');path='.github/workflows/'+wf
  require(workflow.get('path')==path and type(workflow.get('id')) is int and workflow.get('id')>0,'REMOTE_WORKFLOW_MISMATCH')
  run=self._get(f'repos/{repo}/actions/runs/{run_id}',attempt,label+'_run')
  require(run.get('id')==run_id and run.get('workflow_id')==workflow['id'] and str(run.get('path','')).split('@')[0]==path,'REMOTE_RUN_WORKFLOW_MISMATCH')
  require(run.get('repository',{}).get('full_name')==repo and run.get('repository',{}).get('id')==meta['id'] and run.get('head_repository',{}).get('id')==meta['id'],'REMOTE_RUN_REPOSITORY_MISMATCH')
  require(run.get('status')=='completed' and run.get('conclusion')=='success','REMOTE_RUN_NOT_SUCCESSFUL')
  require(type(run.get('run_attempt')) is int and run['run_attempt']==1,'REMOTE_RUN_NOT_FIRST_ATTEMPT')
  require(run.get('head_sha')==g.get('code_commit') and run.get('head_branch')==g.get('branch'),'REMOTE_RUN_SOURCE_MISMATCH')
  require(run.get('event')=='workflow_dispatch' and run.get('display_title')=='QWLF01-'+ident,'REMOTE_RUN_INTENT_LABEL_MISMATCH')
  listing=self._get(f'repos/{repo}/actions/runs/{run_id}/attempts/1/jobs?per_page=100',attempt,label+'_jobs')
  require(listing.get('total_count')==1 and len(listing.get('jobs',[]))==1,'ONE_SUCCESSFUL_JOB_REQUIRED');job_id=listing['jobs'][0].get('id');require(type(job_id) is int and job_id>0,'REMOTE_JOB_ID_MISSING')
  job=self._get(f'repos/{repo}/actions/jobs/{job_id}',attempt,label+'_job')
  require(job.get('id')==job_id and job.get('run_id')==run_id and job.get('run_url')==f'https://api.github.com/repos/{repo}/actions/runs/{run_id}','REMOTE_JOB_RUN_MISMATCH')
  require(job.get('status')=='completed' and job.get('conclusion')=='success','REMOTE_JOB_NOT_SUCCESSFUL')
  # Do not invent optional REST fields. Attempt-specific collection + run checks
  # bind attempt1; when direct Job exposes attempt/head/branch they must agree.
  for key,expected in [('run_attempt',1),('head_sha',g['code_commit']),('head_branch',g['branch'])]:
   if key in job:require(job[key]==expected,'REMOTE_JOB_SOURCE_OR_ATTEMPT_MISMATCH')
  return run,workflow,job,meta
 def read_verified_remote_blob(self,repository,repository_id,commit,path,expected_sha256,attempt,label,expected_size=None):
  """Authenticated GET only; commit→complete tree→regular blob→exact bytes.
  Caller supplies the already-authorized commit and SHA256, never a Blob ID.
  No branch lookup or trust in a return package occurs in this acquisition path.
  """
  import re,binascii
  from urllib.parse import quote
  require(repository=='flyoung588/narque-qw-foundation02' and type(repository_id) is int and repository_id==1427746629,'REMOTE_BLOB_REPOSITORY_NOT_AUTHORIZED')
  require(isinstance(commit,str) and re.fullmatch('[0-9a-f]{40}',commit) is not None,'REMOTE_BLOB_COMMIT_INVALID')
  require(isinstance(path,str) and path and not path.startswith('/') and all(x not in ('','.','..') for x in path.split('/')) and not any(x in path for x in ('\\','?','#','%')),'REMOTE_BLOB_PATH_INVALID')
  require(isinstance(expected_sha256,str) and re.fullmatch('[0-9a-f]{64}',expected_sha256) is not None,'REMOTE_BLOB_SHA256_INVALID')
  require(expected_size is None or type(expected_size) is int and 0<=expected_size<=32*1024*1024,'REMOTE_BLOB_SIZE_INVALID')
  repo=self._get('repos/'+repository,attempt,label+'_repository')
  require(repo.get('id')==repository_id and type(repo.get('id')) is int and repo.get('full_name')==repository,'REMOTE_BLOB_REPOSITORY_MISMATCH')
  commit_meta=self._get(f'repos/{repository}/git/commits/{commit}',attempt,label+'_commit')
  require(commit_meta.get('sha')==commit,'REMOTE_BLOB_COMMIT_MISMATCH')
  tree_sha=commit_meta.get('tree',{}).get('sha');require(isinstance(tree_sha,str) and re.fullmatch('[0-9a-f]{40}',tree_sha) is not None,'REMOTE_BLOB_TREE_ID_INVALID')
  tree=self._get(f'repos/{repository}/git/trees/{tree_sha}?recursive=1',attempt,label+'_tree')
  require(tree.get('sha')==tree_sha and tree.get('truncated') is False and isinstance(tree.get('tree'),list),'REMOTE_BLOB_TREE_INCOMPLETE')
  entries=[x for x in tree['tree'] if x.get('path')==path];require(len(entries)==1,'REMOTE_BLOB_PATH_NOT_UNIQUE')
  entry=entries[0];blob_sha=entry.get('sha');size=entry.get('size')
  require(entry.get('type')=='blob' and entry.get('mode') in ('100644','100755') and isinstance(blob_sha,str) and re.fullmatch('[0-9a-f]{40}',blob_sha) is not None,'REMOTE_BLOB_NOT_REGULAR_FILE')
  require(type(size) is int and 0<=size<=32*1024*1024 and (expected_size is None or size==expected_size),'REMOTE_BLOB_TREE_SIZE_MISMATCH')
  content=self._get(f'repos/{repository}/contents/{quote(path,safe="/")}?ref={commit}',attempt,label+'_contents')
  require(content.get('path')==path and content.get('type')=='file' and content.get('sha')==blob_sha and content.get('size')==size,'REMOTE_BLOB_CONTENTS_ID_MISMATCH')
  def decode(v):
   require(isinstance(v,str),'REMOTE_BLOB_BASE64_INVALID')
   try:return base64.b64decode(''.join(v.split()),validate=True)
   except (ValueError,binascii.Error):require(False,'REMOTE_BLOB_BASE64_INVALID')
  if content.get('encoding')=='base64':
   raw=decode(content.get('content'));channel='CONTENTS_BASE64'
  else:
   require(content.get('encoding')=='none' and content.get('content')=='','REMOTE_BLOB_CONTENTS_ENCODING_UNSUPPORTED')
   blob=self._get(f'repos/{repository}/git/blobs/{blob_sha}',attempt,label+'_blob')
   require(blob.get('sha')==blob_sha and blob.get('size')==size and blob.get('encoding')=='base64','REMOTE_BLOB_RESPONSE_ID_MISMATCH')
   raw=decode(blob.get('content'));channel='GIT_BLOB_BASE64'
  require(len(raw)==size,'REMOTE_BLOB_BYTES_SIZE_MISMATCH')
  require(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blob_sha,'REMOTE_BLOB_OBJECT_ID_MISMATCH')
  require(hashlib.sha256(raw).hexdigest()==expected_sha256,'REMOTE_BLOB_SHA256_MISMATCH')
  receipt={'repository':repository,'repository_id':repository_id,'authorized_commit':commit,'tree_sha':tree_sha,'path':path,'type':'blob','mode':entry['mode'],'git_blob_sha1':blob_sha,'size_bytes':len(raw),'sha256':expected_sha256,'channel':channel,'status':'EXACT_BYTES_VERIFIED','branch_lookup':False}
  (attempt/(label+'_verified_blob.json')).write_text(json.dumps(receipt,indent=2));return raw

 def _verify_staged_source(self,world,intent,g,attempt):
  from dynamics01.transfer import staged_references
  repo=g['repository'];require(repo=='flyoung588/narque-qw-foundation02','REMOTE_REPOSITORY_MISMATCH')
  wf=self._get(f"repos/{repo}/contents/.github/workflows/qw-dynamics01-once.yml?ref={g['code_commit']}",attempt,'authorized_workflow_source')
  require(wf.get('encoding')=='base64','WORKFLOW_CONTENT_UNAVAILABLE');code=base64.b64decode(wf['content'],validate=False);require(hashlib.sha256(code).hexdigest()==g.get('workflow_sha256'),'WORKFLOW_SOURCE_NOT_AUTHORIZED')
  refs=staged_references(world,intent['input_state'],g)
  from dynamics01.transfer import parent_files as physical_parent_files
  parent_files=physical_parent_files(world,intent['input_state'])
  for number,(rel,v) in enumerate(sorted(refs.items())):
   self.read_verified_remote_blob(repo,g['repository_id'],g['code_commit'],v['source_path'],v['sha256'],attempt,f'staged_source_{number}',expected_size=parent_files[rel].stat().st_size)
  provenance=world.root/'remote_provenance'/f"{intent['input_state']}.json"
  if provenance.exists():
   record=json.loads(provenance.read_text());previous=record['verified_run'];require(g.get('parent_execution')=={k:previous[k] for k in ('run_id','job_id','code_commit','raw_log_sha256')} and record['state']==intent['input_state'],'SECOND_PARENT_EXECUTION_NOT_BOUND')
   compare=self._get(f"repos/{repo}/compare/{previous['code_commit']}...{g['code_commit']}",attempt,'second_commit_exact_staging_diff')
   names={x['source_path']:x['sha256'] for x in refs.values()};changes=compare.get('files',[])
   require(compare.get('status')=='ahead' and compare.get('ahead_by')==1 and 0<len(changes)<300,'SECOND_COMMIT_DIFF_UNVERIFIABLE')
   require({x['filename'] for x in changes}==set(g.get('staging_diff',[])) and all(x['filename'] in names and x.get('status')=='added' and not x.get('previous_filename') for x in changes),'SECOND_COMMIT_NOT_EXACT_BYTE_STAGING_ONLY')
  else:require(intent['input_state'] in g.get('initial_states',[]),'UNBOUND_SECOND_PARENT')
 def _verified_dynamics_return(self,repo,wf,run_id,intent,g,source_sha,grant_sha,grant_path,attempt):
  ident=digest(intent);run,workflow,job,meta=self._metadata_binding(repo,wf,run_id,ident,g,attempt,'before_log')
  raw=self.gh_bytes('api',f"repos/{repo}/actions/jobs/{job['id']}/logs");(attempt/'raw_remote.log.bin').write_bytes(raw)
  from dynamics01.transfer import decode_package
  try:result=decode_package(raw.decode('utf-8'))
  except UnicodeError:require(False,'REMOTE_LOG_NOT_UTF8')
  require(result.get('intent_hash')==ident and result.get('source_sha256')==source_sha and result.get('grant_sha256')==grant_sha,'REMOTE_RETURN_BINDING')
  # A rerun, commit or Job change during log acquisition cannot inherit the first snapshot.
  later,w2,j2,m2=self._metadata_binding(repo,wf,run_id,ident,g,attempt,'after_log')
  require(j2['id']==job['id'] and w2['id']==workflow['id'] and m2['id']==meta['id'],'REMOTE_IDENTITY_CHANGED_DURING_READBACK')
  proof={'source':'AUTHENTICATED_GITHUB_REST_GET_AND_RAW_JOB_LOG','repository':repo,'repository_id':meta['id'],'workflow_id':workflow['id'],'workflow_path':workflow['path'],'run_id':run_id,'job_id':job['id'],'status':'completed','conclusion':'success','run_attempt':1,'code_commit':g['code_commit'],'branch':g['branch'],'intent_hash':ident,'source_sha256':source_sha,'grant_sha256':grant_sha,'raw_log_sha256':hashlib.sha256(raw).hexdigest(),'REST_inputs_exposure':'not supplied by run GET; dispatch binding is checked through run title + exact raw request + pinned workflow source','job_optional_fields_present':[k for k in ('run_attempt','head_sha','head_branch') if k in job]}
  (attempt/'verified_remote_source.json').write_text(json.dumps(proof,indent=2));return later,result,proof
 def _verify_dynamics_bundle(self,io,world,intent,g,grant_path,grant_sha,source_sha):
  require((io/'grant.json').is_file() and (io/'request.json').is_file() and (io/'source.json').is_file(),'REMOTE_BINDING_FILES_MISSING')
  require((io/'grant.json').read_bytes()==pathlib.Path(grant_path).read_bytes() and filehash(io/'grant.json')==grant_sha,'REMOTE_GRANT_BYTES_MISMATCH')
  b=json.loads((io/'request.json').read_text());require(b.get('intent')==intent and b.get('grant_sha256')==grant_sha and b.get('source_sha256')==source_sha,'REMOTE_REQUEST_BINDING_MISMATCH')
  source=json.loads((io/'source.json').read_text());require(digest(source)==source_sha and g.get('source_sha256')==source_sha,'REMOTE_SOURCE_MAP_MISMATCH')
  from birth01.preparation import resource_check
  for name in ('resources_before.json','resources_after.json'):
   require((io/name).is_file(),'REMOTE_RUNTIME_RESOURCE_EVIDENCE_MISSING');facts=json.loads((io/name).read_text());resource_check(facts)
   events=dict(line.split() for line in facts['memory.events'].splitlines());require(events.get('oom')=='0' and events.get('oom_kill')=='0','REMOTE_OOM_REJECTED')

 def read_completed_return(self,intent,world,attempt,grant_path,grant_sha,source_sha):
  require(intent.get('model')=='dynamics','DYNAMICS_READBACK_SCOPE_REQUIRED')
  require(filehash(pathlib.Path(grant_path))==grant_sha and intent.get('authorization_ref')==grant_sha,'READBACK_GRANT_PIN_MISMATCH')
  g=json.loads(pathlib.Path(grant_path).read_text());require(g.get('status')=='HUMAN_GRANTED' and g.get('scope')=='QW-LIVE-FABRIC-01' and g.get('source_sha256')==source_sha,'READBACK_AUTHORITY_MISMATCH')
  repo=g['repository'];wf='qw-dynamics01-once.yml';ident=digest(intent)
  rows=self._get(f'repos/{repo}/actions/workflows/{wf}/runs?branch={g["branch"]}&per_page=100',attempt,'readback_listing')
  require(rows.get('total_count',101)<=100,'READBACK_HISTORY_UNBOUNDED');matches=[v for v in rows['workflow_runs'] if v.get('display_title')=='QWLF01-'+ident];require(len(matches)==1,'READBACK_RUN_NOT_UNIQUE')
  run,result,proof=self._verified_dynamics_return(repo,wf,matches[0]['id'],intent,g,source_sha,grant_sha,grant_path,attempt)
  self._verify_staged_source(world,intent,g,attempt)
  package=self._publish_verified_return(result,proof,run,intent,g,source_sha,grant_sha,grant_path,world,attempt)
  self._packages[digest(package)]=package;return package
