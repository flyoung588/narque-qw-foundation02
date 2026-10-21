"""World-side supervisor: never import a scientific engine in this process."""
import json,os,pathlib,signal,subprocess,sys,time
from router import digest,save
WORKER=pathlib.Path(__file__).with_name('solver_worker.py')
def run_isolated(spec,outdir,timeout=60,fault=None):
 out=pathlib.Path(outdir).resolve();out.mkdir(parents=True,exist_ok=True);request=out/'input.json';save(request,spec)
 before={k:(pathlib.Path('/sys/fs/cgroup')/k).read_text() for k in ['memory.events','memory.oom.group'] if (pathlib.Path('/sys/fs/cgroup')/k).exists()}
 cmd=[sys.executable,'-B',str(WORKER),str(request),str(out)]
 if fault is not None:cmd+=['--synthetic-fault',fault]
 env={**os.environ,**{k:'1' for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','BLIS_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS']}}
 started=time.monotonic();timed_out=False
 with (out/'solver.stdout.log').open('wb') as stdout,(out/'solver.stderr.log').open('wb') as stderr:
  proc=subprocess.Popen(cmd,stdout=stdout,stderr=stderr,env=env,start_new_session=True)
  save(out/'process_start.json',{'parent_pid':os.getpid(),'solver_pid':proc.pid,'engine':spec.get('physics',{}).get('engine'),'input_sha256':digest(spec),'timeout_seconds':timeout,'synthetic':fault is not None})
  try:code=proc.wait(timeout=timeout)
  except subprocess.TimeoutExpired:
   timed_out=True
   try:os.killpg(proc.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   code=proc.wait(timeout=3)
 raw=out/'observation.json';result=None
 if raw.exists():
  try:result=json.loads(raw.read_text())
  except (ValueError,OSError):pass
 signal_name=signal.Signals(-code).name if code<0 else None
 after={k:(pathlib.Path('/sys/fs/cgroup')/k).read_text() for k in before}
 if timed_out:reason='TIMEOUT'
 elif code<0:reason='NATIVE_SIGNAL_'+signal_name
 elif code:
  failure=out/'worker_failure.json'
  reason='WORKER_MEMORY_ALLOCATION_FAILED' if failure.exists() and json.loads(failure.read_text()).get('type')=='MemoryError' else 'NONZERO_EXIT'
 elif result is None:reason='NO_VALID_OBSERVATION'
 else:reason='SOLVER_RETURNED'
 if code or timed_out or result is None:result={'status':'UNVERIFIED','spec':spec,'world_spec_sha256':digest(spec),'reason':reason,'exit_code':code,'signal':signal_name,'physical_result':None}
 save(out/'process_receipt.json',{'parent_pid':os.getpid(),'solver_pid':proc.pid,'exit_code':code,'signal':signal_name,'timed_out':timed_out,'reason':reason,'wall_seconds':time.monotonic()-started,'cgroup_before':before,'cgroup_after':after,'OOM_attribution':'SIGKILL alone is not proof of OOM; inspect recorded cgroup event deltas. Whole-parent/container death is outside process-isolation proof.','synthetic':fault is not None})
 save(out/'world_return.json',result);return result
