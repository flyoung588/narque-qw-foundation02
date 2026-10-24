"""Prepared host wrapper; only a later approved manual Job may call main."""
import os,pathlib,json,subprocess,traceback
from .authority import approval_check,job_budget_check

def main():
    approval_check()
    import urllib.request
    repository=os.environ['GITHUB_REPOSITORY'];branch=os.environ['GITHUB_REF_NAME']
    if os.environ.get('RUNNER_ENVIRONMENT')!='github-hosted':raise RuntimeError('STANDARD_HOSTED_RUNNER_REQUIRED')
    headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json'}
    repo_request=urllib.request.Request(f'https://api.github.com/repos/{repository}',headers=headers)
    with urllib.request.urlopen(repo_request,timeout=20) as response:repo_meta=json.load(response)
    if repo_meta.get('private') is not False:raise RuntimeError('PUBLIC_REPOSITORY_FREE_POLICY_REQUIRED')
    url=f'https://api.github.com/repos/{repository}/actions/workflows/world-birth-once.yml/runs?branch={branch}&per_page=100'
    request=urllib.request.Request(url,headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(request,timeout=20) as response:history=json.load(response)
    if history.get('total_count',101)>100:raise RuntimeError('RUN_HISTORY_TOO_LARGE_FAIL_CLOSED')
    budget=job_budget_check(history['workflow_runs'],os.environ['GITHUB_RUN_ID'],os.environ['GITHUB_SHA'],branch)
    out=pathlib.Path(os.environ['RUNNER_TEMP'])/'wb-e01';out.mkdir(parents=True,exist_ok=False)
    (out/'job_budget.json').write_text(json.dumps(budget,indent=2)+'\n')
    cpu=min(os.sched_getaffinity(0));cid=None
    cmd=['docker','create','--network','none','--cpus','1','--cpuset-cpus',str(cpu),'--memory','1g','--memory-swap','1g','--pids-limit','64','--cap-drop','ALL','--security-opt','no-new-privileges','--read-only','--user',f'{os.getuid()}:{os.getgid()}','--tmpfs','/tmp:rw,nosuid,size=512m','--mount',f'type=bind,src={out},dst=/out','qw-world-e01:once','python','-B','-m','birth01.job_entry','--request','/app/birth01/SCIENCE_REQUEST.json']
    if pathlib.Path('birth01/PREVIOUS_SESSION/SESSION_SHA256.json').exists():cmd+=['--previous-session','/app/birth01/PREVIOUS_SESSION']
    try:
        cid=subprocess.check_output(cmd,text=True).strip();info=json.loads(subprocess.check_output(['docker','inspect',cid],text=True))[0];cfg=info['HostConfig']
        if cfg['Memory']!=2**30 or cfg['MemorySwap']!=2**30 or cfg['NanoCpus']!=10**9 or cfg['NetworkMode']!='none' or cfg['Privileged']:raise RuntimeError('HOST_RESOURCE_ADMISSION_FAILED')
        (out/'host_config.json').write_text(json.dumps(info,indent=2)+'\n')
        result=subprocess.run(['docker','start','-a',cid],timeout=630)
        if result.returncode:raise RuntimeError('CONTAINER_FAILED_NO_RETRY')
    except BaseException as e:
        (out/'host_failure.json').write_text(json.dumps({'error':str(e),'type':type(e).__name__,'traceback':traceback.format_exc(),'retry':False},indent=2)+'\n');raise
    finally:
        if cid:
            subprocess.run(['docker','kill',cid],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=3)
            subprocess.run(['docker','rm',cid],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=3)
if __name__=='__main__':main()
