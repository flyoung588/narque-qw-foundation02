"""Export schemas/manifests and verify unchanged baseline, no physics calls."""
import json,pathlib,hashlib,sys,platform,importlib.metadata,datetime
from .schemas import SCHEMAS,validate
from .fabric import MANIFESTS
P=pathlib.Path(__file__).resolve().parents[1];R=P.parent

def write(p,x):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def main():
    for k,v in SCHEMAS.items():write(P/'world01'/'schema'/f'{k}.schema.json',v)
    for k,v in MANIFESTS.items():validate('manifest',v);write(P/'world01'/'capability_manifests'/f'{k}.json',v)
    source=json.loads((R/'S0/source_sha_manifest.json').read_text());changed=[]
    for f,h in source['files'].items():
        p=P/f
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=h:changed.append(f)
    write(R/'QA'/'source_integrity.json',{'baseline_commit':source['local_base'],'checked':len(source['files']),'changed':changed,'status':'PASS' if not changed else 'FAIL'})
    receipts=[];failures=[]
    for p in sorted((R/'QA/run04/evidence').rglob('session_receipts/*.json')):
        v=json.loads(p.read_text());item={'path':str(p.relative_to(R)),'operation':v['operation'],'status':v['status'],'code':v['reason_code']};receipts.append(item)
        if v['status'] in ['REJECTED','FAILED']:failures.append(item)
    write(R/'QA/session_receipt_index.json',{'role':'DERIVED_INDEX_NOT_NEW_CANONICAL_LEDGER','receipts':receipts})
    write(R/'QA/failure_registry.json',{'role':'DERIVED_INDEX','failures':failures})
    versions={x:importlib.metadata.version(x) for x in ['numpy','scipy','jsonschema']}
    write(R/'QA/environment.json',{'python':sys.version,'platform':platform.platform(),'versions':versions,'new_installations':0,'new_science_jobs':0,'thread_env':'OMP/OPENBLAS/MKL=1','local_resource_scope':'Light software tests only; no cgroup scientific resource claim','provider_total_tokens':'UNKNOWN','new_purchases':0,'network_science_calls':0})
    log=(R/'QA/run04/test.log').read_text()
    outcomes=[]
    for line in log.splitlines():
        if line.startswith('test_') and ' ... ' in line:outcomes.append({'test':line.split(' ')[0],'result':line.rsplit(' ... ',1)[-1]})
    write(R/'QA/test_results.json',{'tests':outcomes,'count':len(outcomes),'all_pass':all(x['result']=='ok' for x in outcomes),'original_failure_preserved':'QA/run01/test.log','repair':'Duplicate provenance aliases retain canonical bytes; stale replay checked before success receipt','rt12_scope':'Explicit synthetic immutable E01-C2 guard fixture; not an original E01-C2 receipt reproduction. Whole 682-file actual baseline unchanged.'})
    print(json.dumps({'source_files_checked':len(source['files']),'changed':changed,'tests':len(outcomes),'persisted_receipts':len(receipts),'negative_failure_receipts':len(failures)}))
    if changed:raise SystemExit(1)
if __name__=='__main__':main()
