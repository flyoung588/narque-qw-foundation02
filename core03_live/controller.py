"""Executable host for one frozen operation. No dispatch on import/preparation."""
import pathlib,json
from router import digest
from world01.session import filehash
from live_fabric01.fabric import LIMITS,require
from live_fabric01.github_transport import GithubFabricTransport
from .session import CoupledWorldSession
from .fabric import CoupledExecutionFabric

def setup(root):
 r=pathlib.Path(root).resolve();h=r/'history';manifest={'local_base':'CORE03_4d6f2566','files':{p.name:filehash(p) for p in h.iterdir() if p.is_file()}}
 w=CoupledWorldSession(r/'world',h,manifest,'QW-LIVE-CORE03-01 paired control integration')
 parent=w.import_history()['source_state_hash'];return w,parent
def run_one(root,grant_sha,intent_path):
 r=pathlib.Path(root).resolve();gp=r/'LIVE_SCIENCE_AUTHORITY.json';require(filehash(gp)==grant_sha,'CORE03_GRANT_PIN_REQUIRED');g=json.loads(gp.read_text());require(g.get('release')=='QW-LIVE-CORE03-01' and g.get('status')=='HUMAN_GRANTED' and g.get('human_reference'),'NEW_CORE03_EXECUTION_AUTHORIZATION_REQUIRED')
 require(g.get('zero_additional_cost_verified') is True and g.get('cost_evidence_ref'),'CORE03_COST_UNCONFIRMED')
 source={str(p.relative_to(r/'repo')):filehash(p) for p in (r/'repo').rglob('*') if p.is_file() and p.suffix in ('.py','.json','.f90','.npz') and '__pycache__'not in p.parts and '.git'not in p.parts};require(digest(source)==g['source_sha256'],'CORE03_SOURCE_CHANGED')
 w,parent=setup(r);transport=GithubFabricTransport(r/'remote',runtime_enabled=True);b=CoupledExecutionFabric(r/'broker',w,grant_path=gp,grant_sha256=grant_sha,source_hash=g['source_sha256'],transport=transport);w.attach(b);i=json.loads(pathlib.Path(intent_path).read_text())
 # Existing Broker reserves before POST and refuses duplicate physical requests.
 result=w.execute_physics(i);observation=w.observe(result['state']);out={'result':result,'observation':observation};(r/('RETURN_'+digest(i)+'.json')).write_text(json.dumps(out,indent=2));return out
if __name__=='__main__':
 import sys
 print(json.dumps(run_one(*sys.argv[1:]),indent=2))
