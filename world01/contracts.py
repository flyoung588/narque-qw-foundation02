"""Typed, versioned envelopes referencing unchanged legacy scientific states."""
from dataclasses import dataclass,asdict
from typing import TypedDict,Any,NotRequired
from router import digest

class WorldError(ValueError):
    def __init__(self,code,detail=''):self.code=code;self.detail=detail;super().__init__(code+(': '+detail if detail else ''))
class PhysicalObject(TypedDict):
    object_id:str
    matter_type:str
    matter_spec:dict
class ScientificStateEnvelope(TypedDict):
    schema:str
    state_kind:str
    source_state_hash:str
    model_hash:str
    representation:str
    units:dict
    provenance:dict
    source_execution:NotRequired[dict]
    current_operation_new_scientific_executions:NotRequired[int]
class ObservationEnvelope(TypedDict):
    schema:str
    source_state_hash:str
    values:dict
    status:str
    provenance:dict
    source_execution_kind:NotRequired[str]
    source_execution_status:NotRequired[str]
    observables:NotRequired[dict]
    new_scientific_executions:NotRequired[int]
    new_physics_run:NotRequired[bool]
class EvidenceReceipt(TypedDict):
    operation:str
    status:str
    reason_code:str
    source_state_hash:str
    new_scientific_execution:NotRequired[bool]
    new_scientific_executions:NotRequired[int]
@dataclass(frozen=True)
class OperationRequest:
    action:str
    source_state_hash:str
    parameters:dict
    required_observables:tuple=()
    predicted_effect:str=''
    falsifier:str=''
    budget_id:str='E00_ZERO_NEW_SCIENCE'
    mode:str='OFFLINE'
    def plain(self):return asdict(self)
KIND={
 'QW_PHYSICAL_STATE_01':('STRUCTURE_AND_OPTIONAL_STATIC_BO','angstrom/Eh; no physical time'),
 'QW_EFFECTIVE_QUANTUM_STATE_01':('COMPLEX_TWO_STATE_EFFECTIVE_KET','atomic_time/Eh/atomic_dipole'),
 'QW_CORRELATED_ELECTRONIC_STATE_01':('FINITE_BASIS_MANY_DETERMINANT_CI','Eh/angstrom/hbar^2; static BO')}
def envelope(state,provenance,source_execution=None):
    p=state['payload'];kind=p.get('schema')
    if kind not in KIND:raise WorldError('UNSUPPORTED_STATE_KIND')
    model=p.get('correlation_model',p.get('model',p['world_spec']['physics']))
    return {'schema':'QW_SCIENTIFIC_STATE_ENVELOPE_01','state_kind':kind,'source_state_hash':state['sha256'],
            'parent_state_hash':p.get('parent_state_id'),'model_hash':digest(model),'actual_model':model,
            'representation':KIND[kind][0],'units':{'convention':KIND[kind][1],'position':'angstrom','energy':'Eh/cell' if p['world_spec']['matter']['periodic'] else 'Eh'},
            'time_origin':p.get('control_origin_au'),'physical_time':p.get('time_au'),
            'norm':p.get('norm'),'array_refs':p.get('arrays'),'scope':p.get('scope','Static structure; not quantum evolution'),
            'object':{'object_id':p['world_spec']['object_id'],'matter_type':p['world_spec']['matter']['type'],'matter_spec':p['world_spec']['matter']},
            'provenance':provenance,'source_execution':source_execution or {'source_evidence_status':'UNVERIFIED','real_calculated':False},'current_operation_new_scientific_executions':0,'qualification':{'new_physical_execution':False,'W2':'INCOMPLETE_UNCHANGED','novelty':'NOT_PROVEN','reality':'NOT_PROVEN'}}
