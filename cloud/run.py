import json,os,pathlib,platform,resource,subprocess,sys,time,traceback
from router import save
out=pathlib.Path('/out');out.mkdir(exist_ok=True)
def cg():return {k:(pathlib.Path('/sys/fs/cgroup')/k).read_text() for k in ['memory.max','memory.swap.max','memory.current','memory.peak','memory.events','cpu.max','cpu.stat']}
start=time.monotonic()
try:
 controls=cg();save(out/'admission.json',{'cgroup':controls,'network':os.listdir('/sys/class/net'),'affinity':sorted(os.sched_getaffinity(0))})
 assert controls['memory.max'].strip()=='1073741824' and controls['memory.swap.max'].strip()=='0' and controls['cpu.max'].strip()=='100000 100000'
 assert os.listdir('/sys/class/net')==['lo'] and len(os.sched_getaffinity(0))==1
 save(out/'environment.json',{'python':platform.python_version(),'source_commit':os.environ['GITHUB_SHA'],'installed':subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True)})
 qa=subprocess.run([sys.executable,'-B','-m','unittest','-v','test_software'],capture_output=True,text=True,timeout=10)
 (out/'software_tests.log').write_text(qa.stdout+qa.stderr);assert qa.returncode==0
 from explorer import execute
 request=json.loads(pathlib.Path('/app/'+sys.argv[1]).read_text());execute(request,out/'experiment')
except BaseException as exc:
 save(out/'FAILURE.json',{'type':type(exc).__name__,'error':str(exc),'traceback':traceback.format_exc()});raise
finally:
 save(out/'resources.json',{'wall_seconds':time.monotonic()-start,'self_rusage':list(resource.getrusage(resource.RUSAGE_SELF)),'children_rusage':list(resource.getrusage(resource.RUSAGE_CHILDREN)),'cgroup_end':cg()})
