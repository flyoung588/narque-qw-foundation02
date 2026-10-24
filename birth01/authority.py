"""Stdlib-only, source-bound Human scope check; never grants itself authority."""
import json,pathlib,hashlib
from world01.contracts import WorldError
ROOT=pathlib.Path(__file__).resolve().parent
LIMITS={'max_jobs':2,'per_job_wall_seconds':900,'worker_wall_seconds':600,'CPU':1,'threads':1,'memory_bytes':1073741824,'extra_swap':0,'network':'none','purchases':0,'no_retry':True}
def approval_check():
    scope=json.loads((ROOT/'AUTHORITY.json').read_text())
    if scope.get('status')!='HUMAN_GRANTED_WB_E01':raise WorldError('AUTHORITY_MISSING')
    prereg=ROOT/'FROZEN_PREREGISTRATION.json';signed=ROOT/'EXECUTION_SOURCE_SHA256.json'
    if not prereg.exists() or not signed.exists():raise WorldError('FROZEN_EXECUTION_SOURCE_MISSING')
    def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    if scope.get('prereg_sha256')!=sha(prereg) or scope.get('code_manifest_sha256')!=sha(signed) or scope.get('limits')!=LIMITS or not scope.get('human_approval_reference'):raise WorldError('AUTHORITY_SCOPE_MISMATCH')
    repo=ROOT.parent
    for rel,h in json.loads(signed.read_text())['files'].items():
        p=repo/rel
        if '..' in pathlib.PurePosixPath(rel).parts or not p.is_file() or sha(p)!=h:raise WorldError('EXECUTION_SOURCE_CHANGED')
    return scope


def job_budget_check(rows,current_id,source_sha,branch):
    """All attempts count, including failed/interrupted Jobs. Never refund a slot."""
    selected=[r for r in rows if r.get('head_branch')==branch]
    if len(selected)>LIMITS['max_jobs']:raise WorldError('BUDGET_EXHAUSTED')
    if not any(str(r['id'])==str(current_id) for r in selected):raise WorldError('RUN_HISTORY_EVIDENCE_INCOMPLETE')
    prior=[r for r in selected if str(r['id'])!=str(current_id)]
    if any(r.get('head_sha')==source_sha for r in prior):raise WorldError('NO_IMPLICIT_RETRY')
    if any(r.get('status')!='completed' or r.get('conclusion')!='success' for r in prior):raise WorldError('PREVIOUS_JOB_FAILED_OR_RUNNING')
    return {'count_including_current':len(selected),'prior_runs':len(prior),'status':'JOB_BUDGET_SCREEN_PASSED'}
