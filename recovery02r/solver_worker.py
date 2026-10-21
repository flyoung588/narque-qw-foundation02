"""Only this disposable process imports a physical solver."""
import json,os,pathlib,resource,signal,sys,time,traceback
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from router import save
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
spec=json.loads(pathlib.Path(sys.argv[1]).read_text());out=pathlib.Path(sys.argv[2]);mode=sys.argv[4] if len(sys.argv)>4 else None
try:
 if mode:
  if mode=='segv':os.kill(os.getpid(),signal.SIGSEGV)
  elif mode=='kill':os.kill(os.getpid(),signal.SIGKILL)
  elif mode=='timeout':time.sleep(10)
  elif mode=='exception':raise RuntimeError('INJECTED_SYNTHETIC_EXCEPTION')
  elif mode=='memory':
   resource.setrlimit(resource.RLIMIT_AS,(96*1024**2,96*1024**2));bytearray(256*1024**2)
  elif mode=='ok':save(out/'observation.json',{'status':'SYNTHETIC_OK','scientific_result':False,'worker_pid':os.getpid()})
  else:raise ValueError('Unknown synthetic fault')
 else:
  # Linux data limit bounds allocatable data; cgroup remains the total RSS hard limit.
  # No claim that this makes the world immune to whole-container/host failure.
  if sys.platform.startswith('linux'):resource.setrlimit(resource.RLIMIT_DATA,(512*1024**2,512*1024**2))
  from router import run
  result=run(spec,out);sys.exit(0 if result['status']=='CALCULATED' else 2)
except Exception as exc:
 save(out/'worker_failure.json',{'type':type(exc).__name__,'error':str(exc),'traceback':traceback.format_exc(),'synthetic':mode is not None});sys.exit(3)
