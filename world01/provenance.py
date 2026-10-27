"""Offline source semantics over existing immutable Store and sealed source map.

A mode string is not evidence. A registered, immutable source binding must lead
back to source bytes pinned in the intake manifest. For new scientific records,
all existing Birth/Transition/native-process links are checked. This verifies
record integrity, not independent physics, authorship or a fresh permission.
"""
import json,pathlib,hashlib,math,datetime
from router import digest
from interactive01.world import verify,freeze,apply
from .contracts import WorldError
KINDS={'HISTORICAL_REPLAY','NEW_SCIENTIFIC_EXECUTION','SYNTHETIC','NEW_STRUCTURE_NOT_CALCULATED'}
NEW='NEW_SCIENTIFIC_EXECUTION'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(test,code):
    if not test:raise WorldError(code)
def read(s,relative):return json.loads(s._source(str(relative)).read_text())
def state_at(s,root,ident):
    require(isinstance(ident,str) and len(ident)==64 and all(c in '0123456789abcdef' for c in ident),'INVALID_EVIDENCE_STATE_ID')
    v=read(s,root/'states'/f'{ident}.json');verify(v);require(v['sha256']==ident,'EVIDENCE_PARENT_MISMATCH');return v

def source_kind(s,relative):
    rel=pathlib.PurePosixPath(relative);ref=rel.parent.parent/'references'/rel.name
    payload=read(s,rel)['payload'];computed=(payload.get('observation') or {}).get('status')=='CALCULATED'
    birth_archive=any(f.startswith(str(rel.parent.parent/'birth/physical_returns')+'/') for f in s.manifest)
    if str(ref) in s.manifest:
        p=read(s,ref);kind=p.get('mode','UNKNOWN')
        require(kind in KINDS,'UNKNOWN_SOURCE_KIND')
        if computed and birth_archive:require(kind in (NEW,'SYNTHETIC'),'PROVENANCE_KIND_MISMATCH')
        return kind,p
    # Legacy archives have no separate provenance sidecar. Their classification
    # is tied to the pinned archive bytes and available legacy transition graph.
    require(not (computed and birth_archive),'SOURCE_PROVENANCE_MISSING')
    return 'HISTORICAL_REPLAY',None

def bind(s,relative,state):
    """Register replay without rewriting any legacy State/Observation/Receipt."""
    kind,original=source_kind(s,relative);rawsha=sha(s._source(relative));ident=state['sha256']
    canonical=s.root/'references'/f'{ident}.json'
    expected={'mode':kind,'source_file':relative,'raw_byte_sha256':rawsha,'source_commit':s.source_snapshot_commit}
    binding=s.root/'evidence_bindings'/f'{ident}.json'
    if canonical.exists():
        previous=json.loads(canonical.read_text())
        require(previous.get('mode')==kind and previous.get('raw_byte_sha256')==rawsha,'PROVENANCE_SOURCE_MISMATCH')
        if binding.exists():
            pinned=json.loads(binding.read_text());require(digest(previous)==pinned['local_provenance_digest'],'PROVENANCE_TAMPERED')
        else:
            # Support exact old cloud provenance as well as an old relative import.
            relative_old=previous.get('source_file')
            valid_original=original is not None and previous==original
            if not valid_original:
                require(isinstance(relative_old,str) and relative_old in s.manifest,'SOURCE_BINDING_MISSING')
                require(sha(s._source(relative_old))==rawsha,'PROVENANCE_SOURCE_MISMATCH')
                oldkind,_=source_kind(s,relative_old);require(oldkind==kind,'PROVENANCE_KIND_MISMATCH')
            freeze(binding,{'source_file':relative,'source_state_sha256':ident,'source_kind':kind,'raw_byte_sha256':rawsha,'local_provenance_digest':digest(previous)})
        freeze(s.root/'reference_aliases'/f'{digest(expected)}.json',expected)
        return previous
    freeze(canonical,expected)
    freeze(binding,{'source_file':relative,'source_state_sha256':ident,'source_kind':kind,'raw_byte_sha256':rawsha,'local_provenance_digest':digest(expected)})
    return expected

def legacy_graph(s,root,state):
    """Check available old receipt conventions without inventing missing fields."""
    p=state['payload'];o=p.get('observation') or {};ident=state['sha256'];matched=[]
    prefix=str(root/'transitions')+'/'
    for rel in s.manifest:
        if not rel.startswith(prefix) or not rel.endswith('/receipt.json'):continue
        r=read(s,rel)
        if r.get('new_state_sha256')!=ident:continue
        intent=read(s,pathlib.PurePosixPath(rel).with_name('intent.json'))
        require(not r.get('synthetic') and not r.get('fixture') and not intent.get('synthetic') and not intent.get('fixture'),'SYNTHETIC_EVIDENCE')
        require(r['action']==intent['action'],'LEGACY_INTENT_ACTION_MISMATCH')
        if r.get('action_sha256'):require(r['action_sha256']==digest(r['action']),'LEGACY_ACTION_HASH_MISMATCH')
        parent=r['source_state_sha256'];ancestor=state_at(s,root,parent)
        if r.get('candidate_state_sha256'):
            candidate=state_at(s,root,r['candidate_state_sha256']);require(p['parent_state_id']==candidate['sha256'] and candidate['payload']['parent_state_id']==parent,'LEGACY_PARENT_MISMATCH')
        else:require(p['parent_state_id']==parent,'LEGACY_PARENT_MISMATCH')
        if r.get('result_sha256'):require(r['result_sha256']==digest(o),'LEGACY_OBSERVATION_HASH_MISMATCH')
        if r.get('observation_sha256'):require(r['observation_sha256']==digest(o),'LEGACY_OBSERVATION_HASH_MISMATCH')
        if p['schema']=='QW_CORRELATED_ELECTRONIC_STATE_01':
            request={'world_spec':p['world_spec'],'correlation_model':p['correlation_model']}
            require(intent.get('request')==request and o.get('request_sha256')==digest(request)==r.get('request_sha256'),'LEGACY_REQUEST_BINDING_MISMATCH')
        elif p['schema']=='QW_EFFECTIVE_QUANTUM_STATE_01':
            require(r.get('arrays_sha256')==p['arrays']['sha256'] and ancestor['payload'].get('model')==p['model'],'LEGACY_MODEL_ARRAY_BINDING_MISMATCH')
        else:
            require(o.get('world_spec_sha256')==digest(p['world_spec']),'LEGACY_SPEC_BINDING_MISMATCH')
            require(apply(ancestor,r['action'])==p['world_spec'],'LEGACY_ACTION_SPEC_MISMATCH')
        matched.append(rel)
    # Initial effective preparation states can have no Observation; that is not
    # evidence of a propagation. Computed observations require their old graph.
    require(bool(matched),'LEGACY_EXECUTION_RECEIPT_MISSING')
    return {'checked_legacy_receipts':matched,'legacy_missing_fields':'Not fabricated; validation follows the original schema, no new authority inferred'}

def new_graph(s,root,state,provenance):
    ident=state['sha256'];p=state['payload'];spec=p['world_spec'];obs=p.get('observation') or {};i=provenance.get('intent')
    require(isinstance(i,str) and len(i)==64 and all(c in '0123456789abcdef' for c in i),'EXECUTION_INTENT_MISSING')
    intent=read(s,root/'birth/intents'/f'{i}.json');require(digest(intent)==i,'EXECUTION_INTENT_HASH_MISMATCH')
    attempt=root/'birth/attempts'/i
    require(read(s,attempt/'input.json')==intent,'EXECUTION_INPUT_MISMATCH')
    ret=read(s,root/'birth/physical_returns'/f'{i}.json');require(read(s,attempt/'return.json')==ret,'EXECUTION_RETURN_MISMATCH')
    require(ret['intent']==i and ret['source_state_hash']==ident and ret['world_spec_hash']==digest(spec) and ret['values']==obs,'OBSERVATION_STATE_BINDING_MISMATCH')
    require(ret['status']=='SIMULATION_OBSERVATION_MODEL_ONLY' and ret['new_physical_execution'] is True and obs.get('status')=='CALCULATED' and not obs.get('synthetic'),'UNVERIFIED_EXECUTION_RETURN')
    require(intent['request']['world_spec']==spec and obs.get('spec')==spec and obs.get('world_spec_sha256')==digest(spec),'REQUEST_SPEC_BINDING_MISMATCH')
    context=intent['request']['source_state_hash'];require(ret['parent_context_hash']==context,'CONTEXT_PARENT_MISMATCH');state_at(s,root,context)
    if intent['request'].get('prior_observation_hash'):
        prior=intent['request']['prior_observation_hash'];feedback=read(s,root/'birth/feedback'/f'{prior}.json')
        require(feedback['source_state_hash']==context and feedback['result_hash']==prior,'PRIOR_FEEDBACK_BINDING_MISMATCH')
        priors=[read(s,pathlib.PurePosixPath(rel)) for rel in s.manifest if rel.startswith(str(root/'birth/physical_returns')+'/') and rel.endswith('.json')]
        require(any(v['source_state_hash']==context and digest(v)==prior for v in priors),'PRIOR_OBSERVATION_MISSING')
    t=ret['transition'];action=t['action'];source=t['source_state_sha256'];tid=digest({'source':source,'action':action});tr=root/'transitions'/tid
    require(read(s,tr/'receipt.json')==t and provenance['transition_receipt_hash']==digest(t),'TRANSITION_RECEIPT_MISMATCH')
    require(t['new_state_sha256']==ident and t['result_sha256']==digest(obs) and t['status']=='CALCULATED' and not t.get('synthetic'),'TRANSITION_OBSERVATION_MISMATCH')
    before=state_at(s,root,source);candidate=state_at(s,root,t['candidate_state_sha256'])
    require(candidate['payload']['parent_state_id']==source and p['parent_state_id']==candidate['sha256'],'EXECUTION_PARENT_MISMATCH')
    require(before['payload']['world_spec']==spec==candidate['payload']['world_spec'] and t['model']==spec['physics']==ret['source_model'],'EXECUTION_MODEL_MISMATCH')
    require(apply(before,action)==spec,'EXECUTION_ACTION_SPEC_MISMATCH')
    ti=read(s,tr/'intent.json');require(ti['action']==action and ti['action_sha256']==digest(action)==t['action_sha256'] and ti['source_state_sha256']==source and action['source_state_sha256']==source and ti['candidate_state_sha256']==candidate['sha256'],'TRANSITION_INTENT_BINDING_MISMATCH')
    require(read(s,tr/'return.json')==obs,'TRANSITION_RETURN_HASH_MISMATCH')
    require(read(s,tr/'solver/input.json')==spec and read(s,tr/'solver/observation.json')==obs and read(s,tr/'solver/world_return.json')==obs,'NATIVE_RETURN_BINDING_MISMATCH')
    proc=read(s,tr/'solver/process_receipt.json');start=read(s,tr/'solver/process_start.json')
    require(proc['exit_code']==0 and proc['timed_out'] is False and proc['synthetic'] is False and proc['reason']=='SOLVER_RETURNED' and start['input_sha256']==digest(spec) and start['synthetic'] is False,'NATIVE_EXECUTION_UNVERIFIED')
    require(start['solver_pid']==proc['solver_pid'] and start['parent_pid']==proc['parent_pid'],'NATIVE_PROCESS_IDENTITY_MISMATCH')
    auth=read(s,attempt/'authorization.json');require(auth.get('status')=='HUMAN_GRANTED_WB_E01' and bool(auth.get('human_approval_reference')) and provenance['authorization_sha256']==digest(auth),'EXECUTION_AUTHORITY_RECORD_MISMATCH')
    require(auth['prereg_sha256']==sha(s._source('birth01/FROZEN_PREREGISTRATION.json')) and auth['code_manifest_sha256']==sha(s._source('birth01/EXECUTION_SOURCE_SHA256.json')),'EXECUTION_AUTHORITY_SCOPE_MISMATCH')
    from birth01.preparation import screen_object,resource_check
    from birth01.authority import LIMITS
    require(auth.get('limits')==LIMITS,'EXECUTION_AUTHORITY_LIMIT_MISMATCH')
    screen_object(spec)
    resource_check(read(s,root/'birth/resource_admission'/f'{i}.json'))
    require(provenance['raw_byte_sha256']==sha(s._source(str(root/'states'/f'{ident}.json'))),'PROVENANCE_RAW_HASH_MISMATCH')
    require(datetime.datetime.fromisoformat(intent['created_utc'])<datetime.datetime.fromisoformat(ret['created_utc']),'INTENT_NOT_BEFORE_RETURN')
    return {'intent':i,'context_parent_state_hash':context,'transition_receipt_sha256':digest(t),'native_process_receipt':str(tr/'solver/process_receipt.json'),'authorization':'Recorded source approval verified; NOT a fresh execution grant','record_integrity':'SEALED_SOURCE_GRAPH_VALIDATED','independent_physics_certification':False}

def classify(s,state,provenance):
    ident=state['sha256'];p=state['payload'];o=p.get('observation') or {};kind=provenance.get('mode','UNKNOWN');base={'source_execution_kind':kind,'source_execution_status':o.get('status','NOT_CALCULATED'),'source_evidence_status':'UNVERIFIED','real_calculated':False,'model_qualification':'NOT_CERTIFIED','current_operation_new_scientific_executions':0}
    try:
        require(kind in KINDS,'UNKNOWN_SOURCE_KIND')
        binding=s.root/'evidence_bindings'/f'{ident}.json';local=s.root/'local_origins'/f'{ident}.json'
        if binding.exists():
            b=json.loads(binding.read_text());require(b['source_state_sha256']==ident and b['source_kind']==kind and b['local_provenance_digest']==digest(provenance),'PROVENANCE_TAMPERED')
            source=s._source(b['source_file']);require(sha(source)==b['raw_byte_sha256']==sha(s.root/'states'/f'{ident}.json'),'LOCAL_SOURCE_BYTES_MISMATCH')
            trusted=json.loads(source.read_text());verify(trusted);require(trusted==state,'STATE_SOURCE_BINDING_MISMATCH')
            expected,original=source_kind(s,b['source_file']);require(expected==kind,'PROVENANCE_KIND_MISMATCH');root=pathlib.PurePosixPath(b['source_file']).parent.parent
            if original is not None:require(original.get('raw_byte_sha256')==sha(source),'ORIGINAL_PROVENANCE_HASH_MISMATCH')
            details={}
            if kind==NEW:details=new_graph(s,root,state,original)
            elif kind=='HISTORICAL_REPLAY' and o.get('status') in ('CALCULATED','CALCULATED_EFFECTIVE_MODEL'):details=legacy_graph(s,root,state)
            base.update(source_evidence_status='VERIFIED_PINNED_RECORDS',evidence=details)
        else:
            require(local.exists(),'EVIDENCE_BINDING_MISSING');v=json.loads(local.read_text())
            require(v['provenance_digest']==digest(provenance) and v['raw_byte_sha256']==sha(s.root/'states'/f'{ident}.json') and v['mode']==kind and kind in ('SYNTHETIC','NEW_STRUCTURE_NOT_CALCULATED'),'LOCAL_ORIGIN_TAMPERED')
            base['source_evidence_status']='VERIFIED_LOCAL_CREATION_NOT_SCIENCE'
        if kind=='SYNTHETIC':base.update(source_execution_status='SYNTHETIC',model_qualification='SOFTWARE_FIXTURE_ONLY')
        elif kind=='NEW_STRUCTURE_NOT_CALCULATED':require(not o,'UNCALCULATED_ORIGIN_HAS_RESULT')
        elif o.get('status') in ('CALCULATED','CALCULATED_EFFECTIVE_MODEL'):
            require(not o.get('synthetic'),'SYNTHETIC_EVIDENCE')
            from .fabric import observation_values
            observation_values(state)
            base.update(real_calculated=True,model_qualification='CALCULATED_MODEL_ONLY_NOT_PHYSICALLY_CERTIFIED')
        elif o:base['model_qualification']='UNVERIFIED_RESULT_NOT_A_CALCULATED_CLAIM'
        base['verified']=True;return base
    except (WorldError,ValueError,KeyError,TypeError,OSError) as e:
        base.update(verified=False,reason_code=e.code if isinstance(e,WorldError) else 'MALFORMED_SOURCE_EVIDENCE',detail=str(e));return base
