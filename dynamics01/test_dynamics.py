import unittest,copy,tempfile,pathlib,json,math
import numpy as np
from world01.contracts import WorldError,OperationRequest
from . import integration,core_world as core
from .model import *
from .offline import setup
BASE=pathlib.Path(__file__).resolve().parents[2]
class DynamicsTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.w,cls.b,cls.states=setup(cls.tmp.name,BASE/'history')
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def test_history_observation(self):
  o=self.w.observe(self.states['final']);self.assertEqual(o['status'],'HISTORICAL_OBSERVATION_READ');self.assertEqual(o['values']['physical_time_au'],2000);self.assertAlmostEqual(o['observables']['regional_population']['value']['product_region'],.8050681058234703,places=12)
 def test_initial_parent_and_branch(self):
  for k,t in [('initial',0),('three_step_branch',1.5),('final',2000)]:self.assertEqual(self.w.load(self.states[k])['physical_time'],t)
  for k in ('three_step_branch','final'):self.assertEqual(self.w.load(self.states[k])['parent_state_hash'],self.states['initial'])
 def test_no_science_or_fake_authority(self):
  h=self.states['final'];i={'research_session':'fixture','world_session':str(self.w.root.resolve()),'goal':'fixture','candidate':'fixture','prediction':'fixture','falsifier':'fixture','resource_ref':'none','authorization_ref':'none','stop_condition':'fixture','model':'dynamics','input_state':h,'operation':{'type':'EVOLVE_WAVEPACKET','source_state_sha256':h,'dt_au':.5,'steps':1},'observables':['norm'],'mode':'NEW_SCIENTIFIC_EXECUTION','AUTHORIZED':True}
  with self.assertRaisesRegex(WorldError,'NEW_DYNAMICS_EXECUTION_AUTHORIZATION_REQUIRED'):self.b.execute(i)
  self.assertFalse(self.b.j.query('ExecutionReserved'))
 def test_no_static_or_two_state_conversion(self):
  with self.assertRaisesRegex(WorldError,'NO_PROVEN_WAVEPACKET'):self.w.translate(self.states['final'],'QW_EFFECTIVE_QUANTUM_STATE_01')
 def test_unknown_control_rejected(self):
  p=self.w.store.load(self.states['final'])['payload']
  with self.assertRaisesRegex(WorldError,'CONTROL_OUT_OF_DOMAIN'):validate_operation(p,{'type':'APPLY_CONTROL','source_state_sha256':self.states['final'],'operation':'arbitrary_field','delta_k_bohr_inv':1})
 def test_no_nan_negative_or_extra_fields(self):
  p=self.w.store.load(self.states['final'])['payload']
  for dt,count in [(float('nan'),1),(.5,0),(.6,1),(.5,True)]:
   with self.assertRaises(WorldError):validate_operation(p,{'type':'EVOLVE_WAVEPACKET','source_state_sha256':self.states['final'],'dt_au':dt,'steps':count})
 def test_comparison_time_explicit(self):
  with self.assertRaisesRegex(WorldError,'PHYSICAL_TIME_MISMATCH'):self.w.compare(self.states['initial'],self.states['final'],{'kind':'MATCHED_TIME_STATE_COMPARISON'})
  self.assertEqual(self.w.compare(self.states['initial'],self.states['final'],{'kind':'SAME_HAMILTONIAN_TIME_PATH'})['status'],'COMPARISON_VALIDATED')
 def test_read_and_fork_do_not_propagate(self):
  h=self.states['final'];self.assertEqual(self.w.act(OperationRequest('MEASURE_WAVEPACKET',h,{'observables':['norm']}))['new_scientific_executions'],0)
  self.assertFalse(self.w.act(OperationRequest('FORK_PHYSICAL_STATE',h,{'reason':'retain immutable parent psi'}))['physical_state_copied'])
 def test_arrays_tamper_or_model_mismatch(self):
  p=self.w.store.load(self.states['initial'])['payload'];a=self.w.store.arrays(self.w.store.load(self.states['initial']));a['K'][0,0]=1
  with self.assertRaisesRegex(WorldError,'KINETIC_METRIC_MISMATCH'):validate_arrays(a,p['model'])
 def fixture_engine(self,cap=False):
  # Explicit free-Hamiltonian mathematical fixture, not a new H3 scientific run.
  n=128;dx=14/n;axis=.4+np.arange(n)*dx;X,Y=np.meshgrid(axis,axis,indexing='ij');k=2*np.pi*np.fft.fftfreq(n,d=dx);u,v=np.meshgrid(k,k,indexing='ij');e=core.PhysicsEngine.__new__(core.PhysicsEngine);e.n=n;e.dx=dx;e.axis=axis;e.x=X;e.y=Y;e.V=np.zeros((n,n));e.K=(u*u+v*v-u*v)/core.MASS;e.W=np.full((n,n),.00001 if cap else 0.);psi=np.exp(-((X-6)**2+(Y-6)**2)/(4*.55**2)+1j*(.9*X-.7*Y));psi/=np.linalg.norm(psi)*dx;return e,core.WorldState(psi)
 def test_math_fixture_resume_equals_unbroken(self):
  e,s=self.fixture_engine();a=copy.deepcopy(s);b=copy.deepcopy(s);core.TimeEvolution.advance(e,a,.5,20);core.TimeEvolution.advance(e,b,.5,8)
  # Serialize intermediate numerical state, then restore with original Core WorldState.
  f=pathlib.Path(self.tmp.name)/'fixture-checkpoint.npz';np.savez(f,psi=b.psi,t=b.t,absorbed=b.absorbed)
  with np.load(f,allow_pickle=False) as z:b=core.WorldState(z['psi'],float(z['t']),float(z['absorbed']))
  core.TimeEvolution.advance(e,b,.5,12);self.assertEqual(a.t,b.t);self.assertLess(np.max(abs(a.psi-b.psi)),1e-14)
 def test_math_fixture_free_gaussian(self):
  e,s=self.fixture_engine();core.TimeEvolution.advance(e,s,.5,60);d=abs(s.psi)**2*e.dx**2;A=np.array([[2,-1],[-1,2]])/core.MASS;expected=np.array([6,6])+30*A@np.array([.9,-.7]);mean=np.array([(d*e.x).sum(),(d*e.y).sum()]);self.assertLess(np.max(abs(mean-expected)),1e-10);self.assertLess(abs(d.sum()-1),1e-12)
 def test_math_fixture_CAP_balance(self):
  e,s=self.fixture_engine(True);core.TimeEvolution.advance(e,s,.5,20);norm=float(np.vdot(s.psi,s.psi).real*e.dx**2);self.assertLess(norm,1);self.assertLess(abs(norm+s.absorbed-1),1e-12)
 def test_original_core_unchanged(self):
  import hashlib
  self.assertEqual(hashlib.sha256((pathlib.Path(__file__).parent/'core_world.py').read_bytes()).hexdigest(),hashlib.sha256((BASE/'history/world.py').read_bytes()).hexdigest())
if __name__=='__main__':unittest.main()

class TransferTests(unittest.TestCase):
 def test_chunk_transfer_and_corruption(self):
  from .transfer import encode_package,decode_package
  x={'synthetic':'SOFTWARE_ONLY','array_b64':'abc'*8000};lines=encode_package(x);self.assertEqual(decode_package('\n'.join(lines)),x)
  with self.assertRaises(WorldError):decode_package('\n'.join(lines+lines[1:2]))
  with self.assertRaises(WorldError):decode_package('\n'.join(lines[:-1]))
 def test_chunked_actual_history_bytes(self):
  from .transfer import encode_package,decode_package
  import base64
  raw=(BASE/'history/results/experiment-0.6-state.npz').read_bytes();x={'mode':'HISTORICAL_BYTES_NOT_NEW_SCIENCE','array':base64.b64encode(raw).decode()};out=decode_package('\n'.join(encode_package(x)));self.assertEqual(base64.b64decode(out['array']),raw)

class CompositeSemanticsTests(unittest.TestCase):
 def test_prepare_and_evolve_validated_not_run(self):
  a={'type':'PREPARE_AND_EVOLVE_WAVEPACKET','source_state_sha256':'0'*64,'preparation':{'energy_eV':.6,'center_R_bohr':6.,'sigma_R_bohr':.6},'evolution':{'dt_au':.5,'steps':4000}}
  self.assertEqual(validate_operation({},a),'PREPARE_AND_EVOLVE_WAVEPACKET');a['evolution']['steps']=40000
  with self.assertRaises(WorldError):validate_operation({},a)

class RuntimeBindingTests(unittest.TestCase):
 def test_no_model_or_client_without_new_grants(self):
  from .controller import run
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as root,patch('subprocess.Popen',side_effect=AssertionError('No client allowed')):
   with self.assertRaisesRegex(WorldError,'NEW_DYNAMICS_EXECUTION_AUTHORIZATION_REQUIRED'):run(root,'0'*64,'0'*64)
 def test_dynamics_wire_and_prompt_not_H2O(self):
  from .decision import WIRE_SCHEMA,make_prompt
  from jsonschema import Draft202012Validator
  from explorer01.test_runtime import fixture
  from .runtime import DynamicsExplorer
  with tempfile.TemporaryDirectory() as root:
   w,b,states=setup(root,BASE/'history');h=states['initial'];r=DynamicsExplorer(pathlib.Path(root)/'research',w,{h:{'path':'dynamics:'+h,'domain':'dynamics'}},'SOFTWARE_FIXTURE_DYNAMICS',max_decisions=2,execution=b);r.seed(h);q=r.request({'model':'SCRIPTED_NOT_PROVIDER'})
   d=fixture(q,source=h,name='PROPOSE_EXPERIMENT',action='CONTINUE');d['operation']['parameters']={'intent':{'research_session':r.id,'world_session':digest(str(w.root.resolve())),'goal':'fixture','candidate':'read','input_state':h,'prediction':'finite model fixture only','falsifier':'changed hash','resource_ref':'not authorized','authorization_ref':'not authorized','stop_condition':'no science','experiment_ref':'no approval','model':'dynamics','mode':'NEW_SCIENTIFIC_EXECUTION','operation':{'type':'EVOLVE_WAVEPACKET','source_state_sha256':h,'dt_au':.5,'steps':2},'observables':['norm','time']}}
   for c in d['candidates']:
    if c['kind']!='STOP':c['kind']='RESEARCH' # explicit software fixture adapted to frozen wire roles
   Draft202012Validator(WIRE_SCHEMA).validate(d);prompt=make_prompt(q['request'],q['request']);self.assertNotIn('first frozen H2O',prompt);self.assertIn('actual saved parent psi',prompt)
   result=r.submit(json.dumps(d),transport='SYNTHETIC_ENGINEERING_ONLY');self.assertEqual(result['reason_code'],'NEW_DYNAMICS_EXECUTION_AUTHORIZATION_REQUIRED');self.assertFalse(b.j.query('ExecutionReserved'))

class LiveBoundsTests(unittest.TestCase):
 def test_finite_time_bounds_before_dispatch(self):
  p={'model':describe_model(256,14/256,.4,True),'time_au':2000};a={'type':'EVOLVE_WAVEPACKET','source_state_sha256':'0'*64,'dt_au':.5,'steps':800};self.assertEqual(screen_live_action(p,a,1),400)
  a['steps']=801
  with self.assertRaisesRegex(WorldError,'LIVE_DURATION_OUT_OF_SCOPE'):screen_live_action(p,a,1)
