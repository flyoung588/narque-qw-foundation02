"""Existing outbound secret scan extracted unchanged; no new provider client."""
import json,re,hashlib,pathlib
class PreflightFailure(RuntimeError):pass
def need(v,reason):
 if not v:raise PreflightFailure(reason)
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def strip_read_id(o):return {k:v for k,v in o.items() if k!='read_receipt_sha256'}
def secret_scan(v):
 s=v if isinstance(v,str) else json.dumps(v,ensure_ascii=False,allow_nan=False)
 for p in [r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})',r'Bearer\s+[A-Za-z0-9._-]{16,}',r'/Users/feiyang(?:/|\b)']:
  need(not re.search(p,s),'OUTBOUND_SECRET_OR_UNREDACTED_PATH')
 def walk(x):
  if isinstance(x,dict):
   for k,z in x.items():
    if k.lower() in ('accesstoken','refreshtoken','idtoken','apikey','api_key','password','private_key','cookie','authorization','chatgptaccountid','accountid'):
     need(z in (None,'','[REDACTED]'),'OUTBOUND_CREDENTIAL_FIELD')
    walk(z)
  elif isinstance(x,list):
   for z in x:walk(z)
 if not isinstance(v,str):walk(v)
 return {'pattern_and_field_scan':'PASS','user_path_redaction':'PASS','scope':'Explicit outbound payloads; not attestation of hidden server context'}
