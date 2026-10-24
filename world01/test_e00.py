"""Real historical replay for E00-01..04; explicit synthetic failure/Explorer fixtures.

No SCF/FCI, no QuTiP propagation, no network or remote writes.
RT definitions are bound to the downloaded WORLD01 baseline appendix C.
"""
import copy,hashlib,json,pathlib,tempfile,unittest,os
from unittest.mock import patch
from router import digest
from interactive01.world import freeze
from recovery02r.isolated_router import run_isolated
from world01.session import WorldSession
from world01.contracts import WorldError,OperationRequest
from world01.explorer import ExplorerHarness
P=pathlib.Path(__file__).resolve().parents[1];R=P.parent
MANIFEST=json.loads((R/'S0/source_sha_manifest.json').read_text())
def state_files(kind=None,domain=None,observed=None):
    result=[]
    for f in sorted(MANIFEST['files']):
        if not f.startswith('results/') or '/world/states/' not in f or not f.endswith('.json'):continue
        s=json.loads((P/f).read_text());p=s['payload']
        if kind and p['schema']!=kind:continue
        if domain is not None and p['world_spec']['matter']['periodic']!=domain:continue
        if observed is True and not p.get('observation'):continue
        result.append(f)
    return result
FCI='QW_CORRELATED_ELECTRONIC_STATE_01';KET='QW_EFFECTIVE_QUANTUM_STATE_01';STRUCT='QW_PHYSICAL_STATE_01'
class E00(unittest.TestCase):
    def setUp(self):
        if os.environ.get('QW_EVIDENCE_ROOT'):
            root=pathlib.Path(os.environ['QW_EVIDENCE_ROOT'])/self._testMethodName
            root.mkdir(parents=True,exist_ok=False)
            self.t=type('EvidenceDirectory',(),{'name':str(root)})()
        else:
            self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup)
        self.s=WorldSession(self.t.name,P,MANIFEST)
    def ref(self,kind,domain=None,observed=True):return self.s.reference(state_files(kind,domain,observed)[0])
    def request(self,state,action,**kwargs):return OperationRequest(action,state['source_state_hash'],kwargs)
    def reject(self,result,code):self.assertEqual(result['status'],'REJECTED');self.assertEqual(result['reason_code'],code)
    def test_WB_E00_01_real_historical_import(self):
        seen=set()
        for f in state_files():
            raw=(P/f).read_bytes();e=self.s.reference(f);state=self.s.store.load(e['source_state_hash']);seen.add(e['state_kind'])
            self.assertEqual((self.s.root/'states'/f"{state['sha256']}.json").read_bytes(),raw)
            self.assertEqual(hashlib.sha256((P/f).read_bytes()).hexdigest(),MANIFEST['files'][f])
        self.assertEqual(seen,{STRUCT,KET,FCI})
    def test_WB_E00_02_complete_real_transition_replay(self):
        paths=[f for f in MANIFEST['files'] if f.startswith('results/') and '/world/transitions/' in f and f.endswith('/receipt.json')]
        self.assertGreaterEqual(len(paths),5)
        for f in paths:
            r=self.s.replay(f);self.assertEqual(r['status'],'HISTORICAL_REPLAY_VALIDATED');self.assertFalse(r['new_scientific_execution'])
            self.assertEqual(r['reason_code'],'NOT_A_NEW_PHYSICS_RUN')
    def test_WB_E00_03_one_entry_three_state_kinds(self):
        for kind in (STRUCT,KET,FCI):
            e=self.ref(kind);r=self.s.call('act',request=self.request(e,'OBSERVE'));self.assertEqual(r['status'],'HISTORICAL_OBSERVATION_READ')
            no=self.s.call('act',request=self.request(e,'NOT_A_PHYSICAL_ACTION'));self.reject(no,'OPERATION_OUT_OF_DOMAIN')
    def test_WB_E00_04_negative_paths_all_fail_closed(self):
        a=self.ref(STRUCT,True);b=self.ref(FCI)
        self.reject(self.s.call('compare',a=a['source_state_hash'],b=b['source_state_hash']),'INCOMPARABLE')
        self.reject(self.s.call('translate',ident=b['source_state_hash'],target=KET),'TRANSLATION_FORBIDDEN')
        self.reject(self.s.call('act',request=OperationRequest('OBSERVE',a['source_state_hash'],{},('forces',))),'FORCE_NOT_AVAILABLE')
    def test_WB_E00_05_actual_child_faults_and_preservation(self):
        e=self.ref(FCI);state=self.s.root/'states'/f"{e['source_state_hash']}.json";old=state.read_bytes();oldfail=None
        modes={'SIGSEGV':'NATIVE_SIGNAL_SIGSEGV','TIMEOUT':'TIMEOUT','MEMORY_LIMIT':'WORKER_MEMORY_ALLOCATION_FAILED','CORRUPT_JSON':'NO_VALID_OBSERVATION','INTERRUPTED':'NATIVE_SIGNAL_SIGTERM'}
        for mode,reason in modes.items():
            target=self.s.root/'fixture_faults'/mode
            result=run_isolated({'fault':mode,'physics':{'engine':'SOFTWARE_FIXTURE_ONLY'}},target,timeout=.25 if mode=='TIMEOUT' else 3,fault=mode,worker_path=P/'world01/fault_worker.py')
            self.assertEqual(result['reason'],reason);self.assertEqual(result['status'],'UNVERIFIED');self.assertTrue((target/'completed_fixture.json').exists())
            receipt=self.s.preserve_failure(e['source_state_hash'],reason,{'synthetic':True,'process_receipt':str(target.relative_to(self.s.root))+'/process_receipt.json'})
            if oldfail:self.assertEqual(oldfail[0].read_bytes(),oldfail[1])
            oldfail=(self.s.root/'session_receipts'/f"{receipt['receipt_sha256']}.json",(self.s.root/'session_receipts'/f"{receipt['receipt_sha256']}.json").read_bytes());self.assertEqual(state.read_bytes(),old)
        # Simulate interrupted atomic publication: pending bytes never replace old state.
        (self.s.root/'states'/'interrupted.tmp').write_bytes(b'PARTIAL')
        reopened=WorldSession(self.t.name,P,MANIFEST);self.assertEqual(reopened.store.load(e['source_state_hash'])['sha256'],e['source_state_hash'])
        self.assertTrue((self.s.root/'states'/'interrupted.tmp').exists())
    def test_WB_E00_06_fixture_explorer_feedback_stop(self):
        spec=copy.deepcopy(self.ref(FCI)['object']);raw=self.s.store.load(self.ref(FCI)['source_state_hash'])['payload']['world_spec'];raw=copy.deepcopy(raw);raw['object_id']='e00-synthetic-only'
        e=self.s.create(raw,synthetic=True);x=ExplorerHarness(self.s);candidates=[{'id':'probe','reason':'Test software feedback binding'},{'id':'stop','reason':'Allowed zero-cost alternative'}]
        plan=x.plan(e['source_state_hash'],'Software fixture loop',candidates,'probe','Fixture scalar will be0.4','Any other fixture scalar rejects the fixture forecast')
        with self.assertRaises(WorldError):x.decide(plan,'CONTINUE','Premature',candidates)
        obs=x.fixture_observe(e['source_state_hash'],{'scalar':.4,'synthetic':True});x.return_observation(plan,obs)
        d=x.decide(plan,'CONTINUE','Fixture observed; next test checks STOP path',candidates);self.assertEqual(d['autonomy'],'A0_SCRIPTED_FIXTURE_NOT_NEW_A2')
        plan2=x.plan(e['source_state_hash'],'Stop fixture',candidates,'stop','No new physical result','Any claimed CALCULATED status fails',[obs['read_receipt_sha256']]);obs2=x.fixture_observe(e['source_state_hash'],{'scalar':.4,'synthetic':True});x.return_observation(plan2,obs2);x.decide(plan2,'STOP','Fixture completed; no scientific allocation',candidates)
        self.reject(self.s.call('fork',ident=e['source_state_hash'],reason='after stop'),'SESSION_STOPPED')
    def test_RT_01_invalid_electron_spin(self):
        e=self.ref(FCI);spec=copy.deepcopy(self.s.store.load(e['source_state_hash'])['payload']['world_spec']);spec['matter']['spin_2S']=1
        self.reject(self.s.call('create',spec=spec),'INVALID_ELECTRON_SPIN')
    def test_RT_02_singular_cell_and_collision(self):
        e=self.ref(STRUCT,True);spec=copy.deepcopy(self.s.store.load(e['source_state_hash'])['payload']['world_spec']);bad=copy.deepcopy(spec);bad['matter']['cell_angstrom']=[bad['matter']['cell_angstrom'][0]]*3
        self.reject(self.s.call('create',spec=bad),'INVALID_CELL');bad=copy.deepcopy(spec);bad['matter']['atoms'][1]['xyz_angstrom']=bad['matter']['atoms'][0]['xyz_angstrom'][:]
        self.reject(self.s.call('create',spec=bad),'COLLISION')
    def test_RT_03_cross_composition_ranking(self):
        self.reject(self.s.call('compare',a=self.ref(STRUCT,True)['source_state_hash'],b=self.ref(FCI)['source_state_hash']),'INCOMPARABLE')
    def test_RT_04_fci_to_two_state(self):self.reject(self.s.call('translate',ident=self.ref(FCI)['source_state_hash'],target=KET),'TRANSLATION_FORBIDDEN')
    def test_RT_05_no_periodic_force(self):self.reject(self.s.claim('periodic_force',self.ref(STRUCT,True)['source_state_hash']),'FORCE_NOT_AVAILABLE')
    def test_RT_06_same_family_not_W2(self):
        h=self.ref(FCI)['source_state_hash'];self.reject(self.s.call('compare',a=h,b=h,contract={'kind':'RHF_FCI_SAME_STATE','independent_W2':True}),'INDEPENDENCE_INSUFFICIENT')
    def test_RT_07_covarying_k_and_GDF(self):self.reject(self.s.claim('pure_k_convergence'),'NUMERICAL_SETTING_COVARIATION')
    def test_RT_08_lowdin_not_unique_measurement(self):self.reject(self.s.claim('unique_atomic_lowdin'),'PARTITION_DEPENDENT_CLAIM_BLOCKED')
    def test_RT_09_fixture_not_calculated(self):
        e=self.ref(FCI);spec=copy.deepcopy(self.s.store.load(e['source_state_hash'])['payload']['world_spec']);spec['object_id']='synthetic-status-check';f=self.s.create(spec,synthetic=True)
        self.assertEqual(self.s.observe(f['source_state_hash'])['status'],'SOFTWARE_FIXTURE_ONLY');x=ExplorerHarness(self.s)
        with self.assertRaisesRegex(WorldError,'SYNTHETIC_MISLABEL_BLOCKED'):x.fixture_observe(f['source_state_hash'],{'status':'CALCULATED'})
        self.reject(self.s.claim('fixture_calculated'),'SYNTHETIC_MISLABEL_BLOCKED')
    def test_RT_10_old_quota_no_authority(self):
        e=self.ref(FCI);r=self.s.call('act',request=self.request(e,'DISPLACE_ATOM',authority={'science_jobs':2,'old_run':'39788105394'}));self.reject(r,'AUTHORITY_MISSING')
    def test_RT_11_no_implicit_retry(self):self.reject(self.s.claim('implicit_retry'),'NO_IMPLICIT_RETRY')
    def test_RT_12_historical_failure_not_rewritten(self):
        original={'id':'E01-C2','status':'NO-GO','origin':'SYNTHETIC_SOFTWARE_GUARD_FIXTURE_NOT_HISTORICAL_ORIGINAL'};p=self.s.root/'failure_fixture.json';freeze(p,original);old=p.read_bytes()
        with self.assertRaises(ValueError):freeze(p,{'id':'E01-C2','status':'PASS'})
        self.assertEqual(p.read_bytes(),old);self.reject(self.s.claim('historical_verdict_rewrite'),'HISTORICAL_VERDICT_CONFLICT')
    def test_positive_RHF_FCI_same_state(self):
        h=self.ref(FCI)['source_state_hash'];r=self.s.compare(h,h,{'kind':'RHF_FCI_SAME_STATE'});self.assertLess(r['result']['delta_energy_Eh'],0);self.assertEqual(r['reason_code'],'MODEL_INTERNAL_NOT_INDEPENDENT')
    def test_positive_TDA_descriptor_bridge(self):
        e=self.ref(KET);r=self.s.translate(e['source_state_hash'],'QUTIP_TWO_STATE_PARAMETERS');self.assertEqual(r['status'],'APPROXIMATION_LOSS');self.assertTrue(r['translation']['losses']);self.assertFalse(r['translation']['new_calculation'])
    def test_positive_matter_projection_is_lossy(self):
        r=self.s.translate(self.ref(FCI)['source_state_hash'],'MATTER_SPEC');self.assertEqual(r['status'],'APPROXIMATION_LOSS');self.assertIn('All electronic amplitudes/RDM',r['translation']['losses'])
    def test_state_tamper_and_source_path_rejected(self):
        e=self.ref(FCI);p=self.s.root/'states'/f"{e['source_state_hash']}.json";s=json.loads(p.read_text());s['payload']['state_kind']='WRONG';p.write_text(json.dumps(s));self.reject(self.s.call('load',ident=e['source_state_hash']),'STATE_UNAVAILABLE_OR_CORRUPT')
        self.reject(self.s.call('reference',relative='../secret.json'),'SOURCE_NOT_BOUND')
    def test_no_late_prediction_or_promotion(self):
        e=self.ref(FCI);spec=copy.deepcopy(self.s.store.load(e['source_state_hash'])['payload']['world_spec']);spec['object_id']='late-fixture';f=self.s.create(spec,synthetic=True);x=ExplorerHarness(self.s);obs=x.fixture_observe(f['source_state_hash'],{'v':1});c=[{'id':'a','reason':'fixture'}];p=x.plan(f['source_state_hash'],'test',c,'a','pred','false')
        with self.assertRaisesRegex(WorldError,'PREDICTION_AFTER_RESULT'):x.return_observation(p,obs)
        with self.assertRaisesRegex(WorldError,'REAL_AUTONOMY_NOT_AUTHORIZED'):x.plan(f['source_state_hash'],'test',c,'a','pred','false',level='A2')
    def test_runtime_schemas_and_bad_request(self):
        from world01.schemas import validate
        e=self.ref(FCI);validate('state',e);validate('observation',self.s.observe(e['source_state_hash']))
        validate('request',OperationRequest('OBSERVE',e['source_state_hash'],{}).plain())
        validate('receipt',self.s.reject('test','EXPECTED_REJECTION'))
        from jsonschema import ValidationError
        with self.assertRaises(ValidationError):validate('request',{'action':7})
    def test_stale_replay_parent_has_no_success_receipt(self):
        e=self.ref(FCI)
        f=next(f for f in MANIFEST['files'] if '/world/transitions/' in f and f.endswith('/receipt.json') and json.loads((P/f).read_text())['source_state_sha256']!=e['source_state_hash'])
        self.reject(self.s.act(OperationRequest('REPLAY_HISTORICAL_TRANSITION',e['source_state_hash'],{'receipt_path':f})),'STALE_PARENT')
        self.assertFalse(any(json.loads(p.read_text())['operation']=='replay' for p in (self.s.root/'session_receipts').glob('*.json')))
if __name__=='__main__':unittest.main()
