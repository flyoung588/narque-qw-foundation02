"""Pure structural fixtures; no material calculation or fabricated physical output."""
import copy,json,pathlib,tempfile,unittest
from qw_next.periodic_world import validate_cell,scale_cell,compatible_cell_energy
def fixture():return {'version':'QW-WORLDSPEC-0.1','object_id':'SYNTHETIC_GEOMETRY_FIXTURE','epistemic_mode':'GROUNDED','matter':{'type':'periodic_cell','periodic':True,'atoms':[{'element':'He','xyz_angstrom':[1,1,1]}],'charge':0,'spin_2S':0,'cell_angstrom':[[4,0,0],[0,4,0],[0,0,4]]},'physics':{'engine':'pyscf-pbc','method':'RKS','xc':'PBE','basis':'cc-pvdz','observables':['energy']},'experiment':{'action':'single_point'}}
class Semantics(unittest.TestCase):
 def test_constructor(self):self.assertEqual(validate_cell(fixture())['cell_volume_A3'],64)
 def test_singular(self):
  x=fixture();x['matter']['cell_angstrom'][2]=[0,0,0]
  with self.assertRaises(ValueError):validate_cell(x)
 def test_charge(self):
  x=fixture();x['matter']['charge']=1
  with self.assertRaises(ValueError):validate_cell(x)
 def test_spin(self):
  x=fixture();x['matter']['spin_2S']=1
  with self.assertRaises(ValueError):validate_cell(x)
 def test_dynamics_refused(self):
  x=fixture();x['experiment']['action']='molecular_dynamics'
  with self.assertRaises(ValueError):validate_cell(x)
 def test_unknown_element(self):
  x=fixture();x['matter']['atoms'][0]['element']='U'
  with self.assertRaises(ValueError):validate_cell(x)
 def test_odd_count(self):
  x=fixture();x['matter']['atoms'][0]['element']='Li'
  with self.assertRaises(ValueError):validate_cell(x)
 def test_unsupported_force(self):
  x=fixture();x['physics']['observables']=['energy','forces']
  with self.assertRaises(ValueError):validate_cell(x)
 def test_periodic_explicit(self):
  x=fixture();x['matter']['periodic']=False
  with self.assertRaises(ValueError):validate_cell(x)
 def test_scale(self):
  x=fixture();y=scale_cell(x,1.05);self.assertEqual(x['matter']['atoms'][0]['xyz_angstrom'],[1,1,1]);self.assertEqual(y['matter']['atoms'][0]['xyz_angstrom'],[1.05]*3)
 def test_excess_scale(self):
  with self.assertRaises(ValueError):scale_cell(fixture(),2)
 def test_nonfinite(self):
  x=fixture();x['matter']['atoms'][0]['xyz_angstrom'][0]=float('nan')
  with self.assertRaises(ValueError):validate_cell(x)
 def test_missing_calculation_not_comparable(self):self.assertFalse(compatible_cell_energy({'status':'ENGINE_UNAVAILABLE'},{'status':'CALCULATED'}))
 def test_stage_writer_real_persistence_only(self):
  from qw_next.native_worker import emit
  with tempfile.TemporaryDirectory() as tmp:
   d=pathlib.Path(tmp);emit(d,'START',synthetic_logging_test=True);emit(d,'IMPORT',synthetic_logging_test=True)
   rows=[json.loads(x) for x in (d/'stages.jsonl').read_text().splitlines()];self.assertEqual([x['stage'] for x in rows],['START','IMPORT']);self.assertTrue(all(x['synthetic_logging_test'] for x in rows))
if __name__=='__main__':unittest.main()
