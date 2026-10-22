"""Independent mature KRKS worker. No extra DATA/AS limit."""
import json,pathlib,resource,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from router import save
from periodic03.runtime import run
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
spec=json.loads(pathlib.Path(sys.argv[1]).read_text());out=pathlib.Path(sys.argv[2])
result=run(spec,out)
if not (out/'observation.json').exists():save(out/'observation.json',result)
if result['status']!='CALCULATED':raise SystemExit(1)
