"""One isolated new-domain worker, inherited supervisor handles native failures."""
import json,pathlib,resource,sys,traceback
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from interactive01.world import freeze,verify
from router import digest
from state_space01.state import QuantumStore
from state_space01.world_runtime import act
from state_space01.excitation import build_model
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
def operate(store,state,action):return act(store,state,action,authority=True,resources=True)
request=json.loads(pathlib.Path(sys.argv[1]).read_text());out=pathlib.Path(sys.argv[2]);store=QuantumStore(out/'world')
try:
    if request['stage']==1:
        spec=request['world_spec'];root=store.create(spec,'STRUCTURAL_SOURCE_FOR_NEW_ELECTRONIC_DOMAIN')
        freeze(out/'structural_source.json',root)
        model=build_model(spec,out/'electronic',request['first_control']['polarization'])
        state=store.save(parent=root['sha256'],world_spec=spec,model=model,ket=[1,0],time_au=0,reason='PREPARE_REFERENCE_EFFECTIVE_STATE')
        state,_=operate(store,state,{'type':'APPLY_EXTERNAL_FIELD','source_state_sha256':state['sha256'],'control':request['first_control']})
        state,receipt=operate(store,state,{'type':'EVOLVE_QUANTUM_STATE','source_state_sha256':state['sha256'],'duration_au':request['first_control']['duration_au'],'time_unit':'atomic_time'})
    elif request['stage']==2:
        # The imported scientific arrays are real NPZ bytes, not JSON amplitudes.
        # They must be prepared only after completed Job1 and Work AI decision.
        source_dir=ROOT/'state_space01/inherited';import shutil
        for p in sorted(source_dir.rglob('*')):
            if not p.is_file():continue
            rel=p.relative_to(source_dir);dest=store.root/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
        state=store.load(request['source_state_sha256']);arrays=store.arrays(state)
        ancestor=state
        while ancestor['payload']['parent_state_id'] is not None:
            ancestor=store.load(ancestor['payload']['parent_state_id'])
        decision=request['ai_decision']
        if decision['source_state_sha256']!=state['sha256'] or decision['observation_sha256']!=digest(state['payload']['observation']) or not decision['first_job_run_id']:raise ValueError('UNBOUND_POSTOBSERVATION_DECISION')
        if decision['actions_sha256']!=digest(request['actions']):raise ValueError('UNBOUND_ACTIONS')
        if not 1<=len(request['actions'])<=3 or sum(a['type']=='EVOLVE_QUANTUM_STATE' for a in request['actions'])!=1:raise ValueError('ONE_NEW_PHYSICAL_PROPAGATION_REQUIRED')
        # Work freezes a bounded sequence after observation; only source hash of
        # subsequent operations is filled from actual preceding immutable output.
        for item in request['actions']:
            action={**item,'source_state_sha256':state['sha256']};state,receipt=operate(store,state,action)
    else:raise ValueError('STAGE_DOMAIN')
    result={'status':'CALCULATED','domain':'RESPONSE_DERIVED_EFFECTIVE_QUANTUM_DYNAMICS','request_sha256':digest(request),'state':state,'observation':state['payload']['observation'],'last_transition':receipt,'model_accuracy':'NOT_CERTIFIED','full_electron_realtime':'NOT_IMPLEMENTED'}
    freeze(out/'observation.json',result)
except BaseException as e:
    freeze(out/'worker_failure.json',{'status':'UNVERIFIED','type':type(e).__name__,'error':str(e),'traceback':traceback.format_exc(),'partial_electronic_and_dynamics_evidence_preserved':True});raise
