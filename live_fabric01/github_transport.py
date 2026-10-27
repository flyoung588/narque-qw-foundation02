"""Reuse existing authenticated GH command/log transport; different scope,
workers and output format. This module is prepared, not remotely executed."""
import pathlib,json,base64,zlib,time,hashlib
from live01.transport import GithubTransport
from world01.session import filehash,publish_bytes
from router import digest
from .fabric import require,SCOPE,LIMITS
class GithubFabricTransport(GithubTransport):
 def __init__(self,root,*,runtime_enabled=False):super().__init__(root,timeout=950);self.enabled=runtime_enabled;self._packages={}
 def execute(self,intent,world,attempt,grant_path,grant_sha,source_sha):
  require(self.enabled,'RUNTIME_TRANSPORT_DISABLED');g=json.loads(pathlib.Path(grant_path).read_text())
  require(g.get('status')=='HUMAN_GRANTED' and g.get('scope')==SCOPE and g.get('zero_additional_cost_verified') is True and bool(g.get('cost_evidence_ref')),'REMOTE_COST_OR_AUTHORITY_UNCONFIRMED')
  repo=g['repository'];branch=g['branch'];wf='qw-live-fabric01-once.yml'
  meta=json.loads(self.gh('api',f'repos/{repo}'));require(meta.get('private') is False and not meta.get('disabled'),'PUBLIC_STANDARD_RUNNER_REQUIRED')
  ref=json.loads(self.gh('api',f'repos/{repo}/git/ref/heads/{branch}'));require(ref['object']['sha']==g['code_commit'],'FROZEN_REMOTE_COMMIT_MISMATCH')
  # Send only immutable current states/arrays required by this Session, never credentials.
  files={str(p.relative_to(world.root)):base64.b64encode(zlib.compress(p.read_bytes())).decode() for folder,glob in [('states','*.json'),('arrays','*.npz')] for p in (world.root/folder).glob(glob)}
  payload={'intent':intent,'grant':g,'grant_file_b64':base64.b64encode(pathlib.Path(grant_path).read_bytes()).decode(),'grant_sha256':grant_sha,'source_sha256':source_sha,'world_files':files}
  ident=digest(intent);encoded=base64.b64encode(zlib.compress(json.dumps(payload).encode())).decode();require(len(encoded)<50000,'REMOTE_INPUT_TOO_LARGE')
  history=json.loads(self.gh('api',f'repos/{repo}/actions/workflows/{wf}/runs?branch={branch}&per_page=100'))
  require(history.get('total_count',101)<=100,'REMOTE_HISTORY_UNBOUNDED')
  previous=[r for r in history['workflow_runs'] if r.get('head_sha')==g['code_commit']]
  require(len(previous)<LIMITS['max_jobs'] and not any(r.get('display_title')=='QWLF01-'+ident for r in previous),'REMOTE_BUDGET_OR_ATTEMPT_ALREADY_CONSUMED')
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
  log=self.gh('run','view',str(run['id']),'--repo',repo,'--log');(attempt/'remote.log').write_text(log)
  parts=[x.split('QWLF_PACKAGE=',1)[1].strip() for x in log.splitlines() if 'QWLF_PACKAGE=' in x];require(bool(parts),'REMOTE_PACKAGE_MISSING')
  result=json.loads(zlib.decompress(base64.b64decode(parts[-1])));require(result['intent_hash']==ident and run['head_sha']==g['code_commit'] and run['run_attempt']==1 and run['conclusion']=='success','REMOTE_RUN_NOT_SUCCESSFUL')
  require(result['source_sha256']==source_sha and result['grant_sha256']==grant_sha,'REMOTE_RETURN_BINDING')
  io=attempt/'remote_io';io.mkdir()
  for rel,v in result['files'].items():
   p=pathlib.PurePosixPath(rel);require(not p.is_absolute() and '..' not in p.parts,'REMOTE_PACKAGE_PATH_INVALID');publish_bytes(io/rel,zlib.decompress(base64.b64decode(v)))
  raw=json.loads((io/'worker_result.json').read_text());require(raw['intent_hash']==ident,'REMOTE_INTENT_MISMATCH')
  package={'world_root':str(io/'world'),'result_path':str(io/'worker_result.json'),'state':raw['state'],'files':{str(p.relative_to(io)):filehash(p) for p in io.rglob('*') if p.is_file()},'io':str(io),'run':{k:run[k] for k in ('id','head_sha','head_branch','run_attempt','conclusion')},'log_sha256':hashlib.sha256(log.encode()).hexdigest()};self._packages[digest(package)]=package;return package
 def verify_package(self,p):
  require(digest(p) in self._packages,'UNAUTHENTICATED_WORKER_PACKAGE');require(all(filehash(pathlib.Path(p['io'])/rel)==h for rel,h in p['files'].items()),'WORKER_PACKAGE_BYTES_CHANGED')
