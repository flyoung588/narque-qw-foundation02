"""Future Ubuntu Runner host. Docker image contains no model credentials."""
import base64,json,os,pathlib,subprocess,traceback,sys,zlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
 scope=json.loads((ROOT/'live01/REMOTE_APPROVAL.json').read_text());assert scope.get('status')=='HUMAN_GRANTED_E01' and scope.get('scope')=='QW-EXPLORER-E01','HUMAN_GATE_REQUIRED'
 assert os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted' and os.environ.get('GITHUB_RUN_ATTEMPT')=='1','STANDARD_RUNNER_FIRST_ATTEMPT_REQUIRED'
 import urllib.request
 repo=os.environ['GITHUB_REPOSITORY'];branch=os.environ['GITHUB_REF_NAME'];assert repo=='flyoung588/narque-qw-foundation02' and branch=='qw-explorer-e01'
 rq=urllib.request.Request(f'https://api.github.com/repos/{repo}/actions/workflows/qw-explorer-e01-once.yml/runs?branch={branch}&per_page=100',headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json'})
 with urllib.request.urlopen(rq,timeout=20) as response:history=json.load(response)
 assert history.get('total_count',101)<=100,'RUN_HISTORY_TOO_LARGE'
 selected=[r for r in history['workflow_runs'] if r['head_sha']==os.environ['GITHUB_SHA']]
 assert len(selected)<=2 and any(str(r['id'])==os.environ['GITHUB_RUN_ID'] for r in selected),'REMOTE_JOB_LIMIT'
 out=pathlib.Path(os.environ['RUNNER_TEMP'])/'qw-explorer-e01';out.mkdir(exist_ok=False)
 req=json.loads(base64.b64decode(os.environ['E01_REQUEST_B64']));assert req['intent']==os.environ['E01_INTENT_ID'];(out/'request.json').write_text(json.dumps(req))
 cid=None
 try:
  cpu=min(os.sched_getaffinity(0));cmd=['docker','create','--network','none','--cpus','1','--cpuset-cpus',str(cpu),'--memory','1g','--memory-swap','1g','--pids-limit','64','--cap-drop','ALL','--security-opt','no-new-privileges','--read-only','--user',f'{os.getuid()}:{os.getgid()}','--tmpfs','/tmp:rw,nosuid,size=256m','--mount',f'type=bind,src={out},dst=/out','qw-explorer-e01:once','python','-B','-m','live01.job_entry']
  cid=subprocess.check_output(cmd,text=True).strip();info=json.loads(subprocess.check_output(['docker','inspect',cid],text=True))[0];c=info['HostConfig'];assert c['Memory']==2**30 and c['MemorySwap']==2**30 and c['NanoCpus']==10**9 and c['NetworkMode']=='none' and not c['Privileged'];(out/'host_config.json').write_text(json.dumps(info,indent=2))
  p=subprocess.run(['docker','start','-a',cid],timeout=630)
  if p.returncode:raise RuntimeError('CONTAINER_FAILED_NO_RETRY')
 except BaseException as e:(out/'host_failure.json').write_text(json.dumps({'status':'FAILED_NO_RETRY','type':type(e).__name__,'detail':str(e),'traceback':traceback.format_exc()}));raise
 finally:
  if cid:
   inspected=subprocess.run(['docker','inspect',cid],capture_output=True,text=True,timeout=3);(out/'container_after.json').write_text(inspected.stdout if inspected.returncode==0 else json.dumps({'inspect_error':inspected.stderr}))
   subprocess.run(['docker','kill',cid],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=3);subprocess.run(['docker','rm',cid],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=3)
def export():
 out=pathlib.Path(os.environ['RUNNER_TEMP'])/'qw-explorer-e01'
 if not out.exists():return
 files={str(p.relative_to(out)):base64.b64encode(zlib.compress(p.read_bytes())).decode() for p in out.rglob('*') if p.is_file()}
 get=lambda f:json.loads((out/f).read_text()) if (out/f).is_file() else None
 req=get('request.json') or {};p={'intent':req.get('intent'),'input_sha256':__import__('hashlib').sha256(json.dumps(req.get('spec'),sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest(),'observation':get('observation.json'),'admission':get('admission.json'),'native_process':get('solver/process_receipt.json'),'files_zlib_base64':files,'failure':get('host_failure.json')}
 # Complete small-molecule records fit this bounded ordinary-log envelope; no artifacts/cache.
 data=base64.b64encode(zlib.compress(json.dumps(p).encode())).decode();assert len(data)<500000,'LOG_PACKAGE_TOO_LARGE';print('QW_E01_PACKAGE='+data,flush=True)
if __name__=='__main__':export() if '--export' in sys.argv else main()
