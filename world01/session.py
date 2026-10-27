"""One persistent Session over the EXISTING CorrelatedStore -> QuantumStore -> Store.

Original JSON/NPZ bytes are copied unchanged. Session receipts/indexes annotate
references; they are not another state store, solver or physical evidence ledger.
This E00 build cannot enable new scientific execution by changing request flags.
"""
import copy,datetime,hashlib,json,os,pathlib,shutil,tempfile
import numpy as np
from jsonschema import ValidationError
from router import digest
from interactive01.world import freeze,verify,apply
from frontier01.state import CorrelatedStore
from .contracts import WorldError,OperationRequest,envelope,KIND
from . import fabric,provenance as origin
from types import MappingProxyType
def filehash(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def publish_bytes(p,raw):
    p.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(dir=p.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        try:os.link(tmp,p)
        except FileExistsError:
            if p.read_bytes()!=raw:raise WorldError('IMMUTABLE_CONFLICT')
    finally:os.unlink(tmp)
class WorldSession:
    def __init__(self,root,baseline_root,source_manifest,goal='Offline world integration'):
        self.root=pathlib.Path(root);self.baseline=pathlib.Path(baseline_root).resolve();self.manifest=MappingProxyType(copy.deepcopy(source_manifest['files']));self.source_snapshot_commit=source_manifest['local_base'];self.store=CorrelatedStore(self.root)
        self.metadata={'schema':'QW_WORLD_SESSION_01','research_goal':goal,'source_commit':source_manifest['local_base'],'authority':{'new_science_jobs':0,'external_writes':False,'purchases':0},'resource_envelope':'Light offline read/replay/fixture only','state_storage':'Inherited CorrelatedStore/QuantumStore/Store; unchanged legacy hashes','physical_execution':'DISABLED_IN_THIS_BUILD'}
        if (self.root/'session.json').exists():
            legacy=json.loads((self.root/'session.json').read_text())
            if legacy.get('schema')!='QW_WORLD_SESSION_01':raise WorldError('SESSION_SCHEMA_INVALID')
            self.metadata=legacy # preserve old immutable metadata, not a new execution grant
        else:freeze(self.root/'session.json',self.metadata)
        freeze(self.root/'source_anchor.json',{'snapshot_commit':self.source_snapshot_commit,'source_manifest_sha256':digest(dict(self.manifest)),'trust':'Pinned intake records, not independent physical or Human-signature certification'})
        self._anchor_sha256=filehash(self.root/'source_anchor.json')
    def call(self,operation,**kwargs):
        allowed={'create','reference','load','observe','act','fork','compare','translate','claim','replay','stop'}
        if operation not in allowed:return self.reject(operation,'UNSUPPORTED_OPERATION')
        try:return getattr(self,operation)(**kwargs)
        except WorldError as e:return self.reject(operation,e.code,kwargs.get('ident'),e.detail)
        except (KeyError,TypeError,ValueError,OSError) as e:return self.reject(operation,'MALFORMED_OR_DAMAGED_INPUT',kwargs.get('ident'),str(e))
    def _open(self):
        if (self.root/'STOP.json').exists():raise WorldError('SESSION_STOPPED')
    def _source(self,relative):
        if filehash(self.root/'source_anchor.json')!=self._anchor_sha256:raise WorldError('TRUST_ANCHOR_TAMPERED')
        rel=pathlib.PurePosixPath(relative)
        if rel.is_absolute() or '..' in rel.parts or str(rel) not in self.manifest:raise WorldError('SOURCE_NOT_BOUND')
        p=self.baseline/str(rel)
        if p.is_symlink() or not p.is_file() or filehash(p)!=self.manifest[str(rel)]:raise WorldError('SOURCE_HASH_MISMATCH')
        return p
    def receipt(self,operation,status,code,source=None,**fields):
        if fields.get('new_scientific_execution') or fields.get('new_scientific_executions',0):raise WorldError('READONLY_RECEIPT_CANNOT_CLAIM_EXECUTION')
        v={'schema':'QW_SESSION_RECEIPT_01','operation':operation,'status':status,'reason_code':code,'source_state_hash':source,'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'new_scientific_execution':False,'new_scientific_executions':0,**fields}
        h=digest(v);freeze(self.root/'session_receipts'/f'{h}.json',v);return {**v,'receipt_sha256':h}
    def reject(self,operation,code,source=None,detail=''):return self.receipt(operation,'REJECTED',code,source,detail=detail)
    def reference(self,relative,_seen=None):
        self._open();seen=set() if _seen is None else _seen;p=self._source(relative)
        try:s=json.loads(p.read_text());verify(s)
        except (ValueError,KeyError,TypeError) as e:raise WorldError('STATE_HASH_MISMATCH',str(e)) from e
        if s['sha256'] in seen:raise WorldError('ANCESTRY_CYCLE')
        seen.add(s['sha256']);payload=s['payload']
        if payload.get('schema') not in KIND:raise WorldError('UNSUPPORTED_STATE_KIND')
        parent=payload.get('parent_state_id')
        if parent:
            ancestor=str(pathlib.PurePosixPath(relative).parent/(parent+'.json'));self.reference(ancestor,seen)
        if payload.get('arrays'):
            ref=payload['arrays']
            if ref['path']!=f"arrays/{ref['sha256']}.npz":raise WorldError('ARRAY_PATH_INVALID')
            rel=str(pathlib.PurePosixPath(relative).parent.parent/ref['path']);a=self._source(rel)
            if filehash(a)!=ref['sha256']:raise WorldError('ARRAY_HASH_MISMATCH')
            publish_bytes(self.root/ref['path'],a.read_bytes())
        publish_bytes(self.root/'states'/p.name,p.read_bytes())
        origin.bind(self,relative,s)
        return self.load(s['sha256'])
    def _validate_state(self,s):
        verify(s);p=s['payload'];fabric.validate_object(p['world_spec'])
        if p['schema'] not in KIND:raise WorldError('UNSUPPORTED_STATE_KIND')
        fabric.select(s)
        if p['schema'] in ('QW_EFFECTIVE_QUANTUM_STATE_01','QW_CORRELATED_ELECTRONIC_STATE_01') and not p.get('arrays'):
            raise WorldError('STATE_ARRAYS_REQUIRED')
        if p.get('arrays'):
            try:a=self.store.arrays(s)
            except (ValueError,OSError,KeyError) as e:raise WorldError('ARRAY_HASH_MISMATCH',str(e)) from e
            if not all(np.isfinite(v).all() for v in a.values()):raise WorldError('NONFINITE_ARRAY')
            if p['schema']=='QW_EFFECTIVE_QUANTUM_STATE_01':
                if a['ket'].shape!=(2,) or abs(np.vdot(a['ket'],a['ket']).real-1)>1e-7:raise WorldError('STATE_NORM_INVALID')
                if not np.allclose(a['H0_Eh'],p['model']['H0_Eh'],atol=0,rtol=0):raise WorldError('MODEL_ARRAY_MISMATCH')
                if not np.array_equal(a['dipole_au'],np.asarray(p['model']['dipole_au'])):raise WorldError('MODEL_ARRAY_MISMATCH')
            if p['schema']=='QW_CORRELATED_ELECTRONIC_STATE_01':
                if a['ci'].ndim!=2 or abs(np.vdot(a['ci'],a['ci']).real-1)>1e-7:raise WorldError('STATE_NORM_INVALID')
        return s
    def load(self,ident):
        try:s=self.store.load(ident)
        except (ValueError,KeyError,OSError) as e:raise WorldError('STATE_UNAVAILABLE_OR_CORRUPT',str(e)) from e
        self._validate_state(s);p=self.root/'references'/f'{ident}.json'
        if not p.exists():raise WorldError('PROVENANCE_MISSING')
        provenance=json.loads(p.read_text());trust=origin.classify(self,s,provenance)
        if not trust['verified']:raise WorldError('UNVERIFIED_PROVENANCE',trust.get('reason_code','UNKNOWN'))
        return envelope(s,provenance,trust)
    def create(self,spec,*,synthetic=False):
        self._open();fabric.validate_object(spec);s=self.store.create(spec,'SYNTHETIC_STRUCTURE_ONLY' if synthetic else 'NEW_STRUCTURE_ONLY_NO_SOLVER')
        prov={'mode':'SYNTHETIC' if synthetic else 'NEW_STRUCTURE_NOT_CALCULATED','source_file':None,'raw_byte_sha256':filehash(self.root/'states'/f"{s['sha256']}.json")}
        freeze(self.root/'references'/f"{s['sha256']}.json",prov)
        freeze(self.root/'local_origins'/f"{s['sha256']}.json",{'mode':prov['mode'],'raw_byte_sha256':prov['raw_byte_sha256'],'provenance_digest':digest(prov)})
        return self.load(s['sha256'])
    def observe(self,ident,requested=()):
        env=self.load(ident);s=self.store.load(ident);m=fabric.select(s);trust=env['source_execution']
        if set(requested)-set(m['supported_observables']):
            raise WorldError('FORCE_NOT_AVAILABLE' if 'forces' in requested else 'STRESS_NOT_AVAILABLE' if 'stress' in requested else 'UNSUPPORTED_OBSERVABLE')
        p=s['payload'];raw=p.get('observation');values={'original_observation':copy.deepcopy(raw)};available={}
        if trust['real_calculated']:
            available=fabric.observation_values(s)
        if p['schema']=='QW_EFFECTIVE_QUANTUM_STATE_01':
            a=self.store.arrays(s);values.update(population=(np.abs(a['ket'])**2).tolist(),norm=float(np.vdot(a['ket'],a['ket']).real),time_au=p['time_au'],model=p['model'])
            for k in ('population','norm','time','model'):available[k]={'value':values['time_au'] if k=='time' else values[k],'unit':{'time':'atomic_time','model':'declared_Hamiltonian','population':'dimensionless','norm':'dimensionless'}[k]}
        if set(requested)-set(available):raise WorldError('OBSERVABLE_NOT_AVAILABLE','Requested value absent or not established by this state')
        if p['schema']=='QW_PHYSICAL_STATE_01' and raw:
            data=raw.get('observation',{});flag=data.get('SCF_converged',data.get('converged'))
            if flag is not None:values['SCF_converged']=flag
        kind=trust['source_execution_kind']
        if kind=='SYNTHETIC':status='SOFTWARE_FIXTURE_ONLY'
        elif trust['real_calculated']:status='SCIENTIFIC_OBSERVATION_READ' if kind=='NEW_SCIENTIFIC_EXECUTION' else 'HISTORICAL_OBSERVATION_READ'
        elif raw:status='UNVERIFIED'
        else:status='STRUCTURE_ONLY_NOT_CALCULATED' if p['schema']=='QW_PHYSICAL_STATE_01' else 'MODEL_STATE_READ_NOT_CALCULATED'
        values['available_observables']=list(available)
        v={'schema':'QW_OBSERVATION_ENVELOPE_01','source_state_hash':ident,'status':status,'observation_read_status':'READ_COMPLETED','values':values,'observables':available,'original_status':(raw or {}).get('status'),'source_execution_kind':kind,'source_execution_status':trust['source_execution_status'],'source_evidence_status':trust['source_evidence_status'],'model_qualification':trust['model_qualification'],'unavailable_observables':m['unavailable_observables'],'units':env['units'],'measurement_definition':m['supported_observables'],'model_hash':env['model_hash'],'model_domain':m['domain'],'error_uncertainty':m['model_limitations'],'raw_sha256':digest(raw),'provenance':env['provenance'],'new_physics_run':False,'new_scientific_executions':0}
        rec=self.receipt('observe',status,'ORIGINAL_PHYSICS_STATUS_PRESERVED',ident,observation_sha256=digest(v),source_execution_kind=kind,source_execution_status=trust['source_execution_status'],operation_kind='READ_ONLY')
        return {**v,'read_receipt_sha256':rec['receipt_sha256']}
    def fork(self,ident,reason):
        self._open();self.load(ident)
        if not reason:raise WorldError('FORK_REASON_REQUIRED')
        return self.receipt('fork','SESSION_BRANCH_CREATED','PHYSICAL_STATE_REFERENCE_UNCHANGED',ident,branch_id=digest({'state':ident,'reason':reason}),reason=reason,physical_state_copied=False)
    def compare(self,a,b,contract=None):
        for ident in (a,b):
            env=self.load(ident)
            if env['source_execution']['source_execution_kind']=='SYNTHETIC':raise WorldError('SYNTHETIC_MISLABEL_BLOCKED')
            if not env['source_execution']['real_calculated']:raise WorldError('UNVERIFIED_SCIENTIFIC_RESULT')
        result=fabric.compare(self.store.load(a),self.store.load(b),contract)
        return self.receipt('compare','COMPARISON_VALIDATED',result['status'],a,result=result,other_state=b)
    def translate(self,ident,target):
        self.load(ident);v=fabric.translation(self.store.load(ident),target)
        return self.receipt('translate',v['status'],v['status'],ident,translation=v)
    def replay(self,relative):
        self._open();path=self._source(relative);r=json.loads(path.read_text());intent_path=str(pathlib.PurePosixPath(relative).with_name('intent.json'));intent=json.loads(self._source(intent_path).read_text())
        source=r['source_state_sha256'];target=r['new_state_sha256'];world=pathlib.PurePosixPath(relative).parent.parent.parent
        for h in (source,target):self.reference(str(world/'states'/f'{h}.json'))
        a=self.store.load(source);b=self.store.load(target);action=r['action'];kind=a['payload']['schema']
        if action.get('source_state_sha256',source)!=source:raise WorldError('ACTION_STATE_BINDING_MISMATCH')
        if r.get('action_sha256') and digest(action)!=r['action_sha256']:raise WorldError('ACTION_HASH_MISMATCH')
        if intent.get('action')!=action:raise WorldError('INTENT_ACTION_MISMATCH')
        if action['type']=='PREPARE_CORRELATED_STATE':
            if intent['request']['world_spec']!=b['payload']['world_spec'] or a['payload']['world_spec']!=b['payload']['world_spec']:raise WorldError('ACTION_SPEC_MISMATCH')
            if intent['request']['correlation_model']!=b['payload']['correlation_model']:raise WorldError('MODEL_MISMATCH')
        elif kind=='QW_EFFECTIVE_QUANTUM_STATE_01':
            from state_space01.contract import validate_action
            validate_action(a,action)
            if b['payload']['parent_state_id']!=source:raise WorldError('ANCESTRY_MISMATCH')
            if b['payload']['model']!=a['payload']['model']:raise WorldError('MODEL_MISMATCH')
            if action['type']=='EVOLVE_QUANTUM_STATE' and abs(b['payload']['time_au']-a['payload']['time_au']-action['duration_au'])>1e-10:raise WorldError('TIME_ORIGIN_MISMATCH')
        else:
            spec=apply(a,action)
            if spec!=b['payload']['world_spec']:raise WorldError('ACTION_SPEC_MISMATCH')
            if kind=='QW_CORRELATED_ELECTRONIC_STATE_01' and r.get('observation_sha256')!=digest(b['payload']['observation']):raise WorldError('OBSERVATION_HASH_MISMATCH')
            if r.get('result_sha256') and r['result_sha256']!=digest(b['payload']['observation']):raise WorldError('OBSERVATION_HASH_MISMATCH')
        return self.receipt('replay','HISTORICAL_REPLAY_VALIDATED','NOT_A_NEW_PHYSICS_RUN',source,target_state=target,source_receipt=relative,source_receipt_file_sha256=filehash(path),source_intent_sha256=self.manifest[intent_path],adapter=fabric.select(a)['existing_adapter'],original_receipt=r,observation=self.observe(target))
    def act(self,request):
        req=request if isinstance(request,OperationRequest) else OperationRequest(**request)
        try:
            from .schemas import validate
            validate('request',req.plain())
            if req.action=='OBSERVE':return self.observe(req.source_state_hash,req.required_observables)
            self._open();self.load(req.source_state_hash)
            if req.action=='FORK':return self.fork(req.source_state_hash,req.parameters.get('reason',''))
            if req.action=='REPLAY_HISTORICAL_TRANSITION':
                original=json.loads(self._source(req.parameters['receipt_path']).read_text())
                if original['source_state_sha256']!=req.source_state_hash:raise WorldError('STALE_PARENT')
                r=self.replay(req.parameters['receipt_path'])
                if r['source_state_hash']!=req.source_state_hash:raise WorldError('STALE_PARENT')
                return r
            if req.action=='STOP':return self.stop(req.parameters.get('reason',''))
            state=self.store.load(req.source_state_hash)
            fabric.admit(state,req.action,req.required_observables,execute=True,authority=req.parameters.get('authority'))
            raise WorldError('AUTHORITY_MISSING')
        except WorldError as e:return self.reject(req.action,e.code,req.source_state_hash,e.detail)
        except (KeyError,TypeError,ValueError,ValidationError) as e:return self.reject(req.action,'MALFORMED_OPERATION',req.source_state_hash,str(e))
    def claim(self,kind,source=None):
        try:fabric.validate_claim(kind)
        except WorldError as e:return self.reject('claim',e.code,source)
    def stop(self,reason):
        if not reason:raise WorldError('STOP_REASON_REQUIRED')
        freeze(self.root/'STOP.json',{'status':'STOPPED','reason':reason,'new_science_jobs':0})
        return self.receipt('stop','STOPPED','NO_AUTOMATIC_SUCCESSOR',reason=reason)
    def preserve_failure(self,source,reason,details):
        self.load(source);return self.receipt('failure','FAILED',reason,source,details=details,parent_preserved=True,no_retry=True)
