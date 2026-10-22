"""Small analytic synthetic fixtures only, NOT molecular scientific execution."""
import copy,json,pathlib,sys,tempfile,unittest
import numpy as np
from interactive01.world import freeze,verify
from .contract import field_check,select_root,model_check,validate_system
from .state import QuantumStore
from .runtime import operate
from .dynamics import propagate
def spec():
    return {'version':'QW-WORLDSPEC-0.1','object_id':'SOFTWARE_H2_GEOMETRY_FIXTURE','epistemic_mode':'GROUNDED','matter':{'type':'molecule','atoms':[{'element':'H','xyz_angstrom':[0,0,-.37]},{'element':'H','xyz_angstrom':[0,0,.37]}],'periodic':False,'charge':0,'spin_2S':0},'physics':{'engine':'pyscf','method':'RHF','basis':'cc-pvdz','observables':['energy']},'experiment':{'action':'single_point'}}
def model():
    return {'source_type':'USER_DEFINED_EFFECTIVE_MODEL','H0_Eh':[[0,0],[0,.5]],'dipole_au':[[[0,0],[0,0]],[[0,0],[0,0]],[[0,1],[1,0]]],'selected':{'gap_Eh':.5,'nearest_computed_omitted_root_separation_Eh':.3},'scope':'Artificial analytic software fixture, not computed H2 parameters'}
def control(**kw):
    return {'amplitude_au':.001,'polarization':[0,0,1],'duration_au':40,'carrier_ratio':1,'phase_rad':0,'envelope':'sin2','time_unit':'atomic_time','field_unit':'atomic_electric_field',**kw}
class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=QuantumStore(self.tmp.name);self.root=self.store.create(spec(),'SOFTWARE_FIXTURE')
        self.state=self.store.save(parent=self.root['sha256'],world_spec=spec(),model=model(),ket=[1,0],time_au=0,reason='SOFTWARE_FIXTURE')
    def action(self,t,**kw):return {'type':t,'source_state_sha256':self.state['sha256'],**kw}
    def test_old_state_compatibility(self):self.assertEqual(self.store.load(self.root['sha256']),self.root)
    def test_complex_array_restore(self):
        s=self.store.save(parent=self.state['sha256'],world_spec=spec(),model=model(),ket=[1/np.sqrt(2),1j/np.sqrt(2)],time_au=0,reason='COMPLEX_FIXTURE')
        np.testing.assert_allclose(self.store.arrays(self.store.load(s['sha256']))['ket'],[1/np.sqrt(2),1j/np.sqrt(2)])
    def test_normalization_rejected(self):
        with self.assertRaises(ValueError):self.store.save(parent=None,world_spec=spec(),model=model(),ket=[1,1],time_au=0,reason='bad')
    def test_array_tamper(self):
        p=self.store.root/self.state['payload']['arrays']['path'];p.write_bytes(b'corrupted')
        with self.assertRaises(ValueError):self.store.arrays(self.state)
    def test_hash_stability(self):verify(self.state);self.assertEqual(self.store.load(self.state['sha256']),self.state)
    def test_no_arbitrary_physical_matrices(self):
        with self.assertRaises(ValueError):model_check(model())
    def test_hermitian_check(self):
        m=model();m['H0_Eh'][0][1]=1
        with self.assertRaises(ValueError):model_check(m,True)
    def test_units(self):
        with self.assertRaises(ValueError):field_check(control(time_unit='seconds'))
    def test_amplitude_bound(self):
        with self.assertRaises(ValueError):field_check(control(amplitude_au=.1))
    def test_polarization(self):
        with self.assertRaises(ValueError):field_check(control(polarization=[0,0,2]))
    def test_nan_control(self):
        with self.assertRaises(ValueError):field_check(control(amplitude_au=float('nan')))
    def test_unknown_field(self):
        with self.assertRaises(ValueError):field_check(control(magnetic_field=1))
    def test_root_selection(self):
        s=select_root([.4,.5,.8],[[1,0,0],[0,0,-1],[0,0,.5]],[True]*3,[0,0,1]);self.assertEqual(s['root_index'],1);self.assertEqual(s['effective_root_phase_relative_to_PySCF_X'],1)
    def test_degenerate_root(self):
        with self.assertRaises(ValueError):select_root([.5,.5],[[0,0,1],[0,0,1]],[True,True],[0,0,1])
    def test_dark_root_rejected(self):
        with self.assertRaises(ValueError):select_root([.5],[[0,0,0]],[True],[0,0,1])
    def test_unconverged_root_rejected(self):
        with self.assertRaises(ValueError):select_root([.5],[[0,0,1]],[False],[0,0,1])
    def test_inversion_check(self):
        s=spec();s['matter']['atoms'][0]['xyz_angstrom'][2]=0
        with self.assertRaises(ValueError):validate_system(s)
    def test_geometry_contract(self):self.assertTrue(validate_system(spec()))
    def test_no_unfulfilled_force_request(self):
        s=spec();s['physics']['observables']=['energy','forces']
        with self.assertRaises(ValueError):validate_system(s)
    def test_apply_is_not_evolution(self):
        n,r=operate(self.store,self.state,self.action('APPLY_EXTERNAL_FIELD',control=control()),fixture=True)
        self.assertEqual(n['payload']['time_au'],0);np.testing.assert_equal(self.store.arrays(n)['ket'],[1,0]);self.assertIsNone(n['payload']['observation'])
    def test_prepare_changes_boundary_not_field(self):
        n,r=operate(self.store,self.state,self.action('PREPARE_ELECTRONIC_STATE',basis_index=1),fixture=True)
        np.testing.assert_equal(self.store.arrays(n)['ket'],[0,1]);self.assertIsNone(n['payload']['control'])
    def test_measure_no_collapse(self):
        n,r=operate(self.store,self.state,self.action('MEASURE_STATE_POPULATION'),fixture=True)
        self.assertEqual(n['payload']['observation']['population'],[1,0]);self.assertEqual(r['status'],'SOFTWARE_FIXTURE_ONLY')
    def test_stale_action(self):
        with self.assertRaises(ValueError):operate(self.store,self.state,{'type':'MEASURE_STATE_POPULATION','source_state_sha256':'0'*64},fixture=True)
    def test_no_repeated_action(self):
        a=self.action('MEASURE_STATE_POPULATION');operate(self.store,self.state,a,fixture=True)
        with self.assertRaises(ValueError):operate(self.store,self.state,a,fixture=True)
    def test_failure_preserves_parent(self):
        with self.assertRaises(ValueError):operate(self.store,self.state,self.action('EVOLVE_QUANTUM_STATE',duration_au=40,time_unit='atomic_time'),fixture=True)
        self.assertEqual(self.store.load(self.state['sha256']),self.state);self.assertTrue(list((self.store.root/'transitions').glob('*/FAILURE.json')))
    def test_no_field_analytic_phase(self):
        initial=np.array([1,1j])/np.sqrt(2);v,tr,obs=propagate(model(),initial,control(amplitude_au=0),0,40,fixture=True)
        exact=initial*np.exp(-1j*np.array([0,.5])*40)
        np.testing.assert_allclose(v,exact,atol=1e-8);self.assertLess(np.ptp(tr['H0_expectation_Eh']),1e-8);self.assertLess(obs['quality']['norm_error_max'],1e-7)
    def test_driven_engine_fixture(self):
        v,tr,obs=propagate(model(),[1,0],control(),0,40,fixture=True)
        self.assertGreater(obs['population_max'],1e-6);self.assertGreater(obs['coherence_abs_max'],0);self.assertEqual(tr['kets'].shape,(801,2));self.assertEqual(obs['quality']['propagations'],2)
        self.assertGreater(np.ptp(tr['H0_expectation_Eh']),1e-7) # driven energy is NOT conserved
    def test_continuation_absolute_time(self):
        v,tr,o=propagate(model(),[1,0],control(amplitude_au=0),10,20,origin=0,fixture=True);self.assertEqual(tr['time_au'][0],10);self.assertEqual(tr['time_au'][-1],30)
    def test_weak_screen(self):
        m=model();m['selected']['nearest_computed_omitted_root_separation_Eh']=.001
        with self.assertRaises(ValueError):propagate(m,[1,0],control(),0,40,fixture=True)
    def test_no_PySCF_import(self):self.assertNotIn('pyscf',sys.modules)
    def test_time_is_physical_parameter(self):
        with self.assertRaises(ValueError):self.store.save(parent=self.state['sha256'],world_spec=spec(),model=model(),ket=[1,0],time_au=-1,reason='invalid')
    def test_parent_binding(self):
        with self.assertRaises((ValueError,FileNotFoundError)):self.store.save(parent='0'*64,world_spec=spec(),model=model(),ket=[1,0],time_au=0,reason='invalid')
    def test_driven_state_persists_real_complex_data(self):
        s,_=operate(self.store,self.state,self.action('APPLY_EXTERNAL_FIELD',control=control()),fixture=True)
        n,r=operate(self.store,s,{'type':'EVOLVE_QUANTUM_STATE','source_state_sha256':s['sha256'],'duration_au':40,'time_unit':'atomic_time'},fixture=True)
        arr=self.store.arrays(self.store.load(n['sha256']));self.assertEqual(arr['kets'].dtype,complex);self.assertEqual(n['payload']['time_au'],40)
        np.testing.assert_allclose(arr['ket'],arr['kets'][-1]);self.assertEqual(r['status'],'SOFTWARE_FIXTURE_ONLY')
    def test_unified_quantum_dispatch(self):
        from .world_runtime import act
        n,r=act(self.store,self.state,self.action('MEASURE_STATE_POPULATION'),fixture=True)
        self.assertEqual(n['payload']['observation']['population'],[1,0])
    def test_unified_structural_dispatch(self):
        from .world_runtime import act
        a={'type':'MEASURE_OBSERVABLE','source_state_sha256':self.root['sha256'],'observables':['energy']}
        n,r=act(self.store,self.root,a)
        self.assertEqual(r['status'],'BLOCKED');self.assertEqual(r['semantic_action'],'APPLIED')
    def test_unified_quantum_admission(self):
        from .world_runtime import act
        with self.assertRaises(ValueError):act(self.store,self.state,self.action('MEASURE_STATE_POPULATION'))
if __name__=='__main__':unittest.main()
