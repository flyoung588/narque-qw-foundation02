"""Use: python -m foundation01 validate spec.json | run spec.json output.json."""
import argparse
import json
from .contract import validate
from .runner import run_world,save_json

p=argparse.ArgumentParser();p.add_argument('command',choices=('validate','run'))
p.add_argument('spec');p.add_argument('output',nargs='?')
a=p.parse_args();s=json.loads(open(a.spec).read());
if a.command=='validate':print(json.dumps(validate(s),indent=2))
else:
 out=run_world(s)
 if a.output:save_json(a.output,out)
 print(json.dumps({'status':out['status'],'object_id':s['object_id'],'observation':out['observation']},indent=2))
