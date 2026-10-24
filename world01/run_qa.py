"""Offline-only regression entry point. Physics packages fail closed on import."""
import os,sys,importlib.abc,unittest,time,resource,json,pathlib,datetime
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
class NoNewPhysics(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'pyscf','qutip','psi4'}:raise ImportError('E00_NO_NEW_PHYSICS_ENGINE_IMPORT: '+fullname)
sys.meta_path.insert(0,NoNewPhysics())
from .test_e00 import E00
from interactive01.test_software import Software

def main():
    root=pathlib.Path(sys.argv[1]).resolve()
    root.mkdir(parents=True,exist_ok=False)
    os.environ['QW_EVIDENCE_ROOT']=str(root/'evidence')
    start=time.monotonic();before=resource.getrusage(resource.RUSAGE_SELF);cb=resource.getrusage(resource.RUSAGE_CHILDREN)
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(x) for x in (E00,Software)])
    with (root/'test.log').open('w') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    after=resource.getrusage(resource.RUSAGE_SELF);ca=resource.getrusage(resource.RUSAGE_CHILDREN)
    receipt={'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'wall_seconds':time.monotonic()-start,'process_tree_cpu_seconds':after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime+ca.ru_utime+ca.ru_stime-cb.ru_utime-cb.ru_stime,'parent_peak_rss_native':after.ru_maxrss,'rss_units':'bytes on macOS, KiB on Linux','new_physics':0,'engine_import_guard':['pyscf','qutip','psi4'],'new_purchase':0,'scope':'Software only, no scientific cgroup claim'}
    (root/'run_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
    return 0 if result.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
