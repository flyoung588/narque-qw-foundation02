import json,os,pathlib,platform,resource,sys,time,traceback
sys.path.insert(0,'/app')
from router import save
from qw_next.limited_contrast import run
from qw_next.run_frozen import execute
out=pathlib.Path('/out');out.mkdir(exist_ok=True)
def cg():return {k:(pathlib.Path('/sys/fs/cgroup')/k).read_text().strip() for k in ['memory.max','memory.swap.max','memory.current','memory.peak','memory.events','memory.oom.group','cpu.max','cpu.stat']}
t=time.monotonic()
try:
 a=cg();save(out/'admission.json',{'cgroup':a,'network':os.listdir('/sys/class/net'),'affinity':sorted(os.sched_getaffinity(0))})
 assert a['memory.max']=='1073741824' and a['memory.swap.max']=='0' and a['cpu.max']=='100000 100000' and a['memory.oom.group']=='0'
 assert os.listdir('/sys/class/net')==['lo'] and len(os.sched_getaffinity(0))==1
 import importlib.metadata as md
 save(out/'environment.json',{'python':platform.python_version(),'versions':{n:md.version(n) for n in ['numpy','scipy','pyscf','ase','jsonschema']},'sha':os.environ['GITHUB_SHA'],'process_DATA_policy':'inherited/no newly imposed cap in science child; total1GiB cgroup remains','Psi4':'NOT_INSTALLED_OR_REQUESTED'})
 if not run(out/'import_contrast'):raise RuntimeError('NO_CAP_IMPORT_PATH_FAILED_STOP_BEFORE_SCIENCE')
 execute(out/'experiment')
except BaseException as exc:
 save(out/'FAILURE.json',{'type':type(exc).__name__,'error':str(exc),'traceback':traceback.format_exc()});raise
finally:save(out/'resources.json',{'wall_seconds':time.monotonic()-t,'cgroup_end':cg(),'self_rusage':list(resource.getrusage(resource.RUSAGE_SELF)),'children_rusage':list(resource.getrusage(resource.RUSAGE_CHILDREN))})
