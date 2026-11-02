"""Regression against real saved arrays; every propagation entry is disabled."""
from pathlib import Path
import json,tempfile,copy,unittest,hashlib
from unittest.mock import patch
import numpy as np
from world01.contracts import WorldError
from . import model
from .model import system,restore,validate_arrays,array_diagnostics
from .controller import setup
from .vendor.runtime import TimeEvolution

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'inherited_failure'
class ArrayRepair(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name);self.guard=patch.object(TimeEvolution,'step',side_effect=AssertionError('NO_PROPAGATION_ALLOWED'));self.guard.start()
  self.w,parent=setup(ROOT);self.s=self.w.store.load(parent);self.a=self.w.store.arrays(self.s)
 def tearDown(self):self.guard.stop();self.t.cleanup()
 def test_canonical_arrays_are_original_executed_grid(self):
  v=json.loads((ROOT/'original_core03/view_payload.json').read_text());e=system();h=e.hamiltonian
  for key,val in [('R',e.R),('Vg',h.vg),('Vu',h.vu),('mu',h.mu),('K',h.K[0])]:self.assertTrue(np.array_equal(val,np.asarray(v[key],np.float64)),key)
  self.assertTrue(np.array_equal(h.V,np.stack([h.vg,h.vu])))
 def test_old_input_still_strictly_rejected_with_field_detail(self):
  p=json.loads((OLD/'failed_state.json').read_text())
  with np.load(OLD/'failed_arrays.npz',allow_pickle=False) as z:a={k:z[k].copy() for k in z.files}
  with self.assertRaises(WorldError) as cm:validate_arrays(a,p['payload'])
  self.assertEqual(cm.exception.code,'COUPLED_MODEL_ARRAY_MISMATCH');details=json.loads(cm.exception.detail);self.assertEqual(details['first_mismatch']['key'],'Vg');self.assertEqual(details['first_mismatch']['max_index'],[5]);self.assertEqual(details['first_mismatch']['different_elements'],1)
 def test_single_ulp_corruption_in_every_static_field_rejected(self):
  for key in ('R','Vg','Vu','mu_gu','K'):
   a={k:v.copy() for k,v in self.a.items()};idx=(0,0) if key=='K' else (5,);a[key][idx]=np.nextafter(a[key][idx],np.inf)
   with self.assertRaises(WorldError,msg=key):validate_arrays(a,self.s['payload'])
 def test_bad_dtype_and_shape_rejected(self):
  for altered in (self.a['Vg'].astype(np.float32),self.a['Vg'][:-1]):
   a=dict(self.a,Vg=altered)
   with self.assertRaises(WorldError):validate_arrays(a,self.s['payload'])
 def test_reference_tamper_rejected_by_hash_before_use(self):
  p=self.root/'bad.json';p.write_bytes(model.HAMILTONIAN_REFERENCE.read_bytes()+b' ')
  with patch.object(model,'HAMILTONIAN_REFERENCE',p):
   with self.assertRaisesRegex(WorldError,'REFERENCE_BYTES_CHANGED'):system()
 def test_original_psi_clock_work_and_control_not_reprepared(self):
  with np.load(ROOT/'history/wavefunction.npz',allow_pickle=False) as z:self.assertTrue(np.array_equal(z['psi'],self.a['psi']))
  meta=json.loads((ROOT/'history/evidence.json').read_text());w=restore(self.a,self.s['payload']);self.assertEqual(w.state.t,meta['state_time_au']);self.assertEqual(w.state.work_input,meta['work_input_Eh']);self.assertEqual(w.state.parameters,meta['state_parameters']);self.assertEqual(w.state.controls,meta['controls']);self.assertEqual(w.system.identity,meta['model_id'])
if __name__=='__main__':unittest.main()
