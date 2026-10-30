"""T01–T12: explicit synthetic GitHub fault injection + archived real array bytes.
No network, model, container, native solver or new H3 time propagation.
A fixture acceptance is NOT independently verified GitHub execution.
"""
import pathlib,tempfile,json,copy,hashlib,base64,zlib,unittest,os
from unittest.mock import patch
import numpy as np
from router import digest
from interactive01.world import freeze
from world01.session import filehash,publish_bytes
from world01.contracts import WorldError
from frontier01.state import CorrelatedStore
from live_fabric01.github_transport import GithubFabricTransport
from live_fabric01.fabric import physical_key
from .offline import setup
from .adapter import save_state,verify_return_files
from .model import observe_arrays
from .transfer import parent_files,stage_parent,encode_package
BASE=pathlib.Path(__file__).resolve().parents[2];REPO=BASE/'repo'
FACTS={'memory.max':str(2**30),'memory.swap.max':'0','cpu.max':'100000 100000','memory.current':'100','memory.events':'oom 0\noom_kill 0','cpu.stat':'usage_usec 1','interfaces':['lo'],'threads':1,'affinity_count':1,'mode':'SYNTHETIC_RESOURCE_FIXTURE_NOT_RUNTIME_EVIDENCE'}
def encode_file(b):return base64.b64encode(zlib.compress(b)).decode()
class Harness:
 def __init__(self,root):
  self.root=pathlib.Path(root);self.w,self.b,self.states=setup(self.root,BASE/'history');self.parent=self.states['initial'];self.intent={'research_session':'SYNTHETIC_RESEARCH_SESSION','world_session':digest(str(self.w.root.resolve())),'goal':'SOFTWARE_ONLY','candidate':'fixture','model':'dynamics','operation':{'type':'EVOLVE_WAVEPACKET','source_state_sha256':self.parent,'dt_au':.5,'steps':3},'input_state':self.parent,'prediction':'fixture only','falsifier':'byte mismatch','observables':['norm','time'],'resource_ref':'SYNTHETIC','authorization_ref':'set below','stop_condition':'no real execution','mode':'NEW_SCIENTIFIC_EXECUTION','experiment_ref':'4c040e7ba961dc91ee69f0be10e54d1b13e892937f13c1966415f780d83eb69a'}
  self.source={'dynamics01/core_world.py':filehash(REPO/'dynamics01/core_world.py')};self.g={'status':'HUMAN_GRANTED','human_reference':'SYNTHETIC_FIXTURE_NOT_ACTUAL_AUTHORITY','scope':'QW-LIVE-FABRIC-01','repository':'flyoung588/narque-qw-foundation02','repository_id':1427746629,'branch':'qw-dynamics-live-e01r','code_commit':'a'*40,'source_sha256':digest(self.source),'zero_additional_cost_verified':True,'cost_evidence_ref':'SYNTHETIC_NOT_CURRENT_COST_ADMISSION','workflow_sha256':filehash(REPO/'dynamics01/qw-dynamics01-once.yml'),'initial_states':[self.parent],'staged_world_files':{rel:{'source_path':'dynamics01/staged/'+rel,'sha256':filehash(p)} for rel,p in parent_files(self.w,self.parent).items()}}
  self.gp=self.root/'SYNTHETIC_GRANT.json';self.gp.write_text(json.dumps(self.g));self.pin=filehash(self.gp);self.intent['authorization_ref']=self.pin;self.ident=digest(self.intent)
  self.remote=self.root/'native';store=CorrelatedStore(self.remote)
  for rel,p in parent_files(self.w,self.parent).items():publish_bytes(self.remote/rel,p.read_bytes())
  parent=self.w.store.load(self.parent);historic=self.w.store.load(self.states['three_step_branch']);a=self.w.store.arrays(historic)
  from types import SimpleNamespace
  s=save_state(SimpleNamespace(root=self.remote,store=store),a,parent['payload']['model'],parent=self.parent,provenance={'mode':'NEW_SCIENTIFIC_EXECUTION','intent_sha256':self.ident,'fixture':'SOFTWARE_ONLY_ARCHIVED_THREE_STEP_BYTES'},time_au=1.5,absorbed=0.,controls=[],initial=parent['payload']['initial'],operation=self.intent['operation'],physical_continuity='CONTINUED_PARENT_PSI')
  observation=observe_arrays(a,s['payload']) # one native observation, one exact hash, as in the real worker
  self.state=s;self.ret={'state':s['sha256'],'intent_hash':self.ident,'new_scientific_executions':1,'mode':'NEW_SCIENTIFIC_EXECUTION','receipt':{'source_state_sha256':self.parent,'new_state_sha256':s['sha256'],'action':copy.deepcopy(self.intent['operation']),'action_sha256':digest(self.intent['operation']),'time_before_au':0.,'time_after_au':1.5,'array_sha256':s['payload']['arrays']['sha256'],'result_sha256':digest(observation)},'observation':observation}
  self.files={'grant.json':self.gp.read_bytes(),'request.json':json.dumps({'intent':self.intent,'grant_sha256':self.pin,'source_sha256':self.g['source_sha256']}).encode(),'source.json':json.dumps(self.source).encode(),'worker_result.json':json.dumps(self.ret).encode(),'resources_before.json':json.dumps(FACTS).encode(),'resources_after.json':json.dumps(FACTS).encode()}
  self.files.update({'world/'+str(p.relative_to(self.remote)):p.read_bytes() for p in self.remote.rglob('*') if p.is_file()})
  self.package={'intent_hash':self.ident,'source_sha256':self.g['source_sha256'],'grant_sha256':self.pin,'files':{k:encode_file(v) for k,v in self.files.items()}}
  self.run={'id':99999999,'workflow_id':888888,'path':'.github/workflows/qw-dynamics01-once.yml','repository':{'id':1427746629,'full_name':self.g['repository']},'head_repository':{'id':1427746629,'full_name':self.g['repository']},'status':'completed','conclusion':'success','run_attempt':1,'head_sha':self.g['code_commit'],'head_branch':self.g['branch'],'event':'workflow_dispatch','display_title':'QWLF01-'+self.ident}
  self.job={'id':777777,'run_id':self.run['id'],'run_url':f"https://api.github.com/repos/{self.g['repository']}/actions/runs/{self.run['id']}",'status':'completed','conclusion':'success','run_attempt':1,'head_sha':self.g['code_commit'],'head_branch':self.g['branch'],'labels':['ubuntu-24.04']}
  self.workflow={'id':888888,'path':'.github/workflows/qw-dynamics01-once.yml'};self.dispatched=False;self.api_calls=[];self.fail_api=False;self.extra_staged={};self.compare=None;self.raw_override=None
  self.t=GithubFabricTransport(self.root/'transport',runtime_enabled=True);self.t.gh=self.fake_gh;self.t.gh_bytes=self.fake_bytes
 def fake_gh(self,*args):
  self.api_calls.append(list(args))
  if self.fail_api:raise WorldError('GITHUB_API_FAILED')
  repo='repos/'+self.g['repository'];endpoint=args[1] if len(args)>1 else ''
  if args[0]=='api' and '--method' in args:self.dispatched=True;return ''
  if endpoint==repo:return json.dumps({'id':1427746629,'full_name':self.g['repository'],'private':False,'disabled':False})
  if endpoint==repo+'/git/ref/heads/'+self.g['branch']:return json.dumps({'object':{'sha':self.g['code_commit']}})
  if '/contents/' in endpoint:
   name=endpoint.split('/contents/')[1].split('?')[0]
   if name=='.github/workflows/qw-dynamics01-once.yml':raw=(REPO/'dynamics01/qw-dynamics01-once.yml').read_bytes()
   else:
    rel=name.removeprefix('dynamics01/staged/');raw=self.extra_staged.get(rel,self.files.get('world/'+rel));assert raw is not None,name
   return json.dumps({'encoding':'base64','content':base64.b64encode(raw).decode()})
  if '/compare/' in endpoint:return json.dumps(self.compare)
  if endpoint.endswith('/actions/workflows/qw-dynamics01-once.yml'):return json.dumps(self.workflow)
  if '/actions/workflows/' in endpoint and '/runs?' in endpoint:return json.dumps({'total_count':int(self.dispatched),'workflow_runs':[self.run] if self.dispatched else []})
  if endpoint.endswith('/attempts/1/jobs?per_page=100'):return json.dumps({'total_count':1,'jobs':[{'id':self.job['id']}]})
  if endpoint.endswith('/actions/jobs/'+str(self.job['id'])):return json.dumps(self.job)
  if endpoint.endswith('/actions/runs/'+str(self.run['id'])):return json.dumps(self.run)
  raise AssertionError('UNHANDLED_SYNTHETIC_ENDPOINT '+repr(args))
 def fake_bytes(self,*args):
  self.api_calls.append(list(args));return self.raw_override if self.raw_override is not None else '\n'.join(encode_package(self.package)).encode()
 def execute(self):
  attempt=self.root/'attempt';attempt.mkdir()
  with patch('subprocess.Popen',side_effect=AssertionError('NO_REAL_NETWORK_OR_PROCESS')):return self.t.execute(self.intent,self.w,attempt,self.gp,self.pin,self.g['source_sha256'])
 def ingest(self,package):
  self.b.transport=self.t;out=self.w.ingest_worker(package,self.intent,self.ident,self.root/'attempt')
  self.b.j.append('ExecutionReturned',{'intent_hash':self.ident,'state':out['state'],'new_science':True,'provenance_receipt':out['provenance_receipt'],'fixture':'SYNTHETIC_SOFTWARE_ONLY_NOT_AN_ACTUAL_JOB'});return out
class ProvenanceRepair(unittest.TestCase):
 def setUp(self):
  root=pathlib.Path(os.environ.get('QW_PROVENANCE_EVIDENCE',tempfile.mkdtemp()))/self._testMethodName;root.mkdir(parents=True,exist_ok=False);self.h=Harness(root)
 def tearDown(self):
  (self.h.root/'SYNTHETIC_API_CALLS.json').write_text(json.dumps({'fixture_only':True,'actual_network_calls':0,'actual_science_jobs':0,'calls':self.h.api_calls},indent=2))
 def reject(self,fn,reason=None):
  with self.assertRaises((WorldError,ValueError,KeyError,OSError)) as e:fn()
  if reason:self.assertIn(reason,str(e.exception))
 def test_T01_failed_run_rejected(self):
  for state in ('failure','cancelled','timed_out','skipped','unknown'):
   self.h.run['conclusion']=state
   # Metadata acquisition only; avoid dispatch retry even in fixtures.
   self.reject(lambda:self.h.t._metadata_binding(self.h.g['repository'],'qw-dynamics01-once.yml',self.h.run['id'],self.h.ident,self.h.g,self.h.root,state),'REMOTE_RUN_NOT_SUCCESSFUL')
 def test_T02_attempt2_rejected(self):self.h.run['run_attempt']=2;self.reject(self.h.execute,'REMOTE_RUN_NOT_FIRST_ATTEMPT')
 def test_T03_wrong_commit_rejected(self):self.h.run['head_sha']='c'*40;self.reject(self.h.execute,'REMOTE_RUN_SOURCE_MISMATCH')
 def test_T04_valid_run_job_raw_arrays_and_intake(self):
  self.h.package['files']['world/states/'+('d'*64)+'.json']=encode_file(b'{"fixture_unbound_extra":true}')
  p=self.h.execute();self.assertEqual(p['verified_run']['run_id'],self.h.run['id']);out=self.h.ingest(p);self.assertEqual(out['state'],self.h.state['sha256']);self.assertFalse((self.h.w.root/'states'/(('d'*64)+'.json')).exists());env=self.h.w.load(out['state']);self.assertEqual(env['physical_time'],1.5);self.assertEqual(p['log_sha256'],hashlib.sha256((self.h.root/'attempt/raw_remote.log.bin').read_bytes()).hexdigest())
  log=self.h.root/'attempt/raw_remote.log.bin';log.write_bytes(log.read_bytes()+b'CORRUPTION');self.reject(lambda:self.h.t.verify_package(p),'ACQUISITION_EVIDENCE_BYTES_CHANGED')
 def test_T05_wrong_workflow_job_and_repository_rejected(self):
  self.h.run['workflow_id']=123;self.reject(self.h.execute,'REMOTE_RUN_WORKFLOW_MISMATCH')
  self.h.run['workflow_id']=self.h.workflow['id'];self.h.job['run_id']=123;self.reject(lambda:self.h.t._metadata_binding(self.h.g['repository'],'qw-dynamics01-once.yml',self.h.run['id'],self.h.ident,self.h.g,self.h.root,'wrong_job'),'REMOTE_JOB_RUN_MISMATCH')
  self.h.job['run_id']=self.h.run['id'];self.h.run['repository']['id']=0;self.reject(lambda:self.h.t._metadata_binding(self.h.g['repository'],'qw-dynamics01-once.yml',self.h.run['id'],self.h.ident,self.h.g,self.h.root,'wrong_repo'),'REMOTE_RUN_REPOSITORY_MISMATCH')
 def test_T06_wrong_intent_and_old_return_rejected(self):self.h.package['intent_hash']='d'*64;self.reject(self.h.execute,'REMOTE_RETURN_BINDING')
 def test_T07_self_declared_or_unavailable_API_rejected(self):
  self.h.package['verified_by_github']=True;self.h.fail_api=True;self.reject(self.h.execute,'GITHUB_API_FAILED');self.reject(lambda:self.h.t.verify_package({'verified_by_github':True}),'UNAUTHENTICATED_WORKER_PACKAGE')
  # A caller cannot register a package by directly supplying success JSON to
  # a parsing helper: only the official acquisition entrypoints register trust.
  folder=self.h.root/'caller-only';folder.mkdir();(folder/'caller_supplied.json').write_text('{}')
  fakeproof={'intent_hash':self.h.ident,'raw_log_sha256':'0'*64,'source':'CALLER_SELF_DECLARATION'}
  candidate=self.h.t._publish_verified_return(self.h.package,fakeproof,self.h.run,self.h.intent,self.h.g,self.h.g['source_sha256'],self.h.pin,self.h.gp,self.h.w,folder);self.reject(lambda:self.h.t.verify_package(candidate),'UNAUTHENTICATED_WORKER_PACKAGE')
  self.h.fail_api=False;self.h.run['status']='in_progress';self.reject(lambda:self.h.t._metadata_binding(self.h.g['repository'],'qw-dynamics01-once.yml',self.h.run['id'],self.h.ident,self.h.g,self.h.root,'unfinished'),'REMOTE_RUN_NOT_SUCCESSFUL')
  self.h.run['status']='completed';self.h.job.pop('run_id');self.reject(lambda:self.h.t._metadata_binding(self.h.g['repository'],'qw-dynamics01-once.yml',self.h.run['id'],self.h.ident,self.h.g,self.h.root,'missing_job_run'),'REMOTE_JOB_RUN_MISMATCH')
 def test_T08_raw_and_wavefunction_tamper_rejected(self):
  from .adapter import compare_observations
  wrong=copy.deepcopy(self.h.ret['observation']);wrong['energy']['value']+=1e-8;self.reject(lambda:compare_observations(self.h.ret['observation'],wrong),'DYNAMIC_OBSERVATION_NUMERIC_MISMATCH')
  good='\n'.join(encode_package(self.h.package));self.h.raw_override=good.replace('QWDYN_CHUNK=0:','QWDYN_CHUNK=0:A',1).encode();self.reject(self.h.execute)
  # Test byte integrity separately without dispatching another simulated Job.
  a=self.h.remote/self.h.state['payload']['arrays']['path'];a.write_bytes(a.read_bytes()+b'TAMPER');self.reject(lambda:verify_return_files(self.h.w,self.h.remote,self.h.ret,self.h.intent),'ARRAY_HASH_MISMATCH')
 def test_T09_wrong_parent_and_same_shape_wrong_psi_rejected(self):
  wrong=copy.deepcopy(self.h.ret);wrong['receipt']['source_state_sha256']='e'*64;self.reject(lambda:verify_return_files(self.h.w,self.h.remote,wrong,self.h.intent),'DYNAMICS_RETURN_BINDING_MISMATCH')
  parent=self.h.w.store.load(self.h.parent);p=self.h.remote/parent['payload']['arrays']['path'];old=p.read_bytes()
  with np.load(p,allow_pickle=False) as z:a={k:z[k].copy() for k in z.files}
  a['psi']*=np.exp(.01j);np.savez_compressed(p,**a);self.reject(lambda:verify_return_files(self.h.w,self.h.remote,self.h.ret,self.h.intent),'PHYSICAL_PARENT_OR_WAVEFUNCTION_BYTES_CHANGED');p.write_bytes(old)
  # Correctly rehashed but wrong representation must also fail; not only a bad SHA.
  from types import SimpleNamespace
  store=CorrelatedStore(self.h.remote);a=store.arrays(self.h.state);a['psi']=a['psi'].astype(np.complex64)*np.float32(.5);fixture_absorbed=1-float(np.vdot(a['psi'],a['psi']).real*self.h.state['payload']['model']['grid']['dx_bohr']**2);payload=self.h.state['payload'];candidate=save_state(SimpleNamespace(root=self.h.remote,store=store),a,payload['model'],parent=self.h.parent,provenance={'mode':'NEW_SCIENTIFIC_EXECUTION','intent_sha256':self.h.ident,'fixture':'WRONG_DTYPE_SOFTWARE_ONLY'},time_au=1.5,absorbed=fixture_absorbed,controls=[],initial=payload['initial'],operation=self.h.intent['operation'],physical_continuity='CONTINUED_PARENT_PSI')
  wrong=copy.deepcopy(self.h.ret);wrong['state']=candidate['sha256'];wrong['receipt']['new_state_sha256']=candidate['sha256'];wrong['receipt']['array_sha256']=candidate['payload']['arrays']['sha256'];wrong['observation']=observe_arrays(a,candidate['payload']);wrong['receipt']['result_sha256']=digest(wrong['observation']);self.reject(lambda:verify_return_files(self.h.w,self.h.remote,wrong,self.h.intent),'DYNAMIC_NUMERICAL_REPRESENTATION_MISMATCH')
 def test_T10_second_commit_independent_exact_staging(self):
  p=self.h.execute();out=self.h.ingest(p);new=out['state'];refs=stage_parent(self.h.w,new,self.h.root/'staged-copy');g2=copy.deepcopy(self.h.g);g2['code_commit']='f'*40;g2['staged_world_files']=refs;proof=p['verified_run'];g2['parent_execution']={k:proof[k] for k in ('run_id','job_id','code_commit','raw_log_sha256')}
  self.h.extra_staged={rel:f.read_bytes() for rel,f in parent_files(self.h.w,new).items()};changed=[x['source_path'] for rel,x in refs.items() if rel not in self.h.g['staged_world_files']];g2['staging_diff']=changed;self.h.compare={'status':'ahead','ahead_by':1,'files':[{'filename':n,'status':'added'} for n in changed]};i2=copy.deepcopy(self.h.intent);i2['input_state']=new;i2['operation']={'type':'EVOLVE_WAVEPACKET','source_state_sha256':new,'dt_au':.5,'steps':2}
  self.h.t._verify_staged_source(self.h.w,i2,g2,self.h.root);self.assertNotEqual(g2['code_commit'],self.h.g['code_commit'])
  self.h.compare['files'].append({'filename':'dynamics01/core_world.py','status':'modified'});self.reject(lambda:self.h.t._verify_staged_source(self.h.w,i2,g2,self.h.root),'SECOND_COMMIT_NOT_EXACT_BYTE_STAGING_ONLY')
  self.h.compare['files'].pop();g2['parent_execution']['raw_log_sha256']='0'*64;self.reject(lambda:self.h.t._verify_staged_source(self.h.w,i2,g2,self.h.root),'SECOND_PARENT_EXECUTION_NOT_BOUND')
 def test_T11_checkpoint_does_not_refund_or_repeat_job(self):
  i=self.h.intent;self.h.b.j.append('ExecutionReserved',{'intent_hash':digest(i),'fingerprint':physical_key(i),'new_science':True,'fixture':'NO_REAL_JOB'})
  from .fabric import DynamicsExecutionFabric
  b=DynamicsExecutionFabric(self.h.b.root,self.h.w);self.assertEqual(len(b.j.query('ExecutionReserved')),1);self.assertEqual(b.j.query('ExecutionFailed')[-1]['data']['status'],'INTERRUPTED_NO_RETRY')
  b=DynamicsExecutionFabric(self.h.b.root,self.h.w);self.assertEqual(len(b.j.query('ExecutionReserved')),1);self.assertEqual(len(b.j.query('ExecutionFailed')),1)
  first=self.h.execute();before=sum('--method' in a for a in self.h.api_calls);folder=self.h.root/'read-only-recovery';folder.mkdir();recovered=self.h.t.read_completed_return(self.h.intent,self.h.w,folder,self.h.gp,self.h.pin,self.h.g['source_sha256']);self.assertEqual(first['state'],recovered['state']);self.assertEqual(sum('--method' in a for a in self.h.api_calls),before);self.assertEqual(len(b.j.query('ExecutionReserved')),1)
 def test_T12_worldsession_explorer_legal_offline_path(self):
  from .offline import main
  out=main(self.h.root/'offline-regression',BASE/'history');v=json.loads((out/'OFFLINE_RESULT.json').read_text());self.assertTrue(v['checkpoint_resumed_STOP']);self.assertEqual(v['new_model_calls'],0);self.assertEqual(v['new_scientific_jobs'],0)
if __name__=='__main__':unittest.main()
