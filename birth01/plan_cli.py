"""Prepare an immutable request/handoff plan only; never dispatch a job."""
import argparse,json,pathlib
from world01.session import WorldSession
from .preparation import BirthPreparation
p=argparse.ArgumentParser();p.add_argument('--baseline',required=True);p.add_argument('--source-manifest',required=True);p.add_argument('--session',required=True);p.add_argument('--source-file',required=True);p.add_argument('--request',required=True);a=p.parse_args()
s=WorldSession(a.session,a.baseline,json.loads(pathlib.Path(a.source_manifest).read_text()));s.reference(a.source_file)
b=BirthPreparation(s,pathlib.Path(a.session)/'birth');i=b.submit(json.loads(pathlib.Path(a.request).read_text()));print(json.dumps(b.execution_plan(i),indent=2))
