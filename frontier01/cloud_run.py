"""Hard runtime admission; no engine imported into world supervisor."""
import importlib.metadata as md,json,os,pathlib,platform,resource,sys,time,traceback
sys.path.insert(0,'/app')
from interactive01.world import freeze
from recovery02r.isolated_router import run_isolated
from router import digest
ROOT=pathlib.Path('/app');out=pathlib.Path('/out');start=time.monotonic()
def cg():return {n:(pathlib.Path('/sys/fs/cgroup')/n).read_text().strip() for n in ['memory.max','memory.swap.max','memory.peak','memory.events','cpu.max','cpu.stat']}
try:
    req=json.loads((ROOT/'frontier01/REQUEST.json').read_text());scope=json.loads((ROOT/'frontier01/SCOPE.json').read_text())
    if scope['authority']!='HUMAN_GRANTED_PHYSICS_FRONTIER01' or scope['request_sha256']!=digest(req):raise ValueError('FRESH_FRONTIER_AUTHORITY_PENDING')
    c=cg();freeze(out/'admission.json',{'cgroup':c,'network':os.listdir('/sys/class/net'),'affinity':sorted(os.sched_getaffinity(0))})
    if not (c['memory.max']=='1073741824' and c['memory.swap.max']=='0' and c['cpu.max']=='100000 100000' and os.listdir('/sys/class/net')==['lo'] and len(os.sched_getaffinity(0))==1):raise ValueError('HARD_RESOURCE_ADMISSION_FAILED')
    if any(os.environ.get(k)!='1' for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']):raise ValueError('THREAD_ENV')
    expected={'numpy':'2.2.6','scipy':'1.15.3','ase':'3.29.0','pyscf':'2.8.0','qutip':'5.2.1','jsonschema':'4.25.1'}
    versions={k:md.version(k) for k in expected};freeze(out/'environment.json',{'versions':versions,'Python':platform.python_version(),'source_sha':os.environ['GITHUB_SHA']})
    if versions!=expected or sys.version_info[:2]!=(3,12):raise ValueError('FIXED_VERSIONS_REQUIRED')
    freeze(out/'REQUEST.json',req)
    result=run_isolated(req,out/'science',timeout=480,worker_path=ROOT/'frontier01/worker.py');freeze(out/'ACTUAL_RETURN.json',result)
    if result.get('status')!='CALCULATED':raise RuntimeError('SCIENCE_FAILED_STOP_NO_RETRY')
except BaseException as e:
    freeze(out/'FAILURE.json',{'error':str(e),'type':type(e).__name__,'traceback':traceback.format_exc(),'no_retry':True});raise
finally:freeze(out/'resources.json',{'wall_seconds':time.monotonic()-start,'cgroup':cg(),'self_rusage':list(resource.getrusage(resource.RUSAGE_SELF)),'children_rusage':list(resource.getrusage(resource.RUSAGE_CHILDREN))})
