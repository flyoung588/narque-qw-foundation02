"""Engine child: engine crash cannot kill the world router."""
import json,pathlib,resource,sys,traceback
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from interactive01.world import freeze
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
out=pathlib.Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
try:
    print('START',flush=True)
    from frontier01.solver import solve
    solve(json.loads(pathlib.Path(sys.argv[1]).read_text()),out)
except BaseException as e:
    freeze(out/'worker_failure.json',{'status':'UNVERIFIED','type':type(e).__name__,'error':str(e),'traceback':traceback.format_exc(),'no_retry':True});raise
