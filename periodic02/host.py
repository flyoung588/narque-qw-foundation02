"""Standard free GitHub host: one CPU, 1 GiB, no swap, offline science.

Does NOT schedule or dispatch a job, and is not used in this local preparation.
"""
import json
import os
import pathlib
import subprocess
import sys
import traceback


def main():
    out=pathlib.Path(os.environ['RUNNER_TEMP'])/'qw-periodic02-results'
    out.mkdir(parents=True,exist_ok=True)
    cpu=min(os.sched_getaffinity(0))
    cmd=['docker','create','--network','none','--memory','1g','--memory-swap','1g',
         '--cpus','1','--cpuset-cpus',str(cpu),'--pids-limit','64',
         '--cap-drop','ALL','--security-opt','no-new-privileges','--read-only',
         '--user',f'{os.getuid()}:{os.getgid()}',
         '--tmpfs','/tmp:rw,nosuid,size=512m',
         '--mount',f'type=bind,src={out},dst=/out',
         '-e','GITHUB_SHA='+os.environ['GITHUB_SHA'],
         'qw-periodic02:once']
    cid=None
    try:
        cid=subprocess.check_output(cmd,text=True).strip()
        info=json.loads(subprocess.check_output(['docker','inspect',cid],text=True))[0]
        cfg=info['HostConfig']
        if not (cfg['Memory']==1073741824 and cfg['MemorySwap']==1073741824
                and cfg['NanoCpus']==1000000000 and cfg['NetworkMode']=='none'
                and cfg['Privileged'] is False):
            raise RuntimeError('SCIENCE_CONTAINER_RESOURCE_CONTRACT_REJECTED')
        (out/'host_config.json').write_text(json.dumps({
            'memory':cfg['Memory'],'memory_swap_total':cfg['MemorySwap'],
            'cpu_quota_nano':cfg['NanoCpus'],'network':cfg['NetworkMode'],
            'uid':info['Config']['User'],'image':info['Image']},indent=2)+'\n')
        code=subprocess.run(['docker','start','-a',cid],timeout=650).returncode
        if code:
            raise RuntimeError(f'SCIENCE_CONTAINER_EXIT_{code}')
    except BaseException as ex:
        (out/'host_failure.json').write_text(json.dumps({'type':type(ex).__name__,
            'message':str(ex),'traceback':traceback.format_exc()},indent=2)+'\n')
        raise
    finally:
        if cid:
            subprocess.run(['docker','kill',cid],stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,timeout=3)
            subprocess.run(['docker','rm',cid],stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,timeout=3)

if __name__=='__main__':main()
