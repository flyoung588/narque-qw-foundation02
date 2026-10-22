"""Extend immutable Store by typed complex-array states; old Store unchanged."""
import hashlib,io,json,os,pathlib,tempfile,math
import numpy as np
from interactive01.world import Store,freeze,verify
from router import digest

def blob(root,arrays):
    data=io.BytesIO();np.savez_compressed(data,**arrays);raw=data.getvalue();h=hashlib.sha256(raw).hexdigest()
    p=pathlib.Path(root)/'arrays'/f'{h}.npz';p.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(dir=p.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        try:os.link(name,p)
        except FileExistsError:
            if p.read_bytes()!=raw:raise ValueError('IMMUTABLE_ARRAY_CONFLICT')
    finally:os.unlink(name)
    return {'path':f'arrays/{h}.npz','sha256':h,'format':'NPZ_COMPLEX128_FLOAT64','keys':sorted(arrays)}

class QuantumStore(Store):
    def save(self,*,parent,world_spec,model,ket,time_au,reason,control=None,control_origin_au=0,observation=None,trajectory=None):
        if parent is None:raise ValueError('BOUND_PARENT_REQUIRED')
        self.load(parent)
        if not math.isfinite(time_au) or time_au<0 or not math.isfinite(control_origin_au):raise ValueError('PHYSICAL_TIME')
        v=np.asarray(ket,complex)
        if v.shape!=(2,) or not np.isfinite(v).all() or abs(np.vdot(v,v).real-1)>1e-7:raise ValueError('NORMALIZED_2D_KET_REQUIRED')
        arr={'ket':v,'H0_Eh':np.asarray(model['H0_Eh'],complex),'dipole_au':np.asarray(model['dipole_au'],complex)}
        if trajectory:arr.update(trajectory)
        ref=blob(self.root,arr)
        payload={'schema':'QW_EFFECTIVE_QUANTUM_STATE_01','parent_state_id':parent,'world_spec':world_spec,'reason':reason,
                 'state_kind':'TIME_DEPENDENT_EFFECTIVE_QUANTUM_KET' if trajectory else 'EFFECTIVE_QUANTUM_KET','model':model,
                 'basis':['RHF_REFERENCE_EFFECTIVE_LABEL','SELECTED_TDA_SINGLET_EFFECTIVE_LABEL'] if model['source_type']=='PYSCF_RHF_TDA_RESPONSE_DERIVED' else ['USER_MODEL_BASIS_0','USER_MODEL_BASIS_1'],'dimension':2,'time_au':float(time_au),'control':control,'control_origin_au':float(control_origin_au),'observation':observation,
                 'arrays':ref,'norm':float(np.vdot(v,v).real),'interpretation':'SEPARATE_WORK_AI_DECISION','scope':'Truncated response-derived effective ket; NOT SCF orbitals or a full molecular wavefunction'}
        h=digest(payload);s={'state_id':h,'sha256':h,'payload':payload};freeze(self.root/'states'/f'{h}.json',s);return s
    def arrays(self,state):
        verify(state);ref=state['payload']['arrays'];p=self.root/ref['path']
        if ref['path']!=f"arrays/{ref['sha256']}.npz" or hashlib.sha256(p.read_bytes()).hexdigest()!=ref['sha256']:raise ValueError('ARRAY_HASH_MISMATCH')
        with np.load(p,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}
