"""Prepare exact publication manifest; never dispatch or import scientific engine."""
import hashlib,json,pathlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=['.github/workflows/foundation02.yml','qw_next/periodic_world.py']+[str(p.relative_to(root)) for p in sorted((root/'periodic01').glob('*')) if p.is_file() and p.name!='PUBLIC_FILES.json']
(root/'periodic01/PUBLIC_FILES.json').write_text(json.dumps({'repository':'flyoung588/narque-qw-foundation02','branch':'qw-periodic01','base':'e09fb33a5812feb3cc7c24a695faf77d08c4fbbb','files':{f:sha(root/f) for f in files},'result_scope':'Reviewed outputs only: request, construction, observation, environment, resource and failure logs. No private data.','execution':'One manual standard ubuntu-24.04 job <=15min; single base FCC Ne calculation; no rerun; P3 not started without actual same-job AI feedback'},indent=2)+'\n')
