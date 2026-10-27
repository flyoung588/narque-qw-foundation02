"""Future authorized container entry, NOT run by offline QA.
Reuses existing workers and stores; only orchestrates a declared action."""
import pathlib,json,sys,hashlib,platform,importlib.metadata
from router import digest
from interactive01.world import freeze
from world01.session import WorldSession
from frontier01.state import CorrelatedStore
from .fabric import require,LIMITS,SCOPE

def main(io):
 io=pathlib.Path(io);bundle=json.loads((io/'request.json').read_text());grant=json.loads((io/'grant.json').read_text());intent=bundle['intent']
 require(hashlib.sha256((io/'grant.json').read_bytes()).hexdigest()==bundle['grant_sha256'],'WORKER_GRANT_MISMATCH')
 require(grant.get('scope')==SCOPE and grant.get('status')=='HUMAN_GRANTED' and grant.get('limits')==LIMITS,'WORKER_AUTHORITY_MISSING')
 require(intent['authorization_ref']==bundle['grant_sha256'] and intent['experiment_ref']==grant['preregistration_sha256'],'WORKER_SCOPE_MISMATCH')
 require(platform.python_version().startswith('3.12.'),'PYTHON_VERSION_MISMATCH')
 expected={'numpy':'2.2.6','scipy':'1.15.3','jsonschema':'4.25.1','ase':'3.29.0','pyscf':'2.8.0'}
 if intent['model']=='effective':expected['qutip']='5.2.1'
 versions={k:importlib.metadata.version(k) for k in expected};require(versions==expected,'DEPENDENCY_VERSION_MISMATCH');freeze(io/'versions.json',versions)
 root=pathlib.Path(__file__).resolve().parents[1];source=json.loads((io/'source.json').read_text());require(digest(source)==bundle['source_sha256'] and grant['source_sha256']==bundle['source_sha256'],'WORKER_SOURCE_BINDING')
 for rel,h in source.items():require(hashlib.sha256((root/rel).read_bytes()).hexdigest()==h,'WORKER_SOURCE_MISMATCH')
 from birth01.preparation import runtime_probe,resource_check
 facts=runtime_probe();resource_check(facts);require(facts['memory.swap.max']=='0','SWAP_NOT_ZERO');freeze(io/'resources_before.json',facts)
 # Parent and arrays are already staged unchanged by transport. State store reused.
 store=CorrelatedStore(io/'world');parent=store.load(intent['input_state'])
 from frontier01.world_runtime import act,prepare
 if intent['operation']['type']=='PREPARE_CORRELATED_STATE':
  # Preserve the explicit structural parent rather than prepare() creating another source.
  from frontier01.world_runtime import _transition
  state,receipt=_transition(store,intent['request'],parent,intent['operation'],authority=True,resources=True)
 else:state,receipt=act(store,parent,intent['operation'],authority=True,resources=True)
 freeze(io/'worker_result.json',{'state':state['sha256'],'intent_hash':digest(intent),'receipt':receipt,'world_spec':state['payload']['world_spec'],'new_scientific_executions':1,'mode':'NEW_SCIENTIFIC_EXECUTION'})
 freeze(io/'resources_after.json',runtime_probe())
if __name__=='__main__':main(sys.argv[1])
