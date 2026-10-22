"""One authorized proposal -> one real WorldSpec -> isolated mature backend.

No embedded AI LLM calls, no additional candidate fallbacks, no repeated runs.
"""
import json
import os
import pathlib
import platform
import resource
import sys
import time
import traceback
sys.path.insert(0,'/app')
from periodic02.io import read_json,freeze_json,digest,utc_now
from periodic02.run_once import execute_once
from periodic02.admission import select_engine

OUT=pathlib.Path('/out')

def cgroup():
    cg=pathlib.Path('/sys/fs/cgroup')
    return {k:(cg/k).read_text().strip() for k in ('memory.max','memory.swap.max',
        'memory.peak','memory.events','cpu.max','cpu.stat')}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    try:
        cg=cgroup()
        if (cg['memory.max']!='1073741824' or cg['memory.swap.max']!='0' or
            cg['cpu.max']!='100000 100000' or
            os.listdir('/sys/class/net')!=['lo'] or len(os.sched_getaffinity(0))!=1):
            raise RuntimeError('SCIENCE_CGROUP_ADMISSION_BLOCKED')
        freeze_json(OUT/'admission.json',{'cgroup':cg,'network':os.listdir('/sys/class/net'),
                                         'affinity':list(os.sched_getaffinity(0))})
        decision=read_json('/app/decisions/PREOBSERVATION_FROZEN.json')
        selected=decision['selected_first_candidate_id']
        if decision['human_approval_for_next_science_job']!='NOT_GRANTED':
            raise RuntimeError('FROZEN_AI_DECISION_AUTHORITY_FIELD_MUTATED')
        target=[c for c in decision['candidates'] if c['proposal']['id']==selected]
        if len(target)!=1:
            raise RuntimeError('SELECTED_AI_CANDIDATE_NOT_UNIQUE')
        spec=target[0]['worldspec']
        if digest(spec)!=target[0]['worldspec_sha256']:
            raise RuntimeError('FROZEN_WORLDSPEC_HASH_MISMATCH')
        scope=read_json('/app/periodic02/EXECUTION_SCOPE_TEMPLATE.json')
        # Template requires a *new* signed-off external scope and may not be
        # relabeled by the frozen AI decision itself. Real approval is external.
        if scope.get('authority')!='GRANTED_FOR_QW_PERIODIC02_SINGLE_RUN':
            raise PermissionError('NEW_PERIODIC02_EXTERNAL_SCOPE_NOT_GRANTED')
        freeze_json(OUT/'science_context.json',{'source_sha':os.environ.get('GITHUB_SHA'),
                   'python':platform.python_version(),'selected_candidate':selected,
                   'source_worldspec_sha256':digest(spec),
                   'scientific_qualification':'UNVERIFIED_PENDING_REAL_RUN'})
        os.environ['QW_PERIODIC02_ACTIVE_SCOPE_SHA256']=digest(scope)
        returned=execute_once(spec,OUT/'science_run',scope)
        if returned['quality']['status']!='BOUNDED_CALCULATED':
            raise RuntimeError('NO_BOUNDED_PERIODIC_PHYSICAL_RESULT')
    except BaseException as ex:
        freeze_json(OUT/'execution_failure.json',{'type':type(ex).__name__,
                     'message':str(ex),'traceback':traceback.format_exc(),
                     'no_rerun':True,'at':utc_now()})
        raise
    finally:
        freeze_json(OUT/'resource_end.json',{'wall_seconds':time.monotonic()-started,
                    'cgroup':cgroup(),'self_maxrss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                    'children_maxrss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss})

if __name__=='__main__':main()
