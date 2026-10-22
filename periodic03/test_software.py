"""Pure software/NumPy fixtures only; no ASE/PySCF or physical calculation."""
import ast,copy,json,pathlib,sys,unittest
import numpy as np
import jsonschema
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from periodic03.contract import validate,route,reduced_points,scope_valid
from periodic03.quality import electron_counts,labels,compare
class Contract(unittest.TestCase):
 def setUp(self):
  self.one=json.loads((ROOT/'periodic03/KRKS_111.json').read_text());self.two=json.loads((ROOT/'periodic03/KRKS_222.json').read_text());self.old=json.loads((ROOT/'results/periodic02/science_run/world_result.json').read_text())['spec']
 def test_legacy_unchanged(self):self.assertTrue(validate(self.old)['legacy_request']);self.assertEqual(validate(self.old)['sampling']['mesh'],[1,1,1])
 def test_one_KRKS(self):self.assertEqual(validate(self.one)['method'],'KRKS');self.assertEqual(validate(self.one)['nkpts'],1)
 def test_true_multi_KRKS(self):self.assertEqual(validate(self.two)['nkpts'],8)
 def test_RKS_not_repeated_for_multi(self):
  self.two['physics']['method']='RKS'
  with self.assertRaises(ValueError):validate(self.two)
 def test_no_arbitrary_mesh(self):
  self.two['physics']['k_sampling']['mesh']=[3,3,3]
  with self.assertRaises(ValueError):validate(self.two)
 def test_no_shifted_mesh(self):
  self.two['physics']['k_sampling']['with_gamma_point']=False
  with self.assertRaises(ValueError):validate(self.two)
 def test_no_IBZ(self):
  self.two['physics']['k_sampling']['symmetry_reduction']=True
  with self.assertRaises(ValueError):validate(self.two)
 def test_no_fractional_smearing(self):
  self.two['physics']['smearing']=.01
  with self.assertRaises(ValueError):validate(self.two)
 def test_frozen_numerics(self):
  self.two['physics']['numerics']['Becke_level']=2
  with self.assertRaises(ValueError):validate(self.two)
 def test_boolean_numerics(self):
  self.one['physics']['numerics']['Becke_level']=True
  with self.assertRaises(ValueError):validate(self.one)
 def test_no_nonzero_spin(self):
  self.two['matter']['spin_2S']=2
  with self.assertRaises(ValueError):validate(self.two)
 def test_new_schema_legacy_and_new(self):
  schema=json.loads((ROOT/'periodic03/WorldSpec.schema.json').read_text());jsonschema.Draft202012Validator.check_schema(schema)
  for spec in [self.old,self.one,self.two]:jsonschema.validate(spec,schema)
 def test_schema_reject_thirdmesh(self):
  schema=json.loads((ROOT/'periodic03/WorldSpec.schema.json').read_text());self.two['physics']['k_sampling']['mesh']=[3,3,3]
  with self.assertRaises(jsonschema.ValidationError):jsonschema.validate(self.two,schema)
 def test_Gamma_grid_points(self):self.assertEqual(reduced_points([1,1,1]),[[0,0,0]])
 def test_even_mesh_Gamma_negative_half(self):
  pts=reduced_points([2,2,2]);self.assertEqual(len(pts),8);self.assertEqual(pts[0],[0,0,0]);self.assertEqual(set(np.asarray(pts).flatten()),{0,-.5})
 def test_route_availability_unknown(self):
  x=route(self.two);self.assertEqual(x['status'],'SUPPORTED');self.assertEqual(x['availability'],'UNKNOWN');self.assertEqual(x['cost_screen']['ordered_kpair_upper_count'],64)
 def test_unavailable_not_wrong_physics(self):self.assertEqual(route(self.two,available=[])['status'],'ENGINE_UNAVAILABLE')
 def test_resource_blocked(self):self.assertEqual(route(self.two,resource_ok=False)['status'],'RESOURCE_BLOCKED')
 def test_observable_rejection(self):self.two['physics']['observables']=['forces'];self.assertEqual(route(self.two)['status'],'UNSUPPORTED_OBSERVABLE')
 def test_no_W2(self):self.assertEqual(route(self.two)['W2'],'INCOMPLETE')
 def test_malformed_request(self):self.assertEqual(route(None)['status'],'OUT_OF_MODEL_DOMAIN')
 def test_malformed_physics(self):
  self.one['physics']=[];self.assertEqual(route(self.one)['status'],'OUT_OF_MODEL_DOMAIN')
 def test_scope_before_after(self):
  scope=json.loads((ROOT/'periodic03/SCOPE.json').read_text());plan=json.loads((ROOT/'periodic03/PLAN.json').read_text())
  prepared={**scope,'authority':'NOT_GRANTED'};authorized={**scope,'authority':'GRANTED_FOR_PERIODIC03_ONCE'}
  self.assertTrue(scope_valid(prepared,'prepare',plan));self.assertFalse(scope_valid(prepared,'execute',plan));self.assertTrue(scope_valid(authorized,'execute',plan));self.assertFalse(scope_valid(authorized,'prepare',plan))
 def test_bad_scope_no_extra_job(self):
  scope=json.loads((ROOT/'periodic03/SCOPE.json').read_text());plan=json.loads((ROOT/'periodic03/PLAN.json').read_text());scope.update(authority='GRANTED_FOR_PERIODIC03_ONCE',max_jobs=2);self.assertFalse(scope_valid(scope,'execute',plan))
class Quality(unittest.TestCase):
 setUp=Contract.setUp
 def fixture(self,spec,energy):return {'status':'CALCULATED','spec':copy.deepcopy(spec),'observation':{'SCF_converged':True,'energy_Eh_per_cell':energy,'energy_zero':'test_fixture_only'}}
 def test_three_electron_counts(self):
  dm=np.array([[[2.,0],[0,0]]]*8);s=np.array([np.eye(2)]*8);occ=np.array([[2.,0]]*8)
  q=electron_counts(occ,dm,s,[1/8]*8,[1.9],[1.]);self.assertEqual(q['occupation_electrons'],2);self.assertEqual(q['density_overlap_trace_electrons'],2);self.assertEqual(q['realspace_integrated_electrons'],1.9)
 def test_nonorthogonal_trace_not_plain_trace(self):
  q=electron_counts([[2,0]],[[[1.,0],[0,0]]],[[[2.,0],[0,1]]],[1],[2],[1]);self.assertEqual(q['density_overlap_trace_electrons'],2)
 def test_no_sensitivity_substitution(self):
  labs=labels(True);self.assertIn('NUMERICAL_CONVERGENCE_OBSERVED',labs);self.assertIn('KPOINT_SENSITIVITY_UNKNOWN',labs);self.assertIn('MODEL_ACCURACY_NOT_CERTIFIED',labs)
 def test_k_sensitivity_not_convergence(self):
  q=compare(self.fixture(self.one,-1),self.fixture(self.two,-1.1));self.assertEqual(q['status'],'BOUNDED_KPOINT_SENSITIVITY_MEASURED');self.assertFalse(q['KPOINT_CONVERGENCE_CERTIFIED'])
 def test_solver_path_not_k_sensitivity(self):self.assertEqual(compare(self.fixture(self.old,-1),self.fixture(self.one,-1))['status'],'SOLVER_PATH_CONSISTENCY_DIFFERENCE')
 def test_different_composition_blocked(self):
  self.two['matter']['atoms'][0]['element']='O';self.assertEqual(compare(self.fixture(self.one,-1),self.fixture(self.two,-1))['status'],'INCOMPARABLE')
 def test_unconverged_not_measured(self):
  a=self.fixture(self.one,-1);a['observation']['SCF_converged']=False;self.assertEqual(compare(a,self.fixture(self.two,-1))['status'],'UNVERIFIED')
 def test_synthetic_not_physics(self):
  a=self.fixture(self.one,-1);a['synthetic']=True;self.assertEqual(compare(a,self.fixture(self.two,-1))['status'],'UNVERIFIED')
 def test_runtime_no_engine_import_in_test(self):self.assertNotIn('pyscf',sys.modules)
 def test_syntax_all_modules(self):
  for f in (ROOT/'periodic03').glob('*.py'):ast.parse(f.read_text())
if __name__=='__main__':unittest.main(verbosity=2)
