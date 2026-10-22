"""Opt-in, exactly-one-run execution wrapper. No GitHub API, no dispatch.

This is a local execution API for a *separately authorized* science container;
it cannot grant GitHub/write/compute permission. Its initial state is blocked.
"""
import json
import os
import pathlib
import sys
from .io import freeze_json,digest,utc_now
from .admission import select_engine
from .quality import quality_from_observation


def execute_once(spec, out_path, scope):
    if scope.get('authority')!='GRANTED_FOR_QW_PERIODIC02_SINGLE_RUN':
        raise PermissionError('EXTERNAL_EXECUTION_NOT_AUTHORIZED_FOR_THIS_STAGE')
    if scope.get('max_jobs')!=1 or scope.get('no_automatic_retry') is not True:
        raise PermissionError('NON_SINGLETON_EXECUTION_SCOPE')
    if scope.get('worldspec_sha256')!=digest(spec):
        raise PermissionError('EXECUTION_INPUT_NOT_HASH_BOUND_TO_AUTHORIZATION')
    if os.environ.get('QW_PERIODIC02_ACTIVE_SCOPE_SHA256')!=digest(scope):
        raise PermissionError('NO_ACTIVE_AUTHORIZED_EXECUTION_CONTEXT')
    decision=select_engine(spec)
    if decision['status']!='ELIGIBLE_FOR_RESOURCE_PREFLIGHT':
        raise ValueError('WORLD_SPEC_NOT_PHYSICALLY_ADMITTED')
    out=pathlib.Path(out_path)
    out.mkdir(parents=True,exist_ok=False)
    freeze_json(out/'authorized_scope.json',scope)
    freeze_json(out/'worldspec.json',spec)
    freeze_json(out/'engine_admission.json',decision)
    try:
        from recovery02r.isolated_router import run_isolated
        worker=pathlib.Path(__file__).with_name('science_worker.py')
        result=run_isolated(spec,out/'science',timeout=540,worker_path=worker)
        freeze_json(out/'world_result.json',result)
        qa=quality_from_observation(result)
        freeze_json(out/'claim_ceiling.json',qa)
        return {'result':result,'quality':qa}
    except BaseException as ex:
        freeze_json(out/'process_error.json',{'type':type(ex).__name__,'message':str(ex),
                  'no_auto_retry':True,'at':utc_now()})
        raise
