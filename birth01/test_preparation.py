import copy,json,tempfile,pathlib,unittest,os,subprocess,sys
from jsonschema import ValidationError
from world01.test_e00 import P,MANIFEST,state_files,STRUCT
from world01.session import WorldSession
from world01.contracts import WorldError
from router import digest
from interactive01.world import freeze
from .preparation import BirthPreparation,resource_check
class PreparationTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=pathlib.Path(self.t.name)
  if os.environ.get('BIRTH_EVIDENCE_ROOT'):
   self.root=pathlib.Path(os.environ['BIRTH_EVIDENCE_ROOT'])/self._testMethodName;self.root.mkdir(parents=True,exist_ok=False)
  self.world=WorldSession(self.root/'world',P,MANIFEST)
  f=next(f for f in state_files(STRUCT,domain=False) if len(json.loads((P/f).read_text())['payload']['world_spec']['matter']['atoms'])==2);e=self.world.reference(f);self.state=e['source_state_hash'];self.spec=copy.deepcopy(self.world.store.load(self.state)['payload']['world_spec']);self.spec['physics']={'engine':'pyscf','method':'RHF','basis':'cc-pvdz','observables':['energy','forces']};self.spec['object_id']='E01_FIXTURE_ONLY'
  self.req={'source_state_hash':self.state,'world_spec':self.spec,'action':'CHANGE_OBJECT','prediction':'No real physics in this fixture','falsifier':'Any fixture tagged CALCULATED','information_goal':'Exercise binding only','candidate_reasons':[{'candidate':'probe','reason':'test binding'},{'candidate':'STOP','reason':'valid zero-cost alternative'}],'prior_observation_hash':None,'actor':'B_WORK_AI_DECISION_REQUIRES_TRANSCRIPT_REVIEW'};self.b=BirthPreparation(self.world,self.root/'birth')
 def returned(self):
  i=self.b.submit(self.req);r=self.b.fixture_return(i,{'value':.1,'synthetic':True},spec_hash=digest(self.spec));return i,r
 def test_request_schema(self):
  r=copy.deepcopy(self.req);del r['prediction']
  with self.assertRaises(ValidationError):self.b.submit(r)
 def test_permission_denied_before_any_worker(self):
  i=self.b.submit(self.req);old=(self.world.root/'states'/f'{self.state}.json').read_bytes()
  with self.assertRaisesRegex(WorldError,'AUTHORITY_MISSING'):self.b.execute(i)
  self.assertEqual(old,(self.world.root/'states'/f'{self.state}.json').read_bytes());self.assertTrue((self.b.root/'blocked'/f'{i}.json').exists())
 def test_resource_limits_and_required_evidence(self):
  f={'memory.max':str(2**30),'memory.swap.max':'0','cpu.max':'100000 100000','memory.current':'100','memory.events':'oom 0','cpu.stat':'usage_usec 12','interfaces':['lo'],'threads':1,'affinity_count':1};self.assertIn('PASSED',resource_check(f)['status'])
  for k,v in [('memory.max',str(2**31)),('memory.swap.max','1'),('cpu.max','max 100000'),('interfaces',['eth0','lo']),('threads',2)]:
   with self.subTest(k=k):
    bad=copy.deepcopy(f);bad[k]=v
    with self.assertRaises(WorldError):resource_check(bad)
  with self.assertRaises(WorldError):resource_check({})
 def test_invalid_source_hash(self):
  r=copy.deepcopy(self.req);r['source_state_hash']='0'*64
  with self.assertRaises(WorldError):self.b.submit(r)
 def test_prediction_immutable(self):
  i=self.b.submit(self.req);p=self.b.root/'intents'/f'{i}.json';x=json.loads(p.read_text());x['request']['prediction']='changed after observation'
  with self.assertRaises(ValueError):freeze(p,x)
 def test_model_envelope(self):
  r=copy.deepcopy(self.req);r['world_spec']['physics']['method']='UHF'
  with self.assertRaises(WorldError):self.b.submit(r)
 def test_result_input_binding(self):
  i=self.b.submit(self.req)
  with self.assertRaisesRegex(WorldError,'RESULT_INPUT_MISMATCH'):self.b.fixture_return(i,{},spec_hash='0'*64)
 def test_no_feedback_no_second_action(self):
  self.b.submit(self.req);r=copy.deepcopy(self.req);r['world_spec']['object_id']+='2'
  with self.assertRaisesRegex(WorldError,'FEEDBACK_REQUIRED'):self.b.submit(r)
 def test_once_only_no_retry(self):
  self.b.submit(self.req)
  with self.assertRaisesRegex(WorldError,'NO_IMPLICIT_RETRY'):self.b.submit(self.req)
 def test_two_steps_budget_and_stop(self):
  i,r=self.returned();h=self.b.feedback(i,r,'CHANGE_OBJECT','Choose after reading fixture only',['STOP','CHANGE_OBJECT']);r2=copy.deepcopy(self.req);r2['prior_observation_hash']=h;r2['world_spec']['object_id']+='2';j=self.b.submit(r2);q=self.b.fixture_return(j,{'value':.2},spec_hash=digest(r2['world_spec']));r3=copy.deepcopy(r2);r3['world_spec']['object_id']+='3'
  with self.assertRaisesRegex(WorldError,'BUDGET_EXHAUSTED'):self.b.submit(r3)
  self.b.feedback(j,q,'STOP','Completed fixture; no science',['STOP'])
  with self.assertRaisesRegex(WorldError,'EXPERIMENT_STOPPED'):self.b.submit(r3)
 def test_exception_stops_and_keeps_intent(self):
  i=self.b.submit(self.req);self.b.fail(i,'SIMULATED_TIMEOUT');self.assertTrue((self.b.root/'intents'/f'{i}.json').exists())
  with self.assertRaises(WorldError):self.b.submit(self.req)
 def test_synthetic_not_physics_and_read_before_decision(self):
  i=self.b.submit(self.req)
  with self.assertRaises(WorldError):self.b.feedback(i,{},'STOP','no observation yet',['STOP'])
  with self.assertRaises(WorldError):self.b.fixture_return(i,{'status':'CALCULATED'},spec_hash=digest(self.spec))
 def test_global_job_budget_failed_attempts_count(self):
  from .authority import job_budget_check
  rows=[{'id':1,'head_branch':'b','head_sha':'a','status':'completed','conclusion':'success'},{'id':2,'head_branch':'b','head_sha':'b','status':'in_progress','conclusion':None}]
  self.assertEqual(job_budget_check(rows,2,'b','b')['prior_runs'],1)
  with self.assertRaises(WorldError):job_budget_check(rows,2,'a','b')
  rows[0]['conclusion']='failure'
  with self.assertRaises(WorldError):job_budget_check(rows,2,'b','b')
  rows.append({'id':3,'head_branch':'b','head_sha':'c','status':'queued'})
  with self.assertRaises(WorldError):job_budget_check(rows,3,'c','b')
 def test_stdlib_preinstall_gate(self):
  r=subprocess.run([sys.executable,'-S','-c',"from birth01.authority import approval_check; import sys; assert 'numpy' not in sys.modules; approval_check()"],cwd=P,capture_output=True,text=True)
  self.assertNotEqual(r.returncode,0);self.assertIn('AUTHORITY_MISSING',r.stderr);self.assertNotIn('ModuleNotFoundError',r.stderr)
 def test_workflow_static_manual_only_and_free_storage_path(self):
  text=(P/'birth01/world-birth-once.yml').read_text();self.assertIn('workflow_dispatch:',text)
  for forbidden in ['push:','schedule:','pull_request:','upload-artifact','actions/cache','self-hosted','contents: write']:
   self.assertNotIn(forbidden,text)
  self.assertIn('runs-on: ubuntu-24.04',text);self.assertIn('timeout-minutes: 15',text);self.assertIn('github.run_attempt == 1',text)
 def test_unimplemented_action_is_not_silently_measurement(self):
  r=copy.deepcopy(self.req);r['action']='DISPLACE_ATOM'
  with self.assertRaises(ValidationError):self.b.submit(r)
 def test_periodic_resource_dimension_screen(self):
  from .preparation import screen_object
  a=4.46;s={'version':'QW-WORLDSPEC-0.1','object_id':'PERIODIC_PREFLIGHT_FIXTURE','epistemic_mode':'GROUNDED','matter':{'type':'periodic_cell','periodic':True,'charge':0,'spin_2S':0,'atoms':[{'element':'Ne','xyz_angstrom':[0,0,0]}],'cell_angstrom':[[0,a/2,a/2],[a/2,0,a/2],[a/2,a/2,0]]},'physics':{'engine':'pyscf-pbc','method':'RKS','basis':'cc-pvdz','xc':'PBE','observables':['energy']}}
  self.assertEqual(screen_object(s)['AO_upper'],14)
  s['physics']['observables']=['forces']
  with self.assertRaises(WorldError):screen_object(s)
 def test_numerical_return_guard_synthetic_contract_only(self):
  from .science_entry import check_observation
  n=len(self.spec['matter']['atoms']);fake={'status':'CALCULATED','world_spec_sha256':digest(self.spec),'observation':{'energy':-1.,'energy_zero':'TEST_FIXTURE_REFERENCE','converged':True,'forces_Eh_per_bohr':[[0.,0.,0.] for i in range(n)]}}
  self.assertEqual(check_observation(self.spec,fake)['status'],'CALCULATED')
  fake['observation']['forces_Eh_per_bohr'][0][0]=1.
  self.assertEqual(check_observation(self.spec,fake)['status'],'UNVERIFIED')
  # These values are unit-test inputs; no physical result is persisted or claimed.
if __name__=='__main__':unittest.main(verbosity=2)
