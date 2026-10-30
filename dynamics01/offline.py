"""Read-only historical restore + same Explorer synthetic adapter. Zero model/science calls."""
import pathlib,json,tempfile,copy,os
import numpy as np
from router import digest
from world01.session import filehash
from world01.contracts import WorldError
from . import integration
from .adapter import DynamicsWorldSession
from .fabric import DynamicsExecutionFabric
from .runtime import DynamicsExplorer

def setup(root,history):
 history=pathlib.Path(history);man={'local_base':'CORE01_PINNED_ORIGINAL_OUTPUTS_20261017','files':{str(p.relative_to(history)):filehash(p) for p in history.rglob('*') if p.is_file()}}
 world=DynamicsWorldSession(pathlib.Path(root)/'world',history,man,'Dynamics offline integration;0 new scientific Jobs');broker=DynamicsExecutionFabric(pathlib.Path(root)/'broker',world);world.attach(broker)
 states=world.import_core_history(view_path='results/view_payload.json',trajectory_path='results/experiment-0.6.json',state_path='results/experiment-0.6-state.npz');return world,broker,states

def main(out,history):
 out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=False);world,broker,states=setup(out,history)
 before={p:filehash(p) for p in pathlib.Path(history).rglob('*') if p.is_file()}
 obs=world.observe(states['final']);(out/'historical_observation_restored.json').write_text(json.dumps(obs,indent=2))
 cat={states['final']:{'path':'dynamics:'+states['final'],'domain':'dynamics'}}
 def runtime():return DynamicsExplorer(out/'research',world,cat,'OFFLINE ONLY: historical dynamics output → fixture hypothesis → STOP',max_decisions=3,max_reads=5,execution=broker)
 r=runtime();r.seed(states['final'])
 from explorer01.test_runtime import fixture
 # Deterministic software fixture, NEVER represented as real model reasoning.
 class ReplayDecisionFixture:
  def decide(self,req):
   q={'hash':digest(req),'request':req};d=fixture(q,source=states['final'],name='STOP',action='STOP');d['selected']='stop';h=req['context']['memory']['observations'][-1]['hash'];d['observation_refs']=[h];d['resource_reason']='SOFTWARE_FIXTURE_ONLY: historical t=2000au contains finite regional population, not asymptotic reaction probability. No new authorization; STOP.'
   d['memory_updates']=[{'kind':'ModelKnowledge','content':'Fixture inference: surviving norm and integrated absorption distinguish finite-region population from lost probability; need a later-time hypothesis before a new authorized experiment. This is replay, not new science.','evidence_refs':[h]}]
   return json.dumps(d)
 outcomes=r.run(ReplayDecisionFixture(),{'model':'SCRIPTED_ENGINEERING_FIXTURE_NOT_MODEL'},max_steps=1)
 resumed=runtime();stopped=False
 try:resumed.request({'model':'NO_CALL'})
 except WorldError as e:stopped=e.code=='RESEARCH_STOPPED'
 assert stopped and outcomes[-1]['status']=='STOPPED'
 assert not broker.j.query('ExecutionReserved')
 assert all(filehash(p)==h for p,h in before.items())
 (out/'OFFLINE_RESULT.json').write_text(json.dumps({'mode':'HISTORICAL_REAL_REPLAY_PLUS_SYNTHETIC_DECISION_FIXTURE','historical_states':states,'observations_automatically_entered_same_explorer':len(r.j.query('PhysicalEvidence')),'outcomes':outcomes,'checkpoint_resumed_STOP':stopped,'new_model_calls':0,'new_scientific_jobs':0,'historical_files_unchanged':True,'dynamics_time_au':obs['values']['physical_time_au'],'qualification':'Software integration; not new autonomous dynamics evidence'},indent=2))
 return out
if __name__=='__main__':
 import sys
 main(sys.argv[1],sys.argv[2])
