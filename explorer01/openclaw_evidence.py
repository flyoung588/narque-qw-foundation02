"""Verify real OpenClaw records as OpenClaw, never synthesize Codex protocol.
Pins must come from the independently approved science grant, not this module.
This is local source-bound evidence verification, not provider signature proof.
"""
import json,pathlib,hashlib,copy
from world01.contracts import WorldError
CONTRACT='OPENCLAW_AGENT_E03R_V1'
def require(ok,code):
 if not ok:raise WorldError(code)
def filehash(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def context_hash(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def verify_openclaw(folder,pins,expected_intent,*,bindings=None,grant_sha256=None):
 folder=pathlib.Path(folder);required={'request.json','request_binding.json','response.json'}
 require(set(pins)==required,'OPENCLAW_EXACT_RECORD_PINS_REQUIRED')
 for name in required:require(filehash(folder/name)==pins[name],'OPENCLAW_RECORD_HASH_MISMATCH')
 q=json.loads((folder/'request.json').read_text());b=json.loads((folder/'request_binding.json').read_text());r=json.loads((folder/'response.json').read_text());m=r['result']['meta'];a=m['agentMeta'];context=json.loads(q['message'])
 require(q['model']=='gpt-6.1-sol' and q['thinking']=='low' and q['provider']=='openai' and q['modelRun'] is True and q['promptMode']=='none','OPENCLAW_REQUEST_IDENTITY_MISMATCH')
 require(a['model']=='gpt-6.1-sol' and a['provider']=='openai' and m['requestShaping']['thinking']=='low' and m['executionTrace']['fallbackUsed'] is False,'OPENCLAW_EFFECTIVE_IDENTITY_MISMATCH')
 require(bool(r['runId']) and bool(a['sessionId']) and m.get('aborted') is False,'OPENCLAW_RESPONSE_NOT_COMPLETED')
 require(context_hash(context)==b['context_hash']==b['native_request']['context_manifest_ref'],'OPENCLAW_CONTEXT_BINDING_MISMATCH')
 text=r['result']['payloads'][0]['text'];text=text.removeprefix('```json\n').removesuffix('\n```');decision=json.loads(text)
 require(decision['decision']=='PROPOSE','OPENCLAW_NO_PHYSICAL_PROPOSAL')
 intent=copy.deepcopy(decision['intent']);intent['model_request_hash']=b['context_hash']
 # Grant-bound administrative rebinding only. Scientific operation, prediction,
 # source-state and observables are immutable model output.
 for key,change in (bindings or {}).items():
  require(key in {'research_session','world_session','authorization_ref','experiment_ref'},'OPENCLAW_SCIENTIFIC_REWRITE_FORBIDDEN')
  require(set(change)=={'from','to'} and intent.get(key)==change['from'],'OPENCLAW_BINDING_SOURCE_MISMATCH')
  target=change['to']
  if key=='authorization_ref' and target=='CURRENT_GRANT_SHA256':
   require(isinstance(grant_sha256,str) and len(grant_sha256)==64,'OPENCLAW_GRANT_HASH_REQUIRED');target=grant_sha256
  intent[key]=target
 require(intent==expected_intent,'OPENCLAW_MODEL_INTENT_MISMATCH')
 return {'status':'SOURCE_BOUND_OPENCLAW_EVIDENCE_VERIFIED','contract':CONTRACT,'request_hash':b['context_hash'],'run_id':r['runId'],'effective_session_id':a['sessionId'],'requested_session_id':q['sessionId'],'model':a['model'],'effort':m['requestShaping']['thinking'],'usage':a['usage'],'decision_original':decision,'source':'OPENCLAW_AGENT_RAW_RECORDS_NOT_CODEX','cryptographic_provider_attestation':'NOT_AVAILABLE','local_grant_pin_required':True}
