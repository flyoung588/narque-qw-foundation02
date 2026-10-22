"""Dispatch a WorldSpec to existing mature backends inside an isolated worker.

Import the original science tools lazily. This module contains NO physics
solver, no predefined material energy, no automatic parameter relaxation.
"""
import json
import pathlib
import sys
import traceback

# Supports independent-process invocation by path from the existing supervisor.
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))


def execute(spec, out):
    from periodic02.admission import route_capability,result_route_status
    admitted=route_capability(spec)
    if admitted['status']!='SUPPORTED':
        return {'status':admitted['status'],'routing_status':admitted['status'],'reason':admitted['reason']}
    matter=spec['matter']['type']
    if matter=='periodic_cell':
        # The source-owned backend enforces independent cgroup admission,
        # periodic geometry and actual PBC SCF constraints.
        from qw_next.periodic_world import route_world
        result=route_world(spec,out)
        return {**result,'routing_status':result_route_status(result)}
    if matter=='molecule':
        from foundation01.runner import run_world
        result=run_world(spec)
        return {**result,'routing_status':result_route_status(result)}
    raise ValueError('UNSUPPORTED_WORLD_OBJECT')


def main():
    if len(sys.argv)!=3:
        raise SystemExit('usage: python -m periodic02.science_worker WORLDSPEC_JSON OUT_DIR')
    from periodic02.io import freeze_json
    spec=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))
    out=pathlib.Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
    try:
        result=execute(spec,out)
        freeze_json(out/'observation.json',result)
        if result.get('status')!='CALCULATED':
            raise RuntimeError('SOLVER_NOT_CALCULATED_NO_AUTOMATIC_RETRY')
    except BaseException as ex:
        freeze_json(out/'worker_failure.json',{
            'type':type(ex).__name__,'error':str(ex),'traceback':traceback.format_exc()})
        raise


if __name__=='__main__':
    main()
