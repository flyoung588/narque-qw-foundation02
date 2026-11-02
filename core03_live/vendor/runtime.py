"""Grid-wavefunction runtime. No molecular identity or channel semantics here."""
import copy,hashlib,json
from pathlib import Path
from dataclasses import dataclass,field
import numpy as np

def clean(x):
    if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [clean(v) for v in x]
    if isinstance(x,np.ndarray):return clean(x.tolist())
    if isinstance(x,np.generic):return x.item()
    if isinstance(x,float) and not np.isfinite(x):raise ValueError('nonfinite evidence')
    return x

@dataclass
class QuantumState:
    psi:np.ndarray
    model_id:str
    t:float=0.
    absorbed:float=0.
    initial:dict=field(default_factory=dict)
    controls:list=field(default_factory=list)
    timeline:list=field(default_factory=list)
    parameters:dict=field(default_factory=dict)
    work_input:float=0.

class Hamiltonian:
    def __init__(self,V,K,forward,inverse,W=None,discretization=''):
        self.V=np.asarray(V);self.K=np.asarray(K);self.W=np.zeros_like(V) if W is None else np.asarray(W)
        assert self.V.shape==self.K.shape==self.W.shape and np.all(self.W>=0)
        self.forward=forward;self.inverse=inverse;self.discretization=discretization
    def kinetic(self,psi):return self.inverse(self.K*self.forward(psi))
    def energy(self,psi,dv):return float((np.vdot(psi,self.kinetic(psi)).real+np.sum(abs(psi)**2*self.V))*dv)

class PhysicalSystem:
    """Adapter contract: metadata/coordinates/hamiltonian/prepare/control/observables."""
    def metadata(self):raise NotImplementedError
    def initial_wavefunction(self,initial):raise NotImplementedError
    def apply_control(self,psi,control):raise NotImplementedError
    def observables(self,state):raise NotImplementedError
    def allowed(self):raise NotImplementedError
    @property
    def identity(self):return hashlib.sha256(json.dumps(clean(self.metadata()),sort_keys=True).encode()).hexdigest()

class TimeEvolution:
    @staticmethod
    def step(system,state,dt):
        if hasattr(system.hamiltonian,'propagate'):
            system.hamiltonian.propagate(state,dt,system.dv)
            return
        # Same symmetric split operator and independent CAP accounting as Core01.
        h=system.hamiltonian;a=np.exp((-1j*h.V-h.W)*dt/2);b=np.exp(-1j*h.K*dt)
        loss=-np.expm1(-h.W*dt)
        absorbed=np.sum(abs(state.psi)**2*loss)*system.dv
        middle=h.inverse(b*h.forward(a*state.psi))
        absorbed+=np.sum(abs(middle)**2*loss)*system.dv
        state.psi=a*middle;state.absorbed+=float(absorbed);state.t+=dt

class ObservableEngine:
    @staticmethod
    def measure(system,state):
        norm=float(np.vdot(state.psi,state.psi).real*system.dv)
        h=system.hamiltonian
        energy=h.energy_state(state,system.dv) if hasattr(h,'energy_state') else h.energy(state.psi,system.dv)
        base={'model_id':state.model_id,'time_au':state.t,'time_fs':state.t*.024188843265857,'norm':norm,'absorbed':state.absorbed,'probability_balance':norm+state.absorbed,'energy_Eh':energy/norm,'work_input_Eh':state.work_input}
        return {**base,**system.observables(state)}

class EvidenceInterface:
    @staticmethod
    def export(world,directory):
        p=Path(directory);p.mkdir(parents=True,exist_ok=True)
        np.savez_compressed(p/'wavefunction.npz',psi=world.state.psi,**{'axis'+str(i):a for i,a in enumerate(world.system.axes)})
        meta=clean({'physical_system':world.system.metadata(),'model_id':world.state.model_id,'initial':world.state.initial,'controls':world.state.controls,'timeline':world.state.timeline,'state_time_au':world.state.t,'absorbed':world.state.absorbed,'state_parameters':world.state.parameters,'work_input_Eh':world.state.work_input,'observation':world.observe(),'errors':world.error_evidence,'solver':world.system.hamiltonian.discretization,'state_provenance':'computed wavefunction, not static lookup'})
        (p/'evidence.json').write_text(json.dumps(meta,indent=2,allow_nan=False))
        hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in p.iterdir() if f.name!='SHA256.json'}
        (p/'SHA256.json').write_text(json.dumps(hashes,indent=2));return meta

class QuantumWorld:
    def __init__(self,system_spec):
        if not isinstance(system_spec,PhysicalSystem):raise TypeError('pass a PhysicalSystem adapter')
        self.system=system_spec;self.state=None;self.error_evidence={}
    def allowed(self):return clean(self.system.allowed())
    def prepare(self,initial_state):
        psi=np.asarray(self.system.initial_wavefunction(initial_state),dtype=complex)
        if psi.shape!=getattr(self.system.hamiltonian,'state_shape',self.system.hamiltonian.V.shape) or not np.isfinite(psi).all():raise ValueError('invalid state')
        norm=np.vdot(psi,psi).real*self.system.dv
        if norm<=0:raise ValueError('zero state')
        self.state=QuantumState(psi/np.sqrt(norm),self.system.identity,initial=copy.deepcopy(initial_state));return self.observe()
    def apply(self,control):
        before=self.observe()['energy_Eh']
        if hasattr(self.system,'apply_to_state'):
            self.system.apply_to_state(self.state,control)
            psi=self.state.psi
        else:psi=self.system.apply_control(self.state.psi.copy(),control)
        if not np.isfinite(psi).all():raise ValueError('nonfinite control result')
        self.state.psi=psi
        after=self.observe()['energy_Eh'];self.state.work_input+=after-before
        self.state.controls.append({**control,'time_au':self.state.t,'work_Eh':after-before});return self.observe()
    def step(self,dt=.25,count=1):
        if not np.isfinite(dt) or not(0<dt<=self.system.max_dt) or not isinstance(count,int) or not(1<=count<=20000):raise ValueError('bounded step')
        for _ in range(count):TimeEvolution.step(self.system,self.state,dt)
        self.state.timeline.append({'dt_au':dt,'count':count,'end_au':self.state.t});return self.observe()
    def evolve(self,duration,dt=.25):
        count=round(duration/dt)
        if duration<=0 or abs(count*dt-duration)>1e-10:raise ValueError('duration must be positive integral steps')
        return self.step(dt,count)
    def observe(self):
        if self.state is None:raise RuntimeError('prepare first')
        return clean(ObservableEngine.measure(self.system,self.state))
    def fork(self):
        other=QuantumWorld(self.system);other.state=copy.deepcopy(self.state);other.error_evidence=copy.deepcopy(self.error_evidence);return other
    def compare(self,other):
        if self.system.identity!=other.system.identity:raise ValueError('incompatible physical model/grid/energy zero; cross-system subtraction forbidden')
        a=self.observe();b=other.observe()
        return {'first':a,'second':b,'state_L2':float(np.linalg.norm(self.state.psi-other.state.psi)*np.sqrt(self.system.dv)),'same_time':abs(self.state.t-other.state.t)<1e-12}
    def checkpoint(self,directory):return self.export_evidence(directory)
    def restore(self,directory):
        p=Path(directory);meta=json.loads((p/'evidence.json').read_text());manifest=json.loads((p/'SHA256.json').read_text())
        assert all(hashlib.sha256((p/n).read_bytes()).hexdigest()==h for n,h in manifest.items())
        if meta['model_id']!=self.system.identity:raise ValueError('checkpoint model mismatch')
        with np.load(p/'wavefunction.npz',allow_pickle=False) as z:psi=z['psi'].copy()
        self.state=QuantumState(psi,meta['model_id'],meta['state_time_au'],meta['absorbed'],meta['initial'],meta['controls'],meta['timeline'],meta.get('state_parameters',{}),meta.get('work_input_Eh',0.));self.error_evidence=meta['errors'];return self.observe()
    def export_evidence(self,directory):return EvidenceInterface.export(self,directory)

ExperimentControl=QuantumWorld
