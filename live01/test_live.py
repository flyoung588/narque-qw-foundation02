"""Engineering-only test fixtures. No model or scientific solver is executed."""
import unittest,pathlib,json,copy,os
from unittest.mock import patch
from router import digest
from world01.contracts import WorldError
from world01.session import WorldSession
from explorer01.test_runtime import H,MAN,CAT
from .contracts import admission,screen_spec,check_remote_return,successor,LIMITS
from .broker import LiveBroker
from .session import LiveWorldSession
from .runtime import LiveExplorerRuntime
from .transfer_gate import check_transfer
P=pathlib.Path(__file__).resolve().parents[1];R=P.parent
SPEC=json.loads((P/CAT[H]['path']).read_text())['payload']['world_spec']
class FaultTransport:
 def __init__(self,mode='raise'):self.calls=0;self.mode=mode
 def execute(self,spec,intent,grant):
  self.calls+=1
  if self.mode=='raise':raise RuntimeError('INJECTED_SOFTWARE_TRANSPORT_FAILURE_NOT_A_SCIENCE_JOB')
  return {'source_kind':'SOFTWARE_FIXTURE_NOT_PHYSICS','intent':intent}
class LiveTests(unittest.TestCase):
 def setUp(self):
  self.root=pathlib.Path(os.environ['QW_LIVE_TEST_EVIDENCE'])/self._testMethodName;self.root.mkdir(parents=True);self.events=[]
  self.prereg={'first_world_spec':SPEC,'initial_model_receipt_sha256':'SOFTWARE_FIXTURE_ONLY'};self.review={'status':'PASS','independent_context_review_performed':True,'fixture':'NOT_REAL_REVIEW'}
  self.grant={'scope':'QW-EXPLORER-E01','status':'HUMAN_GRANTED_E01','human_approval_reference':'SOFTWARE_FIXTURE_NOT_HUMAN_AUTHORIZATION','prereg_sha256':digest(self.prereg),'source_manifest_sha256':'SOFTWARE_ONLY','limits':LIMITS,'repository':'flyoung588/narque-qw-foundation02','branch':'qw-explorer-e01','code_commit':'f'*40};self.t=FaultTransport()
 def tearDown(self):(self.root/'RESULT.json').write_text(json.dumps({'scope':'SYNTHETIC_ENGINEERING_ONLY','events':self.events},indent=2))
 def expect(self,code,fn):
  try:fn()
  except Exception as e:self.events.append({'expected':code,'actual':getattr(e,'code',type(e).__name__),'detail':str(e)});self.assertEqual(getattr(e,'code',type(e).__name__),code);return
  self.fail('expected '+code)
 def broker(self):return LiveBroker(self.root/'broker',self.grant,self.prereg,self.review,'SOFTWARE_ONLY',self.t)
 def test_01_current_gate_no_network(self):
  from .controller import run
  with patch('subprocess.Popen',side_effect=AssertionError('No external program allowed before gate')):self.expect('HUMAN_GATE_REQUIRED',lambda:run(R))
 def test_02_old_authority_cannot_transfer(self):
  old=json.loads((P/'birth01/AUTHORITY.json').read_text());self.expect('HUMAN_GATE_REQUIRED',lambda:admission(old,self.prereg,self.review,'SOFTWARE_ONLY'))
 def test_03_independent_review_incomplete(self):
  self.expect('L1_INDEPENDENT_ACCEPTANCE_REQUIRED',lambda:admission(self.grant,self.prereg,{'status':'PARTIAL','independent_context_review_performed':False},'SOFTWARE_ONLY'))
 def test_04_source_or_prereg_mismatch(self):
  self.expect('AUTHORIZATION_SCOPE_MISMATCH',lambda:admission(self.grant,{**self.prereg,'first_world_spec':{}},self.review,'SOFTWARE_ONLY'))
 def test_05_generic_valid_object_no_solver(self):
  with patch('subprocess.Popen',side_effect=AssertionError('No process')):v=screen_spec(SPEC)
  self.assertEqual(v['route'],'molecular');self.events.append({'actual':v,'not_selected_scientific_object':True})
 def test_06_resource_basis_limits(self):
  q=copy.deepcopy(SPEC);q['physics']['basis']='cc-pvtz';self.expect('OUT_OF_DOMAIN',lambda:screen_spec(q))
 def test_07_failed_slot_not_refunded(self):
  b=self.broker();self.expect('RuntimeError',lambda:b.run(SPEC,'SOFTWARE_MODEL_DECISION'));q=copy.deepcopy(SPEC);q['matter']['atoms'][0]['xyz_angstrom'][0]+=.01;self.expect('RuntimeError',lambda:b.run(q,'SOFTWARE_MODEL_DECISION2'));q['matter']['atoms'][0]['xyz_angstrom'][0]+=.01;self.expect('SCIENTIFIC_JOB_LIMIT',lambda:b.run(q,'SOFTWARE_MODEL_DECISION3'));self.assertEqual(self.t.calls,2)
 def test_08_same_failed_input_no_retry(self):
  b=self.broker();self.expect('RuntimeError',lambda:b.run(SPEC,'fixture'));self.expect('SCIENTIFIC_INPUT_ALREADY_ATTEMPTED',lambda:b.run(SPEC,'fixture2'));self.assertEqual(self.t.calls,1)
 def test_09_mock_never_real(self):
  self.t.mode='fixture';b=self.broker();self.expect('UNTRUSTED_SOLVER_TRANSPORT',lambda:b.run(SPEC,'fixture'));self.assertFalse(list((b.root/'attempts').glob('*/validated_return.json')))
 def test_10_no_trusted_import_without_broker(self):
  w=LiveWorldSession(self.root/'world',P,MAN);self.expect('LIVE_BROKER_MISSING',lambda:w.register_return({'spec':SPEC},H))
 def test_11_wrong_parent_and_large_displacement(self):
  w=WorldSession(self.root/'world',P,MAN);state=w.store.create(SPEC,'SOFTWARE_TEST_STRUCTURE_ONLY')
  self.expect('STALE_PARENT',lambda:successor(state,{'action':{'source_state_sha256':'0'*64}},'CONTINUE'))
  a={'type':'DISPLACE_ATOM','source_state_sha256':state['sha256'],'atom_id':'atom-0','vector':[.06,0,0],'unit':'angstrom'};self.expect('ValueError',lambda:successor(state,{'action':a},'CONTINUE'))
 def test_12_external_model_gate_before_client(self):
  with patch('subprocess.Popen',side_effect=AssertionError('Client must not start')):self.expect('MODEL_PAYLOAD_TRANSFER_APPROVAL_REQUIRED',lambda:check_transfer(R))
 def test_13_failure_preservation_and_restore(self):
  b=self.broker();self.expect('RuntimeError',lambda:b.run(SPEC,'fixture'));n=len(b.j.events());b=LiveBroker(self.root/'broker',self.grant,self.prereg,self.review,'SOFTWARE_ONLY',self.t);self.assertEqual(n,len(b.j.events()));self.assertEqual(len(list((b.root/'attempts').glob('*/failure.json'))),1);self.expect('SCIENTIFIC_INPUT_ALREADY_ATTEMPTED',lambda:b.run(SPEC,'different_model_decision'))
 def test_14_live_mode_no_approval_no_science_budget(self):
  self.grant['status']='NOT_GRANTED';b=self.broker();w=LiveWorldSession(self.root/'world',P,MAN,broker=b);r=LiveExplorerRuntime(self.root/'research',w,{},'SOFTWARE TEST',broker=b)
  self.assertEqual(r.context()['resources']['new_science_jobs'],0);self.expect('HUMAN_GATE_REQUIRED',lambda:r.first_frozen({'world_spec':SPEC,'model_decision_hash':'fixture'},True));self.assertEqual(self.t.calls,0)

 def test_15_source_kind_label_is_not_transport_proof(self):
  from .transport import GithubTransport
  t=GithubTransport(self.root/'no_actual_remote_calls')
  self.expect('REMOTE_RETURN_NOT_ACQUIRED_BY_THIS_TRANSPORT',lambda:t.assert_authenticated({'intent':'fabricated','source_kind':'GITHUB_AUTHENTICATED_RUN'}))
 def test_16_fake_result_not_pinned_by_broker(self):
  b=self.broker();fake={'intent':'f'*64,'status':'MODEL_CALCULATED_NOT_PHYSICALLY_CERTIFIED'}
  self.expect('LIVE_BROKER_RETURN_MISSING',lambda:b.verify_persisted(fake))
