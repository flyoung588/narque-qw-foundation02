"""Thin live intake over the existing Store/observe/compare. No new physics solver."""
import json,pathlib,hashlib
from router import digest
from interactive01.world import freeze
from world01.session import WorldSession,filehash
from world01.contracts import envelope,WorldError
from .contracts import check_remote_return,require
class LiveWorldSession(WorldSession):
 def __init__(self,*args,broker=None,**kwargs):
  super().__init__(*args,**kwargs);self.broker=broker
 def register_return(self,result,parent):
  if self.broker is None:raise WorldError('LIVE_BROKER_MISSING')
  self.broker.authorize();self.broker.verify_persisted(result);raw=check_remote_return(result['remote_package'],result['spec'],self.broker.grant,result['intent'])
  self.load(parent);state=self.store.create(result['spec'],'AUTHENTICATED_REMOTE_BO_RETURN_IMPORTED_NOT_RECOMPUTED',parent=parent,observation=raw)
  ident=state['sha256'];record={'state_hash':ident,'raw_sha256':filehash(self.root/'states'/f'{ident}.json'),'result':result,'result_hash':digest(result),'current_import_new_computation':False}
  freeze(self.root/'live_intakes'/f'{ident}.json',record)
  return self.load(ident)
 def load(self,ident):
  p=self.root/'live_intakes'/f'{ident}.json'
  if not p.exists():return super().load(ident)
  if self.broker is None:raise WorldError('LIVE_BROKER_MISSING')
  v=json.loads(p.read_text());require(v['state_hash']==ident and v['result_hash']==digest(v['result']),'LIVE_BINDING_CORRUPT')
  require(v['raw_sha256']==filehash(self.root/'states'/f'{ident}.json'),'STATE_HASH_MISMATCH')
  s=self.store.load(ident);self._validate_state(s);r=v['result'];self.broker.verify_persisted(r);require(s['payload']['world_spec']==r['spec'] and s['payload']['observation']==r['observation'],'LIVE_RESULT_STATE_MISMATCH')
  # The record must still match the consumed intent and immutable returned attempt.
  attempt=self.broker.root/'attempts'/r['intent'];require((attempt/'validated_return.json').is_file() and json.loads((attempt/'validated_return.json').read_text())==r,'LIVE_BROKER_RETURN_MISSING')
  check_remote_return(r['remote_package'],r['spec'],self.broker.grant,r['intent'])
  trust={'verified':True,'real_calculated':True,'source_execution_kind':'NEW_SCIENTIFIC_EXECUTION','source_execution_status':'CALCULATED','source_evidence_status':'VERIFIED_AUTHENTICATED_REMOTE_RECORDS','model_qualification':'CALCULATED_MODEL_ONLY_NOT_PHYSICALLY_CERTIFIED','current_operation_new_scientific_executions':0}
  return envelope(s,{'mode':'NEW_SCIENTIFIC_EXECUTION','remote_intent':r['intent'],'raw_byte_sha256':v['raw_sha256'],'source':'Local validated live intake; not an old archive relabel'},trust)
 def reference(self,relative,*args,**kwargs):
  if relative.startswith('live:'):return self.load(relative.split(':',1)[1])
  return super().reference(relative,*args,**kwargs)
 def act(self,request):
  from world01.contracts import OperationRequest
  req=request if isinstance(request,OperationRequest) else OperationRequest(**request)
  if req.action!='MEASURE_OBSERVABLE' or self.broker is None:return super().act(req)
  self._open();env=self.load(req.source_state_hash);state=self.store.load(req.source_state_hash)
  result=self.broker.run(state['payload']['world_spec'],req.parameters['model_decision_hash']);child=self.register_return(result,state['sha256']);return self.observe(child['source_state_hash'])
