"""Tiny stdlib synthetic software tests. NEVER physical engine qualification."""
import copy,unittest
from router import compare,digest
from explorer import authorize_next
def record(engine='PySCF'):
 return {'status':'CALCULATED','spec':{'object_id':'synthetic','matter':{'atoms':[{'element':'H','xyz_angstrom':[0,0,0]}],'charge':0,'spin_2S':1,'periodic':False},'physics':{'engine':engine,'method':'UHF','basis':'cc-pvdz'}},'observation':{'engine':engine,'energy_Eh':-.4,'energy_zero':'synthetic total BO','energy_unit':'Eh','forces_Eh_per_bohr':[[0,0,0]],'basis_AO_count':5}}
class Software(unittest.TestCase):
 def test_unknown_not_negative(self):
  a=record();b=record();b['status']='ENGINE_UNAVAILABLE';self.assertEqual(compare(a,b)['status'],'UNVERIFIED')
 def test_composition_block(self):
  a=record();b=record();b['spec']['matter']['atoms'][0]['element']='He';self.assertEqual(compare(a,b)['status'],'INCOMPARABLE')
 def test_geometry_block(self):
  a=record();b=record();b['spec']['matter']['atoms'][0]['xyz_angstrom'][0]=1;self.assertEqual(compare(a,b)['status'],'INCOMPARABLE')
 def test_theory_block(self):
  a=record();b=record();b['spec']['physics']['method']='GFN2';self.assertEqual(compare(a,b)['status'],'INCOMPARABLE')
 def test_zero_block(self):
  a=record();b=record();b['observation']['energy_zero']='arbitrary';self.assertEqual(compare(a,b)['status'],'INCOMPARABLE')
 def test_same_engine_not_independent(self):self.assertFalse(compare(record(),record())['different_code_sources'])
 def test_two_sources_not_precision(self):self.assertIn('NOT_CERTIFIED',compare(record(),record('Psi4'))['independent_numerical_qualification'])
 def test_feedback_hash_required(self):
  with self.assertRaises(ValueError):authorize_next({'based_on_observation_sha256':'fake'},record())
 def test_feedback_change_required(self):
  a=record();d={'based_on_observation_sha256':digest(a),'analysis_after_observation':'synthetic','changed_because':'synthetic','action':'compute','worldspec':a['spec']}
  with self.assertRaises(ValueError):authorize_next(d,a)
 def test_stop_supported(self):
  a=record();d={'based_on_observation_sha256':digest(a),'analysis_after_observation':'synthetic','changed_because':'synthetic','action':'stop'};self.assertEqual(authorize_next(d,a)['action'],'stop')
if __name__=='__main__':unittest.main()
