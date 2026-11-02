"""Real saved-state/offline adapter tests; never calls the propagator."""
import unittest,tempfile,pathlib,json,hashlib,copy
from unittest.mock import patch
import numpy as np
from router import digest
from world01.contracts import WorldError
from .session import CoupledWorldSession
from .fabric import CoupledExecutionFabric
from .model import system,restore,observe,validate_action,DOMAIN

HISTORY=pathlib.Path(__file__).resolve().parents[2]/'history'
class Integration(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);m={'local_base':'PINNED_CORE03','files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in HISTORY.iterdir() if p.is_file()}}
  self.w=CoupledWorldSession(self.root/'world',HISTORY,m);self.h=self.w.import_history()['source_state_hash'];self.s=self.w.store.load(self.h)
 def tearDown(self):self.tmp.cleanup()
 def test_saved_real_state_restores_without_solver(self):
  with patch('core03_live.vendor.runtime.TimeEvolution.step',side_effect=AssertionError('NO_PROPAGATION_IN_OFFLINE_TEST')):
   a=self.w.store.arrays(self.s);w=restore(a,self.s['payload']);o=self.w.observe(self.h)['observables']
   self.assertEqual(a['psi'].shape,(2,255));self.assertAlmostEqual(o['Pu'],.012578222295020158,places=13);self.assertTrue(np.array_equal(a['psi'],w.state.psi));self.assertEqual(w.state.t,self.s['payload']['time_au']);self.assertEqual(w.state.parameters,self.s['payload']['parameters']);self.assertEqual(self.w.load(self.h)['units']['position'],'bohr')
 def test_one_session_old_and_new_types(self):
  spec={'version':'QW-WORLDSPEC-0.1','object_id':'old-LiH-structure','epistemic_mode':'GROUNDED','matter':{'type':'molecule','atoms':[{'element':'Li','xyz_angstrom':[0,0,0]},{'element':'H','xyz_angstrom':[0,0,1.6]}],'charge':0,'spin_2S':0,'periodic':False},'physics':{'engine':'pyscf','method':'RHF','basis':'cc-pvdz','observables':['energy','forces']},'experiment':{'action':'single_point'}}
  old=self.w.create(spec);self.assertEqual(self.w.load(old['source_state_hash'])['state_kind'],'QW_PHYSICAL_STATE_01');self.assertEqual(self.w.load(self.h)['state_kind'],'QW_COUPLED_RADIAL_NUCLEAR_STATE_01')
  with self.assertRaises(WorldError):self.w.compare(self.h,old['source_state_hash'],{'kind':'MATCHED_TIME_CONTROL_BRANCH'})
 def test_fork_and_prepare_preserve_parent_bytes(self):
  before=(self.w.root/'states'/f'{self.h}.json').read_bytes();branch=self.w.fork(self.h,'field alternative');self.assertEqual(branch['source_state_hash'],self.h)
  new=self.w.prepare_coupled(self.h,{'center_R_bohr':2.,'sigma_R_bohr':.22});self.assertEqual(new['source_execution']['source_execution_kind'],'PREPARED_NOT_EVOLVED');self.assertEqual(before,(self.w.root/'states'/f'{self.h}.json').read_bytes())
 def test_field_domain_and_no_silent_active_overwrite(self):
  p=self.s['payload'];action={'type':'PULSE_AND_EVOLVE_COUPLED_STATE','source_state_sha256':self.h,'control':{'operation':'electric_pulse','amplitude_au':.002,'duration_au':50.,'omega_ratio_to_local_gap':1.,'omega_au':.4350955420166891,'cep_rad':0.},'dt_au':.05,'steps':1000};validate_action(p,action)
  for value in (float('nan'),.011,True):
   bad=copy.deepcopy(action);bad['control']['amplitude_au']=value
   with self.assertRaises(WorldError):validate_action(p,bad)
  bad=copy.deepcopy(p);bad['time_au']=100.
  with self.assertRaises(WorldError):validate_action(bad,action)
 def test_persisted_pulse_clock_and_work_preserved(self):
  w=restore(self.w.store.arrays(self.s),self.s['payload']);old=w.state.psi.copy();t=w.state.t;work=w.state.work_input;w.apply({'operation':'electric_pulse','amplitude_au':.002,'duration_au':50.,'omega_ratio_to_local_gap':1.,'omega_au':.4350955420166891,'cep_rad':0.})
  self.assertTrue(np.array_equal(old,w.state.psi));self.assertEqual(w.state.parameters['pulse']['start_au'],t);self.assertAlmostEqual(w.state.work_input,work,places=13)
 def test_no_old_grant_or_missing_grant_can_execute(self):
  f=CoupledExecutionFabric(self.root/'broker',self.w)
  with self.assertRaisesRegex(WorldError,'NEW_CORE03_EXECUTION'):f.authorize({'model':DOMAIN})
  with self.assertRaisesRegex(WorldError,'NO_COUPLED_TO_EFFECTIVE'):self.w.translate(self.h,'QW_EFFECTIVE_QUANTUM_STATE_01')
 def test_array_tamper_rejected(self):
  path=self.w.root/self.s['payload']['arrays']['path'];path.write_bytes(path.read_bytes()+b'X')
  with self.assertRaises(ValueError):self.w.load(self.h)
 def test_real_observation_enters_existing_explorer_without_model(self):
  from .explorer import CoupledExplorer
  f=CoupledExecutionFabric(self.root/'broker',self.w);self.w.attach(f)
  e=CoupledExplorer(self.root/'research',self.w,{self.h:{'path':'fabric:'+self.h,'domain':DOMAIN}},'Inspect actual coupled state',execution=f,max_decisions=2)
  e.seed(self.h);c=e.context();self.assertIn(DOMAIN,c['connected_workers']);self.assertEqual(c['resources']['new_science_jobs'],0);self.assertEqual(c['memory']['observations'][0]['state'],self.h)
if __name__=='__main__':unittest.main()
