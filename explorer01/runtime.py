"""Continuous offline Explorer. All action choice comes from submitted model decisions.
No native science dispatcher exists here. A proposal cannot grant itself permission.
"""
import copy,json,pathlib,datetime,hashlib
from router import digest
from world01.contracts import WorldError
from world01 import fabric
from world01.session import publish_bytes
from .contracts import decode
from .memory import Journal,now
ZERO={'new_science_jobs':0,'purchases':0,'external_writes':0}
class ExplorerRuntime:
 def __init__(self,root,world,catalog,goal,*,max_decisions=8,max_reads=12,wall_seconds=3600):
  self.root=pathlib.Path(root);self.world=world;self.j=Journal(self.root);self.catalog=copy.deepcopy(catalog)
  if max_decisions<1 or max_reads<1 or wall_seconds<=0:raise WorldError('INVALID_BUDGET')
  config={'schema':'QW_EXPLORER_SESSION_01','world_session':str(world.root.resolve()),'catalog':self.catalog,'goal':goal,'model_requests_max':max_decisions,'reads_max':max_reads,'wall_seconds':wall_seconds,'resource_envelope':ZERO,'no_live_science_dispatcher':True}
  with self.j.lock():
   es=self.j.events()
   if not es:self.j.append('Started',config)
   elif es[0]['data']!=config:raise WorldError('SESSION_CONFIG_CHANGED','Resume cannot silently increase budget, goal or source access')
   self.j.checkpoint()
  self.id=digest(config);self.recover()
 def recover(self):
  with self.j.lock():
   es=self.j.events()
   # Accepted decisions are write-ahead operations. On interrupted dispatch, never retry.
   done={e['data']['decision_event'] for e in es if e['kind']=='OperationResult'}
   for e in es:
    if e['kind']=='DecisionAccepted' and e['sha256'] not in done:
     self.j.append('OperationResult',{'decision_event':e['sha256'],'status':'INTERRUPTED_NO_REEXECUTION','science_jobs':0})
     if e['data']['decision']['action']=='STOP':self.j.append('Stopped',{'reason':'Recovered already accepted STOP; no automatic successor','automatic_successor':False})
   self.j.checkpoint()
 def _open(self):
  es=self.j.events()
  if any(e['kind']=='Stopped' for e in es):raise WorldError('RESEARCH_STOPPED')
  elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(es[0]['time_utc'])).total_seconds()
  if elapsed>es[0]['data']['wall_seconds']:raise WorldError('RESEARCH_WALL_LIMIT')
  return es
 def _observe(self,ident):
  es=self.j.events();limit=es[0]['data']['reads_max']
  if len([e for e in es if e['kind']=='ReadReserved'])>=limit:raise WorldError('READ_BUDGET_EXHAUSTED')
  if ident not in self.catalog:raise WorldError('STATE_NOT_IN_SEALED_CATALOG')
  self.j.append('ReadReserved',{'state':ident,'science_jobs':0})
  env=self.world.reference(self.catalog[ident]['path'])
  if not env['source_execution']['real_calculated']:raise WorldError('SYNTHETIC_OR_UNCALCULATED_NOT_REAL')
  o=self.world.observe(ident);h=digest(o)
  raw=o['values'].get('original_observation') or {};quality=raw.get('quality',{});native=raw.get('observation',{})
  numerical={'reported_SCF_converged':o['values'].get('SCF_converged',quality.get('RHF_converged')),'reported_FCI_converged':quality.get('FCI_converged'),'raw_numeric_quality':copy.deepcopy(quality),'reported_native_settings':{k:v for k,v in native.items() if k in ('SCF_convergence_threshold_Eh','SCF_max_iterations','numerical_threads','basis','method')},'accuracy':'NOT_INDEPENDENTLY_CERTIFIED','missing_fields':'UNKNOWN_OR_NOT_APPLICABLE; not a failed calculation'}
  self.j.append('PhysicalEvidence',{'hash':h,'observation':o,'state':ident,'domain':o['model_domain'],'evidence_role':'SEALED_HISTORICAL_READ_NOT_NEW_PHYSICS','manifest':fabric.select(self.world.store.load(ident)),'physical_object':env['object'],'physics_model':env['actual_model'],'parent_state':env['parent_state_hash'],'numerical_quality':numerical,'model_limitations':o['error_uncertainty']})
  return o
 def seed(self,ident):
  with self.j.lock():
   es=self._open()
   if any(e['kind']=='PhysicalEvidence' for e in es):raise WorldError('SEED_ALREADY_PRESENT')
   out=self._observe(ident);self.j.checkpoint();return out
 def context(self):
  es=self.j.events();obs=[e['data'] for e in es if e['kind']=='PhysicalEvidence'];negative=[e['data'] for e in es if e['kind'] in ('Rejected','OperationResult','ModelFailure') and e['data'].get('status') not in ('COMPLETED','STOPPED')]
  code={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in pathlib.Path(__file__).parent.glob('*.py')}
  return {'research_session':self.id,'world_session':str(self.world.root.resolve()),'runtime_code_sha256':code,'world_source_anchor':self.world.source_snapshot_commit,'goal':es[0]['data']['goal'],'memory':{'observations':obs,'notes':[e['data'] for e in es if e['kind']=='Memory'],'negative_evidence':negative,'previous_decisions':[e['data']['decision'] for e in es if e['kind']=='DecisionAccepted']},'candidate_catalog':copy.deepcopy(self.catalog),'capabilities':copy.deepcopy(fabric.MANIFESTS),'resources':{'new_science_jobs':0,'purchases':0,'model_requests_remaining':es[0]['data']['model_requests_max']-sum(e['kind']=='ModelRequest' for e in es),'reads_remaining':es[0]['data']['reads_max']-sum(e['kind']=='ReadReserved' for e in es)},'rules':['All observations are already historical, including original NEW_SCIENTIFIC_EXECUTION origins.','No new SCF/FCI/DFT/propagation, no external writes.','Multiple frontier categories and STOP must compete without a scalar ranking.','Only cite observation hashes present in this request.','Same ResearchSession does not imply physical continuity or a legal state conversion.','Use WorldSession comparison/translation contracts; never rank cross-composition absolute energies.','Explicitly answer existing negative evidence and distinguish hypothesis from PhysicalEvidence.','Model may nominate new unknown objects, but no execution authority follows.']}
 def request(self,identity):
  with self.j.lock():
   es=self._open();pending=self.pending()
   if pending:return pending
   if sum(e['kind']=='ModelRequest' for e in es)>=es[0]['data']['model_requests_max']:raise WorldError('MODEL_REQUEST_BUDGET_EXHAUSTED')
   req={'schema':'QW_MODEL_REQUEST_01','model_identity':identity,'context':self.context(),'previous_event':es[-1]['sha256'],'response_schema':'explorer01/decision.schema.json','created_utc':now()};h=digest(req)
   self.j.append('ModelRequest',{'request_hash':h,'request':req,'resource_slot_consumed':True});self.j.checkpoint();return {'hash':h,'request':req}
 def pending(self):
  es=self.j.events();finished={e['data']['request_hash'] for e in es if e['kind'] in ('DecisionAccepted','ModelFailure')}
  for e in reversed(es):
   if e['kind']=='ModelRequest' and e['data']['request_hash'] not in finished:return {'hash':e['data']['request_hash'],'request':e['data']['request']}
 def _validate(self,d,req):
  if d['request_hash']!=req['hash']:raise WorldError('MODEL_REQUEST_BINDING_MISMATCH')
  c=d['candidates'];ids=[x['id'] for x in c]
  if len(set(ids))!=len(ids) or d['selected'] not in ids:raise WorldError('INVALID_CANDIDATE_SELECTION')
  selected=next(x for x in c if x['id']==d['selected'])
  if (selected['kind']=='STOP')!=(d['action']=='STOP'):raise WorldError('SELECTED_STOP_MISMATCH')
  if not any(x['kind']=='STOP' for x in c) or len({x['kind'] for x in c})<2:raise WorldError('FRONTIER_COMPETITION_REQUIRED')
  obs=req['request']['context']['memory']['observations'];known={x['hash'] for x in obs}
  if set(d['observation_refs'])-known:raise WorldError('INVENTED_OBSERVATION')
  if obs and obs[-1]['hash'] not in d['observation_refs']:raise WorldError('LATEST_OBSERVATION_NOT_CONSIDERED')
  if d['negative_evidence_response'].strip().upper() in ('NONE','IGNORE') and req['request']['context']['memory']['negative_evidence']:raise WorldError('NEGATIVE_EVIDENCE_IGNORED')
  for m in d['memory_updates']:
   if set(m['evidence_refs'])-known:raise WorldError('INVENTED_MEMORY_EVIDENCE')
  op=d['operation'];name=op['name']
  if (d['action']=='STOP')!=(name=='STOP'):raise WorldError('STOP_ACTION_MISMATCH')
  if name!='STOP' and op['source'] not in self.catalog:raise WorldError('STATE_NOT_IN_SEALED_CATALOG')
  if name=='OBSERVE' and d['action'] not in ('CONTINUE','CHANGE_OBJECT','CHANGE_MODEL','CHANGE_PHYSICAL_DOMAIN','REQUEST_VALIDATION'):raise WorldError('ACTION_OPERATION_MISMATCH')
  failed=[e['data']['operation'] for e in self.j.events() if e['kind']=='OperationResult' and e['data'].get('status')=='REJECTED' and 'operation' in e['data']]
  if name=='PROPOSE_EXPERIMENT' and any(digest(x)==digest(op) for x in failed):raise WorldError('REPEATED_FAILED_EXPERIMENT_NO_NEW_AUTHORITY')
 def submit(self,raw,*,transport='WORK_FILE_EXCHANGE',provider_record=None):
  with self.j.lock():
   self._open();req=self.pending()
   if not req:raise WorldError('NO_PENDING_MODEL_REQUEST')
   # Store raw output before parse/dispatch. Label transport, never grant model identity by self-report.
   record={'request_hash':req['hash'],'raw_response':raw,'raw_response_sha256':hashlib.sha256(raw.encode()).hexdigest(),'transport':transport,'provider_record':provider_record,'provider_attestation':'UNVERIFIED' if provider_record is None else 'SUPPLIED_NOT_AUTOMATICALLY_TRUSTED','time_utc':now()}
   self.j.append('ModelResponse',record)
   try:d=decode(raw);self._validate(d,req)
   except Exception as e:
    out={'request_hash':req['hash'],'status':'REJECTED','reason_code':getattr(e,'code',type(e).__name__),'detail':str(e)};self.j.append('ModelFailure',out);self.j.checkpoint();return out
   event=self.j.append('DecisionAccepted',{'request_hash':req['hash'],'decision':d,'response_sha256':record['raw_response_sha256'],'physical_execution_permission':False})
   try:out=self._execute(d)
   except Exception as e:out={'status':'REJECTED','reason_code':getattr(e,'code',type(e).__name__),'detail':str(e)}
   out={**out,'decision_event':event['sha256'],'operation':d['operation'],'science_jobs':out.get('new_scientific_executions',0)};self.j.append('OperationResult',out)
   for m in d['memory_updates']:self.j.append('Memory',m)
   self.j.append('Memory',{'kind':'ResearchDecision','content':d['action']+': '+d['resource_reason'],'evidence_refs':d['observation_refs']})
   if d['action']=='STOP':self.j.append('Stopped',{'reason':d['resource_reason'],'automatic_successor':False})
   self.j.checkpoint();return out
 def _execute(self,d):
  op=d['operation'];s=op['source'];q=op['parameters'];name=op['name']
  if name=='STOP':return {'status':'STOPPED','no_new_science':True}
  if name=='OBSERVE':return {'status':'COMPLETED','observation_hash':digest(self._observe(s))}
  self.world.reference(self.catalog[s]['path'])
  if name=='PROPOSE_EXPERIMENT':
   state=self.world.store.load(s)
   if 'world_spec' in q:
    proposal=copy.deepcopy(state);proposal['payload']['world_spec']=q['world_spec'];fabric.select(proposal)
   fabric.admit(state,q.get('action','MEASURE_OBSERVABLE'),q.get('observables',()),execute=False)
   raise WorldError('RESOURCE_ADMISSION_REQUIRED','Research freedom is not a science Job grant;0 authorized Jobs')
  if name=='FORK':return {'status':'COMPLETED','result':self.world.fork(s,q.get('reason',d['resource_reason']))}
  if name=='TRANSLATE':return {'status':'COMPLETED','result':self.world.translate(s,q['target'])}
  if name=='COMPARE':
   if op['other'] not in self.catalog:raise WorldError('STATE_NOT_IN_SEALED_CATALOG')
   self.world.reference(self.catalog[op['other']]['path']);return {'status':'COMPLETED','result':self.world.compare(s,op['other'],q.get('contract'))}
  raise WorldError('UNSUPPORTED_OPERATION')
 def run_one(self,adapter,identity):
  req=self.request(identity)
  try:raw=adapter.decide(req['request'])
  except WorldError as e:
   if e.code=='MODEL_RESPONSE_PENDING':return {'status':e.code,'request_hash':req['hash']}
   with self.j.lock():self.j.append('ModelFailure',{'request_hash':req['hash'],'status':'MODEL_TRANSPORT_FAILED','reason_code':e.code});self.j.checkpoint()
   return {'status':'MODEL_TRANSPORT_FAILED','reason_code':e.code}
  return self.submit(raw,transport=type(adapter).__name__,provider_record=getattr(adapter,'last_receipt',None))
 def run(self,adapter,identity,*,max_steps=8):
  """Route-neutral scheduler; decision content is obtained anew after each observation."""
  outcomes=[]
  for _ in range(max_steps):
   try:out=self.run_one(adapter,identity)
   except WorldError as e:
    outcomes.append({'status':'HALTED','reason_code':e.code});break
   outcomes.append(out)
   if out['status'] in ('STOPPED','MODEL_RESPONSE_PENDING','MODEL_TRANSPORT_FAILED'):break
  return outcomes
