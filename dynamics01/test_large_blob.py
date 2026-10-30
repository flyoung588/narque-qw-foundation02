"""Bounded E01S fault injection; real acquisition is separate and hash-replayed.
No model, solver, propagation, dispatch or genuine network inside this suite.
"""
import pathlib,tempfile,json,hashlib,base64,copy,unittest,os
from unittest.mock import patch
from live_fabric01.github_transport import GithubFabricTransport
from world01.contracts import WorldError
ROOT=pathlib.Path(__file__).resolve().parents[2]
REPO='flyoung588/narque-qw-foundation02';RID=1427746629;COMMIT='9a636fd55ac169df9e680dd743144c72b254ad7c';PATH='dynamics01/staged/arrays/238420577a937ec59c64b1987971fa5b541798c55f01ed17c18b395ca448c593.npz'
def sha(b):return hashlib.sha256(b).hexdigest()
def blobsha(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
class Fixture:
 def __init__(self,root,raw=b'bounded small JSON\n'):
  self.root=pathlib.Path(root);self.root.mkdir(parents=True,exist_ok=True);self.raw=raw;self.path='staged/file.npz';self.commit=COMMIT;self.tree_sha='1'*40;self.entry={'path':self.path,'mode':'100644','type':'blob','sha':blobsha(raw),'size':len(raw)};self.repo={'id':RID,'full_name':REPO};self.commit_meta={'sha':COMMIT,'tree':{'sha':self.tree_sha}};self.tree={'sha':self.tree_sha,'truncated':False,'tree':[self.entry]};self.content={'path':self.path,'type':'file','sha':blobsha(raw),'size':len(raw),'encoding':'base64','content':base64.b64encode(raw).decode()};self.blob={'sha':blobsha(raw),'size':len(raw),'encoding':'base64','content':base64.b64encode(raw).decode()};self.calls=[];self.fail=False;self.t=GithubFabricTransport(self.root/'client');self.t._get=self.get
 def large(self):self.content.update(encoding='none',content='');return self
 def get(self,path,attempt,label):
  self.calls.append(path)
  if self.fail:raise WorldError('GITHUB_API_FAILED')
  prefix='repos/'+REPO
  if path==prefix:return self.repo
  if path==prefix+'/git/commits/'+self.commit:return self.commit_meta
  if path==prefix+'/git/trees/'+self.tree_sha+'?recursive=1':return self.tree
  if path==prefix+'/contents/'+self.path+'?ref='+self.commit:return self.content
  if path==prefix+'/git/blobs/'+self.entry['sha']:return self.blob
  raise AssertionError('UNPLANNED_FIXTURE_API '+path)
 def read(self,**kw):
  args={'repository':REPO,'repository_id':RID,'commit':self.commit,'path':self.path,'expected_sha256':sha(self.raw),'attempt':self.root,'label':'fixture','expected_size':len(self.raw)};args.update(kw);return self.t.read_verified_remote_blob(**args)
class LargeBlobRepair(unittest.TestCase):
 def setUp(self):
  self.root=pathlib.Path(os.environ.get('QW_BLOB_TEST_EVIDENCE',tempfile.mkdtemp()))/self._testMethodName;self.f=Fixture(self.root)
 def tearDown(self):(self.root/'SYNTHETIC_API_CALLS.json').write_text(json.dumps({'fixture':True,'actual_network':False,'calls':self.f.calls},indent=2))
 def reject(self,fn,code=None):
  with self.assertRaises(WorldError) as cm:fn()
  if code:self.assertIn(code,str(cm.exception))
 def test_T01_small_contents_base64(self):
  self.assertEqual(self.f.read(),self.f.raw);self.assertFalse(any('/git/blobs/' in x for x in self.f.calls))
 def test_T02_this_task_actual_npz_acquisition_evidence(self):
  # Evidence from new real code path, not previous E01R independent blob check.
  p=ROOT/'evidence/real-acquisition';r=json.loads((p/'REAL_REMOTE_RESULT.json').read_text());b=(p/'VERIFIED_REMOTE_ORIGINAL.npz').read_bytes();self.assertEqual(len(b),1792909);self.assertEqual(sha(b),pathlib.Path(PATH).stem);self.assertTrue(r['new_code_path']);self.assertEqual(r['production_pre_dispatch_verifier'],'PASS')
 def test_T03_none_encoding_blob_path(self):
  self.f.large();self.assertEqual(self.f.read(),self.f.raw);self.assertTrue(any('/git/blobs/' in x for x in self.f.calls))
 def test_T04_wrong_git_blob_sha(self):
  self.f.large();self.f.blob['sha']='f'*40;self.reject(self.f.read,'REMOTE_BLOB_RESPONSE_ID_MISMATCH');self.f.blob['sha']=self.f.entry['sha'];self.f.blob['content']=base64.b64encode(b'X'*len(self.f.raw)).decode();self.reject(self.f.read,'REMOTE_BLOB_OBJECT_ID_MISMATCH')
 def test_T05_wrong_approved_sha256(self):self.reject(lambda:self.f.read(expected_sha256='0'*64),'REMOTE_BLOB_SHA256_MISMATCH')
 def test_T06_wrong_frozen_commit(self):
  self.f.commit_meta['sha']='f'*40;self.reject(self.f.read,'REMOTE_BLOB_COMMIT_MISMATCH');self.reject(lambda:self.f.read(commit='main'),'REMOTE_BLOB_COMMIT_INVALID')
 def test_T07_truncated_bytes_and_invalid_base64(self):
  self.f.large();self.f.blob['content']=base64.b64encode(self.f.raw[:-1]).decode();self.reject(self.f.read,'REMOTE_BLOB_BYTES_SIZE_MISMATCH');self.f.blob['content']='%%%';self.reject(self.f.read,'REMOTE_BLOB_BASE64_INVALID')
 def test_T08_wrong_size_and_incomplete_tree(self):
  self.reject(lambda:self.f.read(expected_size=123456),'REMOTE_BLOB_TREE_SIZE_MISMATCH');self.f.tree['truncated']=True;self.reject(self.f.read,'REMOTE_BLOB_TREE_INCOMPLETE')
 def test_T09_wrong_repository_path_symlink(self):
  self.reject(lambda:self.f.read(repository='other/repo'),'REMOTE_BLOB_REPOSITORY_NOT_AUTHORIZED');self.f.repo['id']=1;self.reject(self.f.read,'REMOTE_BLOB_REPOSITORY_MISMATCH');self.f.repo['id']=RID;self.f.entry['path']='wrong/file';self.reject(self.f.read,'REMOTE_BLOB_PATH_NOT_UNIQUE');self.f.entry['path']=self.f.path;self.f.entry['mode']='120000';self.reject(self.f.read,'REMOTE_BLOB_NOT_REGULAR_FILE');self.reject(lambda:self.f.read(path='../escape'),'REMOTE_BLOB_PATH_INVALID')
 def test_T10_api_unavailable_fail_closed(self):self.f.fail=True;self.reject(self.f.read,'GITHUB_API_FAILED')
 def test_T11_original_initial_wavefunction_fixture(self):
  raw=(ROOT/'repo'/PATH).read_bytes();f=Fixture(self.root/'npz',raw).large();self.assertEqual(f.read(),raw);self.assertEqual(blobsha(raw),'c2867679bd32b924da04f6b3c90e3b5fb42116e7')
 def test_T12_second_commit_queries_are_independent(self):
  self.f.large();self.f.read();self.f.commit='f'*40;self.f.commit_meta['sha']=self.f.commit;self.f.read();self.assertTrue(any('/git/commits/'+COMMIT==x.split(REPO)[-1] for x in self.f.calls));self.assertTrue(any('/git/commits/'+'f'*40 in x for x in self.f.calls));self.assertFalse(any('/branches/' in x or 'heads/' in x for x in self.f.calls))
 def test_T13_metadata_verification_unchanged(self):
  old=ROOT.parent/'QW-DYNAMICS-LIVE-E01R-EXECUTION-20261030/repo/live_fabric01/github_transport.py';new=ROOT/'repo/live_fabric01/github_transport.py'
  def region(p):return p.read_text().split(' def _metadata_binding(',1)[1].split(' def ',1)[0]
  self.assertEqual(region(old),region(new))
 def test_T14_run_attempt_commit_original_checks(self):
  # Actual original regression class is run separately against upgraded API fixtures.
  p=ROOT/'repo/live_fabric01/github_transport.py';s=p.read_text();self.assertIn("run['run_attempt']==1",s);self.assertIn("run.get('conclusion')=='success'",s);self.assertIn("run.get('head_sha')==g.get('code_commit')",s)
 def test_T15_original_npz_state_and_receipt_immutable(self):
  base=ROOT.parent;protected=json.loads((ROOT/'INHERITED_PROTECTED_FILES.json').read_text());self.assertTrue(all(sha((base/rel).read_bytes())==h for rel,h in protected.items()))
# Extend only the old explicitly synthetic endpoint fixture; production source is not mocked here.
def upgrade_harness():
 from . import test_remote_provenance as old
 original=old.Harness.fake_gh
 def fake(self,*args):
  endpoint=args[1] if len(args)>1 else '';prefix='repos/'+self.g['repository'];data={k.removeprefix('world/'):v for k,v in self.files.items() if k.startswith('world/')};data.update(self.extra_staged)
  tree=[{'path':'dynamics01/staged/'+k,'type':'blob','mode':'100644','size':len(v),'sha':blobsha(v)} for k,v in data.items()]
  tree_sha=hashlib.sha1(json.dumps(tree,sort_keys=True).encode()).hexdigest()
  if '/git/commits/' in endpoint:
   self.api_calls.append(list(args));commit=endpoint.rsplit('/',1)[1];return json.dumps({'sha':commit,'tree':{'sha':tree_sha}})
  if '/git/trees/' in endpoint:
   self.api_calls.append(list(args));return json.dumps({'sha':tree_sha,'truncated':False,'tree':tree})
  if '/contents/dynamics01/staged/' in endpoint:
   # Preserve original fake call recorder; add official field shapes missing from old fixture.
   raw=json.loads(original(self,*args));path=endpoint.split('/contents/')[1].split('?')[0];b=data[path.removeprefix('dynamics01/staged/')];raw.update(path=path,type='file',sha=blobsha(b),size=len(b));return json.dumps(raw)
  return original(self,*args)
 old.Harness.fake_gh=fake;return old
if __name__=='__main__':unittest.main()
