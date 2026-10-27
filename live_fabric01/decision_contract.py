"""Narrow wire contract and conservative lexical compatibility.
No candidate selection, physical intent, prediction or evidence is invented.
"""
import copy,json
from jsonschema import Draft202012Validator
from explorer01.contracts import SCHEMA,decode,obj,text
from world01.contracts import WorldError

HASH={'type':'string','pattern':'^[0-9a-f]{64}$'}
MEASURE=obj({'type':{'const':'MEASURE_OBSERVABLE'},'source_state_sha256':HASH,'observables':{'type':'array','items':{'enum':['energy','forces']},'minItems':1}})
DISPLACE=obj({'type':{'const':'DISPLACE_ATOM'},'source_state_sha256':HASH,'atom_id':text(),'vector':{'type':'array','items':{'type':'number'},'minItems':3,'maxItems':3},'unit':{'const':'angstrom'}})
# Wire is scoped to the unchanged first H2O live tranche, not the world's full taxonomy.
INTENT=obj({**{k:text() for k in ['research_session','world_session','goal','candidate','input_state','prediction','falsifier','resource_ref','authorization_ref','stop_condition','experiment_ref']},'model':{'const':'molecular'},'operation':{'anyOf':[MEASURE,DISPLACE]},'observables':{'type':'array','items':{'enum':['energy','forces']},'minItems':1},'mode':{'const':'NEW_SCIENTIFIC_EXECUTION'}})
PARAMETERS={'anyOf':[obj({}),obj({'intent':INTENT}),obj({'reason':text()}),obj({'target':text()}),obj({'candidate_status':{'enum':['PARKED','ABANDONED']},'candidate_id':text()}),obj({'contract':obj({'kind':{'enum':['SAME_MODEL_IDENTITY','SAME_MODEL_GEOMETRY_PATH']}})})]}
WIRE_SCHEMA=copy.deepcopy(SCHEMA)
WIRE_SCHEMA['properties']['candidates']['items']['properties']['kind']={'enum':['RESEARCH','STOP']}
WIRE_SCHEMA['properties']['operation']['properties']['parameters']=PARAMETERS
Draft202012Validator.check_schema(WIRE_SCHEMA)
WRAPPED_SCHEMA=obj({'decision_json':{'type':'string'}})

RELATION_RULES=(
 'selected is exactly one existing candidate.id. Do not substitute an unregistered State hash or new label; candidate IDs are unique.',
 'candidate.kind is exactly RESEARCH or STOP in this live wire contract. STOP is a role, not a prose description.',
 'If and only if the selected candidate.kind is STOP, action and operation.name are both STOP. STOP has parameters={} and other=null.',
 'A non-STOP selected candidate has kind RESEARCH; use a permitted action and operation. PROPOSE_EXPERIMENT is an operation, not an action.',
 'For an experiment use action CONTINUE/CHANGE_OBJECT/CHANGE_MODEL/CHANGE_PHYSICAL_DOMAIN/REQUEST_VALIDATION and operation.name PROPOSE_EXPERIMENT with parameters.intent.',
 'OBSERVE uses CONTINUE/CHANGE_OBJECT/CHANGE_MODEL/CHANGE_PHYSICAL_DOMAIN/REQUEST_VALIDATION. FORK uses FORK or CONTINUE; ABANDON uses FORK with explicit candidate_status=ABANDONED.',
 'FORK, COMPARE and TRANSLATE never imply a real physical state conversion. PARK uses CONTINUE plus FORK parameters.candidate_status=PARKED.',
 'Do not fabricate observations, predictions, falsifiers or a different selected candidate to repair an ambiguous decision. Return the actual scientifically justified choice.'
)
def fail(code,detail):raise WorldError(code,detail)
def check_relations(d):
 ids=[c['id'] for c in d['candidates']]
 if len(set(ids))!=len(ids):fail('CANDIDATE_IDS_NOT_UNIQUE','candidate.id values must be unique')
 if d['selected'] not in ids:fail('SELECTED_CANDIDATE_NOT_REGISTERED',f"selected={d['selected']!r}; existing candidate.id values={ids!r}. A State hash is not automatically a candidate ID.")
 selected=next(c for c in d['candidates'] if c['id']==d['selected']);a=d['action'];op=d['operation']
 if (a=='STOP')!=(op['name']=='STOP'):fail('ACTION_OPERATION_STOP_CONFLICT','action and operation.name must either both be STOP or neither.')
 if a=='STOP' and selected['kind']!='STOP':
  code='STOP_SELECTION_ROLE_CONFLICT' if selected['kind'].strip().lower().startswith(('research','baseline','experiment')) else 'AMBIGUOUS_STOP_CANDIDATE_ROLE'
  fail(code,f"Selected candidate {selected['id']!r} has kind={selected['kind']!r}, not STOP. No candidate was changed or substituted.")
 if selected['kind']=='STOP' and a!='STOP':fail('STOP_SELECTION_ROLE_CONFLICT','A selected STOP candidate cannot dispatch a non-STOP action.')
 readonly_stop_metadata={'research_session','world_session','input_state','execution_refs'}
 if a=='STOP' and (set(op['parameters'])-readonly_stop_metadata or op['other'] is not None):fail('STOP_CONTAINS_NONSTOP_PAYLOAD','STOP may retain inert context metadata, but cannot contain an executable intent, action or comparison target.')
 if op['name']=='PROPOSE_EXPERIMENT' and a not in ('CONTINUE','CHANGE_OBJECT','CHANGE_MODEL','CHANGE_PHYSICAL_DOMAIN','REQUEST_VALIDATION'):fail('ACTION_OPERATION_MISMATCH','Experiment proposal needs a permitted research action; not FORK/ABANDON/STOP.')
 if op['name']=='OBSERVE' and a not in ('CONTINUE','CHANGE_OBJECT','CHANGE_MODEL','CHANGE_PHYSICAL_DOMAIN','REQUEST_VALIDATION'):fail('ACTION_OPERATION_MISMATCH','OBSERVE cannot implement ABANDON or FORK.')
 if a=='FORK' and op['name']!='FORK':fail('ACTION_OPERATION_MISMATCH','FORK action requires FORK operation.')
 if a=='ABANDON' and not (op['name']=='FORK' and op['parameters'].get('candidate_status')=='ABANDONED'):fail('ACTION_OPERATION_MISMATCH','ABANDON must explicitly identify a candidate status transition, not a physical operation.')
 return d

def decode_with_audit(raw):
 original=decode(raw);d=copy.deepcopy(original);changes=[]
 selected=[c for c in d['candidates'] if c['id']==d['selected']]
 if len(selected)==1 and d['action']=='STOP' and d['operation']['name']=='STOP':
  c=selected[0];kind=c['kind'];canonical=kind.strip().upper()
  # Exact lexical STOP spelling is safe; one observed unambiguous historical alias
  # additionally requires the selected ID itself to be STOP. No missing ID is added.
  safe=canonical=='STOP' or (kind.strip().casefold()=='bounded termination' and c['id']=='STOP')
  if safe and kind!='STOP':
   c['kind']='STOP';changes.append({'path':f"candidates[{d['candidates'].index(c)}].kind",'before':kind,'after':'STOP','reason':'UNAMBIGUOUS_STOP_ROLE_LEXICAL_CANONICALIZATION'})
 check_relations(d)
 return d,{'changes':changes,'raw_unchanged':True,'selected_unchanged':d['selected']==original['selected'],'action_unchanged':d['action']==original['action'],'operation_unchanged':d['operation']==original['operation'],'prediction_unchanged':d['prediction']==original['prediction'],'falsifier_unchanged':d['falsifier']==original['falsifier'],'authority_granted':False}

def unwrap_wire(raw,mode):
 if mode=='DIRECT_OBJECT':
  return raw # Shape/relationship errors are journaled by Runtime, not mislabeled as transport failures.
 if mode=='WRAPPED_COMPAT':
  value=json.loads(raw);Draft202012Validator(WRAPPED_SCHEMA).validate(value);return value['decision_json']
 fail('UNAPPROVED_WIRE_MODE','No automatic mode change or provider retry.')
