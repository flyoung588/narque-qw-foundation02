"""Import-only limit contrast or single frozen science request, never an optimizer."""
import datetime,json,os,pathlib,resource,sys,traceback
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from router import digest,save
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
def emit(out,name,**details):
 out.mkdir(parents=True,exist_ok=True)
 with (out/'stages.jsonl').open('a') as f:f.write(json.dumps({'stage':name,'pid':os.getpid(),'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),**details})+'\n');f.flush();os.fsync(f.fileno())
def main():
 probe=sys.argv[1]=='--import-only'
 if probe:mode=sys.argv[2];out=pathlib.Path(sys.argv[3]);spec=None
 else:mode='inherited';spec=json.loads(pathlib.Path(sys.argv[1]).read_text());out=pathlib.Path(sys.argv[2])
 emit(out,'START',mode=mode,import_only=probe,data_limit_before=list(resource.getrlimit(resource.RLIMIT_DATA)))
 if probe and mode=='512MiB':resource.setrlimit(resource.RLIMIT_DATA,(512*1024**2,512*1024**2))
 elif mode!='inherited':raise ValueError('Unsupported limit contrast')
 save(out/'worker_limits.json',{'RLIMIT_DATA':list(resource.getrlimit(resource.RLIMIT_DATA)),'outer_memory_limit':pathlib.Path('/sys/fs/cgroup/memory.max').read_text().strip(),'only_probe_may_add_DATA_limit':True})
 for name in ['numpy','scipy','pyscf']:
  emit(out,'IMPORT',module=name,position='before');__import__(name);emit(out,'IMPORT',module=name,position='after')
 if probe:save(out/'import_success.json',{'mode':mode,'science_calculations':0});return
 assert spec['physics']['engine']=='pyscf'
 from foundation01.pyscf_bridge import solve
 from pyscf import lib
 lib.num_threads(1)
 result=solve(spec,stage_callback=lambda name:emit(out,name))
 if result.get('status')=='UNVERIFIED':status='UNVERIFIED'
 else:
  status='CALCULATED';result.update(energy_Eh=result['energy'],energy_zero='total BO electronic-structure energy including nuclear repulsion',gradient_Eh_per_bohr=[[-a for a in row] for row in result['forces_Eh_per_bohr']],numerical_threads=lib.num_threads())
 save(out/'observation.json',{'spec':spec,'world_spec_sha256':digest(spec),'status':status,'observation':result,'precision_qualified':False})
 if status!='CALCULATED':raise RuntimeError('SCF_UNVERIFIED_NO_RETRY')
if __name__=='__main__':
 try:main()
 except BaseException as exc:
  out=pathlib.Path(sys.argv[3] if sys.argv[1]=='--import-only' else sys.argv[2]);save(out/'worker_failure.json',{'type':type(exc).__name__,'error':str(exc),'traceback':traceback.format_exc()});raise
