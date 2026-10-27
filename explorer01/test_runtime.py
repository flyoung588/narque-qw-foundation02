"""Synthetic model replies ONLY test engineering, never model autonomy."""
import unittest,json,pathlib,tempfile,copy,os
from unittest.mock import patch
from router import digest
from world01.session import WorldSession
from world01.contracts import WorldError
from .runtime import ExplorerRuntime
from .adapters import FileExchangeAdapter,CommandModelAdapter
from .contracts import SCHEMA
P=pathlib.Path(__file__).resolve().parents[1];R=P.parent
MAN=json.loads((R/'SOURCE_BASELINE_SHA256.json').read_text())
H='43c3236655007b39a8b006e3bb6348a9002e243859c340b2fb77230c82df7865';N='d83908cf6558cbfe48787c84fc8ed3cbbcb3578ae44dea375914427177549694'
CAT={H:{'path':f'results/world-birth01/phase1/raw/session/states/{H}.json','domain':'molecular'},N:{'path':f'results/world-birth01/phase2/raw/session/states/{N}.json','domain':'periodic'}}
def fixture(req,source=N,name='OBSERVE',action='CHANGE_PHYSICAL_DOMAIN'):
 obs=req['request']['context']['memory']['observations']
 return {'schema':'QW_EXPLORER_DECISION_01','request_hash':req['hash'],'goal_interpretation':'SOFTWARE_FIXTURE: test routing, not science or real model','candidates':[{'id':'read','kind':'CHANGE_DOMAIN','question':'Read sealed other domain','information_value':'Observe representation difference','cost_and_limits':'0 science jobs','why_not_selected':'Selected for fixture'}, {'id':'stop','kind':'STOP','question':'Stop this software test','information_value':'No further claim','cost_and_limits':'0','why_not_selected':'Fixture continues'}],'selected':'read','action':action,'operation':{'name':name,'source':source,'other':None,'parameters':{}},'observation_refs':[x['hash'] for x in obs],'interpretation':'Read existing evidence only','limitations':'Fixture output is not a real model call','competing_explanations':['Model limitation','Insufficient observation'],'prediction':'Only existing values returned','falsifier':'New science attempted or unsupported data reported','resource_reason':'One cheap offline read to test semantics','negative_evidence_response':'Preserve all existing rejections and do not repeat failed physics','memory_updates':[{'kind':'Hypothesis','content':'Fixture hypothesis, not PhysicalEvidence','evidence_refs':[obs[-1]['hash']]}]}
class RuntimeTest(unittest.TestCase):
 def setUp(self):
  base=os.environ.get('QW_EXPLORER_TEST_EVIDENCE')
  self.t=None if base else tempfile.TemporaryDirectory()
  self.root=pathlib.Path(base)/self._testMethodName if base else pathlib.Path(self.t.name)
  self.root.mkdir(parents=True,exist_ok=True)
  self.w=WorldSession(self.root/'world',P,MAN);self.r=ExplorerRuntime(self.root/'research',self.w,CAT,'test offline limits',max_decisions=4);self.r.seed(H)
 def tearDown(self):
  if self.t:self.t.cleanup()
 def request(self):return self.r.request({'model':'SOFTWARE_TEST_FIXTURE','effort':'none','identity_verified':False})
 def submit(self,d):return self.r.submit(json.dumps(d),transport='SYNTHETIC_TEST_REPLY_NOT_MODEL')
 def test_01_real_historical_read_two_domains(self):
  x=self.submit(fixture(self.request()));self.assertEqual(x['status'],'COMPLETED');self.assertEqual(len(self.r.j.query('PhysicalEvidence')),2);self.assertEqual(self.r.j.query('PhysicalEvidence')[-1]['data']['observation']['new_scientific_executions'],0)
 def test_02_invalid_json_preserved(self):
  q=self.request();x=self.r.submit('{broken');self.assertEqual(x['status'],'REJECTED');self.assertEqual(self.r.j.query('ModelResponse')[0]['data']['raw_response'],'{broken')
 def test_03_invented_observation_rejected(self):
  d=fixture(self.request());d['observation_refs'].append('0'*64);self.assertEqual(self.submit(d)['reason_code'],'INVENTED_OBSERVATION')
 def test_04_new_science_denied(self):
  d=fixture(self.request(),H,'PROPOSE_EXPERIMENT','CONTINUE');d['operation']['parameters']={'action':'MEASURE_OBSERVABLE','observables':['energy']};self.assertEqual(self.submit(d)['reason_code'],'RESOURCE_ADMISSION_REQUIRED')
 def test_05_illegal_ci_conversion(self):
  f=next(f for f in MAN['files'] if '/world/states/' in f and f.endswith('.json') and json.loads((P/f).read_text())['payload']['schema']=='QW_CORRELATED_ELECTRONIC_STATE_01');h=json.loads((P/f).read_text())['sha256']
  cat={**CAT,h:{'path':f,'domain':'correlated'}};r=ExplorerRuntime(self.root/'ci_research',self.w,cat,'ci test');r.seed(h);q=r.request({'model':'fixture'});d=fixture(q,h,'TRANSLATE','CHANGE_MODEL');d['operation']['parameters']={'target':'QW_EFFECTIVE_QUANTUM_STATE_01'};self.assertEqual(r.submit(json.dumps(d))['reason_code'],'TRANSLATION_FORBIDDEN')
 def test_06_cross_composition_compare_rejected(self):
  d=fixture(self.request(),H,'COMPARE','REQUEST_VALIDATION');d['operation']['other']=N;self.assertEqual(self.submit(d)['reason_code'],'INCOMPARABLE')
 def test_07_out_of_catalog_object(self):
  d=fixture(self.request(),'f'*64);self.assertEqual(self.submit(d)['reason_code'],'STATE_NOT_IN_SEALED_CATALOG')
 def test_08_missing_frontier_stop(self):
  d=fixture(self.request());d['candidates'][1]['kind']='CHANGE_DOMAIN';self.assertEqual(self.submit(d)['reason_code'],'FRONTIER_COMPETITION_REQUIRED')
 def test_09_duplicate_response_no_rerun(self):
  d=fixture(self.request());self.submit(d)
  with self.assertRaisesRegex(WorldError,'NO_PENDING_MODEL_REQUEST'):self.submit(d)
  self.assertEqual(len(self.r.j.query('ReadReserved')),2)
 def test_10_restore_memory_and_budget(self):
  d=fixture(self.request());self.submit(d);old=self.r.j.checkpoint();r=ExplorerRuntime(self.root/'research',self.w,CAT,'test offline limits',max_decisions=4);self.assertEqual(old,r.j.checkpoint());self.assertEqual(len(r.j.query('Hypothesis')),1)
 def test_11_config_budget_escalation_rejected(self):
  with self.assertRaisesRegex(WorldError,'SESSION_CONFIG_CHANGED'):ExplorerRuntime(self.root/'research',self.w,CAT,'test offline limits',max_decisions=5)
 def test_12_interruption_no_implicit_reexecution(self):
  q=self.request();d=fixture(q)
  with self.r.j.lock():self.r.j.append('DecisionAccepted',{'request_hash':q['hash'],'decision':d})
  before=len(self.r.j.query('ReadReserved'));self.r.recover();self.assertEqual(len(self.r.j.query('ReadReserved')),before);self.assertEqual(self.r.j.query('OperationResult')[-1]['data']['status'],'INTERRUPTED_NO_REEXECUTION')
 def test_13_resume_pending_request_same_hash(self):
  q=self.request();r=ExplorerRuntime(self.root/'research',self.w,CAT,'test offline limits',max_decisions=4);self.assertEqual(r.request({'model':'different_attempt_ignored'}),q);self.assertEqual(len(r.j.query('ModelRequest')),1)
 def test_14_model_budget_hard_stop(self):
  for _ in range(4):self.request();self.r.submit('invalid')
  with self.assertRaisesRegex(WorldError,'MODEL_REQUEST_BUDGET_EXHAUSTED'):self.request()
 def test_15_stop_is_terminal(self):
  d=fixture(self.request(),None,'STOP','STOP');d['selected']='stop';self.assertEqual(self.submit(d)['status'],'STOPPED')
  with self.assertRaisesRegex(WorldError,'RESEARCH_STOPPED'):self.request()
 def test_16_memory_tamper(self):
  p=next((self.r.root/'events').glob('*.json'));x=json.loads(p.read_text());x['data']['goal']='tampered';p.write_text(json.dumps(x))
  with self.assertRaisesRegex(WorldError,'MEMORY_CHAIN_CORRUPT'):self.r.j.events()
 def test_17_synthetic_cannot_be_evidence(self):
  spec=self.w.store.load(H)['payload']['world_spec'];v=self.w.create(spec,synthetic=True);h=v['source_state_hash'];p=self.w.root/'states'/f'{h}.json';cat={h:{'path':str(p.relative_to(self.w.root)),'domain':'synthetic'}}
  # Real archive source gate, not a caller-supplied real flag.
  badworld=WorldSession(self.root/'fakeworld',self.w.root,{'local_base':'synthetic-test','files':{str(p.relative_to(self.w.root)):__import__('hashlib').sha256(p.read_bytes()).hexdigest()}});r=ExplorerRuntime(self.root/'fake_research',badworld,cat,'synthetic test')
  with self.assertRaises(WorldError):r.seed(h)
  self.assertFalse(r.j.query('PhysicalEvidence'))
 def test_18_invalid_operation_schema(self):
  d=fixture(self.request());d['operation']['name']='SCF';self.assertEqual(self.submit(d)['status'],'REJECTED')
 def test_19_repeat_failed_science_no_renewal(self):
  d=fixture(self.request(),H,'PROPOSE_EXPERIMENT','CONTINUE');d['operation']['parameters']={'action':'MEASURE_OBSERVABLE'};self.submit(d);d=fixture(self.request(),H,'PROPOSE_EXPERIMENT','CONTINUE');d['operation']['parameters']={'action':'MEASURE_OBSERVABLE'};self.assertEqual(self.submit(d)['reason_code'],'REPEATED_FAILED_EXPERIMENT_NO_NEW_AUTHORITY')
 def test_20_negative_evidence_cannot_ignore(self):
  d=fixture(self.request(),H,'COMPARE','REQUEST_VALIDATION');d['operation']['other']=N;self.submit(d);d=fixture(self.request());d['negative_evidence_response']='IGNORE';self.assertEqual(self.submit(d)['reason_code'],'NEGATIVE_EVIDENCE_IGNORED')
 def test_21_schema_and_duplicate_NaN(self):
  from jsonschema import Draft202012Validator
  Draft202012Validator.check_schema(SCHEMA)
  self.request();self.assertEqual(self.r.submit('{"x":NaN}')['status'],'REJECTED')
  self.request();self.assertEqual(self.r.submit('{"x":1,"x":2}')['status'],'REJECTED')
 def test_22_no_model_transport_fabrication(self):
  a=FileExchangeAdapter(self.root/'exchange');v=self.r.run_one(a,{'model':'UNKNOWN','attestation':'UNVERIFIED'});self.assertEqual(v['status'],'MODEL_RESPONSE_PENDING');self.assertFalse(self.r.j.query('DecisionAccepted'))
 def test_23_command_adapter_requires_authority(self):
  with self.assertRaisesRegex(WorldError,'MODEL_CALL_AUTHORITY_REQUIRED'):CommandModelAdapter(['not_run'])
 def test_24_latest_observation_required(self):
  d=fixture(self.request());d['observation_refs']=[];self.assertEqual(self.submit(d)['reason_code'],'LATEST_OBSERVATION_NOT_CONSIDERED')
 def test_25_readonly_no_native_subprocess(self):
  with patch('subprocess.Popen',side_effect=AssertionError('must not start science')):self.assertEqual(self.submit(fixture(self.request()))['status'],'COMPLETED')
 def test_26_prior_memory_evidence_typed(self):
  d=fixture(self.request());d['memory_updates'][0]['kind']='PhysicalEvidence';self.assertEqual(self.submit(d)['status'],'REJECTED')
 def test_27_capabilities_and_research_not_physical_continuity(self):
  self.submit(fixture(self.request()));e=self.r.j.query('PhysicalEvidence');self.assertNotEqual(e[0]['data']['physical_object'],e[1]['data']['physical_object']);self.assertEqual(len({x['data']['state'] for x in e}),2)
 def test_28_model_assertion_cannot_attest_identity(self):
  self.submit(fixture(self.request()));self.assertEqual(self.r.j.query('ModelResponse')[-1]['data']['provider_attestation'],'UNVERIFIED')

 def test_29_checkpoint_tail_truncation(self):
  self.request();p=sorted((self.r.root/'events').glob('*.json'))[-1];p.unlink()
  with self.assertRaisesRegex(WorldError,'CHECKPOINT_AHEAD_OF_JOURNAL'):self.r.j.events()
 def test_30_checkpoint_wrong_head(self):
  p=self.r.root/'checkpoint.json';v=json.loads(p.read_text());v['journal_head']='0'*64;p.write_text(json.dumps(v))
  with self.assertRaisesRegex(WorldError,'CHECKPOINT_HASH_MISMATCH'):self.r.j.events()
 def test_31_actual_abrupt_dispatch_recovery(self):
  d=fixture(self.request());before=len(self.r.j.query('ReadReserved'))
  with patch.object(self.r,'_execute',side_effect=SystemExit('INJECTED_PROCESS_INTERRUPTION')):
   with self.assertRaises(SystemExit):self.submit(d)
  r=ExplorerRuntime(self.root/'research',self.w,CAT,'test offline limits',max_decisions=4)
  self.assertEqual(len(r.j.query('ReadReserved')),before);self.assertEqual(r.j.query('OperationResult')[-1]['data']['status'],'INTERRUPTED_NO_REEXECUTION')
 def test_32_interrupted_stop_remains_terminal(self):
  d=fixture(self.request(),None,'STOP','STOP');d['selected']='stop'
  with patch.object(self.r,'_execute',side_effect=SystemExit('INJECTED_STOP_INTERRUPTION')):
   with self.assertRaises(SystemExit):self.submit(d)
  r=ExplorerRuntime(self.root/'research',self.w,CAT,'test offline limits',max_decisions=4)
  with self.assertRaisesRegex(WorldError,'RESEARCH_STOPPED'):r.request({'model':'fixture'})
 def test_33_selected_stop_must_be_stop(self):
  d=fixture(self.request());d['selected']='stop';self.assertEqual(self.submit(d)['reason_code'],'SELECTED_STOP_MISMATCH')
 def test_34_raw_quality_fields_retained(self):
  x=self.r.j.query('PhysicalEvidence')[0]['data'];self.assertTrue(x['numerical_quality']['reported_SCF_converged']);self.assertIn('raw_numeric_quality',x['numerical_quality'])
 def test_35_scheduler_pauses_no_mock_pass(self):
  out=self.r.run(FileExchangeAdapter(self.root/'model_exchange'),{'model':'UNAVAILABLE'})
  self.assertEqual(len(out),1);self.assertEqual(out[0]['status'],'MODEL_RESPONSE_PENDING');self.assertFalse(self.r.j.query('DecisionAccepted'))
 def test_36_real_transport_failure_recorded(self):
  a=CommandModelAdapter(['/definitely/nonexistent/qw_model'],authorized=True);v=self.r.run(a,{'model':'TEST_UNAVAILABLE'})
  self.assertEqual(v[0]['status'],'MODEL_TRANSPORT_FAILED');self.assertEqual(len(self.r.j.query('ModelFailure')),1)
 def test_37_request_code_identity_hash(self):
  q=self.request();self.assertIn('runtime.py',q['request']['context']['runtime_code_sha256']);self.assertEqual(q['hash'],digest(q['request']))
