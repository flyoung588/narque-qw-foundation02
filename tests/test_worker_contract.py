"""Subprocess integration using an explicitly SYNTHETIC backend, not PySCF."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from periodic02.construct import from_prototype

ROOT=pathlib.Path(__file__).resolve().parents[1]
CHOICES=json.loads((ROOT/'decisions/AI_PRECOMPUTE_CHOICES.json').read_text())

class WorkerContract(unittest.TestCase):
    def invoke(self, fail=False):
        with tempfile.TemporaryDirectory() as temp:
            path=pathlib.Path(temp)
            q=path/'qw_next';q.mkdir();(q/'__init__.py').write_text('')
            (q/'periodic_world.py').write_text(
                'def route_world(spec,out):\n'
                + (' raise RuntimeError("SYNTHETIC_SOLVER_EXCEPTION")\n' if fail else
                ' return {"status":"CALCULATED","synthetic":True,"spec":spec,"observation":{"test_only":True}}\n'))
            spec=from_prototype(CHOICES['candidates'][0])['spec']
            (path/'request.json').write_text(json.dumps(spec))
            o=path/'result'
            env=os.environ.copy();env['PYTHONPATH']=str(path)+os.pathsep+str(ROOT)
            p=subprocess.run([sys.executable,'-B',str(ROOT/'periodic02/science_worker.py'),
                              str(path/'request.json'),str(o)],
                             cwd=str(path),env=env,capture_output=True,text=True,timeout=8)
            if fail:
                self.assertNotEqual(p.returncode,0)
                self.assertTrue((o/'worker_failure.json').exists())
                self.assertFalse((o/'observation.json').exists())
            else:
                self.assertEqual(p.returncode,0,p.stderr)
                value=json.loads((o/'observation.json').read_text())
                self.assertTrue(value['synthetic'])
                self.assertEqual(value['spec'],spec)
    def test_synthetic_success_contract(self):self.invoke(False)
    def test_synthetic_failure_receipt(self):self.invoke(True)

if __name__=='__main__':unittest.main()
