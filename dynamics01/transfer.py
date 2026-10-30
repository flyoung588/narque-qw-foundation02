"""Bounded hashed array transfer; no server, artifact storage, network or API calls.
Reuse existing authenticated raw Job logs, with short independently indexed lines.
"""
import pathlib,json,hashlib,base64,zlib
from world01.contracts import WorldError
def require(ok,code):
 if not ok:raise WorldError(code)
MAX_BYTES=32*1024*1024

def parent_files(world,ident):
 world.load(ident) # verifies new-science provenance against inherited execution journal
 files={};seen=set()
 while ident:
  require(ident not in seen,'ANCESTRY_CYCLE');seen.add(ident);s=world.store.load(ident)
  for rel in ('states/'+ident+'.json','references/'+ident+'.json',s['payload']['arrays']['path']):files[rel]=world.root/rel
  proof=world.root/'remote_provenance'/f'{ident}.json'
  if proof.exists():files['remote_provenance/'+ident+'.json']=proof
  ident=s['payload'].get('parent_state_id')
 require(sum(p.stat().st_size for p in files.values())<=MAX_BYTES,'STATE_TRANSFER_TOO_LARGE');return files

def stage_parent(world,ident,repo):
 """Offline preparation only. Publication requires matching Human authorization."""
 from world01.session import filehash,publish_bytes
 files=parent_files(world,ident)
 for rel,p in files.items():publish_bytes(pathlib.Path(repo)/'dynamics01/staged'/rel,p.read_bytes())
 return {rel:{'source_path':'dynamics01/staged/'+rel,'sha256':filehash(p)} for rel,p in files.items()}

def staged_references(world,ident,grant):
 from world01.session import filehash
 refs=grant.get('staged_world_files',{});actual=parent_files(world,ident);require(set(actual)<=set(refs),'DYNAMIC_PARENT_NOT_STAGED_IN_AUTHORIZED_COMMIT')
 for rel,p in actual.items():require(refs[rel]['sha256']==filehash(p),'STAGED_PHYSICAL_PARENT_MISMATCH')
 return {rel:refs[rel] for rel in actual}

def encode_package(package):
 raw=json.dumps(package,sort_keys=True,separators=(',',':'),allow_nan=False).encode();require(len(raw)<=MAX_BYTES,'DYNAMIC_EVIDENCE_TOO_LARGE');h=hashlib.sha256(raw).hexdigest();encoded=base64.b64encode(zlib.compress(raw)).decode();chunks=[encoded[i:i+3000] for i in range(0,len(encoded),3000)];require(len(chunks)<=12000,'DYNAMIC_CHUNK_LIMIT')
 return ['QWDYN_HEADER='+json.dumps({'sha256':h,'chunks':len(chunks),'raw_bytes':len(raw)},separators=(',',':'))]+['QWDYN_CHUNK='+str(i)+':'+s for i,s in enumerate(chunks)]

def decode_package(log):
 headers=[s.split('QWDYN_HEADER=',1)[1].strip() for s in log.splitlines() if 'QWDYN_HEADER=' in s];require(len(headers)==1,'DYNAMIC_HEADER_NOT_UNIQUE');meta=json.loads(headers[0]);require(type(meta['chunks']) is int and 0<meta['chunks']<=12000 and type(meta['raw_bytes']) is int and 0<meta['raw_bytes']<=MAX_BYTES,'DYNAMIC_PACKAGE_BOUNDS')
 parts={}
 for line in log.splitlines():
  if 'QWDYN_CHUNK=' not in line:continue
  s=line.split('QWDYN_CHUNK=',1)[1].strip();i,v=s.split(':',1);i=int(i);require(i not in parts and 0<=i<meta['chunks'] and len(v)<=3000,'DYNAMIC_CHUNK_DUPLICATE_OR_RANGE');parts[i]=v
 require(len(parts)==meta['chunks'],'DYNAMIC_CHUNK_MISSING');packed=base64.b64decode(''.join(parts[i] for i in range(meta['chunks'])),validate=True);d=zlib.decompressobj();raw=d.decompress(packed,MAX_BYTES+1);require(d.eof and len(raw)==meta['raw_bytes'] and hashlib.sha256(raw).hexdigest()==meta['sha256'],'DYNAMIC_PACKAGE_HASH_OR_SIZE_MISMATCH');return json.loads(raw)
