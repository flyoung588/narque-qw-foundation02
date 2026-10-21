"""Preserve outputs via ordinary logs. No Actions artifact/cache/Packages upload."""
import base64,hashlib,json,pathlib,sys,zlib
root=pathlib.Path(sys.argv[1])
if root.is_dir():
 for file in sorted(root.rglob('*')):
  if not file.is_file():continue
  raw=file.read_bytes();s=base64.b64encode(zlib.compress(raw,9)).decode()
  parts=[s[i:i+7000] for i in range(0,len(s),7000)] or ['']
  for i,p in enumerate(parts):print('QW_FOUNDATION02_FILE '+json.dumps({'name':str(file.relative_to(root)),'sha256':hashlib.sha256(raw).hexdigest(),'part':i,'parts':len(parts),'data':p}),flush=True)
