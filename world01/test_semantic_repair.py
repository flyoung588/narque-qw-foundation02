"""T01..T20: actual pinned H3+/Ne records, no new electronic-structure calls."""
import copy,json,os,pathlib,tempfile,shutil,unittest,hashlib
from unittest.mock import patch
from jsonschema import ValidationError
from router import digest
from .session import WorldSession
from .contracts import WorldError,OperationRequest
from .schemas import validate
from . import fabric
P=pathlib.Path(__file__).resolve().parents[1];R=P.parent
MANIFEST=json.loads((R/'SOURCE_BASELINE_SHA256.json').read_text())
OUT=pathlib.Path(os.environ.get('QW_REPAIR_EVIDENCE_ROOT') or tempfile.mkdtemp(prefix='qw-semantic-tests-'))
H='43c3236655007b39a8b006e3bb6348a9002e243859c340b2fb77230c82df7865';N='d83908cf6558cbfe48787c84fc8ed3cbbcb3578ae44dea375914427177549694'
PATHS={H:f'results/world-birth01/phase1/raw/session/states/{H}.json',N:f'results/world-birth01/phase2/raw/session/states/{N}.json'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class SemanticRepair(unittest.TestCase):
 def setUp(self):
  self.root=OUT/self._testMethodName;self.root.mkdir(parents=True,exist_ok=False);self.s=WorldSession(self.root/'session',P,MANIFEST);self.events=[]
 def tearDown(self):
  (self.root/'input_expected_actual.json').write_text(json.dumps({'test':self._testMethodName,'source_snapshot':MANIFEST['local_base'],'events':self.events},indent=2,allow_nan=False)+'\n')
 def record(self,label,expected,actual,inputs=None):self.events.append({'label':label,'input':inputs or {'H3':PATHS[H],'Ne':PATHS[N]},'expected':expected,'actual':actual})
 def ref(self,n):
  v=self.s.call('reference',relative=PATHS[n]);self.assertNotEqual(v.get('status'),'REJECTED',str(v));return v
 def rejected(self,v,label):
  self.record(label,'REJECTED before scientific qualification',v);self.assertEqual(v['status'],'REJECTED');self.assertNotIn('delta_energy_Eh',v);return v
 def replica(self,name,edit=None,repin=True):
  root=self.root/name;folder='results/world-birth01/phase1';shutil.copytree(P/folder,root/folder)
  for rel in ['birth01/FROZEN_PREREGISTRATION.json','birth01/EXECUTION_SOURCE_SHA256.json']:
   p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(P/rel,p)
  files={str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()}
  if edit:edit(root)
  if repin:files={str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()}
  m={'local_base':MANIFEST['local_base'],'files':files,'fixture':'INTENTIONALLY_DAMAGED_ARCHIVE_TEST_ONLY_NOT_A_NEW_SCIENTIFIC_RESULT'}
  return WorldSession(self.root/(name+'_session'),root,m)
 def test_T01_H3_real_new_observation(self):
  self.ref(H);o=self.s.call('observe',ident=H,requested=['energy','forces']);self.record('actual H3 replay',{'kind':'NEW_SCIENTIFIC_EXECUTION','energy_Eh':-1.2849928193828906,'forces_shape':[3,3]},o)
  self.assertEqual(o['status'],'SCIENTIFIC_OBSERVATION_READ');self.assertEqual(o['source_execution_kind'],'NEW_SCIENTIFIC_EXECUTION');self.assertTrue(o['values']['SCF_converged']);self.assertEqual(o['observables']['energy']['value'],-1.2849928193828906);self.assertEqual(len(o['observables']['forces']['value']),3)
 def test_T02_Ne_real_new_observation(self):
  self.ref(N);o=self.s.call('observe',ident=N,requested=['energy']);self.record('actual Ne replay',{'energy':-128.7524560633064,'unit':'Eh/cell','SCF':True},o)
  self.assertEqual(o['status'],'SCIENTIFIC_OBSERVATION_READ');self.assertTrue(o['values']['SCF_converged']);self.assertEqual(o['observables']['energy']['value'],-128.7524560633064);self.assertEqual(o['observables']['energy']['unit'],'Eh/cell');self.assertNotIn('forces',o['observables'])
 def test_T03_no_native_call_on_read(self):
  self.ref(H);self.ref(N)
  with patch('subprocess.Popen',side_effect=AssertionError('forbidden physical process')):
   values=[self.s.call('observe',ident=x) for x in (H,N)]
  self.record('read only',{'new_calls':0},values)
  self.assertTrue(all(o['new_physics_run'] is False and o['new_scientific_executions']==0 for o in values))
 def test_T04_missing_force_and_stress(self):
  self.ref(N)
  for key,reason in [('forces','FORCE_NOT_AVAILABLE'),('stress','STRESS_NOT_AVAILABLE')]:
   v=self.rejected(self.s.call('observe',ident=N,requested=[key]),key);self.assertEqual(v['reason_code'],reason)
 def test_T05_cross_domain_physical_incompatibility(self):
  self.ref(H);self.ref(N);v=self.rejected(self.s.call('compare',a=H,b=N),'physics mismatch');self.assertEqual(v['reason_code'],'INCOMPARABLE')
 def test_T06_real_new_provenance_not_synthetic(self):
  for n in (H,N):
   v=self.ref(n);self.record('new source classification',{'real':True},v['source_execution']);self.assertTrue(v['source_execution']['real_calculated']);self.assertNotEqual(v['provenance']['mode'],'SYNTHETIC')
 def test_T07_synthetic_stays_software_only(self):
  spec=json.loads((P/PATHS[H]).read_text())['payload']['world_spec'];v=self.s.create(spec,synthetic=True);o=self.s.observe(v['source_state_hash']);self.record('fixture','SOFTWARE_FIXTURE_ONLY',o)
  self.assertEqual(o['status'],'SOFTWARE_FIXTURE_ONLY');self.assertFalse(v['source_execution']['real_calculated']);self.rejected(self.s.call('compare',a=v['source_state_hash'],b=v['source_state_hash']),'fixture cannot compare as real')
 def test_T08_mode_spoofing_not_a_trust_gate(self):
  spec=json.loads((P/PATHS[H]).read_text())['payload']['world_spec'];v=self.s.create(spec,synthetic=True);n=v['source_state_hash'];p=self.s.root/'references'/f'{n}.json';x=json.loads(p.read_text());x['mode']='NEW_SCIENTIFIC_EXECUTION';p.write_text(json.dumps(x))
  self.rejected(self.s.call('observe',ident=n),'synthetic mode promoted to real')
  # A real-state label cannot be silently downgraded to bypass new evidence checks.
  self.ref(H);p=self.s.root/'references'/f'{H}.json';x=json.loads(p.read_text());x['mode']='HISTORICAL_REPLAY';p.write_text(json.dumps(x));self.rejected(self.s.call('observe',ident=H),'mode downgrade')
 def test_T09_state_observation_receipt_corruption(self):
  for field in ['state','observation','receipt']:
   def mutate(root):
    base=root/'results/world-birth01/phase1/raw/session'
    if field in ('state','observation'):
     p=base/'states'/f'{H}.json';x=json.loads(p.read_text());x['payload']['observation']['observation']['energy']+=1;p.write_text(json.dumps(x))
    else:
     p=next((base/'transitions').glob('*/receipt.json'));x=json.loads(p.read_text());x['result_sha256']='0'*64;p.write_text(json.dumps(x))
   s=self.replica(field,mutate,repin=False);self.rejected(s.call('reference',relative=PATHS[H]),field+' tamper after pin')
 def test_T10_missing_execution_records_no_fallback(self):
  targets=['references/'+H+'.json','birth/intents/*.json','birth/attempts/*/authorization.json','birth/resource_admission/*.json','transitions/*/receipt.json','transitions/*/solver/process_receipt.json','transitions/*/solver/observation.json']
  for i,pattern in enumerate(targets):
   def remove(root):
    base=root/'results/world-birth01/phase1/raw/session'
    for p in base.glob(pattern):p.unlink()
   s=self.replica('missing'+str(i),remove);self.rejected(s.call('reference',relative=PATHS[H]),'missing '+pattern)
 def test_T11_wrong_source_and_parent(self):
  self.ref(H);p=self.s.root/'references'/f'{H}.json';v=json.loads(p.read_text());v['source_file']=PATHS[N];p.write_text(json.dumps(v));self.rejected(self.s.call('observe',ident=H),'wrong source pointer')
  def parent_mismatch(root):
   base=root/'results/world-birth01/phase1/raw/session'
   for p in list((base/'birth/physical_returns').glob('*.json'))+list((base/'birth/attempts').glob('*/return.json')):
    v=json.loads(p.read_text());v['parent_context_hash']='0'*64;p.write_text(json.dumps(v))
  s=self.replica('self_consistent_hashes_wrong_parent',parent_mismatch);v=self.rejected(s.call('reference',relative=PATHS[H]),'pinned damaged package with wrong parent');self.assertIn('CONTEXT_PARENT_MISMATCH',v.get('detail',''))
 def test_T12_historical_calculation_replay(self):
  f=next(f for f in MANIFEST['files'] if '/world/transitions/' in f and f.endswith('/receipt.json'));v=self.s.call('replay',relative=f);self.record('legacy transition','HISTORICAL_REPLAY_VALIDATED',v);self.assertEqual(v['status'],'HISTORICAL_REPLAY_VALIDATED')
 def test_T13_three_state_kinds_preserved(self):
  for k in ['QW_PHYSICAL_STATE_01','QW_EFFECTIVE_QUANTUM_STATE_01','QW_CORRELATED_ELECTRONIC_STATE_01']:
   f=next(f for f in MANIFEST['files'] if '/world/states/' in f and f.endswith('.json') and json.loads((P/f).read_text())['payload']['schema']==k and (json.loads((P/f).read_text())['payload'].get('observation') or {}).get('status') in ('CALCULATED','CALCULATED_EFFECTIVE_MODEL'))
   v=self.s.reference(f);o=self.s.observe(v['source_state_hash']);self.record(k,'HISTORICAL_OBSERVATION_READ',o);self.assertEqual(o['status'],'HISTORICAL_OBSERVATION_READ')
 def fci(self):
  f=next(f for f in MANIFEST['files'] if '/world/states/' in f and f.endswith('.json') and json.loads((P/f).read_text())['payload']['schema']=='QW_CORRELATED_ELECTRONIC_STATE_01');return self.s.reference(f)['source_state_hash']
 def test_T14_FCI_to_two_state_still_forbidden(self):
  h=self.fci();v=self.rejected(self.s.call('translate',ident=h,target='QW_EFFECTIVE_QUANTUM_STATE_01'),'illegal CI projection');self.assertEqual(v['reason_code'],'TRANSLATION_FORBIDDEN')
 def test_T15_same_family_not_W2(self):
  h=self.fci();v=self.rejected(self.s.call('compare',a=h,b=h,contract={'kind':'RHF_FCI_SAME_STATE','independent_W2':True}),'same family');self.assertEqual(v['reason_code'],'INDEPENDENCE_INSUFFICIENT')
 def test_T16_legal_new_and_historical_comparisons(self):
  self.ref(H);v=self.s.call('compare',a=H,b=H,contract={'kind':'SAME_MODEL_IDENTITY'});self.record('new real same-state comparison',{'delta':0},v);self.assertEqual(v['result']['delta_energy_Eh'],0)
  fs=[]
  for f in MANIFEST['files']:
   if '/world/states/' in f and f.endswith('.json'):
    q=json.loads((P/f).read_text())
    if q['payload']['schema']=='QW_CORRELATED_ELECTRONIC_STATE_01' and q['sha256'] not in [i[0] for i in fs]:fs.append((q['sha256'],f))
  a=self.s.reference(fs[0][1])['source_state_hash'];b=self.s.reference(fs[1][1])['source_state_hash'];v=self.s.call('compare',a=a,b=b,contract={'kind':'SAME_MODEL_GEOMETRY_PATH'});self.record('two actual historical geometries','valid finite-model delta only',v);self.assertEqual(v['status'],'COMPARISON_VALIDATED');self.assertNotEqual(v['result']['delta_energy_Eh'],0)
 def test_T17_uncalculated_stays_not_calculated(self):
  spec=json.loads((P/PATHS[H]).read_text())['payload']['world_spec'];v=self.s.create(spec);o=self.s.observe(v['source_state_hash']);self.record('structure creation','STRUCTURE_ONLY_NOT_CALCULATED',o);self.assertEqual(o['status'],'STRUCTURE_ONLY_NOT_CALCULATED');self.assertFalse(v['source_execution']['real_calculated'])
 def test_T18_session_history_failure_STOP_traceable(self):
  self.ref(H);self.ref(N);h=self.fci();failure=self.s.preserve_failure(h,'SOFTWARE_TEST_ONLY',{'not_a_new_physical_failure':True});p=self.s.root/'session_receipts'/f"{failure['receipt_sha256']}.json";before=p.read_bytes()
  originals=['FOUNDATION02_REPORT.json','results/world-birth01/FINAL_AI_STOP_DECISION.json','results/world-birth01/EXECUTION_RECEIPT.json'];old={x:sha(P/x) for x in originals};self.s.stop('Offline replay test only; no scientific execution')
  o=self.s.observe(H);self.assertEqual(o['status'],'SCIENTIFIC_OBSERVATION_READ');self.assertEqual(p.read_bytes(),before);self.assertTrue(all(sha(P/x)==v for x,v in old.items()));self.record('preserved source history and readonly after STOP',old,{'preserved':True,'read_status':o['status'],'failure_receipt':failure,'current_STOP':json.loads((self.s.root/'STOP.json').read_text())})
 def test_T19_read_receipt_never_execution_receipt(self):
  self.ref(H);o=self.s.observe(H);p=self.s.root/'session_receipts'/f"{o['read_receipt_sha256']}.json";v=json.loads(p.read_text());self.record('source/current operation separation',{'source_kind':'NEW_SCIENTIFIC_EXECUTION','new_calls':0},v)
  self.assertFalse(v['new_scientific_execution']);self.assertEqual(v['new_scientific_executions'],0);self.assertEqual(v['operation_kind'],'READ_ONLY')
  with self.assertRaisesRegex(WorldError,'READONLY_RECEIPT_CANNOT_CLAIM_EXECUTION'):self.s.receipt('observe','PASS','bad',new_scientific_execution=True)
 def test_T20_original_input_expected_actual_records_retained(self):
  records=list(OUT.glob('test_T*/input_expected_actual.json'));self.record('persisted test IO','at least19 prior T records',{'count':len(records),'files':[str(x.relative_to(OUT)) for x in records]});self.assertGreaterEqual(len(records),19)
 def test_U01_units_and_reference_gate(self):
  s=json.loads((P/PATHS[H]).read_text());t=copy.deepcopy(s);t['payload']['observation']['observation']['energy_unit']='eV'
  with self.assertRaises(WorldError) as e:fabric.compare(s,t)
  self.record('synthetic unit-corruption contract probe','unit rejection',{'code':e.exception.code});self.assertEqual(e.exception.code,'INVALID_OBSERVATION_UNITS_OR_REFERENCE')
 def test_U02_trust_anchor_and_manifest_not_mutable(self):
  self.ref(H)
  with self.assertRaises(TypeError):self.s.manifest[PATHS[H]]='0'*64
  p=self.s.root/'source_anchor.json';v=json.loads(p.read_text());v['snapshot_commit']='0'*40;p.write_text(json.dumps(v));self.rejected(self.s.call('observe',ident=H),'trust anchor tampered')
 def test_U03_legacy_live_provenance_can_be_explicitly_bound(self):
  raw=P/'results/world-birth01/phase2/raw/session';dest=self.root/'legacy';shutil.copytree(raw,dest);original=(dest/'references'/f'{N}.json').read_bytes();s=WorldSession(dest,P,MANIFEST)
  v=s.call('observe',ident=N);self.rejected(v,'legacy source not yet bound');s.reference(PATHS[N]);o=s.observe(N);self.assertEqual(o['status'],'SCIENTIFIC_OBSERVATION_READ');self.assertEqual((dest/'references'/f'{N}.json').read_bytes(),original);self.record('explicit source registration preserves original provenance','verified new observation without old bytes rewrite',o)
 def test_U04_bound_authorization_cannot_change_limits(self):
  def change(root):
   base=root/'results/world-birth01/phase1/raw/session';p=next((base/'birth/attempts').glob('*/authorization.json'));v=json.loads(p.read_text());v['limits']['CPU']=2;p.write_text(json.dumps(v))
   q=base/'references'/f'{H}.json';x=json.loads(q.read_text());x['authorization_sha256']=digest(v);q.write_text(json.dumps(x))
  s=self.replica('bad_scope_self_consistent_hashes',change);v=self.rejected(s.call('reference',relative=PATHS[H]),'authority limits outside frozen envelope');self.assertIn('EXECUTION_AUTHORITY_LIMIT_MISMATCH',v.get('detail',''))
 def test_U05_unknown_mode_cannot_become_uncalculated_or_real(self):
  self.ref(H);p=self.s.root/'references'/f'{H}.json';v=json.loads(p.read_text());v['mode']='UNKNOWN';p.write_text(json.dumps(v));self.rejected(self.s.call('observe',ident=H),'unknown mode')
 def test_U06_new_envelope_and_receipt_schemas(self):
  for n in (H,N):
   e=self.ref(n);o=self.s.observe(n);validate('state',e);validate('observation',o);p=self.s.root/'session_receipts'/f"{o['read_receipt_sha256']}.json";validate('receipt',json.loads(p.read_text()));self.record('new real schema consistency','state/observation/receipt valid',{'state':e['schema'],'read_status':o['status'],'new_scientific_executions':o['new_scientific_executions']})
if __name__=='__main__':unittest.main(verbosity=2)
