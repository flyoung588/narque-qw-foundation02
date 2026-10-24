"""Machine validation for the new envelopes, never rewrites legacy schemas."""
from jsonschema import Draft202012Validator
HASH={'type':'string','pattern':'^[0-9a-f]{64}$'}
def object_schema(required,properties):
    return {'$schema':'https://json-schema.org/draft/2020-12/schema','type':'object','required':required,'properties':properties}
SCHEMAS={
'state':object_schema(['schema','state_kind','source_state_hash','model_hash','representation','units','provenance','actual_model','qualification'],{'schema':{'const':'QW_SCIENTIFIC_STATE_ENVELOPE_01'},'source_state_hash':HASH,'model_hash':HASH,'state_kind':{'enum':['QW_PHYSICAL_STATE_01','QW_EFFECTIVE_QUANTUM_STATE_01','QW_CORRELATED_ELECTRONIC_STATE_01']},'units':{'type':'object'},'provenance':{'type':'object'},'qualification':{'type':'object','properties':{'new_physical_execution':{'const':False}}}}),
'observation':object_schema(['schema','source_state_hash','status','values','provenance','new_physics_run'],{'schema':{'const':'QW_OBSERVATION_ENVELOPE_01'},'source_state_hash':HASH,'new_physics_run':{'const':False},'values':{'type':'object'},'status':{'enum':['HISTORICAL_OBSERVATION_READ','SOFTWARE_FIXTURE_ONLY','STRUCTURE_ONLY_NOT_CALCULATED']}}),
'request':object_schema(['action','source_state_hash','parameters','mode','budget_id'],{'action':{'type':'string','minLength':1},'source_state_hash':HASH,'parameters':{'type':'object'},'mode':{'const':'OFFLINE'},'budget_id':{'const':'E00_ZERO_NEW_SCIENCE'}}),
'receipt':object_schema(['schema','operation','status','reason_code','time_utc','new_scientific_execution'],{'schema':{'const':'QW_SESSION_RECEIPT_01'},'operation':{'type':'string'},'reason_code':{'type':'string','minLength':1},'new_scientific_execution':{'const':False}}),
'manifest':object_schema(['schema','id','domain','representation','Hamiltonian_approximation','supported_operations','supported_observables','unavailable_observables','units_reference','evidence','physical_qualification','independent_validation','resource_envelope','model_limitations'],{'schema':{'const':'QW_CAPABILITY_MANIFEST_01'},'supported_operations':{'type':'array','minItems':1},'supported_observables':{'type':'array','minItems':1},'resource_envelope':{'type':'object','properties':{'current_E00_science_jobs':{'const':0}}}})
}
def validate(kind,value):
    Draft202012Validator.check_schema(SCHEMAS[kind]);Draft202012Validator(SCHEMAS[kind]).validate(value)
