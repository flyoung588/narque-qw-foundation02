"""One prepared geometry or one observation-bound physical action, never a scan."""
import json,pathlib,shutil,sys,traceback
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from interactive01.world import freeze
from frontier01.state import CorrelatedStore
from frontier01.world_runtime import prepare,act
from router import digest
out=pathlib.Path(sys.argv[2]);store=CorrelatedStore(out/'world')
try:
    req=json.loads(pathlib.Path(sys.argv[1]).read_text())
    if req['stage']==1:
        if set(req)!={'stage','model_request'}:raise ValueError('FIRST_REQUEST_FIELDS')
        state,receipt=prepare(store,req['model_request'],authority=True,resources=True)
    elif req['stage']==2:
        if set(req)!={'stage','source_state_sha256','action','ai_decision'}:raise ValueError('SECOND_REQUEST_FIELDS')
        # Published only after observation; evidence copy contains no executable files.
        src=pathlib.Path(__file__).parent/'inherited'
        for p in sorted(src.rglob('*')):
            if not p.is_file():continue
            rel=p.relative_to(src)
            if p.is_symlink() or p.suffix not in ('.json','.npz') or rel.parts[0] not in ('states','arrays'):raise ValueError('INHERITED_DATA_ONLY')
            dest=store.root/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
        parent=store.load(req['source_state_sha256']);store.arrays(parent)
        d=req['ai_decision']
        if d['source_state_sha256']!=parent['sha256'] or d['observation_sha256']!=digest(parent['payload']['observation']) or d['action_sha256']!=digest(req['action']) or not d['first_job_run_id'] or not d['prediction'] or not d['falsifier']:raise ValueError('UNBOUND_AI_DECISION')
        state,receipt=act(store,parent,req['action'],authority=True,resources=True)
    else:raise ValueError('STAGE_DOMAIN')
    freeze(out/'observation.json',{'status':'CALCULATED','request_sha256':digest(req),'state':state,'observation':state['payload']['observation'],'transition':receipt})
except BaseException as e:
    freeze(out/'worker_failure.json',{'status':'UNVERIFIED','type':type(e).__name__,'error':str(e),'traceback':traceback.format_exc(),'no_retry':True});raise
