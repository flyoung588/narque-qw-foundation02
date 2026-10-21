"""Real OS fault injection, synthetic data only; no physical engine import."""
import hashlib,json,os,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from recovery02r.isolated_router import run_isolated
from router import save
def test(out):
 out=pathlib.Path(out);pid=os.getpid();spec={'physics':{'engine':'SYNTHETIC_NOT_A_PHYSICAL_SOLVER'}}
 first=run_isolated(spec,out/'before',fault='ok');raw=out/'before/observation.json';h=hashlib.sha256(raw.read_bytes()).hexdigest();rows={}
 for mode in ['segv','kill','timeout','exception','memory']:
  result=run_isolated(spec,out/mode,timeout=.3 if mode=='timeout' else 3,fault=mode)
  receipt=json.loads((out/mode/'process_receipt.json').read_text());assert result['status']=='UNVERIFIED' and receipt['solver_pid']!=pid and os.getpid()==pid
  assert hashlib.sha256(raw.read_bytes()).hexdigest()==h
  rows[mode]=receipt
 assert rows['segv']['signal']=='SIGSEGV' and rows['kill']['signal']=='SIGKILL' and rows['timeout']['timed_out']
 last=run_isolated(spec,out/'after',fault='ok');assert first['status']==last['status']=='SYNTHETIC_OK'
 memory_error=json.loads((out/'memory/worker_failure.json').read_text())
 memory_status='MEMORY_ERROR_ISOLATED' if memory_error['type']=='MemoryError' else 'LIMIT_SETUP_UNSUPPORTED_NOT_A_MEMORY_ALLOCATION_TEST'
 result={'status':'ENGINE_FAILURE_ISOLATION_PROVEN','scope':'Actual child SIGSEGV/SIGKILL/timeout/Python exception; parent continued and synthetic completed record hash unchanged. Memory-limit result separately classified, no physical or whole-container OOM guarantee.','parent_pid':pid,'completed_result_sha256':h,'faults':rows,'physical_calculations':0,'memory_limit_test':memory_status,'whole_container_OOM':'NOT_TESTED','parent_survived':True,'continued_after_fault':True}
 save(out/'ISOLATION_QA.json',result);return result
if __name__=='__main__':print(json.dumps(test(sys.argv[1]),indent=2))
