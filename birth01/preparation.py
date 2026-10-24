"""Thin approval/intent/feedback broker over the existing WorldSession.

No solver implementation or automatic AI policy. Scientific dispatch is fail
closed in this preparation build. Handoff plans name audited existing workers.
"""
import json,pathlib,datetime,copy,math,os
from jsonschema import Draft202012Validator
from interactive01.world import freeze
from router import digest
from world01.contracts import WorldError
from world01 import fabric
ROOT=pathlib.Path(__file__).resolve().parent
SCHEMA={'type':'object','additionalProperties':False,'required':['source_state_hash','world_spec','action','prediction','falsifier','information_goal','candidate_reasons','prior_observation_hash','actor'], 'properties':{
'source_state_hash':{'type':'string','pattern':'^[0-9a-f]{64}$'},'world_spec':{'type':'object'},'action':{'enum':['MEASURE_OBSERVABLE','CHANGE_OBJECT']},'prediction':{'type':'string','minLength':1},'falsifier':{'type':'string','minLength':1},'information_goal':{'type':'string','minLength':1},'candidate_reasons':{'type':'array','minItems':2,'items':{'type':'object','required':['candidate','reason']}},'prior_observation_hash':{'type':['string','null'],'pattern':'^[0-9a-f]{64}$'},'actor':{'const':'B_WORK_AI_DECISION_REQUIRES_TRANSCRIPT_REVIEW'}}}
from .authority import LIMITS
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def resource_check(facts):
    required={'memory.max','memory.swap.max','cpu.max','memory.current','memory.events','cpu.stat','interfaces','threads','affinity_count'}
    if not required<=set(facts):raise WorldError('RESOURCE_EVIDENCE_INCOMPLETE')
    try:q,p=map(int,facts['cpu.max'].split());mem=int(facts['memory.max']);swap=int(facts['memory.swap.max'])
    except (ValueError,TypeError):raise WorldError('RESOURCE_UNBOUNDED')
    if not 0<mem<=2**30 or swap!=0 or not 0<q<=p or facts['interfaces']!=['lo'] or facts['threads']!=1 or facts['affinity_count']!=1:raise WorldError('RESOURCE_BLOCKED')
    return {'status':'RESOURCE_EVIDENCE_SCREEN_PASSED','not_proof_of_future_runtime':True}
def runtime_probe():
    cg=pathlib.Path('/sys/fs/cgroup')
    if not cg.is_dir():raise WorldError('RUNTIME_ADMISSION_PENDING')
    try:f={x:(cg/x).read_text().strip() for x in ['memory.max','memory.swap.max','cpu.max','memory.current','memory.events','cpu.stat']};f.update(interfaces=sorted(os.listdir('/sys/class/net')),threads=int(os.environ.get('OMP_NUM_THREADS','0')),affinity_count=len(os.sched_getaffinity(0)))
    except (OSError,ValueError,AttributeError):raise WorldError('RUNTIME_ADMISSION_PENDING')
    resource_check(f);return f

def screen_object(spec):
    fabric.validate_object(spec);m=spec['matter'];p=spec['physics'];atoms=m['atoms']
    if m['periodic']:
        # Small-cell envelope, not arbitrary materials. Reuse legacy RKS, Gamma only.
        if len(atoms)!=1 or atoms[0]['element']!='Ne' or p!={'engine':'pyscf-pbc','method':'RKS','basis':'cc-pvdz','xc':'PBE','observables':['energy']}:raise WorldError('E01_SMALL_CELL_DOMAIN')
        import numpy as np
        cell=np.asarray(m['cell_angstrom']);a=(float(np.linalg.det(cell))*4)**(1/3)
        expected=np.array([[0,a/2,a/2],[a/2,0,a/2],[a/2,a/2,0]])
        if not 4.40<=a<=4.52 or not np.allclose(cell,expected,atol=1e-10) or atoms[0]['xyz_angstrom']!=[0,0,0]:raise WorldError('E01_FCC_ENVELOPE')
        return {'domain':'periodic','worker':'periodic03/worker.py','AO_upper':14,'method':'RKS/PBE','observables':['energy']}
    from foundation01.contract import validate as valid
    meta=valid(spec)
    if not 1<=len(atoms)<=3 or meta['electron_count']>12 or m['spin_2S']!=0 or p!={'engine':'pyscf','method':'RHF','basis':'cc-pvdz','observables':['energy','forces']}:raise WorldError('E01_MOLECULAR_DOMAIN')
    # H/He basis5, Li..Ne14 spherical cc-pVDZ AOs; strict static dimension cap.
    ao=sum(5 if x['element'] in ('H','He') else 14 for x in atoms)
    if ao>24:raise WorldError('E01_AO_RESOURCE_SCREEN')
    return {'domain':'molecular','worker':'qw_next/native_worker.py','AO_upper':ao,'method':'RHF','observables':['energy','forces']}

class BirthPreparation:
    def __init__(self,session,root):
        self.world=session;self.root=pathlib.Path(root);self.root.mkdir(parents=True,exist_ok=True)
        freeze(self.root/'contract.json',{'limits':LIMITS,'science_execution':'REQUIRES_MATCHING_HUMAN_APPROVAL_ARTIFACT','autonomy_target':'A1_WORK_AI_NOT_A2','model_policy':'No preprogrammed second action'})
    def _open(self):
        if (self.root/'STOP.json').exists():raise WorldError('EXPERIMENT_STOPPED')
    def submit(self,request):
        self._open();Draft202012Validator(SCHEMA).validate(request)
        env=self.world.load(request['source_state_hash']);route=screen_object(request['world_spec'])
        for p in (self.root/'intents').glob('*.json'):
            if json.loads(p.read_text())['request']==request:raise WorldError('NO_IMPLICIT_RETRY')
        previous=list((self.root/'intents').glob('*.json'))
        if len(previous)>=LIMITS['max_jobs']:raise WorldError('BUDGET_EXHAUSTED')
        if previous:
            h=request['prior_observation_hash']
            if not h or not (self.root/'feedback'/f'{h}.json').exists():raise WorldError('FEEDBACK_REQUIRED_BEFORE_SECOND_ACTION')
            feedback=json.loads((self.root/'feedback'/f'{h}.json').read_text())
            if feedback['source_state_hash']!=request['source_state_hash']:raise WorldError('STALE_PARENT')
        elif request['prior_observation_hash'] is not None:raise WorldError('NO_PRIOR_RESULT_IN_NEW_EXPERIMENT')
        if request['action']!='CHANGE_OBJECT' and request['world_spec']!=self.world.store.load(request['source_state_hash'])['payload']['world_spec']:
            from interactive01.world import apply
            # Geometry interventions require explicit existing Action envelope;
            # this preflight currently permits measurement/new-object requests only.
            raise WorldError('UNFROZEN_GEOMETRY_ACTION')
        v={'request':copy.deepcopy(request),'route':route,'created_utc':now(),'source_raw_hash':env['provenance']['raw_byte_sha256'],'source_model_hash':env['model_hash'],'status':'INTENT_FROZEN_NOT_EXECUTED','resource_limits':LIMITS}
        ident=digest(v);freeze(self.root/'intents'/f'{ident}.json',v);return ident
    def execution_plan(self,ident):
        self._open();v=json.loads((self.root/'intents'/f'{ident}.json').read_text())
        if digest(v)!=ident:raise WorldError('INTENT_HASH_MISMATCH')
        return {'intent_hash':ident,'worker':v['route']['worker'],'request_hash':digest(v['request']['world_spec']),'supervisor':'recovery02r.isolated_router.run_isolated','state_store':'Existing CorrelatedStore/QuantumStore/Store','stage':'PREPARATION_ONLY','new_solver':False}
    def execute(self,ident):
        from .science_entry import run_scientific
        return run_scientific(self,ident)
    def fixture_return(self,ident,values,*,spec_hash):
        self._open();v=json.loads((self.root/'intents'/f'{ident}.json').read_text())
        if digest(v)!=ident:raise WorldError('INTENT_HASH_MISMATCH')
        if spec_hash!=digest(v['request']['world_spec']):raise WorldError('RESULT_INPUT_MISMATCH')
        if values.get('status')=='CALCULATED':raise WorldError('SYNTHETIC_MISLABEL_BLOCKED')
        rec={'intent':ident,'source_state_hash':v['request']['source_state_hash'],'world_spec_hash':spec_hash,'values':values,'status':'SOFTWARE_FIXTURE_ONLY','time_utc':now()}
        freeze(self.root/'returns'/f'{ident}.json',rec);return rec
    def feedback(self,ident,result,choice,reason,alternatives):
        self._open();p=self.root/'returns'/f'{ident}.json'
        if not p.exists() or json.loads(p.read_text())!=result:raise WorldError('RESULT_NOT_READ_OR_UNBOUND')
        if choice not in ['CONTINUE','CHANGE_OBJECT','SWITCH_MODEL','ABANDON','STOP'] or not reason or not alternatives:raise WorldError('DECISION_RATIONALE_REQUIRED')
        v={'result_hash':digest(result),'source_state_hash':result['source_state_hash'],'choice':choice,'reason':reason,'alternatives':alternatives,'status':'A0_FIXTURE_DECISION_NOT_A1_EVIDENCE','time_utc':now()};h=digest(result);freeze(self.root/'feedback'/f'{h}.json',v)
        if choice in ['STOP','ABANDON']:freeze(self.root/'STOP.json',{'choice':choice,'reason':reason})
        return h
    def fail(self,ident,reason):
        self._open();freeze(self.root/'failures'/f'{ident}.json',{'reason':reason,'status':'FAILED','new_science':False});freeze(self.root/'STOP.json',{'choice':'STOP','reason':reason})
