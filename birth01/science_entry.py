"""Prepared one-shot adapter. NOT invoked/authorized during offline acceptance.

Uses the existing structural transition and isolated workers. Approval artifact,
code hashes, Linux cgroup, no-network and once-only intent must all match.
"""
import hashlib,json,pathlib,os,datetime
from interactive01.world import freeze,transition
from recovery02r.isolated_router import run_isolated
from router import digest
from world01.contracts import WorldError
from .preparation import runtime_probe
from .authority import ROOT,LIMITS,approval_check

def check_observation(spec,result):
    import math
    if result.get('status')!='CALCULATED':return result
    try:
        if result.get('synthetic') or result.get('world_spec_sha256')!=digest(spec):raise ValueError('INPUT_BINDING')
        obs=result['observation'];e=obs.get('energy_Eh_per_cell',obs.get('energy'))
        if type(e) not in (int,float) or not math.isfinite(e) or not obs.get('energy_zero'):raise ValueError('ENERGY_REFERENCE')
        if obs.get('SCF_converged',obs.get('converged')) is not True:raise ValueError('SCF_NOT_CONVERGED')
        if not spec['matter']['periodic']:
            f=obs['forces_Eh_per_bohr'];n=len(spec['matter']['atoms'])
            if len(f)!=n or any(len(v)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in v) for v in f):raise ValueError('FORCE_SHAPE_UNITS')
            if max(abs(sum(v[j] for v in f)) for j in range(3))>1e-5:raise ValueError('TRANSLATIONAL_FORCE_SCREEN')
        else:
            if obs.get('forces_status')!='NOT_IMPLEMENTED' or obs.get('kmesh')!=[1,1,1]:raise ValueError('PERIODIC_OBSERVABLE_SAMPLING')
    except (KeyError,TypeError,ValueError) as e:
        return {'status':'UNVERIFIED','world_spec_sha256':digest(spec),'reason':str(e),'raw_solver_return':result}
    return result


def run_scientific(broker,ident):
    # Actual admission is collected locally, never accepted as caller-provided flags.
    plan=broker.execution_plan(ident)
    try:scope=approval_check()
    except WorldError:
        freeze(broker.root/'blocked'/f'{ident}.json',{'status':'BLOCKED','reason':'AUTHORITY_MISSING','plan':plan});raise
    facts=runtime_probe();freeze(broker.root/'resource_admission'/f'{ident}.json',facts)
    input_=json.loads((broker.root/'intents'/f'{ident}.json').read_text());spec=input_['request']['world_spec']
    attempt=broker.root/'attempts'/ident
    if attempt.exists():raise WorldError('NO_IMPLICIT_RETRY')
    # Consumed before invoking any native code. A crash never releases the slot.
    attempt.mkdir(parents=True);freeze(attempt/'authorization.json',scope);freeze(attempt/'input.json',input_)
    source=broker.world.create(spec);state=broker.world.store.load(source['source_state_hash'])
    action={'type':'MEASURE_OBSERVABLE','source_state_sha256':state['sha256'],'observables':spec['physics']['observables']}
    worker=ROOT.parent/plan['worker']
    def existing_engine(request,out):
        raw=run_isolated(request,out,timeout=LIMITS['worker_wall_seconds'],worker_path=worker)
        return check_observation(request,raw)
    try:
        child,receipt=transition(broker.world.store,state,action,existing_engine,authority=True,resources=True,synthetic=False)
        physical=child['payload']['observation']
        if physical.get('status')!='CALCULATED':
            freeze(attempt/'return.json',{'status':'UNVERIFIED','original_return':physical,'new_state_hash':child['sha256']});broker.fail(ident,'SCIENTIFIC_RETURN_UNVERIFIED');return physical
        prov={'mode':'NEW_SCIENTIFIC_EXECUTION','source_file':str(attempt/'input.json'),'raw_byte_sha256':hashlib.sha256((broker.world.root/'states'/f"{child['sha256']}.json").read_bytes()).hexdigest(),'authorization_sha256':digest(scope),'intent':ident,'transition_receipt_hash':digest(receipt)}
        freeze(broker.world.root/'references'/f"{child['sha256']}.json",prov)
        value={'schema':'WB_E01_PHYSICAL_RETURN_01','status':'SIMULATION_OBSERVATION_MODEL_ONLY','intent':ident,'source_state_hash':child['sha256'],'parent_context_hash':input_['request']['source_state_hash'],'world_spec_hash':digest(spec),'values':physical,'transition':receipt,'source_model':spec['physics'],'units':'Original worker units retained','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'W2':'INCOMPLETE','new_physical_execution':True}
        freeze(attempt/'return.json',value);freeze(broker.root/'physical_returns'/f'{ident}.json',value);return value
    except BaseException as e:
        freeze(attempt/'failure.json',{'type':type(e).__name__,'error':str(e),'status':'FAILED','automatic_retry':False})
        broker.fail(ident,'SCIENTIFIC_EXCEPTION');raise

def physical_feedback(broker,ident,result,choice,reason,alternatives,decision_transcript_reference):
    """Work AI authors this after reading; software cannot prove authorship alone."""
    broker._open();p=broker.root/'physical_returns'/f'{ident}.json'
    if not p.exists() or json.loads(p.read_text())!=result or result.get('status')!='SIMULATION_OBSERVATION_MODEL_ONLY':raise WorldError('UNBOUND_PHYSICAL_RETURN')
    if choice not in ['CONTINUE','CHANGE_OBJECT','SWITCH_MODEL','ABANDON','STOP'] or not reason or not alternatives or not decision_transcript_reference:raise WorldError('AI_DECISION_EVIDENCE_REQUIRED')
    h=digest(result);v={'source_state_hash':result['source_state_hash'],'result_hash':h,'choice':choice,'reason':reason,'alternatives':alternatives,'transcript_reference':decision_transcript_reference,'autonomy':'A1_CANDIDATE_REQUIRES_EXTERNAL_TRACE_REVIEW_NOT_A2','time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    freeze(broker.root/'feedback'/f'{h}.json',v)
    if choice in ['STOP','ABANDON']:freeze(broker.root/'STOP.json',{'choice':choice,'reason':reason})
    return h

def compare_physical_returns(broker,first,second,contract=None):
    for value in (first,second):
        p=broker.root/'physical_returns'/f"{value.get('intent')}.json"
        if not p.exists() or json.loads(p.read_text())!=value or value.get('status')!='SIMULATION_OBSERVATION_MODEL_ONLY':raise WorldError('UNBOUND_PHYSICAL_RETURN')
    from world01.fabric import compare
    a=broker.world.store.load(first['source_state_hash']);b=broker.world.store.load(second['source_state_hash']);broker.world._validate_state(a);broker.world._validate_state(b)
    return compare(a,b,contract)
