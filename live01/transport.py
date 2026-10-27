"""Prepared GH transport. No POST occurs without the broker's frozen Human grant."""
import json,subprocess,time,base64,zlib,pathlib
from .contracts import require
class GithubTransport:
 def __init__(self,root,timeout=1080):self.root=pathlib.Path(root);self.root.mkdir(parents=True,exist_ok=True);self.timeout=timeout;self._authenticated_returns={};self._calls=0
 def gh(self,*argv):
  p=subprocess.run(['gh',*argv],capture_output=True,text=True,timeout=60,check=False)
  self._calls+=1
  (self.root/f'gh_call_{self._calls:04d}.json').write_text(json.dumps({'argv':['gh',*argv],'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'credential_values_not_requested':True},indent=2))
  require(p.returncode==0,'GITHUB_API_FAILED');return p.stdout
 def execute(self,spec,intent,grant):
  require(grant.get('status')=='HUMAN_GRANTED_E01','HUMAN_GATE_REQUIRED');repo=grant['repository'];branch=grant['branch'];wf='qw-explorer-e01-once.yml'
  meta=json.loads(self.gh('api',f'repos/{repo}'));require(meta.get('private') is False and not meta.get('disabled'),'PUBLIC_STANDARD_RUNNER_REQUIRED')
  branchmeta=json.loads(self.gh('api',f'repos/{repo}/git/ref/heads/{branch}'));require(branchmeta['object']['sha']==grant['code_commit'],'FROZEN_REMOTE_COMMIT_MISMATCH')
  request={'intent':intent,'spec':spec,'remote_approval_hash':grant['remote_approval_hash']};encoded=base64.b64encode(json.dumps(request).encode()).decode()
  # No shell interpolation, no token in logs, no Actions artifacts/cache.
  self.gh('api','--method','POST',f'repos/{repo}/actions/workflows/{wf}/dispatches','-f',f'ref={branch}','-f',f'inputs[intent_id]={intent}','-f',f'inputs[request_b64]={encoded}','-F','inputs[enabled]=true')
  deadline=time.monotonic()+self.timeout;run=None
  while time.monotonic()<deadline:
   rows=json.loads(self.gh('api',f'repos/{repo}/actions/workflows/{wf}/runs?branch={branch}&per_page=100'))['workflow_runs'];matches=[r for r in rows if r.get('display_title')=='QWE01-'+intent]
   require(len(matches)<=1,'DUPLICATE_REMOTE_JOB')
   if matches:
    run=matches[0]
    if run['status']=='completed':break
   time.sleep(5)
  require(run is not None and run['status']=='completed','REMOTE_JOB_TIMEOUT_NO_RETRY')
  log=self.gh('run','view',str(run['id']),'--repo',repo,'--log');(self.root/(intent+'.log')).write_text(log)
  tokens=[line.split('QW_E01_PACKAGE=',1)[1].strip() for line in log.splitlines() if 'QW_E01_PACKAGE=' in line];require(bool(tokens),'REMOTE_EVIDENCE_PACKAGE_MISSING')
  package=json.loads(zlib.decompress(base64.b64decode(tokens[-1])));package['run']={k:run[k] for k in ['id','head_sha','head_branch','event','run_attempt','status','conclusion']};package['source_kind']='GITHUB_AUTHENTICATED_RUN';package['log_sha256']=__import__('hashlib').sha256(log.encode()).hexdigest();self._authenticated_returns[intent]=__import__('router').digest(package);return package
 def assert_authenticated(self,package):
  require(self._authenticated_returns.get(package.get('intent'))==__import__('router').digest(package),'REMOTE_RETURN_NOT_ACQUIRED_BY_THIS_TRANSPORT')
