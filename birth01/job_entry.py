"""Future approved single container entry. No automatic second step."""
import argparse,json,pathlib,hashlib,shutil
from .authority import approval_check
from .preparation import BirthPreparation
from world01.session import WorldSession

def copy_inherited(source,target):
    source=pathlib.Path(source);manifest=json.loads((source/'SESSION_SHA256.json').read_text())['files']
    for rel,h in manifest.items():
        p=source/rel
        if pathlib.PurePosixPath(rel).is_absolute() or '..' in pathlib.PurePosixPath(rel).parts or p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=h:raise ValueError('INHERITED_SESSION_HASH_MISMATCH')
    target.mkdir(parents=True,exist_ok=True)
    for rel in manifest:
        p=target/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/rel,p)

def main():
    approval_check() # fail BEFORE material construction or native imports
    p=argparse.ArgumentParser();p.add_argument('--request',required=True);p.add_argument('--previous-session');a=p.parse_args()
    root=pathlib.Path(__file__).resolve().parents[1];out=pathlib.Path('/out');session=out/'session'
    if a.previous_session:copy_inherited(a.previous_session,session)
    from .preparation import ROOT
    m=json.loads((ROOT/'BASELINE_SOURCE_SHA256.json').read_text());w=WorldSession(session,root,m)
    request=json.loads(pathlib.Path(a.request).read_text())
    if not a.previous_session:w.reference(request['historical_source_file'])
    b=BirthPreparation(w,session/'birth');i=b.submit(request['operation_request'])
    try:
        result=b.execute(i)
        if result.get('status')!='SIMULATION_OBSERVATION_MODEL_ONLY':raise SystemExit(1)
    finally:
        files={str(f.relative_to(session)):hashlib.sha256(f.read_bytes()).hexdigest() for f in session.rglob('*') if f.is_file() and f.name!='SESSION_SHA256.json'}
        (session/'SESSION_SHA256.json').write_text(json.dumps({'files':files},indent=2)+'\n')
if __name__=='__main__':main()
