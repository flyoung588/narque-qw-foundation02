import json,copy,hashlib
from jsonschema import Draft202012Validator
from router import digest
from world01.contracts import WorldError
from world01 import fabric
from foundation01.contract import SCHEMA as SPEC_SCHEMA
from live01.contracts import screen_spec
STATES=['ACTIVE','PARKED','DORMANT','ABANDONED','STOPPED','AWAITING_AUTHORITY','AWAITING_CAPABILITY']
RECOVERY=['REVISE_INPUT','USE_EXISTING_CAPABILITY','CHANGE_METHOD','CHANGE_OBJECT','CHANGE_DOMAIN','PARK_FOR_CAPABILITY_EXPANSION','REQUEST_NEW_AUTHORITY','ABANDON','STOP']
def text():return {'type':'string','minLength':1,'maxLength':7000}
def obj(fields):return {'type':'object','properties':fields,'required':list(fields),'additionalProperties':False}
nullable={'type':['string','null']}
CANDIDATE=obj({**{k:text() for k in ['id','domain','question','scientific_importance','information_gain','model_adequacy','numerical_risk','cost','novelty_potential','transferable_capability','opportunity_cost','falsifier','why_not_selected']},'mode':{'enum':['OFFLINE_READ','NEW_PHYSICS','EXPANSION','STOP']},'world_spec_json':nullable,'state_ids':{'type':'array','items':text()}})
EXPANSION=obj({k:text() for k in ['id','scientific_need','new_DOF','state_types','operations','observables','validity','mature_solver','quality_requirements','integration','cross_object_use','cost','priority_reason']})
LIVE=obj({'status':{'enum':['CANDIDATE','NO_QUALIFIED_LIVE_CANDIDATE']},**{k:text() for k in ['question','scientific_value','new_information','current_support','solver','model_approximations','observables','prediction','falsifier','adaptive_rule','resource_limits','stop_conditions','qualification_limits']},'world_spec_json':nullable})
SCHEMA=obj({'schema':{'const':'QW_FRONTIER_RECOVERY_DECISION_01'},'request_hash':{'type':'string','pattern':'^[a-f0-9]{64}$'},'diagnosis':text(),'candidates':{'type':'array','minItems':3,'maxItems':8,'items':CANDIDATE},'selected':text(),'recovery_class':{'enum':RECOVERY},'operation':obj({'name':{'enum':['OBSERVE','COMPARE','PLAN_ONLY','STOP']},'source':nullable,'other':nullable}),'candidate_updates':{'type':'array','items':obj({'id':text(),'status':{'enum':STATES},'reason':text()})},'frontier_state':{'enum':STATES},'mission_state':{'enum':STATES},'interpretation':text(),'limitations':text(),'evidence_refs':{'type':'array','items':text()},'claims':{'type':'array','items':obj({'kind':{'enum':['KNOWN_FACT','HYPOTHESIS','HISTORICAL_OBSERVATION','NEW_PHYSICS_RESULT','PHYSICS_REJECTED','SCIENTIFICALLY_DISPROVEN']},'text':text()})},'assessments':{'type':'array','items':obj({'observation_hash':text(),'quantity':text(),'value_json':text(),'unit':text(),'source_role':{'const':'HISTORICAL_MODEL_OUTPUT_NOT_NEW_SCIENCE'},'limitations':text()})},'expansions':{'type':'array','maxItems':5,'items':EXPANSION},'live_candidate':LIVE,'resource_reason':text()})
GAP_SCHEMA=obj({k:({'type':'array','items':text()} if k in ['Available Alternatives','Evidence References'] else {'type':'object'} if k in ['Current Capability','Missing Capability','Resource Requirement'] else {} if k in ['WorldSpec','Requested Physics Model','Requested Operation'] else text()) for k in ['ResearchSession ID','Candidate ID','Physical Question','WorldSpec','Requested Physics Model','Requested Operation','Admission Stage','Actual Reason Code','Current Capability','Missing Capability','Available Alternatives','Scientific Consequence','Resource Requirement','Evidence References','Suggested Recovery Class']})
Draft202012Validator.check_schema(SCHEMA);Draft202012Validator.check_schema(GAP_SCHEMA)
def require(x,c):
 if not x:raise WorldError(c)
def decode(raw):
 def pairs(xs):
  out={}
  for k,v in xs:
   if k in out:raise WorldError('DUPLICATE_KEY')
   out[k]=v
  return out
 d=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(WorldError('NONFINITE_JSON')))
 Draft202012Validator(SCHEMA).validate(d);return d

def classify(spec,*,operation='MEASURE_OBSERVABLE',observables=('energy',),model_adequate=None,cost_fits=True):
 """Return separate layers; never run/install a solver or infer dependency availability."""
 layers={'schema':'UNKNOWN','object_execution_contract':'UNKNOWN','solver_numeric':'NOT_RUN','model_adequacy':model_adequate if model_adequate is not None else 'UNKNOWN','current_science_authority':'NONE','dependencies':'NOT_PROBED_NO_ENGINE_IMPORT','cost':'WITHIN_PROPOSAL' if cost_fits else 'OVER_BUDGET'}
 try:
  Draft202012Validator(SPEC_SCHEMA).validate(spec);layers['schema']='VALID'
 except Exception as e:return {'stage':'SCHEMA','reason':'SCHEMA_INVALID','detail':str(e),'layers':layers}
 try:fabric.validate_object(spec);layers['object_execution_contract']='VALID'
 except WorldError as e:
  layers['object_execution_contract']='REJECTED';return {'stage':'OBJECT_EXECUTION_CONTRACT','reason':e.code,'detail':str(e),'layers':layers}
 if operation not in ('DISPLACE_ATOM','MEASURE_OBSERVABLE'):return {'stage':'OPERATION','reason':'OPERATION_OUT_OF_DOMAIN','layers':layers}
 if set(observables)-{'energy','forces'}:return {'stage':'OBSERVABLE','reason':'UNSUPPORTED_OBSERVABLE','layers':layers}
 try:screen_spec(spec)
 except WorldError as e:return {'stage':'RESOURCE_OR_MODEL_ENVELOPE','reason':e.code,'detail':str(e),'layers':layers}
 layers['solver_numeric']='KNOWN_ENGINE_ROUTE_NOT_RUNTIME_TESTED'
 if not cost_fits:return {'stage':'RESOURCE','reason':'COST_OVER_BUDGET','layers':layers}
 if model_adequate is False:return {'stage':'MODEL_ADEQUACY','reason':'MODEL_INADEQUATE_FOR_CLAIM','layers':layers}
 return {'stage':'AUTHORITY','reason':'RESOURCE_ADMISSION_REQUIRED','layers':layers,'semantically_routable':True,'new_science':0}

def gap(session,candidate,question,spec,result,refs):
 g={'ResearchSession ID':session,'Candidate ID':candidate,'Physical Question':question,'WorldSpec':copy.deepcopy(spec),'Requested Physics Model':spec.get('physics',{}) if isinstance(spec,dict) else {},'Requested Operation':{'name':'MEASURE_OBSERVABLE'},'Admission Stage':result['stage'],'Actual Reason Code':result['reason'],'Current Capability':result['layers'],'Missing Capability':{'current_block':result.get('detail',result['reason']),'solver_failure':'NOT_ESTABLISHED'},'Available Alternatives':['Reframe a known-model question with explicit scientific justification','Read sealed observations through WorldSession','Compete other objects/domains','Nominate reusable expansion','Request authority without executing','PARK or STOP'],'Scientific Consequence':'No physical rejection; no new calculation exists','Resource Requirement':{'authorized_new_science':0,'new_purchase':0},'Evidence References':refs,'Suggested Recovery Class':'AI_SELECTION_REQUIRED'}
 Draft202012Validator(GAP_SCHEMA).validate(g);return g
