"""Only the future admitted Linux science container may enter this function."""
import os,sys,pathlib,json,time,platform,importlib.metadata
from router import digest
from interactive01.world import freeze
from .contracts import screen_spec,require
from birth01.preparation import runtime_probe,resource_check
from recovery02r.isolated_router import run_isolated
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
 out=pathlib.Path('/out');request=json.loads(pathlib.Path('/out/request.json').read_text());approval=json.loads((ROOT/'live01/REMOTE_APPROVAL.json').read_text())
 require(approval.get('scope')=='QW-EXPLORER-E01' and approval.get('status')=='HUMAN_GRANTED_E01' and bool(approval.get('human_approval_reference')),'HUMAN_GATE_REQUIRED')
 require(request['remote_approval_hash']==digest(approval),'REMOTE_APPROVAL_MISMATCH')
 import hashlib
 manifest_path=ROOT/'live01/SOURCE_SHA256.json';require(hashlib.sha256(manifest_path.read_bytes()).hexdigest()==approval.get('source_manifest_sha256'),'WORKER_SOURCE_MANIFEST_MISMATCH')
 for name,h in json.loads(manifest_path.read_text()).items():require(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,'WORKER_SOURCE_BYTES_MISMATCH')
 screen_spec(request['spec'])
 require(platform.python_version().startswith('3.12.'),'PYTHON_VERSION_MISMATCH')
 expected={'numpy':'2.2.6','scipy':'1.15.3','jsonschema':'4.25.1','ase':'3.29.0','pyscf':'2.8.0'};versions={k:importlib.metadata.version(k) for k in expected};require(versions==expected,'FIXED_DEPENDENCY_VERSION_MISMATCH');freeze(out/'versions.json',versions)
 facts=runtime_probe();resource_check(facts);require(facts['memory.swap.max']=='0','SWAP_NOT_ZERO');freeze(out/'admission.json',facts)
 raw=run_isolated(request['spec'],out/'solver',timeout=600,worker_path=ROOT/'qw_next/native_worker.py');freeze(out/'observation.json',raw)
 require(raw.get('status')=='CALCULATED','SCIENTIFIC_RETURN_UNVERIFIED')
 freeze(out/'resources_after.json',runtime_probe())
if __name__=='__main__':main()
