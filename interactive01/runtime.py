"""One state operation per separately authorized offline cloud stage."""
import json, os, pathlib, sys
from router import digest
from recovery02r.isolated_router import run_isolated
from .world import Store, freeze, transition, verify

ROOT=pathlib.Path(__file__).resolve().parents[1]
def execute(spec,out):
    # Both existing workers isolate native failures; no solver reimplementation.
    worker=ROOT/('periodic03/worker.py' if spec['matter'].get('periodic') else 'qw_next/native_worker.py')
    return run_isolated(spec,out,timeout=480,worker_path=worker)

def run_stage(bundle,root,authority,resources):
    if not authority or not resources:raise ValueError('EXTERNAL_OR_RESOURCE_ADMISSION_REQUIRED')
    store=Store(root)
    for inherited in bundle.get('inherited_states',[]):
        verify(inherited);freeze(store.root/'states'/f"{inherited['state_id']}.json",inherited)
    source=bundle['source_state'];state=store.create(**bundle['state_creation'])
    if state!=source:raise ValueError('SOURCE_STATE_RECONSTRUCTION_MISMATCH')
    stage=bundle['stage']
    if stage not in (1,2):raise ValueError('ONLY_TWO_STAGES')
    if stage==2:
        parent=source['payload']['parent_state_id']
        while parent is not None:
            ancestor=store.load(parent);parent=ancestor['payload']['parent_state_id']
        obs=source['payload']['observation']
        if not obs or obs.get('status')!='CALCULATED' or obs.get('synthetic'):raise ValueError('FIRST_REAL_OBSERVATION_REQUIRED')
        d=bundle['ai_decision']
        if d['read_observation_sha256']!=digest(obs) or d['action_sha256']!=digest(bundle['action']) or d['source_state_sha256']!=source['sha256']:raise ValueError('UNBOUND_FEEDBACK_DECISION')
        # This check binds stored decisions; chronology/model authorship still
        # requires Work transcript + separate completed first Job, not this flag.
        if not d['first_job_run_id'] or not d['prediction'] or not d['reason']:raise ValueError('INCOMPLETE_FEEDBACK_RECORD')
    freeze(pathlib.Path(root)/'frozen_request.json',bundle)
    return transition(store,state,bundle['action'],execute,authority,resources)

def main():
    bundle=json.loads((ROOT/'interactive01/STAGE_REQUEST.json').read_text())
    scope=json.loads((ROOT/'interactive01/SCOPE.json').read_text())
    if scope.get('authority')!='HUMAN_GRANTED_INTERACTIVE01' or scope.get('request_sha256')!=digest(bundle):raise ValueError('NO_MATCHING_EXECUTION_SCOPE')
    return run_stage(bundle,'/out/world',True,True)
if __name__=='__main__':main()
