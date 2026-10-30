"""New propagation container branch. Never invoked by offline integration."""
import json
from router import digest
from interactive01.world import freeze
from world01.session import filehash
from live_fabric01.fabric import require
from .adapter import save_state
from .model import transition_arrays,validate_arrays

def execute(io,intent,store):
 from birth01.preparation import runtime_probe,resource_check
 facts=runtime_probe();resource_check(facts);require(facts['memory.swap.max']=='0','SWAP_NOT_ZERO')
 parent=store.load(intent['input_state']);a=store.arrays(parent);p=parent['payload'];validate_arrays(a,p['model']);require(intent['operation']['source_state_sha256']==parent['sha256'],'PHYSICAL_PARENT_MISMATCH')
 if intent['operation']['type'] in ('PREPARE_WAVEPACKET','PREPARE_AND_EVOLVE_WAVEPACKET'):
  from . import core_world
  import pathlib
  require(pathlib.Path('/opt/qw-core/vendor/liblsth.so').is_file(),'LSTH_PREPARATION_LIBRARY_UNAVAILABLE')
  core_world.ROOT=pathlib.Path('/opt/qw-core')
 arrays,change=transition_arrays(a,p,intent['operation'])
 # Store and publish primitives remain the same; wrapper only supplies root/store.
 from types import SimpleNamespace
 world=SimpleNamespace(root=store.root,store=store)
 state=save_state(world,arrays,p['model'],parent=parent['sha256'],provenance={'mode':'NEW_SCIENTIFIC_EXECUTION','intent_sha256':digest(intent),'resources':facts},**change)
 from .model import observe_arrays
 observation=observe_arrays(arrays,state['payload'])
 receipt={'source_state_sha256':parent['sha256'],'new_state_sha256':state['sha256'],'action':intent['operation'],'action_sha256':digest(intent['operation']),'time_before_au':p['time_au'],'time_after_au':state['payload']['time_au'],'array_sha256':state['payload']['arrays']['sha256'],'result_sha256':digest(observation)}
 freeze(io/'worker_result.json',{'state':state['sha256'],'intent_hash':digest(intent),'receipt':receipt,'observation':observation,'new_scientific_executions':1,'mode':'NEW_SCIENTIFIC_EXECUTION'})
 freeze(io/'resources_after.json',runtime_probe())
