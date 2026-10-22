"""Additional pure software status regressions; no physical solver imports."""
import copy,json,pathlib,unittest
from periodic02.admission import route_capability,result_route_status
ROOT=pathlib.Path(__file__).resolve().parents[1]
class RouteStatus(unittest.TestCase):
 def setUp(self):self.spec=json.loads((ROOT/'decisions/WorldSpec_QW_P02_C_DIAMOND_2ATOM.json').read_text())
 def test_supported_not_computed(self):
  x=route_capability(self.spec);self.assertEqual(x['status'],'SUPPORTED');self.assertFalse(x['physical_calculation']);self.assertEqual(x['availability'],'UNKNOWN')
 def test_unsupported_observable(self):
  self.spec['physics']['observables']=['forces'];self.assertEqual(route_capability(self.spec)['status'],'UNSUPPORTED_OBSERVABLE')
 def test_out_of_domain(self):
  self.spec['matter']['spin_2S']=2;self.assertEqual(route_capability(self.spec)['status'],'OUT_OF_MODEL_DOMAIN')
 def test_boolean_quantum_numbers(self):
  self.spec['matter']['charge']=False;self.assertEqual(route_capability(self.spec)['status'],'OUT_OF_MODEL_DOMAIN')
 def test_engine_unavailable(self):self.assertEqual(route_capability(self.spec,available_engines=[])['status'],'ENGINE_UNAVAILABLE')
 def test_resource_block(self):self.assertEqual(route_capability(self.spec,resource_available=False)['status'],'RESOURCE_BLOCKED')
 def test_numerically_unverified(self):self.assertEqual(result_route_status({'status':'UNVERIFIED'}) ,'NUMERICALLY_UNVERIFIED')
 def test_actual_resource_return(self):self.assertEqual(result_route_status({'status':'BLOCKED','error':'RESOURCE_ADMISSION_BLOCKED: example'}) ,'RESOURCE_BLOCKED')
 def test_registered_workflow_same_science_entry(self):
  y=(ROOT/'.github/workflows/foundation02.yml').read_text()
  self.assertIn('periodic02/Dockerfile',y);self.assertIn('periodic02/host.py',y)
  self.assertNotIn('  push:',y);self.assertNotIn('schedule:',y)
if __name__=='__main__':unittest.main()
