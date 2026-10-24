"""Deterministic control shell; A0 fixtures are never A2 scientific experiments."""
import datetime,json
from router import digest
from interactive01.world import freeze
from .contracts import WorldError
CHOICES={'CONTINUE','FORK','CHANGE_MODEL','CHANGE_OBJECT','ABANDON','STOP','SWITCH_MODEL'}
class ExplorerHarness:
    def __init__(self,session):self.session=session;self.root=session.root/'explorer'
    def plan(self,source,goal,candidates,selected,prediction,falsifier,prior_reads=(),level='A0'):
        self.session._open();self.session.load(source)
        if level!='A0':raise WorldError('REAL_AUTONOMY_NOT_AUTHORIZED','E00 exercises A0 fixture shell only; historical A1 remains history')
        if not goal or not prediction or not falsifier or not candidates or selected not in [x['id'] for x in candidates]:raise WorldError('INCOMPLETE_PLAN')
        if len(set(x['id'] for x in candidates))!=len(candidates) or any(not x.get('reason') for x in candidates):raise WorldError('CANDIDATE_RATIONALE_REQUIRED')
        for h in prior_reads:
            p=self.session.root/'session_receipts'/f'{h}.json'
            if not p.exists() or json.loads(p.read_text())['operation'] not in ('observe','fixture_observe'):raise WorldError('OBSERVATION_NOT_READ')
        v={'source_state_hash':source,'goal':goal,'candidates':candidates,'selected':selected,'prediction':prediction,'falsifier':falsifier,'prior_reads':list(prior_reads),'autonomy_level':'A0_SCRIPTED_SOFTWARE_FIXTURE','time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cost':'Offline software only; new physical solves0'}
        h=digest(v);freeze(self.root/'plans'/f'{h}.json',v);return h
    def fixture_observe(self,source,values):
        env=self.session.load(source)
        if env['provenance']['mode']!='SYNTHETIC':raise WorldError('FIXTURE_REQUIRES_SYNTHETIC_STATE')
        if values.get('status')=='CALCULATED':raise WorldError('SYNTHETIC_MISLABEL_BLOCKED')
        v={'schema':'QW_OBSERVATION_ENVELOPE_01','source_state_hash':source,'status':'SOFTWARE_FIXTURE_ONLY','values':values,'provenance':{'mode':'SYNTHETIC'},'new_physics_run':False}
        r=self.session.receipt('fixture_observe','SOFTWARE_FIXTURE_ONLY','NOT_PHYSICAL',source,observation_sha256=digest(v))
        return {**v,'read_receipt_sha256':r['receipt_sha256']}
    def return_observation(self,plan,observation):
        p=json.loads((self.root/'plans'/f'{plan}.json').read_text());h=observation['read_receipt_sha256'];path=self.session.root/'session_receipts'/f'{h}.json'
        if not path.exists():raise WorldError('OBSERVATION_NOT_READ')
        r=json.loads(path.read_text());v={k:x for k,x in observation.items() if k!='read_receipt_sha256'}
        if digest(r)!=h or r.get('observation_sha256')!=digest(v):raise WorldError('OBSERVATION_HASH_MISMATCH')
        if r['time_utc']<=p['time_utc'] or h in p['prior_reads']:raise WorldError('PREDICTION_AFTER_RESULT')
        state=self.session.store.load(observation['source_state_hash'])
        if state['sha256']!=p['source_state_hash'] and state['payload'].get('parent_state_id')!=p['source_state_hash']:raise WorldError('STALE_PARENT')
        freeze(self.root/'returns'/f'{plan}.json',{'observation':observation,'plan':plan,'status':'SOFTWARE_FIXTURE_RETURN_ONLY','time_utc':r['time_utc']});return digest(observation)
    def decide(self,plan,choice,reason,alternatives):
        self.session._open()
        if choice not in CHOICES or not reason or not alternatives:raise WorldError('DECISION_RATIONALE_REQUIRED')
        path=self.root/'returns'/f'{plan}.json'
        if not path.exists():raise WorldError('OBSERVATION_NOT_READ')
        v={'plan':plan,'choice':choice,'reason':reason,'alternatives':alternatives,'observation_sha256':digest(json.loads(path.read_text())['observation']),'autonomy':'A0_SCRIPTED_FIXTURE_NOT_NEW_A2','new_science':False}
        freeze(self.root/'decisions'/f'{plan}.json',v)
        if choice=='STOP':self.session.stop(reason)
        return v
