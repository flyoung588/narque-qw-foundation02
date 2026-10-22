"""Unified state/action dispatch, with isolated FCI solver and preserved failures."""
import pathlib
import numpy as np
from interactive01.world import apply,freeze,verify
from recovery02r.isolated_router import run_isolated
from router import digest
from frontier01.contract import validate
def _execute(request,out):
    result=run_isolated(request,out,timeout=420,worker_path=pathlib.Path(__file__).with_name('solver_worker.py'))
    arrays=None
    if result.get('status')=='CALCULATED':
        with np.load(pathlib.Path(out)/'scientific_arrays.npz',allow_pickle=False) as z:arrays={k:z[k].copy() for k in z.files}
    return result,arrays
def _transition(store,request,parent,action,*,authority,resources,execute=None):
    validate(request);verify(parent)
    ident=digest({'parent':parent['sha256'],'request':request,'action':action});out=store.root/'transitions'/ident
    if out.exists():raise ValueError('TRANSITION_ALREADY_ATTEMPTED_NO_RETRY')
    if not authority or not resources:raise ValueError('ADMISSION_PENDING')
    out.mkdir(parents=True)
    freeze(out/'intent.json',{'parent':parent['sha256'],'request':request,'request_sha256':digest(request),'action':action})
    try:
        result,arrays=(execute or _execute)(request,out/'solver')
        if result.get('status')!='CALCULATED':raise RuntimeError('SOLVER_FAILED_NO_RETRY')
        state=store.save_correlated(request,result,arrays,parent['sha256'],parent['payload']['atom_ids'])
    except BaseException as e:
        freeze(out/'failure.json',{'type':type(e).__name__,'error':str(e),'parent_preserved':True});raise
    receipt={'status':'CALCULATED_MODEL_ONLY','source_state_sha256':parent['sha256'],'new_state_sha256':state['sha256'],'request_sha256':digest(request),'observation_sha256':digest(result),'action':action,'scope':'Finite-basis correlated BO electronic state; not nuclear time evolution'}
    freeze(out/'receipt.json',receipt);return state,receipt
def prepare(store,request,*,authority=False,resources=False):
    validate(request);source=store.create(request['world_spec'],'REFERENCE_STRUCTURE_BEFORE_FCI')
    return _transition(store,request,source,{'type':'PREPARE_CORRELATED_STATE'},authority=authority,resources=resources)
def act(store,state,action,*,authority=False,resources=False):
    verify(state)
    if state['payload']['schema']!='QW_CORRELATED_ELECTRONIC_STATE_01':
        from state_space01.world_runtime import act as old_act
        return old_act(store,state,action,authority=authority,resources=resources)
    if action['type']!='DISPLACE_ATOM':raise ValueError('ONLY_EXISTING_BOUNDED_DISPLACEMENT_EXECUTABLE')
    spec=apply(state,action)
    # First tranche allows one z-directed displacement only; no scan.
    if action['vector'][0]!=0 or action['vector'][1]!=0:raise ValueError('FROZEN_Z_ACTION_DOMAIN')
    request={'world_spec':spec,'correlation_model':state['payload']['correlation_model']}
    return _transition(store,request,state,action,authority=authority,resources=resources)
