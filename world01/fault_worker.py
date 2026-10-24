"""Software fault injection only. No engine imports or scientific inputs."""
import json,os,pathlib,resource,signal,sys,time
resource.setrlimit(resource.RLIMIT_CORE,(0,0));out=pathlib.Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
request=json.loads(pathlib.Path(sys.argv[1]).read_text());mode=request['fault']
(out/'completed_fixture.json').write_text(json.dumps({'synthetic':True,'status':'SOFTWARE_FIXTURE_ONLY','completed_before_failure':True}))
print('SYNTHETIC_FAULT_START '+mode,flush=True)
if mode=='SIGSEGV':os.kill(os.getpid(),signal.SIGSEGV)
elif mode=='TIMEOUT':time.sleep(5)
elif mode=='MEMORY_LIMIT':
    (out/'worker_failure.json').write_text(json.dumps({'type':'MemoryError','synthetic':True,'note':'Injected resource exception, not real OOM'}));raise MemoryError('INJECTED_NO_ALLOCATION')
elif mode=='CORRUPT_JSON':(out/'observation.json').write_text('{BROKEN')
elif mode=='INTERRUPTED':os.kill(os.getpid(),signal.SIGTERM)
else:raise ValueError('UNKNOWN_FIXTURE_MODE')
