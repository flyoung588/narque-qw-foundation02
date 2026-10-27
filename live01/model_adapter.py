"""Live observation role is distinct from historical replay; same gateway API."""
import json,copy,hashlib,math
from router import digest
from explorer01.adapters import ModelAdapter
from explorer01.contracts import SCHEMA
from explorer01.l1_adapter import WRAPPER
from world01.contracts import WorldError
LIVE_WRAPPER=copy.deepcopy(WRAPPER)
LIVE_WRAPPER['properties']['observation_assessments']['items']['properties']['source_role']={'const':'NEW_E01_MODEL_OUTPUT_NOT_INDEPENDENTLY_VALIDATED'}
class LiveModelAdapter(ModelAdapter):
 def __init__(self,gateway,thread,prereg):self.g=gateway;self.thread=thread;self.prereg=prereg;self.last_receipt=None
 def decide(self,request):
  h=digest(request);ctx=request['context'];prompt=('Return only outer JSON, decision_json is serialized inner Decision schema. No tools. You are in a live E01 controller after a newly computed finite-model observation. You may STOP.\n'
   'To request one new approved calculation use operation.name=PROPOSE_EXPERIMENT, source=latest observation state hash, parameters={"action":{"type":"DISPLACE_ATOM","source_state_sha256":"latest hash","atom_id":"atom-N","vector":[dx,dy,dz],"unit":"angstrom"}}. Vector norm must be>0 and<=0.05A. MEASURE_OBSERVABLE is only worth a new Job with a distinct admitted input; no identical repeats. For CHANGE_OBJECT only, parameters.world_spec may hold a new valid admitted generic molecule; no cross-composition energy ranking. Other domains may be proposed in text but not executed.\n'
   'Read actual forces/energy and model limits. Choose direction, magnitude, different object or STOP yourself. No optimizer or second geometry is specified. Preserve alternatives, prediction/falsifier and exact current observation hashes. Quote available scalar values with exact units in observation_assessments, source_role=NEW_E01_MODEL_OUTPUT_NOT_INDEPENDENTLY_VALIDATED. This is not independent physical certification.\n'
   'Request hash '+h+'\nCurrent exact request:\n'+json.dumps(request,ensure_ascii=False,sort_keys=True)+'\nFrozen protocol:\n'+json.dumps(self.prereg,ensure_ascii=False,sort_keys=True)+'\nInner schema:\n'+json.dumps(SCHEMA,sort_keys=True))
  raw=self.g.invoke(self.thread,prompt,LIVE_WRAPPER,request_hash=h,observation_digest=digest(ctx['memory']['observations']),research_session=ctx['research_session'],purpose='E01_NEW_OBSERVATION_FEEDBACK')
  data=json.loads(raw);known={x['hash']:x['observation'] for x in ctx['memory']['observations']}
  if known and not data['observation_assessments']:raise WorldError('NEW_OBSERVATION_NOT_ASSESSED')
  for a in data['observation_assessments']:
   if a['source_role']!='NEW_E01_MODEL_OUTPUT_NOT_INDEPENDENTLY_VALIDATED' or a['observation_hash'] not in known:raise WorldError('LIVE_OBSERVATION_ROLE_OR_HASH_MISMATCH')
   q=known[a['observation_hash']]['observables'].get(a['quantity']);v=json.loads(a['value_json'])
   if not q or q['unit']!=a['unit'] or not a['limitations']:raise WorldError('LIVE_OBSERVABLE_CONTRACT_MISMATCH')
   if type(v) in (int,float) and type(q['value']) in (int,float):ok=math.isfinite(v) and math.isclose(v,q['value'],rel_tol=1e-8,abs_tol=1e-10)
   else:ok=v==q['value']
   if not ok:raise WorldError('LIVE_OBSERVABLE_VALUE_MISMATCH')
  self.last_receipt=copy.deepcopy(self.g.last_receipt);self.last_receipt['observation_assessments']=data['observation_assessments'];self.last_receipt['runtime_decision_sha256']=hashlib.sha256(data['decision_json'].encode()).hexdigest();return data['decision_json']
