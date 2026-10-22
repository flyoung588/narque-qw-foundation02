"""Synthetic engineering tests, no PySCF/ASE import or physical execution."""
import copy,json,pathlib,subprocess,sys,tempfile,unittest
from unittest.mock import patch
import numpy as np
from router import digest
from .world import Store,apply,freeze,transition,compare_states
from .runtime import run_stage
ROOT=pathlib.Path(__file__).resolve().parents[1]
def spec():
    s=json.loads((ROOT/'decisions/WorldSpec_QW_P02_MGO_ROCKSALT_2ATOM.json').read_text())
    from periodic03.contract import SAMPLING,NUMERICS
    s['object_id']='QW_I01_MGO_INITIAL';s['physics'].update(method='KRKS',k_sampling={**SAMPLING,'mesh':[1,1,1]},numerics=NUMERICS)
    return s
class Software(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name);self.s=self.store.create(spec(),'synthetic fixture')
    def action(self,kind='DISPLACE_ATOM',**kw):
        a={'type':kind,'source_state_sha256':self.s['sha256']}
        if kind=='DISPLACE_ATOM':a.update(atom_id='atom-1',vector=[.01,0,0],unit='angstrom')
        elif kind=='AFFINE_STRAIN_CELL':a.update(deformation=(np.eye(3)*1.01).tolist(),coordinates='preserve_fractional',unit='dimensionless')
        else:a.update(observables=['energy'])
        a.update(kw);return a
    def test_persistent_identity(self):self.assertEqual(self.s,self.store.load(self.s['state_id']))
    def test_identical_content_stable(self):self.assertEqual(self.s,self.store.create(spec(),'synthetic fixture'))
    def test_deep_copy(self):
        s=self.store.load(self.s['state_id']);s['payload']['world_spec']['matter']['charge']=1
        self.assertEqual(self.store.load(self.s['state_id']),self.s)
    def test_tamper_detected(self):
        s=copy.deepcopy(self.s);s['payload']['reason']='tamper'
        with self.assertRaises(ValueError):apply(s,self.action())
    def test_path_escape(self):
        with self.assertRaises(ValueError):self.store.load('../outside')
    def test_immutable_conflict(self):
        p=pathlib.Path(self.tmp.name)/'f.json';freeze(p,{'x':1})
        with self.assertRaises(ValueError):freeze(p,{'x':2})
        self.assertEqual(json.loads(p.read_text()),{'x':1})
    def test_nonfinite_write_rejected(self):
        with self.assertRaises(ValueError):freeze(pathlib.Path(self.tmp.name)/'bad.json',{'x':float('nan')})
    def test_displacement(self):
        n=apply(self.s,self.action());self.assertAlmostEqual(n['matter']['atoms'][1]['xyz_angstrom'][0],2.115)
        self.assertEqual(self.store.load(self.s['state_id']),self.s)
    def test_bound(self):
        with self.assertRaises(ValueError):apply(self.s,self.action(vector=[.1,0,0]))
    def test_unit(self):
        with self.assertRaises(ValueError):apply(self.s,self.action(unit='bohr'))
    def test_nan_vector(self):
        with self.assertRaises(ValueError):apply(self.s,self.action(vector=[float('nan'),0,0]))
    def test_atom_identity(self):
        with self.assertRaises(ValueError):apply(self.s,self.action(atom_id='invented'))
    def test_stale_action(self):
        with self.assertRaises(ValueError):apply(self.s,self.action(source_state_sha256='0'*64))
    def test_composition_change_rejected(self):
        with self.assertRaises(ValueError):apply(self.s,self.action(charge=2))
    def test_fractional_invariance(self):
        n=apply(self.s,self.action('AFFINE_STRAIN_CELL'));m=self.s['payload']['world_spec']['matter']
        for a,b in zip(m['atoms'],n['matter']['atoms']):np.testing.assert_allclose(np.array(a['xyz_angstrom'])@np.linalg.inv(m['cell_angstrom']),np.array(b['xyz_angstrom'])@np.linalg.inv(n['matter']['cell_angstrom']))
    def test_cartesian_fixed(self):
        n=apply(self.s,self.action('AFFINE_STRAIN_CELL',coordinates='fixed_cartesian'));self.assertEqual(n['matter']['atoms'],spec()['matter']['atoms'])
    def test_strain_bounds(self):
        with self.assertRaises(ValueError):apply(self.s,self.action('AFFINE_STRAIN_CELL',deformation=(np.eye(3)*1.1).tolist()))
    def test_unsupported_force(self):
        with self.assertRaises(ValueError):apply(self.s,self.action('MEASURE_OBSERVABLE',observables=['forces']))
    def test_unsupported_md(self):
        with self.assertRaises(ValueError):apply(self.s,{'type':'MD','source_state_sha256':self.s['sha256']})
    def test_measurement(self):self.assertEqual(apply(self.s,self.action('MEASURE_OBSERVABLE')),self.s['payload']['world_spec'])
    def test_no_authority_no_solver(self):
        def forbidden(*a):raise AssertionError('must not execute')
        n,r=transition(self.store,self.s,self.action(),forbidden,False,False)
        self.assertEqual(r['status'],'BLOCKED');self.assertNotEqual(n['state_id'],self.s['state_id'])
    def test_failure_preserved(self):
        def fault(*a):raise RuntimeError('synthetic')
        n,r=transition(self.store,self.s,self.action(),fault,True,True,True)
        self.assertEqual(r['status'],'UNVERIFIED');self.assertEqual(self.store.load(self.s['state_id']),self.s)
        self.assertIn('error',n['payload']['observation'])
    def test_no_retry(self):
        transition(self.store,self.s,self.action())
        with self.assertRaises(ValueError):transition(self.store,self.s,self.action())
    def test_synthetic_observation_chain(self):
        def fake(s,o):return {'status':'CALCULATED','world_spec_sha256':digest(s),'observation':{'energy_Eh_per_cell':-1,'engine':'SYNTHETIC'}}
        n,r=transition(self.store,self.s,self.action(),fake,True,True,True)
        self.assertEqual(r['physical_transition'],'SYNTHETIC_NOT_PHYSICAL');self.assertEqual(self.store.load(n['payload']['parent_state_id'])['payload']['parent_state_id'],self.s['state_id'])
    def test_comparison_requires_real_result(self):
        with self.assertRaises(ValueError):compare_states(self.s,self.s)
    def test_native_failure_isolated(self):
        from recovery02r.isolated_router import run_isolated
        f=pathlib.Path(self.tmp.name)/'fault.py';f.write_bytes(b'import os,signal,resource\nresource.setrlimit(resource.RLIMIT_CORE,(0,0))\nos.kill(os.getpid(),signal.SIGSEGV)\n')
        result=run_isolated(spec(),pathlib.Path(self.tmp.name)/'fault',timeout=3,worker_path=f)
        self.assertEqual(result['reason'],'NATIVE_SIGNAL_SIGSEGV');self.assertTrue((pathlib.Path(self.tmp.name)/'fault/process_receipt.json').exists())
        self.assertEqual(self.store.load(self.s['state_id']),self.s)
    def test_stage_permission(self):
        with self.assertRaises(ValueError):run_stage({},self.tmp.name,False,False)
    def test_no_science_import(self):self.assertNotIn('pyscf',sys.modules)
    def test_pbc_collision(self):
        s=spec();s['matter']['atoms'][1]['xyz_angstrom']=[.01,0,0]
        with self.assertRaises(ValueError):self.store.create(s,'invalid')
    def test_spin_change_rejected(self):
        with self.assertRaises(ValueError):apply(self.s,self.action(spin_2S=2))
    def test_model_change_rejected(self):
        with self.assertRaises(ValueError):apply(self.s,self.action(method='RHF'))
    def test_no_negative_volume(self):
        with self.assertRaises(ValueError):apply(self.s,self.action('AFFINE_STRAIN_CELL',deformation=[[-1,0,0],[0,1,0],[0,0,1]]))
    def test_missing_strain_policy(self):
        a=self.action('AFFINE_STRAIN_CELL');a['coordinates']='automatic'
        with self.assertRaises(ValueError):apply(self.s,a)
    def test_duplicate_atom_id(self):
        with self.assertRaises(ValueError):self.store.create(spec(),'invalid',atom_ids=['same','same'])
    def test_measurement_creates_new_state(self):
        n,r=transition(self.store,self.s,self.action('MEASURE_OBSERVABLE'))
        self.assertNotEqual(n['state_id'],self.s['state_id']);self.assertEqual(n['payload']['structure_sha256'],self.s['payload']['structure_sha256'])
    def test_tampered_state_file(self):
        p=self.store.root/'states'/f"{self.s['state_id']}.json";p.write_text('{}')
        with self.assertRaises((ValueError,KeyError)):self.store.load(self.s['state_id'])
    def test_atomic_abort_keeps_valid_file(self):
        p=pathlib.Path(self.tmp.name)/'save.json';freeze(p,{'complete':True})
        with patch('interactive01.world.os.link',side_effect=OSError('synthetic interrupted publish')):
            with self.assertRaises(OSError):freeze(p,{'complete':False})
        self.assertEqual(json.loads(p.read_text()),{'complete':True})
        self.assertEqual(list(p.parent.glob('.pending-*')),[])
    def test_exception_keeps_candidate(self):
        def fail(*a):raise MemoryError('synthetic OOM exception, not actual cgroup OOM')
        n,r=transition(self.store,self.s,self.action(),fail,True,True,True)
        self.assertEqual(self.store.load(r['candidate_state_sha256'])['payload']['reason'],'ACTION_SEMANTICS_APPLIED')
        self.assertEqual(n['payload']['observation']['type'],'MemoryError')
    def test_native_timeout(self):
        from recovery02r.isolated_router import run_isolated
        f=pathlib.Path(self.tmp.name)/'sleep.py';f.write_bytes(b'import time\ntime.sleep(5)\n')
        r=run_isolated(spec(),pathlib.Path(self.tmp.name)/'timeout',timeout=.1,worker_path=f)
        self.assertEqual(r['reason'],'TIMEOUT');self.assertEqual(self.store.load(self.s['state_id']),self.s)
    def test_stage2_synthetic_rejected(self):
        source=self.store.create(spec(),'synthetic',observation={'status':'CALCULATED','synthetic':True})
        bundle={'source_state':source,'stage':2,'state_creation':{'spec':spec(),'reason':'synthetic','observation':{'status':'CALCULATED','synthetic':True}}}
        with self.assertRaisesRegex(ValueError,'FIRST_REAL'):run_stage(bundle,self.tmp.name,True,True)
    def test_reject_unsupported_comparison(self):
        n,r=transition(self.store,self.s,self.action(),lambda *a:{'status':'CALCULATED','observation':{'energy':-1}},True,True,True)
        with self.assertRaises(ValueError):compare_states(n,n)
if __name__=='__main__':unittest.main()
