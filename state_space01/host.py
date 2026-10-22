"""One container only. No dispatch, retry, second action or decision generation."""
import json,os,pathlib,subprocess,traceback
out=pathlib.Path(os.environ['RUNNER_TEMP'])/'state-space01-results';out.mkdir(exist_ok=True);cid=None
try:
    cpu=min(os.sched_getaffinity(0))
    cid=subprocess.check_output(['docker','create','--network','none','--memory','1g','--memory-swap','1g','--cpus','1','--cpuset-cpus',str(cpu),'--pids-limit','64','--cap-drop','ALL','--security-opt','no-new-privileges','--read-only','--user',f'{os.getuid()}:{os.getgid()}','--tmpfs','/tmp:rw,nosuid,size=512m','--mount',f'type=bind,src={out},dst=/out','-e','GITHUB_SHA='+os.environ['GITHUB_SHA'],'state-space01:once'],text=True).strip()
    h=json.loads(subprocess.check_output(['docker','inspect',cid]))[0]['HostConfig']
    assert h['Memory']==h['MemorySwap']==1073741824 and h['NanoCpus']==1000000000 and h['NetworkMode']=='none' and h['Privileged'] is False
    (out/'host_config.json').write_text(json.dumps(h,indent=2))
    code=subprocess.run(['docker','start','-a',cid],timeout=540).returncode
    if code:raise RuntimeError('CONTAINER_EXIT_'+str(code))
except BaseException as e:
    (out/'HOST_FAILURE.json').write_text(json.dumps({'type':type(e).__name__,'error':str(e),'traceback':traceback.format_exc()}));raise
finally:
    if cid:
        subprocess.run(['docker','kill',cid],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=3)
        subprocess.run(['docker','rm',cid],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=3)
