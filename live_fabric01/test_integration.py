"""No solver/model invocation: actual historical records + explicitly synthetic decisions."""
import unittest,pathlib,json,tempfile,copy,os
from unittest.mock import patch
from router import digest
from world01.contracts import WorldError
from world01 import fabric as semantics
from explorer01.test_runtime import fixture as legacy_fixture
from .fabric import ExecutionFabric,FabricWorldSession,LIMITS,physical_key
from .runtime import FabricExplorer
from .catalog import examples,replay_intent
P=pathlib.Path(__file__).resolve().parents[1];MAN=json.loads((P.parent/'SOURCE_BASELINE_SHA256.json').read_text());EX=examples(P,MAN)
def fixture(req,**kwargs):
 if req['request']['context']['memory']['observations']:return legacy_fixture(req,**kwargs)
 # Legacy test helper assumed a seeded observation. Empty sessions are legal;
 # remove helper-only placeholder references before any decision is submitted.
 q=copy.deepcopy(req);q['request']['context']['memory']['observations']=[{'hash':'HELPER_ONLY_NEVER_SUBMITTED'}]
 d=legacy_fixture(q,**kwargs);d['observation_refs']=[];d['memory_updates']=[];return d

class Integration(unittest.TestCase):
 def setUp(self):
  self.root=pathlib.Path(os.environ['QW_FABRIC_TEST_EVIDENCE'])/self._testMethodName;self.root.mkdir(parents=True)
  self.w=FabricWorldSession(self.root/'world',P,MAN);self.b=ExecutionFabric(self.root/'broker',self.w);self.w.attach(self.b)
  for v in EX.values():self.w.reference(v['source_path'])
 def intent(self,d='molecular'):return replay_intent(EX[d],d,self.w)
 def reject(self,code,fn):
  with self.assertRaises(WorldError) as e:fn()
  self.assertEqual(e.exception.code,code)
 def run_domain(self,d):
  with patch('subprocess.Popen',side_effect=AssertionError('No science or process allowed in replay')):r=self.w.execute_physics(self.intent(d))
  self.assertEqual(r['status'],'HISTORICAL_REAL_EVIDENCE_REPLAY');self.assertEqual(r['new_scientific_executions'],0);self.assertEqual(r['state'],EX[d]['target_state']);return r
 def test_01_molecular_real_replay(self):self.run_domain('molecular')
 def test_02_correlated_real_replay(self):self.run_domain('correlated')
 def test_03_effective_real_replay(self):self.run_domain('effective')
 def test_04_distinct_worker_semantics(self):
  routes=[self.b.resolve(self.intent(d)) for d in EX];self.assertEqual(len({x['worker'] for x in routes}),3)
 def test_05_wrong_model_rejected(self):
  i=self.intent();i['model']='effective';self.reject('PHYSICAL_MODEL_MISMATCH',lambda:self.b.execute(i))
 def test_06_unknown_model_rejected(self):
  i=self.intent();i['model']='core03';self.reject('MODEL_NOT_CONNECTED',lambda:self.b.execute(i))
 def test_07_stale_parent_rejected(self):
  i=self.intent();i['input_state']=EX['correlated']['input_state'];self.reject('STALE_PHYSICAL_PARENT',lambda:self.b.execute(i))
 def test_08_wrong_action_rejected(self):
  i=copy.deepcopy(self.intent());i['operation']['type']='EVOLVE_QUANTUM_STATE';self.reject('HISTORICAL_ACTION_MISMATCH',lambda:self.b.execute(i))
 def test_09_absent_observable_rejected(self):
  i=self.intent('correlated');i['observables']=['forces'];self.reject('OBSERVABLE_OUT_OF_DOMAIN',lambda:self.b.execute(i))
 def test_10_no_science_grant(self):
  i=self.intent();i['mode']='NEW_SCIENTIFIC_EXECUTION';self.reject('NEW_SCIENCE_NOT_AUTHORIZED',lambda:self.b.execute(i));self.assertFalse(self.b.j.query('ExecutionReserved'))
 def test_11_model_flag_never_grants(self):
  i=self.intent();i.update(mode='NEW_SCIENTIFIC_EXECUTION',AUTHORIZED=True,authority=True);self.reject('NEW_SCIENCE_NOT_AUTHORIZED',lambda:self.b.execute(i))
 def test_12_duplicate_no_second_dispatch(self):
  self.run_domain('molecular');self.reject('DUPLICATE_OPERATION_NO_REEXECUTION',lambda:self.b.execute(self.intent()));self.assertEqual(len(self.b.j.query('ExecutionReserved')),1)
 def test_13_restore_no_refund(self):
  self.run_domain('correlated');b=ExecutionFabric(self.root/'broker',self.w);self.reject('DUPLICATE_OPERATION_NO_REEXECUTION',lambda:b.execute(self.intent('correlated')))
 def test_14_failed_attempt_preserved(self):
  with patch.object(self.w,'replay',side_effect=RuntimeError('INJECTED_ENGINEERING_FAILURE')):
   with self.assertRaises(RuntimeError):self.b.execute(self.intent())
  self.assertEqual(len(list((self.root/'broker/attempts').glob('*/failure.json'))),1);self.reject('DUPLICATE_OPERATION_NO_REEXECUTION',lambda:self.b.execute(self.intent()))
 def test_15_interrupted_reservation_no_retry(self):
  i=self.intent();h=digest(i);fp=physical_key(i)
  with self.b.j.lock():self.b.j.append('ExecutionReserved',{'intent_hash':h,'fingerprint':fp,'new_science':False});self.b.j.checkpoint()
  b=ExecutionFabric(self.root/'broker',self.w);self.assertEqual(b.j.query('ExecutionFailed')[0]['data']['status'],'INTERRUPTED_NO_RETRY');self.reject('DUPLICATE_OPERATION_NO_REEXECUTION',lambda:b.execute(i))
 def test_16_illegal_state_translation(self):
  r=self.run_domain('correlated');self.reject('TRANSLATION_FORBIDDEN',lambda:self.w.translate(r['state'],'QW_EFFECTIVE_QUANTUM_STATE_01'))
 def test_17_cross_object_energy_comparison(self):
  a=self.run_domain('molecular');b=self.run_domain('correlated');self.reject('INCOMPARABLE',lambda:self.w.compare(a['state'],b['state']))
 def test_18_effective_energy_zero_comparison(self):
  r=self.run_domain('effective');self.reject('INCOMPARABLE',lambda:self.w.compare(r['state'],r['state']))
 def test_19_synthetic_cannot_be_real(self):
  s=self.w.create(EX['molecular']['world_spec'],synthetic=True);self.assertFalse(s['source_execution']['real_calculated']);self.reject('SYNTHETIC_MISLABEL_BLOCKED',lambda:self.w.compare(s['source_state_hash'],s['source_state_hash']))
 def test_20_old_e00_gate_unchanged(self):
  from world01.contracts import OperationRequest
  s=EX['molecular']['input_state'];r=self.w.act(OperationRequest('MEASURE_OBSERVABLE',s,{'authority':True},('energy',)));self.assertEqual(r['reason_code'],'AUTHORITY_MISSING')
 def make_runtime(self):
  cat={x['input_state']:{'path':x['source_path'],'domain':d} for d,x in EX.items()}
  return FabricExplorer(self.root/'research',self.w,cat,'OFFLINE QA: replay molecular/correlated/effective; no new science',max_decisions=5,execution=self.b)
 def submit(self,r,domain):
  q=r.request({'model':'SCRIPTED_ENGINEERING_FIXTURE_NOT_MODEL'});d=fixture(q,source=EX[domain]['input_state'],name='PROPOSE_EXPERIMENT',action='CHANGE_PHYSICAL_DOMAIN');d['operation']['parameters']={'intent':replay_intent(EX[domain],domain,self.w,r.id)}
  return r.submit(json.dumps(d),transport='SYNTHETIC_ENGINEERING_ONLY')
 def test_21_auto_return_same_explorer(self):
  r=self.make_runtime();out=self.submit(r,'molecular');self.assertEqual(out['status'],'COMPLETED',out);ctx=r.request({'model':'SCRIPTED_ENGINEERING_FIXTURE_NOT_MODEL'})
  self.assertEqual(ctx['request']['context']['memory']['observations'][-1]['state'],EX['molecular']['target_state']);self.assertEqual(out['science_jobs'],0)
 def test_22_two_domains_one_research_context(self):
  r=self.make_runtime();self.assertEqual(self.submit(r,'molecular')['status'],'COMPLETED');self.assertEqual(self.submit(r,'correlated')['status'],'COMPLETED');obs=r.context()['memory']['observations'];self.assertEqual(len(obs),2);self.assertEqual(obs[-1]['evidence_role'],'HISTORICAL_REAL_EVIDENCE_REPLAY');self.assertNotEqual(obs[-1]['domain'],obs[0]['domain'])
 def test_23_checkpoint_resume_and_stop(self):
  r=self.make_runtime();self.submit(r,'effective');r=self.make_runtime();q=r.request({'model':'SCRIPTED_ENGINEERING_FIXTURE_NOT_MODEL'});d=fixture(q,source=EX['effective']['input_state'],name='STOP',action='STOP');d['selected']='stop';out=r.submit(json.dumps(d));self.assertEqual(out['status'],'STOPPED');self.reject('RESEARCH_STOPPED',lambda:r.request({}))
 def test_24_failed_candidate_can_switch(self):
  r=self.make_runtime();q=r.request({});d=fixture(q,source=EX['molecular']['input_state'],name='PROPOSE_EXPERIMENT');i=replay_intent(EX['molecular'],'molecular',self.w,r.id);i['mode']='NEW_SCIENTIFIC_EXECUTION';d['operation']['parameters']={'intent':i};out=r.submit(json.dumps(d));self.assertEqual(out['reason_code'],'NEW_SCIENCE_NOT_AUTHORIZED');self.assertEqual(r.j.query('CandidateStatus')[-1]['data']['status'],'PARKED');self.assertEqual(self.submit(r,'correlated')['status'],'COMPLETED')
 def test_25_source_hash_unchanged(self):
  import hashlib
  used=set()
  for d in EX:
   r=self.run_domain(d);used|={EX[d]['receipt_path'],EX[d]['source_path']}
  self.assertTrue(all(hashlib.sha256((P/f).read_bytes()).hexdigest()==MAN['files'][f] for f in used))
 def test_26_cross_session_rejected(self):
  i=self.intent();i['world_session']='elsewhere';self.reject('WORLD_SESSION_MISMATCH',lambda:self.b.execute(i))
 def test_27_required_intent_fields(self):
  i=self.intent();del i['falsifier'];self.reject('INCOMPLETE_PHYSICAL_INTENT',lambda:self.b.execute(i))
 def test_28_bad_grant_pin(self):
  p=self.root/'fake.json';p.write_text('{}');self.b.grant_path=p;self.b.grant_sha256='0'*64;self.reject('GRANT_PIN_MISMATCH',lambda:self.b.authorize(self.intent()))
 def test_29_legacy_grant_not_reused(self):
  from world01.session import filehash
  p=P/'birth01/AUTHORITY.json';self.b.grant_path=p;self.b.grant_sha256=filehash(p);self.reject('NEW_SCIENCE_NOT_AUTHORIZED',lambda:self.b.authorize(self.intent()))
 def test_30_replay_zero_job_consumption(self):
  for d in EX:self.run_domain(d)
  self.assertEqual(sum(e['data']['new_science'] for e in self.b.j.query('ExecutionReserved')),0)
 def test_31_automatic_loop_observation_conditioned_fixture(self):
  r=self.make_runtime()
  class ScriptedAdapter:
   def decide(inner,request):
    req={'hash':digest(request),'request':request};obs=request['context']['memory']['observations']
    if len(obs)<2:
     domain='molecular' if not obs else 'correlated';d=fixture(req,source=EX[domain]['input_state'],name='PROPOSE_EXPERIMENT',action='CHANGE_PHYSICAL_DOMAIN');d['operation']['parameters']={'intent':replay_intent(EX[domain],domain,self.w,r.id)}
    else:
     d=fixture(req,source=obs[-1]['state'],name='STOP',action='STOP');d['selected']='stop'
    return json.dumps(d)
  outcomes=r.run(ScriptedAdapter(),{'model':'SYNTHETIC_ENGINEERING_FIXTURE'},max_steps=4)
  self.assertEqual([x['status'] for x in outcomes],['COMPLETED','COMPLETED','STOPPED']);self.assertEqual(len(r.j.query('PhysicalEvidence')),2)
  self.assertEqual(r.j.query('DecisionAccepted')[-1]['data']['decision']['observation_refs'][-1],r.j.query('PhysicalEvidence')[-1]['data']['hash'])
 def test_32_live_controller_default_denies_before_client(self):
  from .controller import run
  with patch('subprocess.Popen',side_effect=AssertionError('Client forbidden')):self.reject('LIVE_SCIENCE_GRANT_REQUIRED',lambda:run(self.root,'0'*64,'0'*64))
 def test_33_failed_science_slot_no_refund_fixture(self):
  # Engineering-only admission stub: no solver or real authority is asserted.
  from .transport import DockerTransport
  self.b.transport=DockerTransport(P,'synthetic@sha256:'+'0'*64)
  # This live precondition was added in E01: displacement needs an actual prior force.
  # Replay an existing measured parent; still no new scientific calculation.
  self.w.replay(EX['molecular']['receipt_path'])
  with patch.object(self.b,'authorize',return_value={'fixture':'NO_REAL_AUTHORITY'}):
   for n in range(2):
    i=self.intent();i['input_state']=EX['molecular']['target_state'];i.update(mode='NEW_SCIENTIFIC_EXECUTION',stop_condition=f'Synthetic failure {n}');i['operation']={'type':'DISPLACE_ATOM','source_state_sha256':i['input_state'],'atom_id':'atom-0','vector':[0,0,.001*(n+1)],'unit':'angstrom'}
    self.reject('RUNTIME_TRANSPORT_DISABLED',lambda:self.b.execute(i))
   i=self.intent();i['input_state']=EX['molecular']['target_state'];i.update(mode='NEW_SCIENTIFIC_EXECUTION',stop_condition='third synthetic request');i['operation']={'type':'DISPLACE_ATOM','source_state_sha256':i['input_state'],'atom_id':'atom-0','vector':[0,0,.003],'unit':'angstrom'}
   self.reject('SCIENTIFIC_JOB_LIMIT',lambda:self.b.execute(i))
  self.assertEqual(sum(e['data']['new_science'] for e in self.b.j.query('ExecutionReserved')),2);self.assertFalse(self.b.j.query('ExecutionReturned'))
 def test_34_transport_never_accepts_arbitrary_return(self):
  from .transport import DockerTransport
  t=DockerTransport(P,'fixture@sha256:'+'0'*64);self.reject('UNAUTHENTICATED_WORKER_PACKAGE',lambda:t.verify_package({'state':'fake'}))
 def test_35_effective_control_change_not_science(self):
  i=self.intent('effective');i['mode']='NEW_SCIENTIFIC_EXECUTION';i['operation']={'type':'APPLY_EXTERNAL_FIELD','source_state_sha256':i['input_state']}
  self.reject('CONTROL_STATE_CHANGE_IS_NOT_A_NEW_SCIENCE_JOB',lambda:self.b.resolve(i))
 def test_36_runtime_resource_guard_inherited(self):
  from birth01.preparation import resource_check
  facts={'memory.max':str(2**30),'memory.swap.max':'0','cpu.max':'100000 100000','memory.current':'100','memory.events':'oom 0','cpu.stat':'usage_usec 1','interfaces':['lo'],'threads':1,'affinity_count':1}
  self.assertEqual(resource_check(facts)['status'],'RESOURCE_EVIDENCE_SCREEN_PASSED');facts['memory.swap.max']='1';self.reject('RESOURCE_BLOCKED',lambda:resource_check(facts))
 def test_37_new_mode_and_archive_not_interchangeable(self):
  i=self.intent();i['mode']='CALCULATED';self.reject('EXECUTION_MODE_INVALID',lambda:self.b.execute(i))
 def test_38_preserved_core_not_fake_supported(self):
  from .fabric import WORKERS
  self.assertNotIn('core03',WORKERS);self.assertNotIn('periodic',WORKERS)

 def test_39_changed_narrative_is_still_duplicate(self):
  self.run_domain('molecular');i=self.intent();i.update(candidate='a different name',stop_condition='renamed stop rule',prediction='changed story');self.reject('DUPLICATE_OPERATION_NO_REEXECUTION',lambda:self.b.execute(i))
 def test_40_github_disabled_before_network(self):
  from .github_transport import GithubFabricTransport
  t=GithubFabricTransport(self.root/'remote')
  with patch.object(t,'gh',side_effect=AssertionError('No network')):self.reject('RUNTIME_TRANSPORT_DISABLED',lambda:t.execute({},self.w,self.root,None,None,None))
 def test_41_reobserve_archive_never_becomes_new_science(self):
  r=self.make_runtime();self.submit(r,'molecular');h=EX['molecular']['target_state'];q=r.request({});d=fixture(q,source=h);out=r.submit(json.dumps(d));self.assertEqual(out['status'],'COMPLETED');self.assertEqual(r.j.query('PhysicalEvidence')[-1]['data']['evidence_role'],'HISTORICAL_REAL_EVIDENCE_REPLAY')
 def test_42_fork_returned_state_remains_same_physics(self):
  r=self.make_runtime();self.submit(r,'correlated');h=EX['correlated']['target_state'];q=r.request({});d=fixture(q,source=h,name='FORK',action='FORK');d['operation']['parameters']={'reason':'Research branch only'};out=r.submit(json.dumps(d));self.assertEqual(out['status'],'COMPLETED');self.assertFalse(out['result']['physical_state_copied'])
 def test_43_candidate_park_and_abandon_not_mission_death(self):
  r=self.make_runtime();self.submit(r,'molecular')
  for status,action in [('PARKED','CONTINUE'),('ABANDONED','ABANDON')]:
   q=r.request({});d=fixture(q,source=EX['molecular']['input_state'],name='FORK',action=action);d['operation']['parameters']={'candidate_status':status,'candidate_id':'read'};out=r.submit(json.dumps(d));self.assertEqual(out['status'],'LOCAL_CANDIDATE_STATE_UPDATED');self.assertFalse(out['physical_conversion'])
  self.assertFalse(r.j.query('Stopped'))
 def test_44_remote_fee_uncertainty_blocks_before_network(self):
  from .github_transport import GithubFabricTransport
  p=self.root/'unapproved_fee.json';p.write_text(json.dumps({'status':'HUMAN_GRANTED','scope':'QW-LIVE-FABRIC-01','zero_additional_cost_verified':False}))
  t=GithubFabricTransport(self.root/'remote',runtime_enabled=True)
  with patch.object(t,'gh',side_effect=AssertionError('No network')):self.reject('REMOTE_COST_OR_AUTHORITY_UNCONFIRMED',lambda:t.execute({},self.w,self.root,p,None,None))
