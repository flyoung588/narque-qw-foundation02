"""Prepared standard Runner host; imports stdlib only before container admission."""
import pathlib,os,sys,json,base64,zlib,hashlib,subprocess,traceback
ROOT=pathlib.Path(__file__).resolve().parents[1]
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def main():
 assert os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted' and os.environ.get('GITHUB_RUN_ATTEMPT')=='1','STANDARD_FIRST_ATTEMPT_ONLY'
 scope=json.loads((ROOT/'live_fabric01/REMOTE_APPROVAL.json').read_text());assert scope.get('status')=='HUMAN_GRANTED' and scope['scope']=='QW-LIVE-FABRIC-01','REMOTE_AUTHORITY_MISSING'
 req=json.loads(zlib.decompress(base64.b64decode(os.environ['QWLF_REQUEST_B64'])));g=req['grant'];assert digest(req['intent'])==os.environ['QWLF_INTENT_ID']
 assert g['repository']==os.environ['GITHUB_REPOSITORY'] and g['branch']==os.environ['GITHUB_REF_NAME'] and g['code_commit']==os.environ['GITHUB_SHA'],'REMOTE_SOURCE_MISMATCH'
 assert g['zero_additional_cost_verified'] and g['cost_evidence_ref'] and g['status']=='HUMAN_GRANTED' and g['scope']==scope['scope'] and g['human_reference']==scope['human_reference'],'REMOTE_AUTHORITY_MISMATCH'
 io=pathlib.Path(os.environ['RUNNER_TEMP'])/'qw-live-fabric01';io.mkdir(exist_ok=False)
 (io/'grant.json').write_bytes(base64.b64decode(req['grant_file_b64']));assert hashlib.sha256((io/'grant.json').read_bytes()).hexdigest()==req['grant_sha256'] and json.loads((io/'grant.json').read_text())==g
 source={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.rglob('*') if p.is_file() and p.suffix in ('.py','.json','.f90','.npz') and '__pycache__' not in p.parts and '.git' not in p.parts}
 assert digest(source)==req['source_sha256']==g['source_sha256'];(io/'source.json').write_text(json.dumps(source))
 (io/'request.json').write_text(json.dumps({k:req[k] for k in ('intent','grant_sha256','source_sha256')}))
 for rel,raw in req['world_files'].items():
  p=pathlib.PurePosixPath(rel);assert not p.is_absolute() and '..' not in p.parts and p.parts[0] in ('states','arrays');f=io/'world'/rel;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(zlib.decompress(base64.b64decode(raw)))
 for rel,ref in req.get('world_references',{}).items():
  p=pathlib.PurePosixPath(rel);s=pathlib.PurePosixPath(ref['source_path']);assert not p.is_absolute() and '..' not in p.parts and p.parts[0] in ('states','arrays','references','remote_provenance');assert not s.is_absolute() and '..' not in s.parts and str(s).startswith('dynamics01/staged/');raw=(ROOT/s).read_bytes();assert hashlib.sha256(raw).hexdigest()==ref['sha256'] and source[str(s)]==ref['sha256'];dest=io/'world'/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 cid=None
 try:
  cmd=['docker','create','--network','none','--cpus','1','--cpuset-cpus',str(min(os.sched_getaffinity(0))),'--memory','1g','--memory-swap','1g','--pids-limit','64','--cap-drop','ALL','--security-opt','no-new-privileges','--read-only','--user',f'{os.getuid()}:{os.getgid()}','--tmpfs','/tmp:rw,size=128m','--mount',f'type=bind,src={io},dst=/io','qw-live-fabric:once','python','-B','-m','live_fabric01.worker','/io']
  cid=subprocess.check_output(cmd,text=True).strip();cfg=json.loads(subprocess.check_output(['docker','inspect',cid],text=True))[0];h=cfg['HostConfig'];assert h['Memory']==2**30 and h['MemorySwap']==2**30 and h['NanoCpus']==10**9 and h['NetworkMode']=='none' and not h['Privileged'];(io/'host_config.json').write_text(json.dumps(cfg))
  result=subprocess.run(['docker','start','-a',cid],timeout=630);assert result.returncode==0,'SOLVER_FAILURE_NO_RETRY'
 except BaseException as e:(io/'failure.json').write_text(json.dumps({'type':type(e).__name__,'detail':str(e),'traceback':traceback.format_exc(),'retry':False}));raise
 finally:
  if cid:
   subprocess.run(['docker','kill',cid],capture_output=True,timeout=4)
def export():
 io=pathlib.Path(os.environ['RUNNER_TEMP'])/'qw-live-fabric01'
 if not io.exists():return
 r=json.loads((io/'request.json').read_text()) if (io/'request.json').exists() else {}
 files={str(p.relative_to(io)):base64.b64encode(zlib.compress(p.read_bytes())).decode() for p in io.rglob('*') if p.is_file()}
 package={k:r.get(k) for k in ('source_sha256','grant_sha256')};package.update(intent_hash=digest(r.get('intent')),files=files)
 if r.get('intent',{}).get('model')=='dynamics':
  from dynamics01.transfer import encode_package
  for line in encode_package(package):print(line,flush=True)
 else:
  raw=base64.b64encode(zlib.compress(json.dumps(package).encode())).decode();assert len(raw)<500000,'EVIDENCE_LOG_PACKAGE_TOO_LARGE';print('QWLF_PACKAGE='+raw,flush=True)
if __name__=='__main__':export() if '--export' in sys.argv else main()
