"""Model transport is distinct from model output trust. Never infer authorship from actor labels."""
import json,pathlib,subprocess,os
from router import digest
from world01.contracts import WorldError
class ModelAdapter:
 def decide(self,request):raise NotImplementedError
class FileExchangeAdapter(ModelAdapter):
 """Durable pause/resume with the current Work model; no pretend network/API call."""
 def __init__(self,root):self.root=pathlib.Path(root);self.root.mkdir(parents=True,exist_ok=True)
 def decide(self,request):
  p=self.root/(digest(request)+'.response.txt')
  if not p.exists():raise WorldError('MODEL_RESPONSE_PENDING','Work must read the actual request and submit a fresh decision')
  return p.read_text()
class CommandModelAdapter(ModelAdapter):
 """Explicit caller-supplied existing authorized model client. No shell, credentials or purchase flow."""
 def __init__(self,argv,*,authorized=False,timeout=60):
  if not authorized:raise WorldError('MODEL_CALL_AUTHORITY_REQUIRED')
  self.argv=list(argv);self.timeout=timeout
 def decide(self,request):
  try:v=subprocess.run(self.argv,input=json.dumps(request),text=True,capture_output=True,timeout=self.timeout,check=False)
  except (subprocess.TimeoutExpired,OSError) as e:raise WorldError('MODEL_TRANSPORT_FAILED',type(e).__name__) from e
  if v.returncode:raise WorldError('MODEL_TRANSPORT_FAILED',str(v.returncode))
  if len(v.stdout)>1000000:raise WorldError('MODEL_OUTPUT_TOO_LARGE')
  return v.stdout
