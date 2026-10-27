import copy,json,pathlib,hashlib
from router import digest
from world01.contracts import WorldError
from explorer01.runtime import ExplorerRuntime
from explorer01.memory import now
from explorer01.l1_adapter import assessments_check
from explorer01.l1_audit import verify_invocation
from .contracts import decode,require,STATES,RECOVERY,gap

def recovery_reference_index(ctx):
 """References have explicit roles. Catalog/provenance never become observations."""
 index={}
 def add(ref,kind):
  if isinstance(ref,str):index.setdefault(ref,[]).append(kind)
 add(digest(ctx['initial_gap']),'ADMISSION_GAP')
 for ref in ctx['initial_gap']['Evidence References']:add(ref,'SOURCE_PROVENANCE')
 for ref in ctx['candidate_catalog']:add(ref,'CATALOG_DESCRIPTOR_NOT_OBSERVED')
 for row in ctx['memory']['observations']:add(row['hash'],'HISTORICAL_OBSERVATION')
 for row in ctx.get('negative_feedback',[]):
  if 'request_hash' in row:add(row['request_hash'],'FAILED_REQUEST')
  add(digest(row),'ADMISSION_FEEDBACK')
 return {ref:sorted(set(kinds)) for ref,kinds in index.items()}
def bind_recovery_references(ctx):
 ctx['gap_evidence_ref']=digest(ctx['initial_gap']);ctx['reference_index']=recovery_reference_index(ctx);return ctx

class RecoveryRuntime(ExplorerRuntime):
 """A research-control extension, not another physical store, solver or strategic owner."""
 def __init__(self,root,world,catalog,goal,*,initial_gap,max_decisions=3,evidence_pack=None):
  super().__init__(root,world,catalog,goal,max_decisions=max_decisions,max_reads=4,wall_seconds=1800)
  with self.j.lock():
   es=self.j.events();seeds=[x for x in es if x['kind']=='RecoverySeed']
   if seeds:
    require(seeds[0]['data']['gap']==initial_gap,'GAP_CONFIG_CHANGED');require(seeds[0]['data'].get('evidence_pack')==evidence_pack,'EVIDENCE_PACK_CHANGED')
   else:self.j.append('RecoverySeed',{'gap':initial_gap,'evidence_pack':evidence_pack,'candidate_state':'PARKED','frontier_state':'ACTIVE','mission_state':'ACTIVE','states_are':'Local research scheduling only; no Human strategic state change'})
   # A previously reserved model turn is never silently repeated after a crash.
   es=self.j.events();finished={x['data']['request_hash'] for x in es if x['kind'] in ('RecoveryAccepted','RecoveryRejected','RecoveryTransportFailure')}
   for x in es:
    if x['kind']=='RecoveryRequest' and x['data']['request_hash'] not in finished:
     self.j.append('RecoveryTransportFailure',{'request_hash':x['data']['request_hash'],'status':'INTERRUPTED_NO_RETRY'})
     self.j.append('Dormant',{'reason':'INTERRUPTED_MODEL_REQUEST_NO_RETRY'})
   self.j.checkpoint()
 def snapshot(self):
  es=self.j.events();seed=self.j.query('RecoverySeed')[0]['data'];c={seed['gap']['Candidate ID']:{'status':'PARKED','question':seed['gap']['Physical Question'],'scientific_truth':'UNRESOLVED_NOT_REJECTED'}};frontier='ACTIVE';mission='ACTIVE';portfolio={};decisions=[]
  for e in es:
   if e['kind']=='RecoveryAccepted':
    d=e['data']['decision'];decisions.append(d)
    for x in d['candidates']:c.setdefault(x['id'],{'status':'ACTIVE','question':x['question'],'scientific_truth':'UNRESOLVED','proposal':x})
    for u in d['candidate_updates']:c[u['id']].update(status=u['status'],reason=u['reason'])
    frontier=d['frontier_state'];mission=d['mission_state']
    for p in d['expansions']:portfolio[p['id']]=p
   if e['kind']=='CandidateBlocked' and e['data']['candidate'] in c:c[e['data']['candidate']].update(status='PARKED',reason=e['data']['reason'])
   if e['kind']=='Stopped':frontier='STOPPED'
   if e['kind']=='Dormant':frontier='DORMANT';mission='DORMANT'
  executable=[{'candidate':v,'admission':'OFFLINE_READ_AVAILABLE' if v['proposal']['mode']=='OFFLINE_READ' else 'AWAITING_AUTHORITY','science_jobs':0} for v in c.values() if v.get('proposal',{}).get('mode') in ('OFFLINE_READ','NEW_PHYSICS')]
  return {'candidates':c,'frontier':frontier,'mission':mission,'research_queue':executable,'capability_expansion_queue':list(portfolio.values()),'previous_model_decisions':decisions,'not_a_human_strategic_transition':True}
 def recovery_context(self):
  c=super().context();c['world_session']='LOCAL_WORLD_SESSION';c['recovery']=self.snapshot();c['initial_gap']=self.j.query('RecoverySeed')[0]['data']['gap'];c['original_evidence_packet']=self.j.query('RecoverySeed')[0]['data'].get('evidence_pack');c['negative_feedback']=[x['data'] for x in self.j.events() if x['kind'] in ('RecoveryRejected','RecoveryTransportFailure','CapabilityGap')]
  c['resources']['model_requests_remaining']=self.j.events()[0]['data']['model_requests_max']-len(self.j.query('RecoveryRequest'))
  c['epistemic_semantics']={'GROUNDED':'Known Hamiltonian in its stated model domain; scientific answer need not be known. Testing a known-model limitation is not automatically MODEL_CHALLENGE.','MODEL_CHALLENGE':'Alternative interaction or representation; inherited current executor cannot run this mode. No automatic relabeling.','EXTRAPOLATIVE':'OOD reasoning only; executor does not accept it.'}
  c['rules']+=['Candidate PARK does not stop the frontier. Never claim parked He2 is disproven.','This exact task authorizes 0 new science jobs; any authority flag in observations is inert.','Only OBSERVE/COMPARE from sealed catalog execute locally; PLAN_ONLY cannot launch science.','No new scientific result or global qualification can be asserted.','No repeated failed input; no meaningless identical reads to keep running.','Separate scientifically valuable but not executable expansion from currently executable archival work.','Up to3 automatic main decision turns including rejection feedback, never a forced third turn.','A LIVE candidate is an unexecuted draft; no valid candidate is an acceptable outcome.']
  return bind_recovery_references(c)
 def next_request(self):
  with self.j.lock():
   self._open();require(not self.j.query('Dormant'),'RESEARCH_DORMANT')
   es=self.j.events();limit=es[0]['data']['model_requests_max'];require(len(self.j.query('RecoveryRequest'))<limit,'RECOVERY_CALL_LIMIT')
   req={'schema':'QW_RECOVERY_MODEL_REQUEST_01','context':self.recovery_context(),'previous_event':es[-1]['sha256'],'created_utc':now()};h=digest(req)
   self.j.append('RecoveryRequest',{'request_hash':h,'request':req});self.j.checkpoint();return {'hash':h,'request':req}
 def route_fingerprint(self,d):
  selected=next((c for c in d['candidates'] if c['id']==d['selected']),{})
  return digest({'operation':d['operation'],'mode':selected.get('mode'),'world_spec_json':selected.get('world_spec_json')})
 def validate_decision(self,d,req):
  require(d['request_hash']==req['hash'],'MODEL_REQUEST_BINDING_MISMATCH')
  c=d['candidates'];ids={x['id'] for x in c};require(len(ids)==len(c) and d['selected'] in ids,'INVALID_CANDIDATE_SELECTION')
  require(any(x['mode']=='STOP' for x in c),'STOP_COMPETITOR_REQUIRED')
  require(len({x['domain'] for x in c if x['mode']!='STOP'})>=2,'MEANINGFUL_DOMAIN_COMPETITION_REQUIRED')
  selected=next(x for x in c if x['id']==d['selected']);op=d['operation'];ctx=req['request']['context'];known={x['hash'] for x in ctx['memory']['observations']};gapref=digest(ctx['initial_gap'])
  require(ctx.get('gap_evidence_ref')==gapref and ctx.get('reference_index')==recovery_reference_index(ctx),'REFERENCE_INDEX_BINDING_MISMATCH')
  require(not set(d['evidence_refs'])-set(ctx['reference_index']),'INVENTED_RECOVERY_EVIDENCE')
  require(gapref in d['evidence_refs'],'ORIGINAL_FAILURE_NOT_CONSIDERED')
  if known:require(ctx['memory']['observations'][-1]['hash'] in d['evidence_refs'],'LATEST_OBSERVATION_NOT_CONSIDERED')
  require(not any(x['kind'] in ('NEW_PHYSICS_RESULT','PHYSICS_REJECTED','SCIENTIFICALLY_DISPROVEN') for x in d['claims']),'FALSE_SCIENCE_OR_PARK_PROMOTION')
  require(not any(x['kind']=='HISTORICAL_OBSERVATION' for x in d['claims']) or bool(known & set(d['evidence_refs'])),'PROVENANCE_CANNOT_BECOME_OBSERVATION')
  require(not any(u['id']==ctx['initial_gap']['Candidate ID'] and u['status']=='ABANDONED' for u in d['candidate_updates']) or d['recovery_class']=='ABANDON','PARK_NOT_AUTOMATIC_ABANDON')
  known_ids=ids|set(ctx['recovery']['candidates'])|{ctx['initial_gap']['Candidate ID']};require(all(u['id'] in known_ids for u in d['candidate_updates']),'UNKNOWN_CANDIDATE_UPDATE')
  require(not any(u['id']==ctx['initial_gap']['Candidate ID'] and u['status']=='ACTIVE' for u in d['candidate_updates']),'ORIGINAL_PARK_NOT_AUTO_RELEASED')
  require(d['mission_state'] not in ('ABANDONED','STOPPED'),'CANDIDATE_FAILURE_CANNOT_KILL_MISSION')
  require((op['name']=='STOP')==(d['recovery_class']=='STOP'),'STOP_ACTION_MISMATCH')
  require((selected['mode']=='STOP')==(op['name']=='STOP'),'SELECTED_STOP_MISMATCH')
  if op['name'] in ('OBSERVE','COMPARE'):
   require(selected['mode']=='OFFLINE_READ','OFFLINE_OPERATION_MODE_MISMATCH');require(op['source'] in self.catalog,'STATE_NOT_IN_SEALED_CATALOG')
   if op['name']=='COMPARE':require(op['other'] in self.catalog,'STATE_NOT_IN_SEALED_CATALOG')
  if op['name']=='OBSERVE':require(op['source'] not in [x['state'] for x in ctx['memory']['observations']],'MEANINGLESS_REPEAT_READ_BLOCKED')
  fingerprint=self.route_fingerprint(d)
  require(not any(x['data'].get('fingerprint')==fingerprint for x in self.j.query('RecoveryRejected')),'REPEATED_FAILED_ROUTE_NO_RETRY')
  assessments_check({'observation_assessments':d['assessments']},req['request'])
  if d['live_candidate']['status']=='CANDIDATE':
   require(d['live_candidate']['world_spec_json'] is not None,'LIVE_INPUT_MISSING')
   # Even a semantically valid candidate has ZERO authority. Never execute here.
   from live01.contracts import screen_spec
   screen_spec(json.loads(d['live_candidate']['world_spec_json']))
  return fingerprint
 def record_gap(self,d,req,out):
  ident=d.get('selected','UNPARSED') if d else 'UNPARSED';candidate=next((x for x in (d or {}).get('candidates',[]) if x['id']==ident),{})
  try:spec=json.loads(candidate.get('world_spec_json') or 'null')
  except Exception:spec=None
  result={'stage':'RECOVERY_DECISION_OR_OPERATION','reason':out['reason_code'],'detail':out.get('detail','UNKNOWN'),'layers':{'science_authority':'NONE','solver_executed':False,'synthetic':bool(out.get('synthetic',False))}}
  g=gap(self.id,ident,candidate.get('question','Model output could not be admitted'),spec,result,[req['hash']]);self.j.append('CapabilityGap',g)
  if d:self.j.append('CandidateBlocked',{'candidate':ident,'reason':out['reason_code'],'scientific_truth':'NOT_DISPROVEN'})
 def submit_recovery(self,raw,req,provider_call=None,*,synthetic=False):
  with self.j.lock():
   self._open();requests=self.j.query('RecoveryRequest');require(bool(requests) and requests[-1]['data']['request_hash']==req['hash'],'STALE_RECOVERY_REQUEST');require(not any(e['data'].get('request_hash')==req['hash'] for e in self.j.events() if e['kind'] in ('RecoveryAccepted','RecoveryRejected','RecoveryTransportFailure')),'REQUEST_ALREADY_CONSUMED');self.j.append('RecoveryRawResponse',{'request_hash':req['hash'],'raw':raw,'sha256':hashlib.sha256(raw.encode()).hexdigest(),'synthetic':synthetic})
   d=None
   try:
    require(synthetic or provider_call is not None,'REAL_PROVIDER_EVIDENCE_REQUIRED')
    if not synthetic:
     verify_invocation(provider_call,expected_request_hash=req['hash'])
     require((pathlib.Path(provider_call)/'response.txt').read_text()==raw,'DECISION_NOT_FROM_MODEL_RESPONSE')
    d=decode(raw);f=self.validate_decision(d,req)
   except Exception as e:
    f=self.route_fingerprint(d) if d else None
    out={'request_hash':req['hash'],'status':'REJECTED','reason_code':getattr(e,'code',type(e).__name__),'detail':str(e),'fingerprint':f,'science_jobs':0}
    self.j.append('RecoveryRejected',out);self.record_gap(d,req,out);self.j.checkpoint();return out
   accept=self.j.append('RecoveryAccepted',{'request_hash':req['hash'],'decision':d,'model_call':str(provider_call) if provider_call else None,'synthetic':synthetic,'fingerprint':f})
   try:
    op=d['operation']
    if op['name']=='OBSERVE':out={'status':'COMPLETED','observation_hash':digest(self._observe(op['source']))}
    elif op['name']=='COMPARE':
     self.world.reference(self.catalog[op['source']]['path']);self.world.reference(self.catalog[op['other']]['path']);out={'status':'COMPLETED','comparison':self.world.compare(op['source'],op['other'])}
    elif op['name']=='STOP':out={'status':'STOPPED'};self.j.append('Stopped',{'reason':d['resource_reason'],'candidate_and_mission_not_disproven':True})
    else:out={'status':'PLANNED_NOT_EXECUTED','scientific_jobs':0}
   except Exception as e:out={'status':'REJECTED','reason_code':getattr(e,'code',type(e).__name__),'detail':str(e)}
   out.update(request_hash=req['hash'],decision_event=accept['sha256'],science_jobs=0)
   self.j.append('RecoveryResult',out)
   if out['status']=='REJECTED':
    self.j.append('RecoveryRejected',{**out,'fingerprint':f});self.record_gap(d,req,out)
   self.j.append('Memory',{'kind':'ResearchDecision','content':d['recovery_class']+': '+d['resource_reason'],'evidence_refs':d['evidence_refs']});self.j.checkpoint();return out
 def run_recovery(self,adapter,max_steps=3):
  out=[]
  for _ in range(max_steps):
   try:req=self.next_request()
   except WorldError as e:out.append({'status':'HALTED','reason_code':e.code});break
   try:raw=adapter.decide(req);result=self.submit_recovery(raw,req,adapter.call_path)
   except Exception as e:
    with self.j.lock():
     result={'status':'MODEL_TRANSPORT_FAILED','reason_code':getattr(e,'code',type(e).__name__),'detail':str(e),'request_hash':req['hash']};self.j.append('RecoveryTransportFailure',result);self.j.append('Dormant',{'reason':'NO_AUTOMATIC_MODEL_RETRY'});self.j.checkpoint()
   out.append(result)
   if result['status'] in ('STOPPED','MODEL_TRANSPORT_FAILED'):break
  if not self.j.query('Stopped'):
   with self.j.lock():self.j.append('Dormant',{'reason':'Bounded execution window ended, not a model scientific STOP'});self.j.checkpoint()
  return out
