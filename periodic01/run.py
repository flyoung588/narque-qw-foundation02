import importlib.metadata as md,json,os,pathlib,platform,sys,time,traceback
sys.path.insert(0,'/app')
from router import save
from recovery02r.isolated_router import run_isolated
out=pathlib.Path('/out');out.mkdir(exist_ok=True);t=time.monotonic()
def cg():return {k:(pathlib.Path('/sys/fs/cgroup')/k).read_text().strip() for k in ['memory.max','memory.swap.max','memory.current','memory.peak','memory.events','memory.oom.group','cpu.max','cpu.stat']}
try:
 a=cg();save(out/'admission.json',{'cgroup':a,'network':os.listdir('/sys/class/net'),'affinity':sorted(os.sched_getaffinity(0))})
 assert a['memory.max']=='1073741824' and a['memory.swap.max']=='0' and a['cpu.max']=='100000 100000' and a['memory.oom.group']=='0'
 assert os.listdir('/sys/class/net')==['lo'] and len(os.sched_getaffinity(0))==1
 save(out/'environment.json',{'python':platform.python_version(),'versions':{n:md.version(n) for n in ['numpy','scipy','pyscf','ase','jsonschema']},'sha':os.environ['GITHUB_SHA']})
 spec=json.loads(pathlib.Path('/app/periodic01/input.json').read_text())
 result=run_isolated(spec,out/'base',timeout=540,worker_path='/app/periodic01/worker.py')
 save(out/'P3.json',{'status':'NOT_STARTED','reason':'No live B-Work AI feedback channel inside single offline Job; do not preselect a strain or claim scripted adaptation.'})
 if result['status']!='CALCULATED':raise RuntimeError('BASE_PERIODIC_FAILED_NO_RETRY')
except BaseException as exc:
 save(out/'FAILURE.json',{'type':type(exc).__name__,'error':str(exc),'traceback':traceback.format_exc()});raise
finally:save(out/'resources.json',{'wall_seconds':time.monotonic()-t,'cgroup_end':cg()})
