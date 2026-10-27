"""T01..T15: real failed bytes + transparent software fixtures, no model or solver."""
import json,copy,pathlib,types,hashlib
from unittest.mock import patch
from jsonschema import Draft202012Validator
from explorer01.contracts import decode,SCHEMA
from explorer01.runtime import ExplorerRuntime
from explorer01.codex_invocation import InvocationBudget
from world01.contracts import WorldError
from router import digest
from .test_integration import Integration,EX,MAN,P,fixture
from .decision_contract import decode_with_audit,check_relations,WIRE_SCHEMA,unwrap_wire
from .runtime import FabricExplorer
R=P.parent
class RepairTests(Integration):
 def d(self,r,name='STOP',action='STOP'):
  q=r.request({'model':'SYNTHETIC_ENGINEERING_NOT_REAL_MODEL'});d=fixture(q,source=EX['molecular']['input_state'],name=name,action=action)
  if name=='STOP':d['selected']='stop'
  return q,d
 def test_T01_reproduce_three_original_rejections(self):
  old=R.parent/'QW-LIVE-FABRIC01-LIVE-E01-20261027';es=[json.loads(p.read_text()) for p in sorted((R/'evidence/old_research_session/events').glob('*.json'))]
  class FrozenJournal:
   def events(self):return es
   def query(self,k):return [e for e in es if e['kind']==k]
  fake=types.SimpleNamespace(catalog=es[0]['data']['catalog'],j=FrozenJournal());requests={e['data']['request_hash']:e['data']['request'] for e in es if e['kind']=='ModelRequest'};results=[]
  for n,reason in [(2,'INVALID_CANDIDATE_SELECTION'),(3,'SELECTED_STOP_MISMATCH'),(4,'SELECTED_STOP_MISMATCH')]:
   raw=json.loads((R/f'evidence/old_failures/call{n:02d}/response.txt').read_text())['decision_json'];d=decode(raw)
   with self.assertRaises(WorldError) as e:ExplorerRuntime._validate(fake,d,{'hash':d['request_hash'],'request':requests[d['request_hash']]})
   self.assertEqual(e.exception.code,reason)
   try:new,audit=decode_with_audit(raw);result={'status':'FORMAT_ONLY_SAFE_COMPATIBILITY','selected':new['selected'],'changes':audit['changes']}
   except WorldError as e:result={'status':'REJECTED','reason':e.code,'detail':e.detail}
   results.append({'call':n,'old_rejection_reproduced':reason,'new_offline_classification':result,'old_verdict_changed':False,'science':0})
  self.assertEqual(results[0]['new_offline_classification']['reason'],'SELECTED_CANDIDATE_NOT_REGISTERED');self.assertEqual(results[1]['new_offline_classification']['reason'],'STOP_SELECTION_ROLE_CONFLICT');self.assertEqual(results[2]['new_offline_classification']['status'],'FORMAT_ONLY_SAFE_COMPATIBILITY')
  (self.root/'ORIGINAL_FAILURE_REPLAY.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
 def test_T02_valid_stop_executes(self):
  r=self.make_runtime();q,d=self.d(r);out=r.submit(json.dumps(d),transport='SYNTHETIC_REPAIR_QA');self.assertEqual(out['status'],'STOPPED');self.assertEqual(len(r.j.query('Stopped')),1);self.assertFalse(self.b.j.query('ExecutionReserved'))
 def test_T03_selected_id_and_uniqueness(self):
  r=self.make_runtime();q,d=self.d(r);d['selected']='unknown';self.reject('SELECTED_CANDIDATE_NOT_REGISTERED',lambda:decode_with_audit(json.dumps(d)))
  d['selected']='stop';d['candidates'][0]['id']='stop';self.reject('CANDIDATE_IDS_NOT_UNIQUE',lambda:decode_with_audit(json.dumps(d)))
 def test_T04_stop_role_consistency(self):
  r=self.make_runtime();q,d=self.d(r);d['candidates'][1]['kind']='RESEARCH';self.reject('STOP_SELECTION_ROLE_CONFLICT',lambda:decode_with_audit(json.dumps(d)))
  d['candidates'][1]['kind']='STOP';d['action']='CONTINUE';d['operation']['name']='OBSERVE';self.reject('STOP_SELECTION_ROLE_CONFLICT',lambda:decode_with_audit(json.dumps(d)))
 def test_T05_action_operation_consistency(self):
  r=self.make_runtime();q,d=self.d(r);d['operation']['name']='OBSERVE';self.reject('ACTION_OPERATION_STOP_CONFLICT',lambda:decode_with_audit(json.dumps(d)))
  d['operation']['name']='STOP';d['operation']['parameters']={'intent':{'unauthorized':'payload'}};self.reject('STOP_CONTAINS_NONSTOP_PAYLOAD',lambda:decode_with_audit(json.dumps(d)))
 def test_T06_legal_proposal_remains_routable(self):
  r=self.make_runtime();q,d=self.d(r,name='PROPOSE_EXPERIMENT',action='CONTINUE');from .catalog import replay_intent
  d['operation']['parameters']={'intent':replay_intent(EX['molecular'],'molecular',self.w,r.id)}
  normalized,audit=decode_with_audit(json.dumps(d));self.assertEqual(normalized,d);out=r.submit(json.dumps(d),transport='SYNTHETIC_REPAIR_QA');self.assertEqual(out['status'],'COMPLETED');self.assertEqual(out['new_scientific_executions'],0)
  # Direct wire uses a closed physical Intent shape, not a string escape hatch.
  direct=copy.deepcopy(d);direct['candidates'][0]['kind']='RESEARCH';i=direct['operation']['parameters']['intent'];i.pop('receipt_path');i['mode']='NEW_SCIENTIFIC_EXECUTION';i['experiment_ref']='SYNTHETIC_PREREGISTRATION_REFERENCE';Draft202012Validator(WIRE_SCHEMA).validate(direct)
  self.assertEqual(unwrap_wire(json.dumps(direct),'DIRECT_OBJECT'),json.dumps(direct))
  from interactive01.world import apply
  self.assertEqual(apply(self.w.store.load(direct['operation']['source']),i['operation']),EX['molecular']['world_spec'])
 def test_T07_normalization_cannot_change_science(self):
  original=json.loads((R/'evidence/old_failures/call04/response.txt').read_text())['decision_json'];d=json.loads(original);n,a=decode_with_audit(original);expected=copy.deepcopy(d);next(c for c in expected['candidates'] if c['id']==d['selected'])['kind']='STOP';self.assertEqual(n,expected);self.assertTrue(all(a[k] for k in ('selected_unchanged','action_unchanged','operation_unchanged','prediction_unchanged','falsifier_unchanged')));self.assertEqual(json.loads(original),d)
 def test_T08_ambiguity_not_guessed(self):
  r=self.make_runtime();q,d=self.d(r);d['candidates'][1]['kind']='continue or stop depending on unstated conditions';self.reject('AMBIGUOUS_STOP_CANDIDATE_ROLE',lambda:decode_with_audit(json.dumps(d)))
 def test_T09_missing_fields_rejected(self):
  r=self.make_runtime();q,d=self.d(r);del d['prediction'];out=r.submit(json.dumps(d));self.assertEqual(out['status'],'REJECTED');self.assertFalse(r.j.query('DecisionAccepted'));self.assertFalse(self.b.j.query('ExecutionReserved'))
 def test_T10_forged_observation_rejected(self):
  r=self.make_runtime();q,d=self.d(r);d['observation_refs']=['0'*64];out=r.submit(json.dumps(d));self.assertEqual(out['reason_code'],'INVENTED_OBSERVATION')
 def test_T11_unauthorized_science_rejected(self):
  r=self.make_runtime();q,d=self.d(r,name='PROPOSE_EXPERIMENT',action='CONTINUE');from .catalog import replay_intent
  i=replay_intent(EX['molecular'],'molecular',self.w,r.id);i['mode']='NEW_SCIENTIFIC_EXECUTION';d['operation']['parameters']={'intent':i};out=r.submit(json.dumps(d));self.assertEqual(out['reason_code'],'NEW_SCIENCE_NOT_AUTHORIZED');self.assertFalse(self.b.j.query('ExecutionReserved'))
 def test_T12_self_granted_resources_and_budget(self):
  i=self.intent();i.update(mode='NEW_SCIENTIFIC_EXECUTION',AUTHORIZED=True,resource_ref='MODEL_SAYS_UNLIMITED');self.reject('NEW_SCIENCE_NOT_AUTHORIZED',lambda:self.b.execute(i))
  b=InvocationBudget(self.root/'synthetic_model_budget',2);b.reserve('a'*64,'SOFTWARE_IDENTITY_FIXTURE');cat={x['input_state']:{'path':x['source_path'],'domain':d} for d,x in EX.items()};r=FabricExplorer(self.root/'budget_research',self.w,cat,'SOFTWARE BUDGET TEST',execution=self.b,model_budget=b,max_decisions=2)
  self.assertEqual(r.context()['resources']['model_requests_remaining'],1);b.reserve('b'*64,'SOFTWARE_DECISION_FIXTURE');before=len(r.j.query('ModelRequest'));self.reject('MODEL_CALL_BUDGET_EXHAUSTED_BEFORE_REQUEST',lambda:r.request({}));self.assertEqual(len(r.j.query('ModelRequest')),before)
 def test_T13_stop_prevents_later_execution(self):
  r=self.make_runtime();q,d=self.d(r);r.submit(json.dumps(d));self.reject('RESEARCH_STOPPED',lambda:r.request({}));self.assertFalse(self.b.j.query('ExecutionReserved'))
 def test_T14_old_response_hashes_unchanged(self):
  root=json.loads((R/'LIVE_E01R_ACTUAL_FAILURE_ROOT_CAUSE.json').read_text())
  for row in root['failures']:
   src=pathlib.Path(row['original_paths']['response']).parent
   if not src.exists():src=R/'evidence/old_failures'/row['call']
   for name,h in row['sha256'].items():self.assertEqual(hashlib.sha256((src/name).read_bytes()).hexdigest(),h)
 def test_T15_existing_semantics_and_clarification_bound(self):
  self.run_domain('molecular');self.run_domain('correlated');self.reject('INCOMPARABLE',lambda:self.w.compare(EX['molecular']['target_state'],EX['correlated']['target_state']));self.reject('TRANSLATION_FORBIDDEN',lambda:self.w.translate(EX['correlated']['target_state'],'QW_EFFECTIVE_QUANTUM_STATE_01'))
  r=self.make_runtime()
  for _ in range(2):
   q,d=self.d(r);d['selected']='not-in-catalog';out=r.submit(json.dumps(d));self.assertEqual(out['reason_code'],'SELECTED_CANDIDATE_NOT_REGISTERED')
  self.reject('DECISION_CLARIFICATION_LIMIT',lambda:r.request({}));self.assertFalse(r.j.query('DecisionAccepted'))
 def test_T16_adapter_direct_and_explicit_wrapper_no_real_model(self):
  from .model_adapter import FabricModelAdapter
  from .decision_contract import WRAPPED_SCHEMA
  from world01.session import filehash
  r=self.make_runtime();q,d=self.d(r);d['candidates'][0]['kind']='RESEARCH';raw=json.dumps(d)
  class FakeGateway:
   last_receipt={'transcript_path':str(self.root/'MOCK_NOT_REAL/transcript.json')}
   def invoke(inner,thread,prompt,schema,**kwargs):
    inner.record={'prompt':prompt,'schema':schema,'metadata':kwargs};return raw if schema==WIRE_SCHEMA else json.dumps({'decision_json':raw})
  for mode,expected in [('DIRECT_OBJECT',WIRE_SCHEMA),('WRAPPED_COMPAT',WRAPPED_SCHEMA)]:
   a={'scope':'QW-LIVE-FABRIC-01','release':'LIVE-E01R','status':'HUMAN_GRANTED_MODEL_TRANSFER','source_sha256':'SOFTWARE_ONLY','model':'gpt-6.1-sol','effort':'low','max_calls':6,'new_purchases':0,'context_fields':list(q['request']['context']),'wire_mode':mode,'output_schema_sha256':digest(expected)}
   p=self.root/(mode+'.json');p.write_text(json.dumps(a));g=FakeGateway();adapter=FabricModelAdapter(g,{},p,filehash(p),'SOFTWARE_ONLY',r)
   with patch('live_fabric01.model_adapter.verify_invocation',return_value={'fixture':'NO_REAL_IDENTITY_ATTESTATION'}):out=adapter.decide(q['request'])
   self.assertEqual(out,raw);self.assertEqual(g.record['schema'],expected);self.assertNotIn('Choose competing scientifically meaningful candidates and STOP.',g.record['prompt']);self.assertIn('selected is exactly one existing candidate.id',g.record['prompt'])
   self.assertEqual(r.j.query('OutboundPreflight')[-1]['data']['actual_output_schema_sha256'],digest(expected))
 def test_T17_current_gate_denies_before_any_gateway(self):
  from .controller import run
  with patch('subprocess.Popen',side_effect=AssertionError('No new model process')):self.reject('LIVE_SCIENCE_GRANT_REQUIRED',lambda:run(self.root,'0'*64,'0'*64))
