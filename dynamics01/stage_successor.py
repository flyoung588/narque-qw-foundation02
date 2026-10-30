import pathlib,json,subprocess,hashlib,base64
from world01.session import filehash
from router import digest
from dynamics01.transfer import stage_parent

def stage(r,w,ident,old,transport):
 proof_path=w.root/'remote_provenance'/f'{ident}.json';record=json.loads(proof_path.read_text());proof=record['verified_run'];assert proof['status']=='completed' and proof['conclusion']=='success' and proof['run_attempt']==1
 refs=stage_parent(w,ident,r/'repo');apiroot='repos/'+old['repository']
 def api(path,body=None):
  args=['/opt/homebrew/bin/gh','api',apiroot+'/'+path]
  if body is not None:args+=['--method','POST','--input','-']
  p=subprocess.run(args,input=json.dumps(body).encode() if body else None,capture_output=True,check=True);return json.loads(p.stdout)
 current=api('git/ref/heads/'+old['branch']);assert current['object']['sha']==old['code_commit']
 tree=api('git/trees/'+old['code_commit']+'?recursive=1');assert not tree['truncated'];existing={v['path']:v['sha'] for v in tree['tree'] if v['type']=='blob'};add=[]
 for v in refs.values():
  path=v['source_path'];raw=(r/'repo'/path).read_bytes();assert hashlib.sha256(raw).hexdigest()==v['sha256'];blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
  if path in existing:assert existing[path]==blob
  else:
   b=api('git/blobs',{'content':base64.b64encode(raw).decode(),'encoding':'base64'});assert b['sha']==blob;add.append({'path':path,'mode':'100644','type':'blob','sha':blob})
 assert 0<len(add)<20
 t=api('git/trees',{'base_tree':tree['sha'],'tree':add});c=api('git/commits',{'message':'Stage exact verified first-return state bytes for bounded successor decision','tree':t['sha'],'parents':[old['code_commit']]})
 # Update only this approved successor ref, never force or rewrite history.
 args=['/opt/homebrew/bin/gh','api','--method','PATCH',apiroot+'/git/refs/heads/'+old['branch'],'--input','-'];subprocess.run(args,input=json.dumps({'sha':c['sha'],'force':False}).encode(),capture_output=True,check=True)
 diff=api('compare/'+old['code_commit']+'...'+c['sha']);assert diff['status']=='ahead' and diff['ahead_by']==1 and {x['filename'] for x in diff['files']}=={x['path'] for x in add} and all(x['status']=='added' for x in diff['files'])
 source={str(p.relative_to(r/'repo')):filehash(p) for p in (r/'repo').rglob('*') if p.is_file() and p.suffix in ('.py','.json','.f90','.npz') and '__pycache__' not in p.parts and '.git' not in p.parts}
 g=dict(old);g.update(code_commit=c['sha'],source_sha256=digest(source),staged_world_files=refs,parent_execution={k:proof[k] for k in ('run_id','job_id','code_commit','raw_log_sha256')},staging_diff=sorted(x['path'] for x in add))
 (r/'SECOND_SOURCE_STAGING.json').write_text(json.dumps({'state':ident,'parent_proof_sha256':filehash(proof_path),'commit':c,'compare':diff,'references':refs,'source_sha256':digest(source),'no_condition_selected':True,'no_solver_changes':True},indent=2));return g
