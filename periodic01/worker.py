"""Generic periodic worker; no material-specific solver or DATA/AS cap."""
import json,pathlib,resource,sys,traceback
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from router import save
from qw_next.periodic_world import route_world
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
out=pathlib.Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
try:
 save(out/'worker_start.json',{'RLIMIT_DATA':list(resource.getrlimit(resource.RLIMIT_DATA)),'RLIMIT_AS':list(resource.getrlimit(resource.RLIMIT_AS))})
 result=route_world(json.loads(pathlib.Path(sys.argv[1]).read_text()),out)
 save(out/'observation.json',result)
 if result['status']!='CALCULATED':raise RuntimeError('PERIODIC_RESULT_NOT_VERIFIED_NO_RETRY')
except BaseException as exc:
 save(out/'worker_failure.json',{'type':type(exc).__name__,'error':str(exc),'traceback':traceback.format_exc()});raise
