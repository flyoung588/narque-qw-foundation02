"""Future Docker execution with existing outer cgroup protection; no network client.
The exact already-built image is supplied by a future source-bound Human grant.
No image pull/install/remote writes from this transport."""
import pathlib,json,shutil,subprocess,os,signal,time,hashlib
from router import digest
from interactive01.world import freeze
from world01.session import filehash,publish_bytes
from .fabric import require,LIMITS
class DockerTransport:
 def __init__(self,repo,image,*,runtime_enabled=False):
  self.repo=pathlib.Path(repo).resolve();self.image=image;self.enabled=runtime_enabled;self._packages={}
 def execute(self,intent,world,attempt,grant_path,grant_sha,source_sha):
  require(self.enabled,'RUNTIME_TRANSPORT_DISABLED')
  require(hasattr(os,'sched_getaffinity'),'LINUX_CGROUP_RUNTIME_REQUIRED')
  cpuset=str(min(os.sched_getaffinity(0)))
  require('@sha256:' in self.image,'IMAGE_DIGEST_REQUIRED')
  grant=json.loads(pathlib.Path(grant_path).read_text());require(grant.get('container_image')==self.image,'IMAGE_NOT_IN_GRANT')
  io=attempt/'container_io';io.mkdir();shutil.copyfile(grant_path,io/'grant.json')
  source={str(p.relative_to(self.repo)):filehash(p) for p in self.repo.rglob('*') if p.is_file() and p.suffix in ('.py','.json') and '__pycache__' not in p.parts and '.git' not in p.parts}
  require(digest(source)==source_sha,'TRANSPORT_SOURCE_CHANGED');freeze(io/'source.json',source)
  freeze(io/'request.json',{'intent':intent,'grant_sha256':grant_sha,'source_sha256':source_sha})
  for folder,pattern in [('states','*.json'),('arrays','*.npz')]:
   for p in (world.root/folder).glob(pattern):publish_bytes(io/'world'/folder/p.name,p.read_bytes())
  # --pull never prevents hidden download/purchase. Read-only source; writable isolated output only.
  name='qw-live-'+digest(intent)[:24];cmd=['docker','run','--pull','never','--name',name,'--network','none','--cpus','1','--cpuset-cpus',cpuset,'--memory','1g','--memory-swap','1g','--pids-limit','64','--cap-drop','ALL','--security-opt','no-new-privileges','--read-only','--tmpfs','/tmp:rw,size=128m','--user',f'{os.getuid()}:{os.getgid()}','-v',f'{self.repo}:/app:ro','-v',f'{io.resolve()}:/io:rw','-w','/app']
  for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','BLIS_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):cmd+=['-e',k+'=1']
  cmd+=['-e','PYTHONDONTWRITEBYTECODE=1',self.image,'python','-B','-m','live_fabric01.worker','/io']
  freeze(attempt/'docker_command.json',cmd);started=time.monotonic();timeout=False
  with (attempt/'stdout.log').open('wb') as out,(attempt/'stderr.log').open('wb') as err:
   p=subprocess.Popen(cmd,stdout=out,stderr=err,start_new_session=True)
   try:code=p.wait(timeout=880)
   except subprocess.TimeoutExpired:
    timeout=True
    subprocess.run(['docker','kill',name],capture_output=True,timeout=5);os.killpg(p.pid,signal.SIGKILL);code=p.wait(timeout=5)
  inspect=subprocess.run(['docker','inspect',name],capture_output=True,text=True,timeout=5);(attempt/'container_inspect.json').write_text(inspect.stdout or '[]')
  freeze(attempt/'transport_exit.json',{'code':code,'timeout':timeout,'wall_seconds':time.monotonic()-started,'auto_retry':False})
  require(not timeout and code==0,'SOLVER_CONTAINER_FAILED_NO_RETRY')
  obj=json.loads(inspect.stdout)[0];host=obj['HostConfig'];require(host['Memory']==LIMITS['memory_bytes'] and host['MemorySwap']==LIMITS['memory_bytes'] and host['NanoCpus']==1000000000 and host['NetworkMode']=='none','ACTUAL_DOCKER_LIMITS_MISMATCH')
  data=json.loads((io/'worker_result.json').read_text());require(data['intent_hash']==digest(intent),'WORKER_INTENT_MISMATCH')
  files={str(p.relative_to(io)):filehash(p) for p in io.rglob('*') if p.is_file()};package={'world_root':str(io/'world'),'result_path':str(io/'worker_result.json'),'state':data['state'],'files':files,'io':str(io)};self._packages[digest(package)]=package
  return package
 def verify_package(self,package):
  require(digest(package) in self._packages,'UNAUTHENTICATED_WORKER_PACKAGE')
  require(all(filehash(pathlib.Path(package['io'])/r)==h for r,h in package['files'].items()),'WORKER_PACKAGE_BYTES_CHANGED')
