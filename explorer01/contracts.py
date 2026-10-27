"""Decision contents are model outputs; safety checks are deterministic."""
import json
from jsonschema import Draft202012Validator
ACTIONS=['CONTINUE','FORK','CHANGE_OBJECT','CHANGE_MODEL','CHANGE_PHYSICAL_DOMAIN','REQUEST_VALIDATION','ABANDON','STOP']
OPS=['OBSERVE','COMPARE','TRANSLATE','FORK','PROPOSE_EXPERIMENT','STOP']
def text():return {'type':'string','minLength':1,'maxLength':12000}
def obj(fields):return {'type':'object','properties':fields,'required':list(fields),'additionalProperties':False}
CANDIDATE=obj({'id':text(),'kind':text(),'question':text(),'information_value':text(),'cost_and_limits':text(),'why_not_selected':text()})
SCHEMA=obj({'schema':{'const':'QW_EXPLORER_DECISION_01'},'request_hash':{'type':'string','pattern':'^[0-9a-f]{64}$'},'goal_interpretation':text(),'candidates':{'type':'array','minItems':2,'maxItems':10,'items':CANDIDATE},'selected':text(),'action':{'enum':ACTIONS},'operation':obj({'name':{'enum':OPS},'source':{'type':['string','null']},'other':{'type':['string','null']},'parameters':{'type':'object'}}),'observation_refs':{'type':'array','items':{'type':'string','pattern':'^[0-9a-f]{64}$'},'uniqueItems':True},'interpretation':text(),'limitations':text(),'competing_explanations':{'type':'array','minItems':2,'items':text()},'prediction':text(),'falsifier':text(),'resource_reason':text(),'negative_evidence_response':text(),'memory_updates':{'type':'array','items':obj({'kind':{'enum':['ModelKnowledge','Hypothesis','CandidateFrontier','FailedPath','OpenQuestion','ResearchDecision']},'content':text(),'evidence_refs':{'type':'array','items':{'type':'string'}}})}})
Draft202012Validator.check_schema(SCHEMA)
def decode(raw):
 def pairs(items):
  d={}
  for k,v in items:
   if k in d:raise ValueError('DUPLICATE_JSON_KEY')
   d[k]=v
  return d
 v=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('NONFINITE_JSON')))
 Draft202012Validator(SCHEMA).validate(v)
 return v
