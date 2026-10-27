"""Budget consumed before remote dispatch; never releases a failed slot."""
import pathlib,json,copy
from router import digest
from interactive01.world import freeze
from explorer01.memory import Journal
from world01.contracts import WorldError
from .contracts import admission,screen_spec,check_remote_return,LIMITS
class LiveBroker:
 def __init__(self,root,grant,prereg,review,manifest_sha,transport):
  self.root=pathlib.Path(root);self.grant=copy.deepcopy(grant);self.prereg=copy.deepcopy(prereg);self.review=copy.deepcopy(review);self.manifest_sha=manifest_sha;self.transport=transport;self.j=Journal(self.root/'job_ledger')
 def authorize(self):return admission(self.grant,self.prereg,self.review,self.manifest_sha)
 def run(self,spec,model_decision_hash):
  self.authorize();screen_spec(spec);key=digest(spec)
  with self.j.lock():
   es=self.j.events();used=[e for e in es if e['kind']=='JobReserved']
   if len(used)>=LIMITS['max_jobs']:raise WorldError('SCIENTIFIC_JOB_LIMIT')
   if any(e['data']['spec_hash']==key for e in used):raise WorldError('SCIENTIFIC_INPUT_ALREADY_ATTEMPTED')
   intent={'scope':'QW-EXPLORER-E01','spec':copy.deepcopy(spec),'spec_hash':key,'model_decision_hash':model_decision_hash,'job_number':len(used)+1,'limits':LIMITS,'prereg_hash':digest(self.prereg)};ident=digest(intent)
   self.j.append('JobReserved',{'intent':ident,'spec_hash':key,'model_decision_hash':model_decision_hash,'job_number':len(used)+1});self.j.checkpoint()
  folder=self.root/'attempts'/ident;folder.mkdir(parents=True,exist_ok=False);freeze(folder/'intent.json',intent)
  try:
   package=self.transport.execute(spec,ident,self.grant)
   from .transport import GithubTransport
   if type(self.transport) is not GithubTransport:raise WorldError('UNTRUSTED_SOLVER_TRANSPORT')
   self.transport.assert_authenticated(package);freeze(folder/'raw_remote_return.json',package);raw=check_remote_return(package,spec,self.grant,ident)
   result={'status':'MODEL_CALCULATED_NOT_PHYSICALLY_CERTIFIED','intent':ident,'spec':spec,'observation':raw,'remote_package':package,'model_decision_hash':model_decision_hash};freeze(folder/'validated_return.json',result)
   with self.j.lock():self.j.append('JobReturned',{'intent':ident,'result_hash':digest(result)});self.j.checkpoint()
   return result
  except BaseException as e:
   freeze(folder/'failure.json',{'status':'FAILED_NO_RETRY','reason_code':getattr(e,'code',type(e).__name__),'detail':str(e),'slot_remains_consumed':True})
   with self.j.lock():self.j.append('JobFailed',{'intent':ident,'reason_code':getattr(e,'code',type(e).__name__),'slot_released':False});self.j.checkpoint()
   raise

 def verify_persisted(self,result):
  from .contracts import require
  ident=result['intent'];path=self.root/'attempts'/ident/'validated_return.json'
  require(path.is_file() and json.loads(path.read_text())==result,'LIVE_BROKER_RETURN_MISSING')
  require(any(e['kind']=='JobReturned' and e['data'].get('intent')==ident and e['data'].get('result_hash')==digest(result) for e in self.j.events()),'LIVE_RESULT_NOT_PINNED_BY_BROKER')
  return True
