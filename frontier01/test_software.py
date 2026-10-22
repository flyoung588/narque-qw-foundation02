"""Analytic synthetic fermion fixtures only; never import PySCF or solve molecules."""
import copy,json,pathlib,tempfile,unittest
from unittest.mock import patch
import numpy as np
from frontier01.contract import validate,MODEL
from frontier01.observables import wick,rotate,measure,diagnostics
from frontier01.state import CorrelatedStore
from frontier01.world_runtime import act,_transition
from interactive01.world import freeze,apply
from router import digest
HERE=pathlib.Path(__file__).parent
def fermion_rdm(amplitudes,norb):
    """Independent bit-string creation/annihilation oracle, not an eigensolver."""
    def expectation(ops):
        ans=0.
        for bits,amp in amplitudes.items():
            ket=bits;sign=1
            for create,k in reversed(ops):
                occupied=bool(ket & (1<<k))
                if occupied==create:sign=0;break
                sign*=(-1)**((ket & ((1<<k)-1)).bit_count());ket^=1<<k
            ans+=amplitudes.get(ket,0)*amp*sign
        return ans
    one=[]
    for spin in range(2):
        d=np.zeros((norb,norb))
        for p in range(norb):
            for q in range(norb):d[p,q]=expectation([(True,q+spin*norb),(False,p+spin*norb)])
        one.append(d)
    two=[]
    for sp,sr in [(0,0),(0,1),(1,1)]:
        g=np.zeros((norb,)*4)
        for p,q,r,s in np.ndindex(g.shape):g[p,q,r,s]=expectation([(True,p+sp*norb),(True,r+sr*norb),(False,s+sr*norb),(False,q+sp*norb)])
        two.append(g)
    return tuple(one),tuple(two)
class Software(unittest.TestCase):
    def setUp(self):self.req=json.loads((HERE/'REQUEST.json').read_text())['model_request']
    def test_contract(self):validate(self.req)
    def test_no_implicit_fci_label(self):
        self.assertEqual(self.req['world_spec']['physics']['method'],'RHF');self.assertEqual(self.req['correlation_model']['method'],'FCI')
    def test_model_tamper(self):
        self.req['correlation_model']['conv_tol']=.1
        with self.assertRaises(ValueError):validate(self.req)
    def test_atom_domain(self):
        self.req['world_spec']['matter']['atoms'][0]['element']='He'
        with self.assertRaises(ValueError):validate(self.req)
    def test_covalent_singlet(self):
        r=fermion_rdm({9:2**-.5,6:2**-.5},2);m=measure(r,singlet=True)
        np.testing.assert_allclose(m['natural_occupations'],[1,1]);np.testing.assert_allclose(m['site_double_occupancy'],[0,0])
        np.testing.assert_allclose(m['spin_dot_matrix_hbar2'],[[.75,-.75],[-.75,.75]],atol=1e-14)
        self.assertAlmostEqual(m['nonidempotency'],2)
        self.assertLess(max(diagnostics(r,(1,1)).values()),1e-14)
    def test_closed_shell_wick_oracle(self):
        r=fermion_rdm({5:1.},2);w=wick(np.diag([1.,0]),np.diag([1.,0]))
        for x,y in zip(r[0]+r[1],w[0]+w[1]):np.testing.assert_allclose(x,y)
        m=measure(r,singlet=True);self.assertAlmostEqual(m['nonidempotency'],0);self.assertEqual(m['site_double_occupancy'],[1,0])
    def test_delocalized_rhf_is_already_spin_correlated(self):
        u=np.array([[1,1],[1,-1]])/np.sqrt(2);d=np.diag([1.,0]);m=measure(rotate(wick(d,d),u),singlet=True)
        np.testing.assert_allclose(m['site_double_occupancy'],[.25,.25]);self.assertAlmostEqual(m['spin_dot_matrix_hbar2'][0][1],-.375)
        self.assertAlmostEqual(m['nonidempotency'],0,places=12)
    def test_rotation_matches_independent_determinant_oracle(self):
        # Occupied bonding MO gives four equal alpha/beta determinant amplitudes.
        u=np.array([[1,1],[1,-1]])/np.sqrt(2);d=np.diag([1.,0]);a=rotate(wick(d,d),u);b=fermion_rdm({5:.5,9:.5,6:.5,10:.5},2)
        for x,y in zip(a[0]+a[1],b[0]+b[1]):np.testing.assert_allclose(x,y,atol=1e-14)
    def test_ionic_superposition(self):
        m=measure(fermion_rdm({5:2**-.5,10:2**-.5},2),singlet=True)
        np.testing.assert_allclose(m['site_double_occupancy'],[.5,.5]);np.testing.assert_allclose(m['spin_dot_matrix_hbar2'],0,atol=1e-14)
        np.testing.assert_allclose(m['connected_charge_covariance'],[[1,-1],[-1,1]],atol=1e-14)
    def test_reject_non_singlet_factor(self):
        with self.assertRaises(ValueError):measure(wick(np.eye(2),np.eye(2)),singlet=False)
    def test_bad_rotation(self):
        with self.assertRaises(ValueError):rotate(wick(np.eye(2),np.eye(2)),np.eye(2)*2)
    def test_trace_contraction_detect_corruption(self):
        r=fermion_rdm({5:1},2);r[1][1][0,0,0,0]=0
        self.assertGreater(diagnostics(r,(1,1))['ab_contraction_error'],.9)
    def test_state_roundtrip_and_action(self):
        with tempfile.TemporaryDirectory() as t:
            store=CorrelatedStore(t);p=store.create(self.req['world_spec'],'SYNTHETIC_SOFTWARE_ONLY')
            result={'status':'CALCULATED','request_sha256':digest(self.req),'fixture':'SYNTHETIC_NOT_PHYSICAL'}
            s=store.save_correlated(self.req,result,{'ci':np.eye(2),'synthetic':np.array([1])},p['sha256'],p['payload']['atom_ids'])
            np.testing.assert_equal(store.arrays(store.load(s['sha256']))['ci'],np.eye(2))
            a={'type':'DISPLACE_ATOM','source_state_sha256':s['sha256'],'atom_id':'atom-0','vector':[0,0,.02],'unit':'angstrom'}
            new=apply(s,a);self.assertAlmostEqual(new['matter']['atoms'][0]['xyz_angstrom'][2],-2.23)
            with self.assertRaises(ValueError):act(store,s,a)
    def test_blob_tamper_detected(self):
        with tempfile.TemporaryDirectory() as t:
            store=CorrelatedStore(t);p=store.create(self.req['world_spec'],'SYNTHETIC')
            s=store.save_correlated(self.req,{'status':'CALCULATED','request_sha256':digest(self.req)},{'ci':np.ones((1,1))},p['sha256'],p['payload']['atom_ids'])
            file=pathlib.Path(t)/s['payload']['arrays']['path'];file.write_bytes(b'CORRUPTED')
            with self.assertRaises(ValueError):store.arrays(s)
    def test_failed_solver_keeps_parent_and_blocks_retry(self):
        with tempfile.TemporaryDirectory() as t:
            store=CorrelatedStore(t);p=store.create(self.req['world_spec'],'SYNTHETIC')
            def fail(*args):raise RuntimeError('INJECTED_ENGINE_FAILURE')
            for _ in range(2):
                with self.assertRaises((ValueError,RuntimeError)):_transition(store,self.req,p,{'type':'SYNTHETIC'},authority=True,resources=True,execute=fail)
            self.assertEqual(store.load(p['sha256']),p);self.assertEqual(len(list(pathlib.Path(t).rglob('failure.json'))),1)
    def test_freeze_nan_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):freeze(pathlib.Path(t)/'bad.json',{'x':float('nan')})
    def test_ungranted_scope(self):
        s=json.loads((HERE/'SCOPE.json').read_text());self.assertEqual(s['authority'],'NOT_GRANTED')
    def test_source_no_process_memory_regression(self):
        for f in ['solver_worker.py','worker.py','solver.py']:self.assertNotIn('RLIMIT_DATA',(HERE/f).read_text())
    def test_no_engine_import_for_router(self):
        text=(HERE/'world_runtime.py').read_text();self.assertNotIn('import pyscf',text)
    def test_workflow_manual_only(self):
        text=(HERE.parent/'.github/workflows/foundation02.yml').read_text()
        self.assertIn('workflow_dispatch:',text);self.assertNotIn('schedule:',text);self.assertNotIn('pull_request:',text);self.assertNotIn('push:',text);self.assertIn('timeout-minutes: 15',text)
if __name__=='__main__':unittest.main()
