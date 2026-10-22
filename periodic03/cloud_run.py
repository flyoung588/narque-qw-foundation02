"""One predeclared two-SCF sensitivity experiment, not adaptive second selection."""
import importlib.metadata as md,json,os,pathlib,platform,resource,sys,time,traceback
sys.path.insert(0,'/app')
from router import digest,save
from recovery02r.isolated_router import run_isolated
from periodic03.quality import compare
from periodic03.contract import scope_valid
out=pathlib.Path('/out');out.mkdir(exist_ok=True);start=time.monotonic()
def cg():return {n:(pathlib.Path('/sys/fs/cgroup')/n).read_text().strip() for n in ['memory.max','memory.swap.max','memory.peak','memory.events','memory.oom.group','cpu.max','cpu.stat']}
try:
 scope=json.loads(pathlib.Path('/app/periodic03/SCOPE.json').read_text());plan=json.loads(pathlib.Path('/app/periodic03/PLAN.json').read_text())
 if not scope_valid(scope,'execute',plan):raise RuntimeError('UNAUTHORIZED_OR_UNBOUND_PLAN')
 a=cg();save(out/'admission.json',{'scope':scope,'cgroup':a,'network':os.listdir('/sys/class/net'),'affinity':sorted(os.sched_getaffinity(0))})
 assert a['memory.max']=='1073741824' and a['memory.swap.max']=='0' and a['cpu.max']=='100000 100000' and a['memory.oom.group']=='0' and os.listdir('/sys/class/net')==['lo'] and len(os.sched_getaffinity(0))==1
 save(out/'environment.json',{'python':platform.python_version(),'versions':{x:md.version(x) for x in ['pyscf','numpy','scipy','ase','jsonschema']},'source_sha':os.environ['GITHUB_SHA']});save(out/'plan.json',plan)
 results=[]
 for i,(name,timeout) in enumerate([('KRKS_111',120),('KRKS_222',420)]):
  if time.monotonic()-start>540-timeout:raise RuntimeError('RESOURCE_BLOCKED: insufficient total remaining internal deadline, no further SCF')
  spec=json.loads(pathlib.Path('/app/periodic03/'+name+'.json').read_text());assert digest(spec)==plan['requests'][name]['worldspec_sha256']
  result=run_isolated(spec,out/name,timeout=timeout,worker_path='/app/periodic03/worker.py');results.append(result)
  if result.get('status')!='CALCULATED':raise RuntimeError('SCF_OR_DIAGNOSTIC_FAILED_STOP_NO_RETRY')
  if i==0:
   old=json.loads(pathlib.Path('/app/periodic03/history_RKS.json').read_text());assert digest(old)==plan['historical_observation_canonical_sha256']
   save(out/'RKS_vs_KRKS111.json',compare(old,result))
 save(out/'KPOINT_COMPARISON.json',compare(*results))
 save(out/'AI_feedback_status.json',{'status':'PENDING_BWORK_ACTUAL_OBSERVATION_READING','two_SCFs':'Preplanned controlled comparison, not feedback-adaptive selection','automatic_next_science':False})
except BaseException as e:
 save(out/'FAILURE.json',{'error':str(e),'type':type(e).__name__,'traceback':traceback.format_exc(),'no_retry':True});raise
finally:save(out/'resources.json',{'container_wall_seconds':time.monotonic()-start,'cgroup':cg(),'self_rusage':list(resource.getrusage(resource.RUSAGE_SELF)),'child_rusage':list(resource.getrusage(resource.RUSAGE_CHILDREN))})
