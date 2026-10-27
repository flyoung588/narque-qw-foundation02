"""Derive engineering fixtures ONLY from pinned original transitions."""
import json,pathlib
from .fabric import require
DOMAINS={'QW_CORRELATED_ELECTRONIC_STATE_01':'correlated','QW_EFFECTIVE_QUANTUM_STATE_01':'effective'}
def examples(repo,manifest):
 repo=pathlib.Path(repo);found={}
 for rel in manifest['files']:
  if '/transitions/' not in rel or not rel.endswith('/receipt.json'):continue
  r=json.loads((repo/rel).read_text())
  if not all(k in r for k in ('action','source_state_sha256','new_state_sha256')):continue
  base=pathlib.PurePosixPath(rel).parent.parent.parent;t=base/'states'/f"{r['new_state_sha256']}.json";s=base/'states'/f"{r['source_state_sha256']}.json"
  if str(t) not in manifest['files'] or str(s) not in manifest['files']:continue
  state=json.loads((repo/t).read_text());p=state['payload'];domain=DOMAINS.get(p['schema'],'periodic' if p['world_spec']['matter']['periodic'] else 'molecular')
  if domain=='effective' and r['action']['type']!='EVOLVE_QUANTUM_STATE':continue
  if domain not in ('molecular','effective','correlated') or domain in found:continue
  found[domain]={'receipt_path':rel,'source_path':str(s),'input_state':r['source_state_sha256'],'target_state':r['new_state_sha256'],'operation':r['action'],'world_spec':p['world_spec']}
 require(set(found)=={'molecular','effective','correlated'},'ARCHIVAL_DOMAINS_MISSING');return found

def replay_intent(example,domain,world,research='SOFTWARE_INTEGRATION_QA'):
 return {'research_session':research,'world_session':str(world.root.resolve()),'goal':'Route an existing physics transition and preserve its exact state and model semantics','candidate':domain+'-archive','model':domain,'operation':example['operation'],'input_state':example['input_state'],'prediction':'Original immutable state/observation will be recovered, not recomputed','falsifier':'Any changed state, hash, unsupported value or new solver call','observables':{'molecular':['energy','forces'],'effective':['population','norm','time'],'correlated':['energy','natural_occupations']}[domain],'resource_ref':'ZERO_NEW_SCIENCE_OFFLINE','authorization_ref':'HUMAN_OFFLINE_INTEGRATION_MANDATE','stop_condition':'Stop on mismatch or after bounded engineering trace','mode':'HISTORICAL_REAL_EVIDENCE_REPLAY','receipt_path':example['receipt_path']}
