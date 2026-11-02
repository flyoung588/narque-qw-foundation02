"""Generic real-Hermitian2x2 local potential, coherent channels, midpoint Strang.
No molecular identity; dipoles/potentials must be supplied by a physical adapter.
"""
import numpy as np
from scipy.fft import dst,idst
from .runtime import Hamiltonian

def field(t,pulse):
    if not pulse:return 0.,0.
    tau=t-pulse['start_au'];T=pulse['duration_au']
    if tau<=0 or tau>=T:return 0.,0.
    a=np.pi*tau/T;phase=pulse['omega_au']*(tau-T/2)+pulse['cep_rad'];E0=pulse['amplitude_au']
    E=E0*np.sin(a)**2*np.cos(phase)
    derivative=E0*((np.pi/T)*np.sin(2*a)*np.cos(phase)-pulse['omega_au']*np.sin(a)**2*np.sin(phase))
    return float(E),float(derivative)

def local_exponential(psi,vg,vu,coupling,duration):
    average=(vg+vu)/2;difference=(vg-vu)/2;omega=np.sqrt(difference**2+coupling**2)
    sinc=duration*np.sinc(omega*duration/np.pi);cos=np.cos(omega*duration)
    factor=np.exp(-1j*average*duration);g,u=psi
    return np.stack([factor*(cos*g-1j*sinc*(difference*g+coupling*u)),factor*(cos*u-1j*sinc*(coupling*g-difference*u))])

class MatrixHamiltonian(Hamiltonian):
    def __init__(self,R,vg,vu,mu,mass):
        self.R=R;self.vg=np.asarray(vg);self.vu=np.asarray(vu);self.mu=np.asarray(mu);self.dx=R[1]-R[0]
        if not all(np.isfinite(x).all() for x in [self.vg,self.vu,self.mu]):raise ValueError('missing physical input')
        n=len(R);length=self.dx*(n+1);K=(np.pi*np.arange(1,n+1)/length)**2/mass
        super().__init__(np.stack([vg,vu]),np.broadcast_to(K,(2,n)),lambda x:dst(x,type=1,axis=-1,norm='ortho'),lambda x:idst(x,type=1,axis=-1,norm='ortho'),discretization='two-channel midpoint Strang; exact real-Hermitian2x2 local exponential; radial DST-I')
        self.state_shape=(2,n)
    def potential_matrix(self,t,parameters):
        E,_=field(t,parameters.get('pulse'));c=-self.mu*E
        return np.stack([np.stack([self.vg,c]),np.stack([c,self.vu])])
    def energy_state(self,state,dv):
        E,_=field(state.t,state.parameters.get('pulse'));g,u=state.psi
        kinetic=np.vdot(state.psi,self.kinetic(state.psi)).real
        potential=np.sum(self.vg*abs(g)**2+self.vu*abs(u)**2-2*self.mu*E*np.real(g.conj()*u))
        return float((kinetic+potential)*dv)
    def propagate(self,state,dt,dv):
        midpoint=state.t+dt/2;E,dE=field(midpoint,state.parameters.get('pulse'))
        p=local_exponential(state.psi,self.vg,self.vu,-self.mu*E,dt/2)
        kinetic_half=np.exp(-1j*self.K*dt/2)
        mid=self.inverse(kinetic_half*self.forward(p))
        power=-2*np.sum(self.mu*dE*np.real(mid[0].conj()*mid[1]))*dv
        p=self.inverse(kinetic_half*self.forward(mid))
        state.psi=local_exponential(p,self.vg,self.vu,-self.mu*E,dt/2)
        state.work_input+=float(power*dt);state.t+=dt
