"""Hard runtime checks precede any scientific imports or solver launch."""
import importlib.metadata as md,json,os,pathlib,platform,resource,sys,time,traceback
sys.path.insert(0,'/app')
from interactive01.world import freeze
out=pathlib.Path('/out');start=time.monotonic()
def cg():return {n:(pathlib.Path('/sys/fs/cgroup')/n).read_text().strip() for n in ['memory.max','memory.swap.max','memory.peak','memory.events','cpu.max','cpu.stat']}
try:
    a=cg();net=os.listdir('/sys/class/net');aff=sorted(os.sched_getaffinity(0))
    freeze(out/'admission.json',{'cgroup':a,'network':net,'affinity':aff})
    assert a['memory.max']=='1073741824' and a['memory.swap.max']=='0' and a['cpu.max']=='100000 100000' and net==['lo'] and len(aff)==1
    expected={'numpy':'2.2.6','scipy':'1.15.3','ase':'3.29.0','pyscf':'2.8.0','jsonschema':'4.25.1'}
    actual={k:md.version(k) for k in expected}
    freeze(out/'environment.json',{'python':platform.python_version(),'versions':actual,'commit':os.environ['GITHUB_SHA']})
    assert actual==expected and sys.version_info[:2]==(3,12)
    from interactive01.runtime import main
    state,receipt=main();freeze(out/'stage_result.json',{'state':state,'transition':receipt})
    if receipt['status']!='CALCULATED':raise RuntimeError('STAGE_FAILED_NO_RETRY')
except BaseException as e:
    freeze(out/'FAILURE.json',{'type':type(e).__name__,'error':str(e),'traceback':traceback.format_exc(),'no_retry':True});raise
finally:
    freeze(out/'resources.json',{'wall_seconds':time.monotonic()-start,'cgroup':cg(),'self_rusage':list(resource.getrusage(resource.RUSAGE_SELF)),'children_rusage':list(resource.getrusage(resource.RUSAGE_CHILDREN))})
