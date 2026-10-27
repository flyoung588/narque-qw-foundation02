"""Append-only hash-bound journal and verifiable derived checkpoint, not physics storage."""
import json,os,tempfile,pathlib,contextlib,fcntl,copy,datetime
from router import digest
from world01.contracts import WorldError
from world01.session import publish_bytes
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
class Journal:
 def __init__(self,root):
  self.root=pathlib.Path(root);self.root.mkdir(parents=True,exist_ok=True);(self.root/'events').mkdir(exist_ok=True)
 @contextlib.contextmanager
 def lock(self):
  with (self.root/'lock').open('a') as f:
   fcntl.flock(f,fcntl.LOCK_EX)
   try:yield
   finally:fcntl.flock(f,fcntl.LOCK_UN)
 def events(self):
  out=[];prev=None
  for i,p in enumerate(sorted((self.root/'events').glob('*.json'))):
   x=json.loads(p.read_text());h=x.pop('sha256')
   if x['seq']!=i or x['previous']!=prev or digest(x)!=h:raise WorldError('MEMORY_CHAIN_CORRUPT')
   if p.name!=f'{i:06d}-{h}.json':raise WorldError('MEMORY_EVENT_PATH_MISMATCH')
   x['sha256']=h;out.append(x);prev=h
  checkpoint=self.root/'checkpoint.json'
  if checkpoint.exists():
   c=json.loads(checkpoint.read_text());n=c.get('event_count')
   if type(n) is not int or n<0:raise WorldError('CHECKPOINT_INVALID')
   if n>len(out):raise WorldError('CHECKPOINT_AHEAD_OF_JOURNAL')
   if c.get('journal_head')!=(out[n-1]['sha256'] if n else None):raise WorldError('CHECKPOINT_HASH_MISMATCH')
  return out
 def append(self,kind,data):
  # Caller holds the process lock for multi-event transactions.
  es=self.events();v={'seq':len(es),'previous':es[-1]['sha256'] if es else None,'kind':kind,'time_utc':now(),'data':copy.deepcopy(data)};h=digest(v);v['sha256']=h
  publish_bytes(self.root/'events'/f'{len(es):06d}-{h}.json',(json.dumps(v,sort_keys=True,allow_nan=False,indent=2)+'\n').encode());return v
 def checkpoint(self):
  es=self.events();v={'journal_head':es[-1]['sha256'] if es else None,'event_count':len(es),'derived_only':True}
  fd,tmp=tempfile.mkstemp(dir=self.root)
  with os.fdopen(fd,'w') as f:json.dump(v,f);f.flush();os.fsync(f.fileno())
  os.replace(tmp,self.root/'checkpoint.json');return v
 def query(self,kind=None):return [e for e in self.events() if kind is None or e['kind']==kind or (e['kind']=='Memory' and e['data']['kind']==kind)]
