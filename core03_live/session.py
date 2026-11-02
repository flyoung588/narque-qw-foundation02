"""One inherited Store/WorldSession. New radial two-channel domain stays distinct."""
import copy,json
from types import SimpleNamespace
from pathlib import Path
import numpy as np
from router import digest
from interactive01.world import freeze,verify
from state_space01.state import blob
from world01.session import filehash,publish_bytes
from world01.contracts import KIND,envelope,WorldError
from world01.fabric import MANIFESTS,manifest
from dynamics01.adapter import DynamicsWorldSession
from .model import SCHEMA,DOMAIN,OBS,OPS,QUALIFICATION,system,arrays_of,state_fields,validate_arrays,observe,validate_action,require

KIND[SCHEMA]=('TWO_ELECTRONIC_CHANNEL_RADIAL_NUCLEAR_PSI','bohr/Eh/atomic_time; sum |chi|^2 dR')
MANIFESTS[DOMAIN]=manifest(DOMAIN,'Aligned H2+ two BO channels, radial nuclei','complex128 chi[2,255], NOT effective electronic ket',OPS,OBS,['full_electron_density','ionization','rotation','intrinsic_nonadiabatic_coupling'],'T_R I + [[Vg,-mu E(t)],[-mu E(t),Vu]]','Pinned original Core03 curves, source and raw checkpoints',list(QUALIFICATION.values()),'core03_live.model.transition','Total BO curve reference; electron at infinity and separated protons')
MANIFESTS[DOMAIN]['evidence_level']='ENGINE_INTEGRATED_NOT_LIVE_PROVEN'

def is_coupled(s):return s['payload'].get('schema')==SCHEMA
def save(world,a,fields,*,parent,provenance):
 e=system();p={'schema':SCHEMA,'state_kind':'COUPLED_RADIAL_NUCLEAR_PSI','parent_state_id':parent,'world_spec':{'object_id':'H2plus-aligned-two-channel','matter':{'type':'radial_quantum_nuclei','atoms':[{'element':'H'},{'element':'H'}],'charge':1,'spin_2S':1,'periodic':False},'physics':{'engine':'Core03','method':'two_BO_channel_nuclear_TDSE'}},'model':e.metadata(),'qualification':QUALIFICATION,'control_origin_au':0.,**copy.deepcopy(fields)}
 validate_arrays(a,p)
 if parent:world.store.load(parent)
 p['arrays']=blob(world.root,a);h=digest(p);s={'state_id':h,'sha256':h,'payload':p};freeze(world.root/'states'/f'{h}.json',s)
 freeze(world.root/'references'/f'{h}.json',{'state_sha256':h,'state_file_sha256':filehash(world.root/'states'/f'{h}.json'),'evidence':provenance})
 return s

class CoupledWorldSession(DynamicsWorldSession):
 def _validate_state(self,s):
  if not is_coupled(s):return super()._validate_state(s)
  verify(s);validate_arrays(self.store.arrays(s),s['payload']);return s
 def load(self,ident):
  s=self.store.load(ident)
  if not is_coupled(s):return super().load(ident)
  self._validate_state(s);path=self.root/'references'/f'{ident}.json';require(path.is_file(),'COUPLED_PROVENANCE_MISSING');rec=json.loads(path.read_text());require(rec['state_file_sha256']==filehash(self.root/'states'/f'{ident}.json'),'COUPLED_PROVENANCE_MISMATCH');ev=rec['evidence'];mode=ev['mode']
  require(mode in ('HISTORICAL_REAL_EVIDENCE_REPLAY','PREPARED_NOT_EVOLVED','NEW_SCIENTIFIC_EXECUTION'),'COUPLED_PROVENANCE_MODE_INVALID')
  if mode=='HISTORICAL_REAL_EVIDENCE_REPLAY':
   for rel,h in ev['source_files'].items():require(filehash(self._source(rel))==h,'COUPLED_HISTORICAL_SOURCE_CHANGED')
  elif mode=='PREPARED_NOT_EVOLVED':
   require(s['payload']['time_au']==0 and s['payload']['work_input_Eh']==0,'PREPARATION_CANNOT_CLAIM_EVOLUTION')
  else:
   proof=self.root/'remote_provenance'/f'{ident}.json';require(proof.is_file() and hasattr(self,'execution'),'COUPLED_LIVE_RETURN_NOT_BOUND')
   require(any(x['data'].get('state')==ident and x['data'].get('new_science') and x['data'].get('provenance_receipt',{}).get('sha256')==filehash(proof) for x in self.execution.j.query('ExecutionReturned')),'COUPLED_LIVE_RETURN_NOT_JOURNALED')
  out=envelope(s,rec,{'verified':True,'real_calculated':mode!='PREPARED_NOT_EVOLVED','source_execution_kind':mode,'source_execution_status':'CALCULATED' if mode!='PREPARED_NOT_EVOLVED' else mode,'model_qualification':'NOT_INDEPENDENTLY_CERTIFIED'})
  out['units']={'position':'bohr','energy':'Eh','time':'atomic_time','field':'atomic_electric_field','dipole':'e*a0','measure':'dR; chi[2,N] not r^2dr'}
  return out
 def import_history(self,relative='evidence.json',array_relative='wavefunction.npz',manifest_relative='SHA256.json'):
  meta=json.loads(self._source(relative).read_text());checks=json.loads(self._source(manifest_relative).read_text());require(checks.get(Path(relative).name)==filehash(self._source(relative)) and checks.get(Path(array_relative).name)==filehash(self._source(array_relative)),'CORE03_ORIGINAL_CHECKPOINT_HASH_MISMATCH')
  e=system();require(meta['physical_system']==e.metadata() and meta['model_id']==e.identity,'CORE03_ORIGINAL_MODEL_MISMATCH')
  with np.load(self._source(array_relative),allow_pickle=False) as z:psi=z['psi'].copy();require(np.array_equal(z['axis0'],e.R),'CORE03_ORIGINAL_AXIS_MISMATCH')
  w=__import__('core03_live.vendor.runtime',fromlist=['QuantumWorld']).QuantumWorld(e)
  from .vendor.runtime import QuantumState
  w.state=QuantumState(psi,meta['model_id'],meta['state_time_au'],meta['absorbed'],meta['initial'],meta['controls'],meta['timeline'],meta['state_parameters'],meta['work_input_Eh'])
  require(all(abs(w.observe()[k]-meta['observation'][k])<1e-12 for k in ('Pg','Pu','norm','energy_Eh','work_input_Eh')),'CORE03_ORIGINAL_OBSERVATION_MISMATCH')
  s=save(self,arrays_of(w),state_fields(w),parent=None,provenance={'mode':'HISTORICAL_REAL_EVIDENCE_REPLAY','source_files':{p:filehash(self._source(p)) for p in (relative,array_relative,manifest_relative)},'scope':'No new propagation; original computed state restored'})
  return self.load(s['sha256'])
 def prepare_coupled(self,parent,initial):
  self._open();s=self.store.load(parent);require(is_coupled(s),'COUPLED_PREPARATION_PARENT_REQUIRED');self.load(parent);action={'type':'PREPARE_COUPLED_STATE','source_state_sha256':parent,'initial':initial};validate_action(s['payload'],action)
  from .vendor.runtime import QuantumWorld
  w=QuantumWorld(system());w.prepare(initial)
  s=save(self,arrays_of(w),state_fields(w),parent=parent,provenance={'mode':'PREPARED_NOT_EVOLVED','operation':action});return self.load(s['sha256'])
 def observe(self,ident,requested=()):
  s=self.store.load(ident)
  if not is_coupled(s):return super().observe(ident,requested)
  env=self.load(ident);require(not set(requested)-set(OBS),'COUPLED_OBSERVABLE_OUT_OF_DOMAIN');v=observe(self.store.arrays(s),s['payload']);return {'schema':'QW_OBSERVATION_ENVELOPE_01','source_state_hash':ident,'physical_time_au':s['payload']['time_au'],'model_hash':digest(s['payload']['model']),'source_execution':env['source_execution'],'observables':{k:v[k] for k in requested or OBS},'units':{'time':'atomic_time','energy':'Eh','position':'bohr','coherence':'dimensionless','field':'atomic_electric_field'},'qualification':QUALIFICATION,'values':{'original_observation':v,'available_observables':OBS},'model_domain':DOMAIN,'error_uncertainty':QUALIFICATION,'new_scientific_executions':0}
 def act(self,request):
  q=request.plain() if hasattr(request,'plain') else request;ident=q.get('source_state_hash')
  if not ident or not is_coupled(self.store.load(ident)):return super().act(request)
  self._open();self.load(ident)
  if q['action']=='OBSERVE':return self.observe(ident,q.get('required_observables',()))
  if q['action']=='FORK':return self.fork(ident,q.get('parameters',{}).get('reason',''))
  action={'type':q['action'],'source_state_sha256':ident,**q.get('parameters',{})};validate_action(self.store.load(ident)['payload'],action)
  raise WorldError('NEW_CORE03_EXECUTION_AUTHORIZATION_REQUIRED','Use the attached source-bound existing Live Fabric; action text does not grant science')
 def compare(self,a,b,contract=None):
  x=self.store.load(a);y=self.store.load(b)
  if not is_coupled(x) and not is_coupled(y):return super().compare(a,b,contract)
  require(is_coupled(x) and is_coupled(y),'NO_COUPLED_TO_OTHER_STATE_MAPPING');self.load(a);self.load(b);p=x['payload'];q=y['payload'];require(p['model']==q['model'],'COUPLED_MODEL_MISMATCH')
  require((contract or {}).get('kind') in ('MATCHED_TIME_CONTROL_BRANCH','SAME_MODEL_TIME_PATH'),'COUPLED_COMPARISON_CONTRACT_REQUIRED')
  if contract['kind']=='MATCHED_TIME_CONTROL_BRANCH':require(abs(p['time_au']-q['time_au'])<1e-9,'COUPLED_TIME_MISMATCH')
  aa=self.store.arrays(x);bb=self.store.arrays(y);dx=aa['R'][1]-aa['R'][0];oa=observe(aa,p);ob=observe(bb,q)
  return self.receipt('compare','COMPARISON_VALIDATED','COUPLED_FINITE_MODEL_ONLY',a,result={'other':b,'delta_Pu':ob['Pu']-oa['Pu'],'delta_energy_Eh':ob['energy_Eh']-oa['energy_Eh'],'delta_work_Eh':ob['work_input_Eh']-oa['work_input_Eh'],'state_L2':float(np.linalg.norm(aa['psi']-bb['psi'])*np.sqrt(dx)),'same_time':abs(p['time_au']-q['time_au'])<1e-9,'interpretation':'Applied field changes energy; not free energy, W2 or discovery'})
 def translate(self,ident,target):
  if is_coupled(self.store.load(ident)):raise WorldError('NO_COUPLED_TO_EFFECTIVE_KET_MAPPING')
  return super().translate(ident,target)
 def ingest_worker(self,package,i,ident,attempt):
  if i.get('model')!=DOMAIN:return super().ingest_worker(package,i,ident,attempt)
  self.execution.transport.verify_package(package);base=Path(package['world_root']);ret=json.loads(Path(package['result_path']).read_text());parent=self.store.load(i['input_state']);source=parent['sha256'];require((base/'states'/f'{source}.json').read_bytes()==(self.root/'states'/f'{source}.json').read_bytes(),'COUPLED_PARENT_BYTES_CHANGED')
  ar=parent['payload']['arrays']['path'];require((base/ar).read_bytes()==(self.root/ar).read_bytes(),'COUPLED_PARENT_ARRAY_BYTES_CHANGED')
  from frontier01.state import CorrelatedStore
  store=CorrelatedStore(base);s=store.load(ret['state']);require(is_coupled(s) and s['payload']['parent_state_id']==source,'COUPLED_PARENT_MISMATCH');a=store.arrays(s);validate_arrays(a,s['payload'])
  require(s['payload']['model']==parent['payload']['model'] and ret['intent_hash']==digest(i) and ret['receipt']['action']==i['operation'] and ret.get('mode')=='NEW_SCIENTIFIC_EXECUTION' and ret.get('new_scientific_executions')==1,'COUPLED_RETURN_INTENT_MISMATCH')
  require(ret['receipt']['source_state_sha256']==source and ret['receipt']['new_state_sha256']==s['sha256'] and ret['receipt']['array_sha256']==s['payload']['arrays']['sha256'],'COUPLED_RETURN_HASH_MISMATCH')
  action=i['operation'];expected=parent['payload']['time_au']+(action['dt_au']*action['steps'] if 'steps' in action else 0)
  if action['type']=='PREPARE_COUPLED_STATE':expected=0
  require(abs(s['payload']['time_au']-expected)<1e-9,'COUPLED_RETURN_TIME_MISMATCH')
  if action['type']!='PREPARE_COUPLED_STATE':
   from .model import restore
   control_check=restore(self.store.arrays(parent),parent['payload'])
   if action['type'] in ('APPLY_ELECTRIC_PULSE','PULSE_AND_EVOLVE_COUPLED_STATE'):control_check.apply(action['control'])
   require(s['payload']['initial']==parent['payload']['initial'] and s['payload']['parameters']==control_check.state.parameters and s['payload']['controls']==control_check.state.controls,'COUPLED_RETURN_CONTROL_OR_INITIAL_MISMATCH')
  from dynamics01.adapter import compare_observations
  actual=observe(a,s['payload']);compare_observations(actual,ret['observation']);require(digest(ret['observation'])==ret['receipt']['result_sha256'],'COUPLED_OBSERVATION_HASH_MISMATCH')
  for rel in (f"states/{s['sha256']}.json",s['payload']['arrays']['path'],f"references/{s['sha256']}.json"):publish_bytes(self.root/rel,(base/rel).read_bytes())
  proof=self.root/'remote_provenance'/f"{s['sha256']}.json";freeze(proof,{'package_sha256':digest(package),'intent_sha256':ident,'array_sha256':s['payload']['arrays']['sha256'],'parent':source})
  return {'status':'NEW_SCIENTIFIC_EXECUTION','state':s['sha256'],'new_scientific_executions':1,'physical_parent_state':source,'provenance_receipt':{'path':str(proof),'sha256':filehash(proof)},'observables':actual}
