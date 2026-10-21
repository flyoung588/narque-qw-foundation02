"""Lightweight actual NumPy + mocked Cell regression; NOT real PySCF evidence."""
import ast,copy,json,pathlib,sys,tempfile,unittest
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from qw_next.periodic_evidence import plain,stage,cell_evidence
from qw_next.periodic_world import validate_cell
B=.52917721092
class Cell:
 unit='Angstrom';nelectron=10;spin=0;dimension=3;precision=1e-6;max_memory=400;mesh=[2201]*3
 def __init__(self,a):self.a=a;self.vol=float(np.linalg.det(np.asarray(a)/B))
 def lattice_vectors(self):return np.asarray(self.a)/B
 def atom_coords(self,unit='Bohr'):assert unit=='Bohr';return np.zeros((1,3))
 def nao_nr(self):return 14
class Atoms:
 def __init__(self,a):
  self.positions=np.zeros((1,3));self.pbc=np.ones(3,dtype=bool)
  self.cell=type('Lattice',(),{'array':np.asarray(a)})()
 def get_chemical_symbols(self):return ['Ne']
 def get_volume(self):return float(np.linalg.det(self.cell.array))
class Repair(unittest.TestCase):
 def setUp(self):self.spec=json.loads((ROOT/'periodic01/input.json').read_text());self.a=self.spec['matter']['cell_angstrom']
 def test_old_bug_reproduced(self):
  with self.assertRaises(AttributeError):self.a.tolist()
 def test_list_and_real_ndarray(self):
  for x in [self.a,np.asarray(self.a)]:self.assertEqual(json.loads(json.dumps(plain(x))),self.a)
 def test_units_and_evidence(self):
  for a in [self.a,np.asarray(self.a)]:
   e=cell_evidence(self.spec,Atoms(a),Cell(a),[{'count':12,'distance_A':4.46/2**.5}],B)
   self.assertAlmostEqual(e['PySCF_Cell']['lattice_vectors_Bohr'][0][1],2.23/B)
   self.assertAlmostEqual(e['ASE']['volume_A3'],4.46**3/4)
   self.assertEqual(e['PySCF_Cell']['input_unit'],'Angstrom');json.dumps(e,allow_nan=False)
 def test_wrong_units_rejected(self):
  c=Cell(self.a);c.lattice_vectors=lambda:np.asarray(self.a)
  with self.assertRaisesRegex(ValueError,'UNIT_CHECK_FAILED'):cell_evidence(self.spec,Atoms(self.a),c,[],B)
 def test_atomic_stage_survives_failure(self):
  with tempfile.TemporaryDirectory() as t:
   stage(t,'PYSCF_CELL_BUILT',nelectron=10)
   try:raise RuntimeError('synthetic failure after completed stage')
   except RuntimeError:pass
   self.assertEqual(json.loads((pathlib.Path(t)/'PYSCF_CELL_BUILT.json').read_text())['nelectron'],10)
   self.assertFalse((pathlib.Path(t)/'PERIODIC_SCF_FINISHED.json').exists())
 def test_frozen_input(self):self.assertEqual(validate_cell(self.spec)['all_electron_count'],10)
 def test_syntax(self):
  for name in ['qw_next/periodic_evidence.py','qw_next/periodic_world.py','periodic01/run.py','periodic01/host.py']:ast.parse((ROOT/name).read_text())
if __name__=='__main__':unittest.main(verbosity=2)
