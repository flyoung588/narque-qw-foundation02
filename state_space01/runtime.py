"""Extend the existing immutable state/action/receipt pattern, no AI policy."""
import copy,datetime,pathlib
import numpy as np
from router import digest
from interactive01.world import freeze,verify
from .contract import validate_action,model_check
from .dynamics import propagate
from .state import blob

def operate(store,state,action,fixture=False):
    verify(state);kind=validate_action(state,action);p=state['payload'];arrays=store.arrays(state);v=arrays['ket'];model=p['model'];model_check(model,allow_fixture=fixture)
    ident=digest({'source':state['sha256'],'action':action});out=store.root/'transitions'/ident
    if out.exists():raise ValueError('ACTION_ALREADY_ATTEMPTED_NO_RETRY')
    out.mkdir(parents=True);intent={'source_state_sha256':state['sha256'],'action':action,'action_sha256':digest(action),'created_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'fixture':fixture}
    freeze(out/'intent.json',intent)
    params={'parent':state['state_id'],'world_spec':p['world_spec'],'model':model,'ket':v,'time_au':p['time_au'],'reason':kind,'control':p['control'],'control_origin_au':p['control_origin_au']}
    try:
        if kind=='APPLY_EXTERNAL_FIELD':params.update(control=copy.deepcopy(action['control']),control_origin_au=p['time_au'])
        elif kind=='PREPARE_ELECTRONIC_STATE':params.update(ket=np.eye(2,dtype=complex)[:,action['basis_index']])
        elif kind=='EVOLVE_QUANTUM_STATE':
            if p['control'] is None:raise ValueError('EXPLICIT_FIELD_CONTROL_REQUIRED_ZERO_ALLOWED')
            v,tr,obs=propagate(model,v,p['control'],p['time_au'],action['duration_au'],p['control_origin_au'],fixture=fixture,evidence_dir=out)
            raw=blob(store.root,tr);freeze(out/'RAW_PROPAGATION.json',{'arrays':raw,'observation':obs})
            if obs['status']!='CALCULATED_EFFECTIVE_MODEL':raise RuntimeError('NUMERICAL_PROPAGATION_QUALITY_FAILED_RAW_SAVED')
            # Save completed propagation arrays BEFORE publication/QA receipt.
            params.update(ket=v,trajectory=tr,time_au=p['time_au']+action['duration_au'],observation=obs)
        elif kind=='MEASURE_STATE_POPULATION':params.update(observation={'status':'READ_EXISTING_EFFECTIVE_STATE','population':np.abs(v).astype(float).tolist(),'population_definition':'Squared modulus, no new collapse/measurement backaction simulated'})
        if kind=='MEASURE_STATE_POPULATION':params['observation']['population']=(np.abs(v)**2).tolist()
        new=store.save(**params)
        receipt={**intent,'new_state_sha256':new['sha256'],'arrays_sha256':new['payload']['arrays']['sha256'],'status':'SOFTWARE_FIXTURE_ONLY' if fixture else 'EFFECTIVE_MODEL_TRANSITION','physical_action':kind,'model_source':model['source_type'],'scope':'No full-electron realtime dynamics, no W2 or discovery promotion'}
        freeze(out/'receipt.json',receipt);return new,receipt
    except BaseException as e:
        freeze(out/'FAILURE.json',{'type':type(e).__name__,'error':str(e),'parent_preserved':True,'no_retry':True});raise
