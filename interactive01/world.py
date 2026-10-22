"""Thin generic state/action layer. No physical solver or named-material logic."""
import copy, datetime, hashlib, json, math, os, pathlib, tempfile
import numpy as np
from router import digest

def freeze(path, value):
    """Atomically publish once; existing different bytes are never overwritten."""
    p=pathlib.Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    b=(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    fd,name=tempfile.mkstemp(dir=p.parent,prefix='.pending-')
    try:
        with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
        try:os.link(name,p)
        except FileExistsError:
            if p.read_bytes()!=b:raise ValueError('IMMUTABLE_CONFLICT')
    finally:os.unlink(name)
    return hashlib.sha256(b).hexdigest()

def validate(spec):
    if spec['matter'].get('periodic'):
        from periodic03.contract import validate as check
    else:
        from foundation01.contract import validate as check
    check(spec)
    a=spec['matter']['atoms'];xyz=np.array([x['xyz_angstrom'] for x in a],float)
    if xyz.shape!=(len(a),3) or not np.isfinite(xyz).all():raise ValueError('INVALID_COORDINATES')
    if spec['matter'].get('periodic'):
        cell=np.asarray(spec['matter']['cell_angstrom'],float)
        if cell.shape!=(3,3) or not np.isfinite(cell).all() or np.linalg.det(cell)<=0:raise ValueError('INVALID_CELL')
        # Conservative nearest-image screening includes self images; existing ASE
        # solver performs its own complete neighbor check before calculation.
        import itertools
        for i in range(len(a)):
            for j in range(len(a)):
                for t in itertools.product(range(-2,3),repeat=3):
                    if i==j and t==(0,0,0):continue
                    if np.linalg.norm(xyz[i]-xyz[j]+np.array(t)@cell)<.35:raise ValueError('COLLISION')
    else:
        for i in range(len(a)):
            for j in range(i):
                if np.linalg.norm(xyz[i]-xyz[j])<.35:raise ValueError('COLLISION')

def capabilities(spec):
    return {'actions':['DISPLACE_ATOM','MEASURE_OBSERVABLE']+(['AFFINE_STRAIN_CELL'] if spec['matter'].get('periodic') else []),
            'observables':['energy'] if spec['matter'].get('periodic') else ['energy','forces'],
            'response_kind':'ENERGY_ONLY_STRUCTURAL_RESPONSE' if spec['matter'].get('periodic') else 'ANALYTIC_FORCE',
            'availability':'RUNTIME_CHECK_REQUIRED','dynamics':'NOT_IMPLEMENTED'}

class Store:
    def __init__(self,root):self.root=pathlib.Path(root)
    def create(self,spec,reason,parent=None,atom_ids=None,observation=None,quality=None):
        validate(spec);n=len(spec['matter']['atoms'])
        ids=atom_ids or ['atom-'+str(i) for i in range(n)]
        if len(ids)!=n or len(set(ids))!=n:raise ValueError('ATOM_IDENTITY')
        payload={'schema':'QW_PHYSICAL_STATE_01','parent_state_id':parent,'world_spec':copy.deepcopy(spec),
                 'atom_ids':ids,'structure_sha256':digest(spec['matter']),'reason':reason,
                 'observation':copy.deepcopy(observation),'numerical_quality':copy.deepcopy(quality),
                 'supported_operations':capabilities(spec),'interpretation':'SEPARATE_AI_DECISION_ONLY',
                 'state_kind':'STATIC_BO_STRUCTURE_AND_OPTIONAL_SCF_OBSERVATION_NOT_TIME_WAVEFUNCTION'}
        h=digest(payload);state={'state_id':h,'sha256':h,'payload':payload}
        freeze(self.root/'states'/f'{h}.json',state);return copy.deepcopy(state)
    def load(self,ident):
        if not isinstance(ident,str) or len(ident)!=64 or any(x not in '0123456789abcdef' for x in ident):raise ValueError('INVALID_STATE_ID')
        s=json.loads((self.root/'states'/f'{ident}.json').read_text());verify(s)
        if s['state_id']!=ident:raise ValueError('STATE_FILE_ID_MISMATCH')
        return s

def verify(state):
    if digest(state['payload'])!=state['sha256'] or state['sha256']!=state['state_id']:raise ValueError('STATE_HASH_MISMATCH')

def apply(state,action):
    verify(state);p=state['payload'];spec=copy.deepcopy(p['world_spec']);m=spec['matter']
    if action.get('source_state_sha256')!=state['sha256']:raise ValueError('STALE_ACTION')
    kind=action.get('type');allowed={'type','source_state_sha256'}
    if kind=='DISPLACE_ATOM':
        allowed|={'atom_id','vector','unit'}
        if action.get('unit')!='angstrom':raise ValueError('UNIT_REQUIRED')
        d=np.asarray(action['vector'],float)
        if d.shape!=(3,) or not np.isfinite(d).all() or not 0<np.linalg.norm(d)<=.05:raise ValueError('DISPLACEMENT_BOUND')
        i=p['atom_ids'].index(action['atom_id']);m['atoms'][i]['xyz_angstrom']=(np.array(m['atoms'][i]['xyz_angstrom'])+d).tolist()
    elif kind=='AFFINE_STRAIN_CELL':
        allowed|={'deformation','coordinates','unit'}
        if not m.get('periodic') or action.get('unit')!='dimensionless':raise ValueError('STRAIN_DOMAIN_UNIT')
        f=np.asarray(action['deformation'],float)
        if f.shape!=(3,3) or not np.isfinite(f).all() or np.linalg.det(f)<=0 or np.linalg.norm(f-np.eye(3),ord=2)>.020000000001:raise ValueError('STRAIN_BOUND')
        cell=np.asarray(m['cell_angstrom']);m['cell_angstrom']=(cell@f.T).tolist()
        if action['coordinates']=='preserve_fractional':
            for a in m['atoms']:a['xyz_angstrom']=(np.array(a['xyz_angstrom'])@f.T).tolist()
        elif action['coordinates']!='fixed_cartesian':raise ValueError('COORDINATE_POLICY_REQUIRED')
    elif kind=='MEASURE_OBSERVABLE':
        allowed|={'observables'}
        if not action.get('observables') or not set(action['observables'])<=set(capabilities(spec)['observables']):raise ValueError('UNSUPPORTED_OBSERVABLE')
        # Keep solver/model request fixed; supported measured outputs are selected
        # from the existing observation, not a silently changed Hamiltonian.
    else:raise ValueError('UNSUPPORTED_ACTION')
    if set(action)!=allowed:raise ValueError('UNDECLARED_ACTION_FIELDS')
    validate(spec);return spec

def transition(store,state,action,execute=None,authority=False,resources=False,synthetic=False):
    """Candidate is persisted before solver; failed solver cannot erase parent."""
    new_spec=apply(state,action)
    candidate=store.create(new_spec,'ACTION_SEMANTICS_APPLIED',state['state_id'],state['payload']['atom_ids'])
    ident=digest({'source':state['state_id'],'action':action})
    location=store.root/'transitions'/ident
    frozen={'source_state_sha256':state['sha256'],'action':action,'action_sha256':digest(action),
            'candidate_state_sha256':candidate['sha256'],'candidate_structure_sha256':candidate['payload']['structure_sha256'],
            'synthetic':synthetic,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    # Once-only intent, including a failed attempt; no implicit solver retry.
    if location.exists():raise ValueError('TRANSITION_ALREADY_ATTEMPTED')
    location.mkdir(parents=True);freeze(location/'intent.json',frozen)
    result={'status':'BLOCKED','reason':'AUTHORITY_OR_RESOURCE_ADMISSION_PENDING'}
    if authority and resources and execute is not None:
        try:result=execute(new_spec,location/'solver')
        except Exception as e:result={'status':'UNVERIFIED','error':str(e),'type':type(e).__name__}
    freeze(location/'return.json',result)
    valid=result.get('status')=='CALCULATED'
    if valid and not synthetic:
        o=result.get('observation',{});e=o.get('energy_Eh_per_cell',o.get('energy'))
        valid=(result.get('world_spec_sha256')==digest(new_spec) and type(e) in (int,float) and math.isfinite(e)
               and o.get('SCF_converged',o.get('converged',False)) is True)
        if not valid:
            result={'status':'UNVERIFIED','reason':'OBSERVATION_CONTRACT_MISMATCH','raw_solver_return':result}
    if synthetic:result={**result,'synthetic':True}
    observed=store.create(new_spec,'SYNTHETIC_TEST_RETURN' if synthetic else 'SOLVER_RETURN',candidate['state_id'],candidate['payload']['atom_ids'],result,result.get('numerical_quality'))
    receipt={**frozen,'result_sha256':digest(result),'new_state_sha256':observed['sha256'],
             'semantic_action':'APPLIED','physical_transition':'SYNTHETIC_NOT_PHYSICAL' if synthetic else 'CALCULATED_MODEL_ONLY' if valid else 'NOT_PROVEN',
             'status':result.get('status'),'model':new_spec['physics'],
             'resource_evidence':'solver/process_receipt.json; /out/admission.json; /out/resources.json',
             'scope':'Static finite-basis BO calculation; no dynamics/stability/novelty qualification'}
    freeze(location/'receipt.json',receipt);return observed,receipt

def compare_states(a,b):
    verify(a);verify(b)
    x,y=a['payload'],b['payload']
    for key in ['atom_ids']:
        if x[key]!=y[key]:raise ValueError('INCOMPARABLE_ATOMS')
    sa,sb=x['world_spec'],y['world_spec']
    if sa['physics']!=sb['physics'] or any(sa['matter'][k]!=sb['matter'][k] for k in ['charge','spin_2S','periodic']) or [t['element'] for t in sa['matter']['atoms']]!=[t['element'] for t in sb['matter']['atoms']]:raise ValueError('INCOMPARABLE_PHYSICS')
    def energy(p):
        r=p['observation']
        if not r or r.get('status')!='CALCULATED' or r.get('synthetic'):raise ValueError('NO_REAL_CALCULATED_OBSERVATION')
        o=r['observation'];return o.get('energy_Eh_per_cell',o.get('energy'))
    ea,eb=energy(x),energy(y)
    if ea is None or eb is None:raise ValueError('ENERGY_UNAVAILABLE')
    if x['observation']['observation'].get('energy_zero')!=y['observation']['observation'].get('energy_zero'):raise ValueError('INCOMPARABLE_ENERGY_REFERENCE')
    return {'delta_energy_Eh':eb-ea,'first_state':a['sha256'],'second_state':b['sha256'],
            'interpretation':'FINITE_STRUCTURE_PATH_RESPONSE_NOT_FORCE_OR_STABILITY',
            'numerical_caveat':'Inspect both raw qualities and realized GDF/grid settings; nominal equality does not isolate numerical error.'}
