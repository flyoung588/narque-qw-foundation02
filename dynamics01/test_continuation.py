"""Continuation software admission only. No model, solver or live transport.
Synthetic grants exist only inside temporary test folders; never execution authority.
"""
import pathlib,tempfile,json,copy,shutil,unittest,os
from unittest.mock import patch
from types import SimpleNamespace
from router import digest
from world01.session import filehash
from world01.contracts import WorldError
from explorer01.codex_invocation import InvocationBudget
from explorer01.memory import Journal
from .offline import setup
from .fabric import DynamicsExecutionFabric
from .continuation import ContinuationResearchSession,load_binding,derive_intent,validate_execution_delegation
ROOT=pathlib.Path(__file__).resolve().parents[2]
class ContinuationAdmission(unittest.TestCase):
 def setUp(self):
  self.root=pathlib.Path(os.environ.get('QW_CONTINUATION_EVIDENCE',tempfile.mkdtemp()))/self._testMethodName;self.root.mkdir(parents=True,exist_ok=False)
  shutil.copytree(ROOT/'inherited',self.root/'inherited');shutil.copyfile(ROOT/'CONTINUATION_BINDING.json',self.root/'CONTINUATION_BINDING.json');shutil.copytree(self.root/'inherited/model_budget',self.root/'live/model_budget')
  self.budget=InvocationBudget(self.root/'live/model_budget',6);self.w,_,self.states=setup(self.root/'session',ROOT/'history');self.original_binding,self.original,self.raw,self.provider=load_binding(self.root)
  self.g=json.loads((ROOT/'LIVE_SCIENCE_AUTHORITY.json').read_text());self.g.update(status='HUMAN_GRANTED',human_reference='SYNTHETIC_SOFTWARE_TEST_NOT_AUTHORITY',source_sha256='SYNTHETIC_SOURCE')
  self.gp=self.root/'LIVE_SCIENCE_AUTHORITY.json';self.gp.write_text(json.dumps(self.g));self.b=DynamicsExecutionFabric(self.root/'live/broker',self.w,grant_path=self.gp,grant_sha256=filehash(self.gp),source_hash='SYNTHETIC_SOURCE',model_budget=self.budget);self.w.attach(self.b)
  self.s=ContinuationResearchSession(self.root/'live/research',self.w,{self.states['initial']:{'path':'dynamics:'+self.states['initial'],'domain':'dynamics'}},'SOFTWARE_ONLY_NO_MODEL_NO_SCIENCE',max_decisions=3,execution=self.b,model_budget=self.budget,binding_root=self.root)
  self.g['research_session']=self.s.id;self.save();self.s.seed(self.states['initial'])
 def save(self):self.gp.write_text(json.dumps(self.g));self.b.grant_sha256=filehash(self.gp)
 def intent(self):return derive_intent(self.original,research_session=self.s.id,world_session=digest(str(self.w.root.resolve())),grant_sha256=self.b.grant_sha256,binding_sha256=self.s.binding_pin)
 def authorize(self,intent=None):return self.b.authorize(intent or self.intent(),self.provider,self.raw)
 def reject(self,fn,reason=None):
  with self.assertRaises((WorldError,ValueError)) as cm:fn()
  if reason:self.assertIn(reason,str(cm.exception))
 def tearDown(self):
  (self.root/'SOFTWARE_TEST_RECEIPT.json').write_text(json.dumps({'new_model_calls':0,'actual_cloud_jobs':0,'new_propagations':0,'historical_call_prefix':2,'current_calls':len(self.budget.j.query('CallReserved')) if (self.root/'live/model_budget/checkpoint.json').exists() else 'FIXTURE_RESET','engine_invocations':'NONE; any Observation is explicit archived fixture'},indent=2))
 def test_01_original_chain_and_only_metadata_rebinding(self):
  original_sha=filehash(self.root/'inherited/model/call02/response.txt');i=self.intent();self.assertEqual(i['operation'],self.original['operation']);self.assertEqual(i['prediction'],self.original['prediction']);self.assertEqual(i['falsifier'],self.original['falsifier']);self.assertEqual(original_sha,self.original_binding['original_response_sha256']);self.assertNotEqual(self.s.id,self.original['research_session']);self.assertTrue(Journal(self.root/'inherited/research').query('Stopped'))
 def test_02_exact_authorized_delegation_accepts_without_debit(self):
  self.assertEqual(self.authorize()['human_reference'],'SYNTHETIC_SOFTWARE_TEST_NOT_AUTHORITY');self.assertEqual(len(self.b.j.query('ExecutionReserved')),0);self.assertEqual(len(self.budget.j.query('CallReserved')),2)
 def test_03_no_new_human_authority_rejected(self):
  self.g.update(status='NOT_GRANTED',human_reference=None);self.save();self.reject(self.s.execute_original_decision,'NEW_DYNAMICS_EXECUTION_AUTHORIZATION_REQUIRED');self.assertFalse(self.b.j.query('ExecutionReserved'))
 def test_04_explicit_new_job_budget_required(self):
  self.g.pop('new_independent_science_tranche');self.save();self.reject(self.authorize,'EXPLICIT_NEW_JOB_BUDGET_REQUIRED')
 def test_05_every_scientific_change_rejected(self):
  for key,value in [('prediction','changed prediction'),('falsifier','changed falsifier'),('observables',['norm']),('goal','different scientific goal'),('input_state','0'*64),('experiment_ref','0'*64)]:
   i=self.intent();i[key]=value;self.reject(lambda:self.authorize(i))
  for key,value in [('dt_au',.25),('steps',1999),('source_state_sha256','0'*64)]:
   i=self.intent();i['operation'][key]=value;self.reject(lambda:self.authorize(i),'DELEGATION_SCIENTIFIC_FIELDS_CHANGED')
 def test_06_wrong_parent_array_bytes_rejected(self):
  state=self.w.store.load(self.states['initial']);p=self.w.root/state['payload']['arrays']['path'];p.write_bytes(p.read_bytes()+b'WRONG_PSI')
  self.reject(lambda:self.b.resolve(self.intent()))
 def test_07_model_budget_reset_rejected(self):
  shutil.rmtree(self.root/'live/model_budget');self.budget=InvocationBudget(self.root/'live/model_budget',6);self.b.model_budget=self.budget;self.reject(self.authorize,'DELEGATION_MODEL_BUDGET_RESET')
 def test_08_original_model_or_stop_evidence_tamper_rejected(self):
  p=self.root/'inherited/model/call02/response.txt';raw=p.read_bytes();p.write_bytes(raw+b' ');self.reject(self.authorize,'DELEGATION_EVIDENCE_CHANGED');p.write_bytes(raw)
  p=next((self.root/'inherited/research/events').glob('*'+self.original_binding['original_stop_event']+'.json'));p.write_bytes(p.read_bytes()+b' ');self.reject(self.authorize,'DELEGATION_EVIDENCE_CHANGED')
 def archived_return(self):
  state=self.states['three_step_branch'];return {'status':'HISTORICAL_REAL_EVIDENCE_REPLAY','state':state,'observation':self.w.observe(state),'new_scientific_executions':0}
 def test_09_automatic_observation_ingress_to_next_request(self):
  with patch.object(self.w,'execute_physics',return_value=self.archived_return()) as worker:
   out=self.s.execute_original_decision();self.assertEqual(out['mode'],'ENGINEERING_RECOVERED_CONTINUATION');self.assertEqual(worker.call_args.kwargs['raw_decision'],self.raw)
  req=self.s.request({'model':'SYNTHETIC_NO_CALL'});observations=req['request']['context']['memory']['observations'];self.assertEqual(observations[-1]['state'],self.states['three_step_branch']);self.assertEqual(req['request']['context']['continuation']['original_prediction'],self.original['prediction']);self.assertEqual(len(self.budget.j.query('CallReserved')),2);self.assertFalse(self.s.j.query('ModelResponse'));self.assertTrue(self.s.j.query('OriginalDecisionDelegated'))
 def test_10_one_delegation_no_automatic_retry(self):
  with patch.object(self.w,'execute_physics',return_value=self.archived_return()):self.s.execute_original_decision()
  self.reject(self.s.execute_original_decision,'CONTINUATION_ALREADY_ATTEMPTED_NO_RETRY')
 def test_11_failure_preserves_both_stops_and_budget(self):
  with patch.object(self.w,'execute_physics',side_effect=WorldError('SYNTHETIC_SOLVER_FAILURE_NO_REAL_JOB')):self.reject(self.s.execute_original_decision)
  self.assertTrue(self.s.j.query('Stopped'));self.assertTrue(Journal(self.root/'inherited/research').query('Stopped'));self.assertEqual(len(self.budget.j.query('CallReserved')),2);self.reject(self.s.execute_original_decision,'RESEARCH_STOPPED')
 def test_12_ordinary_current_model_path_not_replaced_by_delegation(self):
  i=self.intent();i.pop('delegation_ref');d=json.loads(self.raw);d['operation']['parameters']['intent']=copy.deepcopy(i);d['operation']['parameters']['intent'].pop('model_request_hash');fake=json.dumps(d)
  with patch('explorer01.l1_audit.verify_invocation',return_value={'explicit_mock':'NO_REAL_NEW_MODEL_IDENTITY'}):self.assertEqual(self.b.authorize(i,self.provider,fake)['source_sha256'],'SYNTHETIC_SOURCE')
  wrong=copy.deepcopy(i);wrong['prediction']='changed';self.reject(lambda:self.b.authorize(wrong,self.provider,fake),'MODEL_INTENT_MISMATCH')
 def test_13_bound_grant_and_first_slot_only(self):
  self.g['source_sha256']='OTHER';self.save();self.reject(self.authorize,'SOURCE_RESOURCE_BINDING_MISMATCH');self.g['source_sha256']='SYNTHETIC_SOURCE';self.save();self.b.j.append('ExecutionReserved',{'intent_hash':'FIXTURE_ALREADY_RESERVED','new_science':True,'fingerprint':'FIXTURE_NO_JOB'});self.reject(self.authorize,'DELEGATION_FIRST_ATTEMPT_ONLY')
if __name__=='__main__':unittest.main()
