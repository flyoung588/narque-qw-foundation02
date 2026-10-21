"""Engineering checks only; no scientific engine imported."""
import ast,itertools,json,math,pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from qw_next.periodic_world import validate_cell,scale_cell,det
class Prepare(unittest.TestCase):
 def setUp(self):self.spec=json.loads((ROOT/'periodic01/input.json').read_text())
 def test_cell(self):
  m=validate_cell(self.spec);self.assertEqual(m['all_electron_count'],10);self.assertAlmostEqual(m['cell_volume_A3'],4.46**3/4)
 def test_neighbors(self):
  cell=self.spec['matter']['cell_angstrom'];d=[]
  for n in itertools.product(range(-2,3),repeat=3):
   if n==(0,0,0):continue
   r=[sum(n[i]*cell[i][j] for i in range(3)) for j in range(3)];d.append(math.sqrt(sum(x*x for x in r)))
  self.assertAlmostEqual(min(d),4.46/math.sqrt(2));self.assertEqual(sum(abs(x-min(d))<1e-10 for x in d),12)
 def test_scale(self):self.assertAlmostEqual(det(scale_cell(self.spec,1.01)['matter']['cell_angstrom']),det(self.spec['matter']['cell_angstrom'])*1.01**3)
 def test_syntax(self):
  for p in (ROOT/'periodic01').glob('*.py'):ast.parse(p.read_text())
 def test_no_data_cap(self):
  t=(ROOT/'periodic01/worker.py').read_text();self.assertNotIn('setrlimit(resource.RLIMIT_DATA',t);self.assertNotIn('setrlimit(resource.RLIMIT_AS',t)
if __name__=='__main__':unittest.main(verbosity=2)
