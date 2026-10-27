"""Evidence checks, not a new model caller or a cryptographic provider signature."""
import json,pathlib,hashlib
from router import digest
from world01.contracts import WorldError
from .codex_invocation import MODEL,EFFORT

def verify_invocation(call,*,expected_request_hash=None,expected_decision_raw=None):
 call=pathlib.Path(call);r=json.loads((call/'invocation_receipt.json').read_text())
 if r.get('source')!='LIVE_GATEWAY' or r.get('automatic_invocation') is not True:raise WorldError('NONLIVE_OR_MANUAL_RESPONSE_NOT_L1')
 if r.get('status')!='MODEL_RESPONSE_RECEIVED':raise WorldError('MODEL_INVOCATION_NOT_COMPLETED')
 if not r.get('thread_id') or not r.get('turn_id'):raise WorldError('GATEWAY_RESPONSE_IDENTITY_MISSING')
 if r.get('gateway_confirmed_model')!=MODEL or r.get('requested_model')!=MODEL or r.get('effective_effort')!=EFFORT:raise WorldError('MODEL_IDENTITY_MISMATCH')
 if expected_request_hash is not None and r['request_hash']!=expected_request_hash:raise WorldError('INVOCATION_REQUEST_BINDING_MISMATCH')
 contexts=r.get('persisted_turn_context') or []
 if not contexts or any(x.get('model')!=MODEL or x.get('effort')!=EFFORT for x in contexts):raise WorldError('PERSISTED_EFFECTIVE_IDENTITY_MISMATCH')
 thread=json.loads((call/'thread_identity.json').read_text())
 if thread['thread']['id']!=r['thread_id'] or thread['model']!=MODEL or thread['reasoningEffort']!=EFFORT:raise WorldError('THREAD_IDENTITY_MISMATCH')
 raw=(call/'response.txt').read_text()
 if hashlib.sha256(raw.encode()).hexdigest()!=r['raw_response_sha256']:raise WorldError('RESPONSE_HASH_MISMATCH')
 p=call/'gateway_protocol_redacted.json'
 if hashlib.sha256(p.read_bytes()).hexdigest()!=r['transcript_sha256']:raise WorldError('PROTOCOL_HASH_MISMATCH')
 messages=json.loads(p.read_text());starts=[];ends=[];outputs=[]
 for index,m in enumerate(messages):
  x=m['message'];params=x.get('params',{})
  if m['direction']=='request' and x.get('method')=='turn/start':
   if params.get('threadId')!=r['thread_id'] or params.get('model')!=MODEL or params.get('effort')!=EFFORT:raise WorldError('TURN_REQUEST_MODEL_MISMATCH')
   if params.get('responsesapiClientMetadata',{}).get('request_hash')!=r['request_hash']:raise WorldError('TURN_REQUEST_HASH_MISMATCH')
   starts.append(index)
  if m['direction']=='response' and x.get('method')=='item/completed' and params.get('threadId')==r['thread_id'] and params.get('item',{}).get('type')=='agentMessage':outputs.append(params['item']['text'])
  if m['direction']=='response' and x.get('method')=='turn/completed' and params.get('threadId')==r['thread_id'] and params.get('turn',{}).get('id')==r['turn_id'] and params['turn']['status']=='completed':ends.append(index)
 if not starts or not ends or starts[-1]>=ends[-1] or '\n'.join(outputs)!=raw:raise WorldError('NO_MATCHING_AUTOMATIC_MODEL_RETURN')
 body=json.loads(raw)
 if expected_decision_raw is not None and body.get('decision_json',raw)!=expected_decision_raw:raise WorldError('DECISION_NOT_FROM_MODEL_RESPONSE')
 return {'status':'INVOCATION_BOUND_TO_OFFICIAL_GATEWAY_TRACE','gateway_model':MODEL,'effort':EFFORT,'thread_id':r['thread_id'],'turn_id':r['turn_id'],'provider_response_id':r['provider_response_id'],'backend_model':'NOT_SEPARATELY_EXPOSED','local_audit_not_cryptographic_signature':True}
