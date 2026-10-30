"""Collinear ordered A-B-C nuclear TDSE on a licensed ground-doublet LSTH PES.

Atomic units. x=B-A>0,y=C-B>0. Removing COM gives
T=-(d_xx+d_yy-d_xy)/m. No rotation, electronic excitation, or nuclear statistics.
FFT periodic box is a discretization, NOT physical periodic H3. Inspect boundary mass.
"""
import copy, ctypes, hashlib, json, math
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np

ROOT=Path(__file__).parent
MASS=1836.15267343 # proton/electron mass ratio, nuclear BO kinetic convention
EV=27.211386245988
FS=0.024188843265857

class PhysicsEngine:
    def __init__(self,n=256,length=14.,lower=.4,cap=True):
        if n not in (128,256,512): raise ValueError('supported grids 128,256,512')
        self.n=n;self.dx=length/n;self.axis=lower+np.arange(n)*self.dx
        self.x,self.y=np.meshgrid(self.axis,self.axis,indexing='ij')
        self.lib=ctypes.CDLL(str(ROOT/'vendor/liblsth.so'))
        self.lib.potential.argtypes=[ctypes.c_int,np.ctypeslib.ndpointer(dtype=np.float64,flags='F_CONTIGUOUS'),np.ctypeslib.ndpointer(dtype=np.float64),ctypes.c_int]
        self.V=self.potential(self.x,self.y,self.x+self.y)
        k=2*np.pi*np.fft.fftfreq(n,d=self.dx);a,b=np.meshgrid(k,k,indexing='ij')
        self.K=(a*a+b*b-a*b)/MASS
        w=lambda z: .04*np.maximum((z-11.5)/2.9,0)**4
        self.W=w(self.x)+w(self.y) if cap else np.zeros_like(self.V)
        # H2 ground vibrational packet from same PES's separated-atom channel.
        kr=2*np.pi*np.fft.fftfreq(n,d=self.dx)
        kinetic=np.fft.ifft((kr*kr/MASS)[:,None]*np.fft.fft(np.eye(n),axis=0),axis=0).real
        v=self.potential(self.axis,np.full(n,40.),self.axis+40.)
        e,u=np.linalg.eigh(kinetic+np.diag(v))
        self.bond=u[:,0]/np.sqrt(self.dx);self.bond_energies=e[:4];self.vdiatom=v
    def potential(self,a,b,c,legacy=0):
        a,b,c=np.broadcast_arrays(a,b,c);shape=a.shape
        xyz=np.asfortranarray(np.stack([a.ravel(),b.ravel(),c.ravel()]))
        out=np.empty(a.size);self.lib.potential(a.size,xyz,out,legacy)
        return out.reshape(shape)

@dataclass
class WorldState:
    psi: np.ndarray
    t: float=0.
    absorbed: float=0.
    controls: list=field(default_factory=list)
    initial: dict=field(default_factory=dict)

class TimeEvolution:
    @staticmethod
    def advance(engine,state,dt,count):
        a=np.exp((-1j*engine.V-engine.W)*dt/2)
        b=np.exp(-1j*engine.K*dt)
        for _ in range(count):
            # Integrate each exact CAP half-step independently of FFT roundoff.
            # Do not define absorption as total norm loss (a tautological QA).
            decay_loss=-np.expm1(-engine.W*dt)
            lost=float(np.sum(abs(state.psi)**2*decay_loss)*engine.dx**2)
            middle=np.fft.ifft2(b*np.fft.fft2(a*state.psi))
            lost+=float(np.sum(abs(middle)**2*decay_loss)*engine.dx**2)
            state.psi=a*middle
            state.absorbed+=lost
            state.t+=dt

class ObservableEngine:
    @staticmethod
    def measure(e,s):
        d=abs(s.psi)**2*e.dx**2;n=float(d.sum())
        f=np.fft.fft2(s.psi)
        ke=float(np.sum(abs(f)**2*e.K)*e.dx**2/e.n**2)
        pe=float(np.sum(d*e.V))
        return dict(time_au=s.t,time_fs=s.t*FS,norm=n,absorbed=s.absorbed,
                    probability_balance=n+s.absorbed,energy_Eh=(ke+pe)/n,
                    mean_x=float((d*e.x).sum()/n),mean_y=float((d*e.y).sum()/n),
                    reactant_region=float(d[(e.x<3)&(e.y>3)].sum()),
                    product_region=float(d[(e.y<3)&(e.x>3)].sum()),
                    interaction_region=float(d[(e.x<3)&(e.y<3)].sum()),
                    edge_probability=float(d[(e.x<.65)|(e.y<.65)|(e.x>13.5)|(e.y>13.5)].sum()))

class EvidenceInterface:
    @staticmethod
    def export(world,path):
        p=Path(path);p.mkdir(parents=True,exist_ok=True)
        np.savez_compressed(p/'state.npz',psi=world.state.psi,axis=world.engine.axis,V=world.engine.V,W=world.engine.W)
        obj={'model':'QML-LSTH ground-doublet collinear BO','initial':world.state.initial,'controls':world.state.controls,'observation':world.observe(),'n':world.engine.n,'dx':world.engine.dx,'claim_ceiling':'finite-box wavepacket; regional populations are NOT asymptotic reaction probabilities'}
        (p/'evidence.json').write_text(json.dumps(obj,indent=2,allow_nan=False))
        (p/'SHA256.json').write_text(json.dumps({f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in p.iterdir() if f.name!='SHA256.json'},indent=2))
        return obj

class ExperimentControl:
    def __init__(self,engine=None):self.engine=engine or PhysicsEngine();self.state=None
    def prepare(self,energy_eV=.6,center_R=6.,sigma_R=.6):
        if not(.05<=energy_eV<=1.2 and 4.5<=center_R<=8 and .45<=sigma_R<=1.):raise ValueError('outside frozen preparation domain')
        e=self.engine;R=e.y+e.x/2;k=-np.sqrt(2*(2*MASS/3)*energy_eV/EV)
        psi=e.bond[:,None]*np.exp(-(R-center_R)**2/(4*sigma_R**2)+1j*k*R)
        psi/=np.sqrt(np.vdot(psi,psi).real*e.dx**2)
        self.state=WorldState(psi,initial=dict(energy_eV=energy_eV,center_R=center_R,sigma_R=sigma_R))
        return self.observe()
    def apply(self,operation,**kw):
        if operation!='momentum_kick':raise NotImplementedError('only explicit momentum kick; no fictitious fields')
        dk=float(kw['delta_k']);
        if abs(dk)>1:raise ValueError('bounded kick <=1 bohr^-1')
        before=self.observe()['energy_Eh'];self.state.psi*=np.exp(1j*dk*(self.engine.y+self.engine.x/2))
        self.state.controls.append(dict(operation=operation,delta_k=dk,time_au=self.state.t,work_Eh=self.observe()['energy_Eh']-before))
        return self.observe()
    def step(self,count=1,dt=.5):
        if not(1<=count<=20000 and 0<dt<=.5):raise ValueError('step bound')
        TimeEvolution.advance(self.engine,self.state,dt,count);return self.observe()
    def observe(self):return ObservableEngine.measure(self.engine,self.state)
    def fork(self):
        other=ExperimentControl(self.engine);other.state=copy.deepcopy(self.state);return other
    def compare(self,other):
        if self.engine.n!=other.engine.n:raise ValueError('matched grid required')
        a=self.observe();b=other.observe()
        return {'first':a,'second':b,'product_difference':b['product_region']-a['product_region'],'state_L2':float(np.linalg.norm(self.state.psi-other.state.psi)*self.engine.dx)}
    def export_evidence(self,path):return EvidenceInterface.export(self,path)
