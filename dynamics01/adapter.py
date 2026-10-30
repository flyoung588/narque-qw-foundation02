"""WorldSession extension over inherited hashed Store/NPZ, Session receipts and Live Fabric.
Historical import is hash-pinned; no new science enabled by this adapter.
"""
import copy,json,pathlib
import numpy as np
from router import digest
from interactive01.world import freeze,verify
from state_space01.state import blob
from world01.session import publish_bytes,filehash
from world01.contracts import WorldError,envelope
from live_fabric01.fabric import FabricWorldSession,require
from .model import SCHEMA,MODEL,OPS,OBS,describe_model,validate_arrays,observe_arrays,validate_operation
from . import integration

def is_dynamic(s):return s['payload'].get('schema')==SCHEMA

def save_state(world,arrays,model,*,parent=None,provenance,**state):
 validate_arrays(arrays,model)
 if parent:world.store.load(parent)
 p={'schema':SCHEMA,'state_kind':'COLLINEAR_H3_NUCLEAR_WAVEPACKET','parent_state_id':parent,'world_spec':{'object_id':'collinear-H3-LSTH','matter':{'type':'ordered_collinear_nuclei','elements':['H','H','H'],'periodic':False,'charge':0,'spin_2S':1},'physics':{'engine':'QML_LSTH_Core01','method':'single_BO_nuclear_TDSE'}},'model':model,'arrays':blob(world.root,arrays),'time_origin_au':0.,'time_au':0.,'absorbed':0.,'controls':[],'initial':{},'scope':MODEL['limitations'],**state}
 require(all(type(p[k]) in (int,float) and np.isfinite(p[k]) and p[k]>=0 for k in ('time_au','time_origin_au','absorbed')),'INVALID_PHYSICAL_TIME_OR_ABSORBED')
 norm=validate_arrays(arrays,model);require(abs(norm+p['absorbed']-1)<1e-7,'PROBABILITY_ACCOUNTING_INVALID')
 p['norm']=norm;h=digest(p);s={'state_id':h,'sha256':h,'payload':p};freeze(world.root/'states'/f'{h}.json',s)
 rec={'mode':provenance['mode'],'state_sha256':h,'state_file_sha256':filehash(world.root/'states'/f'{h}.json'),'evidence':provenance}
 freeze(world.root/'references'/f'{h}.json',rec);return s

class DynamicsWorldSession(FabricWorldSession):
 def _validate_state(self,s):
  if not is_dynamic(s):return super()._validate_state(s)
  verify(s);p=s['payload'];a=self.store.arrays(s);n=validate_arrays(a,p['model']);require(abs(n-p['norm'])<1e-12,'NORM_METADATA_MISMATCH');require(abs(n+p['absorbed']-1)<1e-7,'PROBABILITY_ACCOUNTING_INVALID');require(p['time_au']>=0,'INVALID_TIME');return s
 def load(self,ident):
  s=self.store.load(ident)
  if not is_dynamic(s):return super().load(ident)
  self._validate_state(s);p=self.root/'references'/f'{ident}.json';require(p.is_file(),'PROVENANCE_MISSING');rec=json.loads(p.read_text());require(rec['state_file_sha256']==filehash(self.root/'states'/f'{ident}.json'),'STATE_PROVENANCE_MISMATCH')
  ev=rec['evidence'];mode=ev['mode'];require(mode in ('HISTORICAL_REAL_EVIDENCE_REPLAY','SOFTWARE_FIXTURE_ONLY','NEW_SCIENTIFIC_EXECUTION'),'UNKNOWN_PROVENANCE_MODE')
  if mode=='HISTORICAL_REAL_EVIDENCE_REPLAY':
   for rel,h in ev['source_files'].items():require(filehash(self._source(rel))==h,'HISTORICAL_SOURCE_CHANGED')
  elif mode=='NEW_SCIENTIFIC_EXECUTION':
   require(hasattr(self,'execution') and any(x['data'].get('state')==ident and x['data'].get('new_science') for x in self.execution.j.query('ExecutionReturned')),'LIVE_RETURN_NOT_JOURNALED')
   proofpath=self.root/'remote_provenance'/f'{ident}.json';require(proofpath.is_file(),'LIVE_REMOTE_PROVENANCE_MISSING')
   require(any(x['data'].get('state')==ident and x['data'].get('provenance_receipt',{}).get('sha256')==filehash(proofpath) for x in self.execution.j.query('ExecutionReturned')),'LIVE_REMOTE_PROVENANCE_NOT_JOURNALED')
  trust={'verified':True,'real_calculated':mode!='SOFTWARE_FIXTURE_ONLY','source_execution_kind':mode,'source_execution_status':'HISTORICAL_CALCULATED' if mode.startswith('HISTORICAL') else 'SOFTWARE_ONLY' if mode=='SOFTWARE_FIXTURE_ONLY' else 'CALCULATED','source_evidence_status':'PINNED_CORE01_OUTPUT' if mode.startswith('HISTORICAL') else mode,'model_qualification':'FINITE_LSTH_MODEL_NOT_REALITY_CERTIFIED'}
  return envelope(s,rec,trust)
 def reference(self,relative,*args,**kw):
  if relative.startswith('dynamics:'):return self.load(relative.split(':',1)[1])
  return super().reference(relative,*args,**kw)
 def import_core_history(self,*,view_path,trajectory_path,state_path):
  self._open();paths=[view_path,trajectory_path,state_path];src={rel:filehash(self._source(rel)) for rel in paths}
  v=json.loads(self._source(view_path).read_text());tr=json.loads(self._source(trajectory_path).read_text());n=v['n'];dx=v['dx'];require(n==tr['n']==256 and dx==14/n and v['mass']==MODEL['mass_me'],'CORE_MODEL_BINDING_MISMATCH')
  m=describe_model(n,dx,v['axis'][0],True);a={k:np.asarray(v[k],float).reshape(n,n) for k in ('V','W','K')};a['axis']=np.asarray(v['axis']);a['psi']=np.asarray(v['initial_re']).reshape(n,n)+1j*np.asarray(v['initial_im']).reshape(n,n)
  prov={'mode':'HISTORICAL_REAL_EVIDENCE_REPLAY','source_files':src,'original_execution':'QW-CORE01-FIRST-RUN-20261017','new_scientific_executions':0,'license':'QML vendor/LICENSE retained','scope':'restoring saved output, no new propagation'}
  first=save_state(self,a,m,provenance=prov,time_au=0.,initial=tr['initial'],historical_stage='EXECUTED_INITIAL_STATE')
  a['psi']=np.asarray(v['reference_re']).reshape(n,n)+1j*np.asarray(v['reference_im']).reshape(n,n)
  small=save_state(self,a,m,parent=first['sha256'],provenance=prov,time_au=1.5,initial=tr['initial'],physical_continuity='HISTORICAL_3_STEPS_FROM_SAME_INITIAL_PSI',operation={'type':'EVOLVE_WAVEPACKET','source_state_sha256':first['sha256'],'dt_au':.5,'steps':3})
  with np.load(self._source(state_path),allow_pickle=False) as z:
   require(np.array_equal(z['axis'],a['axis']),'HISTORICAL_AXIS_MISMATCH');a['psi']=z['psi'].copy()
  last=tr['rows'][-1];require(abs(last['time_au']-len(tr['rows'][1:])*50*tr['dt'])<1e-10,'HISTORICAL_TIME_MISMATCH')
  final=save_state(self,a,m,parent=first['sha256'],provenance=prov,time_au=last['time_au'],absorbed=last['absorbed'],initial=tr['initial'],physical_continuity='HISTORICAL_PROPAGATION_FROM_SAME_INITIAL_PSI_NOT_FROM_3STEP_BRANCH',operation={'type':'EVOLVE_WAVEPACKET','source_state_sha256':first['sha256'],'dt_au':tr['dt'],'steps':round(last['time_au']/tr['dt'])},historical_observation=last)
  actual=observe_arrays(a,final['payload']);require(abs(actual['norm']['value']-last['norm'])<1e-12 and abs(actual['energy']['value']-last['energy_Eh'])<1e-12,'HISTORICAL_OBSERVATION_RESTORE_MISMATCH')
  return {'initial':first['sha256'],'three_step_branch':small['sha256'],'final':final['sha256'],'source_files':src,'new_scientific_executions':0}
 def observe(self,ident,requested=()):
  s=self.store.load(ident)
  if not is_dynamic(s):return super().observe(ident,requested)
  env=self.load(ident);require(not set(requested)-set(OBS),'UNSUPPORTED_OBSERVABLE');out=observe_arrays(self.store.arrays(s),s['payload']);mode=env['source_execution']['source_execution_kind'];values={k:out[k] for k in requested or out}
  return {'schema':'QW_OBSERVATION_ENVELOPE_01','source_state_hash':ident,'status':'SOFTWARE_FIXTURE_ONLY' if mode=='SOFTWARE_FIXTURE_ONLY' else 'HISTORICAL_OBSERVATION_READ' if mode.startswith('HISTORICAL') else 'SCIENTIFIC_OBSERVATION_READ','values':{'available_observables':list(out),'original_observation':s['payload'].get('historical_observation'),'physical_time_au':s['payload']['time_au']},'observables':values,'model_hash':digest(s['payload']['model']),'model_domain':'dynamics','units':MODEL['units'],'source_execution_kind':mode,'source_execution_status':env['source_execution']['source_execution_status'],'source_evidence_status':env['source_execution']['source_evidence_status'],'model_qualification':'FINITE_COLLINEAR_LSTH_ONLY','error_uncertainty':MODEL['limitations'],'provenance':env['provenance'],'new_physics_run':False,'new_scientific_executions':0}
 def act(self,request):
  q=request.plain() if hasattr(request,'plain') else request;ident=q.get('source_state_hash')
  if ident and is_dynamic(self.store.load(ident)):
   self._open();self.load(ident);action={'type':q['action'],'source_state_sha256':ident,**q.get('parameters',{})};kind=validate_operation(self.store.load(ident)['payload'],action)
   if kind=='MEASURE_WAVEPACKET':return self.observe(ident,action['observables'])
   if kind=='FORK_PHYSICAL_STATE':return self.fork(ident,action['reason'])
   raise WorldError('NEW_DYNAMICS_EXECUTION_AUTHORIZATION_REQUIRED','No new propagation/control/preparation in offline integration')
  return super().act(request)
 def compare(self,a,b,contract=None):
  x=self.store.load(a);y=self.store.load(b)
  if not is_dynamic(x) and not is_dynamic(y):return super().compare(a,b,contract)
  require(is_dynamic(x) and is_dynamic(y),'NO_STATIC_BO_TO_NUCLEAR_STATE_CONVERSION');self.load(a);self.load(b);p=x['payload'];q=y['payload']
  require(p['model']==q['model'],'DYNAMICS_HAMILTONIAN_OR_GRID_MISMATCH');require((contract or {}).get('kind') in ('SAME_HAMILTONIAN_TIME_PATH','MATCHED_TIME_STATE_COMPARISON'),'DYNAMICS_COMPARISON_CONTRACT_REQUIRED')
  if contract['kind']=='MATCHED_TIME_STATE_COMPARISON':require(p['time_au']==q['time_au'],'PHYSICAL_TIME_MISMATCH')
  u=self.store.arrays(x)['psi'];v=self.store.arrays(y)['psi'];dx=p['model']['grid']['dx_bohr'];return self.receipt('compare','COMPARISON_VALIDATED','SAME_DECLARED_HAMILTONIAN_FINITE_GRID',a,result={'other_state':b,'time_au':[p['time_au'],q['time_au']],'L2_distance':float(np.linalg.norm(u-v)*dx),'overlap_squared_raw':float(abs(np.vdot(u,v)*dx**2)**2),'definition':'raw surviving overlap; distinct times only explicit time-path contract; not fidelity with absorbed environment'})
 def translate(self,ident,target):
  if is_dynamic(self.store.load(ident)):raise WorldError('NO_PROVEN_WAVEPACKET_TO_BO_OR_ELECTRONIC_MAPPING')
  return super().translate(ident,target)
 def ingest_worker(self,package,i,ident,attempt):
  if i.get('model')!='dynamics':return super().ingest_worker(package,i,ident,attempt)
  self.execution.transport.verify_package(package);base=pathlib.Path(package['world_root']);ret=json.loads(pathlib.Path(package['result_path']).read_text());rec=ret['receipt']
  require(package.get('verified_run',{}).get('intent_hash')==digest(i),'REMOTE_PROVENANCE_NOT_VERIFIED')
  verified=verify_return_files(self,base,ret,i)
  # Parent bytes already exist and were compared exactly. Unbound extra states
  # remain in the raw package quarantine; never import a whole remote directory.
  for rel in ('states/'+verified['sha256']+'.json',verified['payload']['arrays']['path'],'references/'+verified['sha256']+'.json'):
   publish_bytes(self.root/rel,(base/rel).read_bytes())
  s=self.store.load(ret['state']);self._validate_state(s);p=s['payload'];require(is_dynamic(s) and p['parent_state_id']==i['input_state'] and rec['new_state_sha256']==s['sha256'],'DYNAMICS_PARENT_MISMATCH')
  parent=self.store.load(i['input_state']);require(p['model']==parent['payload']['model'],'HAMILTONIAN_CHANGED_WITHOUT_CONTROL')
  pa=self.store.arrays(parent);na=self.store.arrays(s)
  for key in ('axis','V','W','K'):require(np.allclose(na[key],pa[key],rtol=0,atol=1e-12),'HAMILTONIAN_ARRAY_CHANGED_WITHOUT_CONTROL')
  if i['operation']['type']=='EVOLVE_WAVEPACKET':require(abs(p['time_au']-parent['payload']['time_au']-i['operation']['dt_au']*i['operation']['steps'])<1e-9,'EVOLUTION_TIME_MISMATCH')
  actual=observe_arrays(self.store.arrays(s),p);require(rec['result_sha256']==digest(ret['observation']),'DYNAMIC_OBSERVATION_HASH_MISMATCH');compare_observations(actual,ret['observation'])
  provenance=self.root/'remote_provenance'/f"{s['sha256']}.json";freeze(provenance,{'state':s['sha256'],'verified_run':package['verified_run'],'package_sha256':digest(package),'intent_hash':digest(i),'parent':i['input_state'],'array_sha256':p['arrays']['sha256']})
  proof={'path':str(provenance.resolve()),'sha256':filehash(provenance)}
  return {'status':'NEW_SCIENTIFIC_EXECUTION','new_scientific_executions':1,'state':s['sha256'],'worker_package':package,'provenance_receipt':proof,'observables':actual,'physical_parent_state':i['input_state'],'research_parent_context':i['research_session']}


def verify_return_files(world,base,ret,intent):
 """Bind raw return before copying anything into the live scientific Store.
 Does not certify physics accuracy or rerun the propagator.
 """
 base=pathlib.Path(base);ident=digest(intent);source=intent['input_state'];world.load(source)
 from .transfer import parent_files
 for rel,original in parent_files(world,source).items():
  remote=base/rel;require(remote.is_file() and remote.read_bytes()==original.read_bytes(),'PHYSICAL_PARENT_OR_WAVEFUNCTION_BYTES_CHANGED')
 rec=ret.get('receipt',{});require(ret.get('intent_hash')==ident and ret.get('mode')=='NEW_SCIENTIFIC_EXECUTION' and ret.get('new_scientific_executions')==1,'DYNAMIC_NATIVE_RETURN_INVALID')
 require(rec.get('source_state_sha256')==source and rec.get('action')==intent['operation'] and rec.get('action_sha256')==digest(intent['operation']),'DYNAMICS_RETURN_BINDING_MISMATCH')
 require(isinstance(ret.get('state'),str) and len(ret['state'])==64 and all(c in '0123456789abcdef' for c in ret['state']) and ret['state']!=source,'DYNAMIC_TARGET_STATE_INVALID')
 from frontier01.state import CorrelatedStore
 remote_store=CorrelatedStore(base);s=remote_store.load(ret['state']);p=s['payload'];require(is_dynamic(s) and p['parent_state_id']==source and rec.get('new_state_sha256')==s['sha256'],'DYNAMICS_PARENT_MISMATCH')
 parent=world.store.load(source);pa=world.store.arrays(parent);a=remote_store.arrays(s);require(a['psi'].dtype==np.dtype('complex128') and all(a[k].dtype==np.dtype('float64') for k in ('axis','V','W','K')) and all(a[k].dtype==pa[k].dtype for k in a),'DYNAMIC_NUMERICAL_REPRESENTATION_MISMATCH');norm=validate_arrays(a,p['model']);require(abs(norm-p['norm'])<1e-12 and abs(norm+p['absorbed']-1)<1e-7,'DYNAMIC_NORM_OR_ABSORPTION_INVALID')
 require(p['model']==parent['payload']['model'],'DYNAMICS_HAMILTONIAN_MISMATCH')
 for key in ('axis','V','W','K'):require(np.array_equal(a[key],pa[key]),'DYNAMIC_GRID_OR_HAMILTONIAN_ARRAY_CHANGED')
 require(rec.get('array_sha256')==p['arrays']['sha256'] and rec.get('time_before_au')==parent['payload']['time_au'] and rec.get('time_after_au')==p['time_au'],'DYNAMIC_ARRAY_OR_TIME_RECEIPT_MISMATCH')
 action=intent['operation'];require(p.get('operation')==action,'DYNAMIC_OPERATION_NOT_PERSISTED');kind=validate_operation(parent['payload'],action)
 if kind=='EVOLVE_WAVEPACKET':
  expected=parent['payload']['time_au']+action['dt_au']*action['steps'];require(p.get('physical_continuity')=='CONTINUED_PARENT_PSI' and p['initial']==parent['payload']['initial'] and p['controls']==parent['payload']['controls'],'DYNAMIC_CONTINUATION_IDENTITY_MISMATCH')
 elif kind=='PREPARE_AND_EVOLVE_WAVEPACKET':
  expected=action['evolution']['dt_au']*action['evolution']['steps'];prep=action['preparation'];require(p.get('physical_continuity')=='NEW_PREPARATION_NOT_CONTINUATION','DYNAMIC_PREPARATION_MISLABELED')
  require(p['initial']=={'energy_eV':prep['energy_eV'],'center_R':prep['center_R_bohr'],'sigma_R':prep['sigma_R_bohr']} and p['controls']==[],'DYNAMIC_INITIAL_CONDITIONS_MISMATCH')
 else:require(False,'DYNAMIC_ACTION_NOT_IN_LIVE_EXPERIMENT_SCOPE')
 require(abs(p['time_au']-expected)<1e-9 and p['time_origin_au']==0.,'DYNAMIC_PHYSICAL_TIME_MISMATCH')
 actual=observe_arrays(a,p);require(rec.get('result_sha256')==digest(ret.get('observation')),'DYNAMIC_OBSERVATION_HASH_MISMATCH');compare_observations(actual,ret['observation'])
 # Reference metadata from the worker must bind exactly the emitted state file.
 ref=base/'references'/f"{s['sha256']}.json";require(ref.is_file(),'DYNAMIC_STATE_REFERENCE_MISSING');v=json.loads(ref.read_text())
 require(v.get('state_sha256')==s['sha256'] and v.get('state_file_sha256')==filehash(base/'states'/f"{s['sha256']}.json") and v.get('evidence',{}).get('mode')=='NEW_SCIENTIFIC_EXECUTION' and v.get('evidence',{}).get('intent_sha256')==ident,'DYNAMIC_STATE_REFERENCE_MISMATCH')
 return s


def compare_observations(actual,returned):
 """Exact evidence hashes are checked separately. Recomputed IEEE reductions may
 differ by a few ulps; this engineering check is NOT a physics accuracy threshold.
 Units/references/array IDs/time remain exact; no original scientific criterion changes.
 """
 import math
 differences=[]
 def walk(a,b,path=''):
  if isinstance(a,dict):
   require(isinstance(b,dict) and set(a)==set(b),'DYNAMIC_OBSERVATION_STRUCTURE_MISMATCH')
   for k in a:walk(a[k],b[k],path+'/'+k)
  elif isinstance(a,list):
   require(isinstance(b,list) and len(a)==len(b),'DYNAMIC_OBSERVATION_STRUCTURE_MISMATCH')
   for k,(x,y) in enumerate(zip(a,b)):walk(x,y,path+'/'+str(k))
  elif type(a) in (int,float):
   require(type(b) in (int,float) and math.isfinite(a) and math.isfinite(b),'DYNAMIC_OBSERVATION_NONFINITE')
   bound=0. if path.startswith('/time/') else 64*np.finfo(float).eps*max(1.,abs(a),abs(b))
   require(abs(a-b)<=bound,'DYNAMIC_OBSERVATION_NUMERIC_MISMATCH')
   if a!=b:differences.append({'path':path,'recomputed':a,'raw_returned':b,'absolute_difference':abs(a-b),'engineering_bound':bound})
  else:require(a==b,'DYNAMIC_OBSERVATION_METADATA_MISMATCH')
 walk(actual,returned);return {'status':'ENGINEERING_READBACK_CONSISTENT','criterion':'64*float64_epsilon*max(1,abs(value)); time/metadata/array references exact','physical_accuracy':'NOT_CERTIFIED; original scientific criteria unchanged','raw_array_and_observation_hash_checks':'EXACT_SEPARATE_CHECKS','differences':differences}
