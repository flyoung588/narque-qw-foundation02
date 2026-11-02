"""Aligned, rotation-frozen H2+ two BO channels with actual dipole electric coupling."""
import hashlib,json
from pathlib import Path
import numpy as np
from scipy.interpolate import CubicSpline
from .runtime import PhysicalSystem
from .coupled import MatrixHamiltonian,field
MASS=1836.15267343

class H2PlusSystem(PhysicalSystem):
    max_dt=.1
    def __init__(self,curve_file,n=255,stride=1):
        file=Path(curve_file);data=json.loads(file.read_text());rows=data['rows'][::stride]
        if rows[-1]['R_bohr']!=data['rows'][-1]['R_bohr']:rows.append(data['rows'][-1])
        self.data_sha=hashlib.sha256(file.read_bytes()).hexdigest();self.basis=data['basis'];self.stride=stride
        self.lower=.7;self.upper=12.;self.n=n;self.dx=(self.upper-self.lower)/(n+1);self.R=self.lower+self.dx*np.arange(1,n+1);self.axes=[self.R];self.dv=self.dx
        x=[r['R_bohr'] for r in rows]
        self.curves={key:CubicSpline(x,[r[key] for r in rows],extrapolate=False) for key in ['Vg_Eh','Vu_Eh','mu_gu_au']}
        values=[self.curves[key](self.R) for key in ['Vg_Eh','Vu_Eh','mu_gu_au']]
        self.hamiltonian=MatrixHamiltonian(self.R,*values,MASS)
    def metadata(self):return {'system':'H2+ aligned two-electronic-channel nuclear dynamics','particles':{'protons':2,'electrons':1,'proton_mass_me':MASS,'nuclear_reduced_mass_me':MASS/2,'total_charge':1,'electron_spin':'spectator doublet; electric coupling spin conserving'},'channels':['1s sigma_g','2p sigma_u'],'coordinates':'reduced radial chi_g(R),chi_u(R), sum channel |chi|² dR','units':'bohr,Eh,e*a0,electric field atomic units,atomic time','energy_zero':'electron at infinity and separated bare protons, BO total energies epsilon+1/R','source':{'basis':self.basis,'curve_sha256':self.data_sha,'nuclear_grid':self.n,'electronic_interpolation_stride':self.stride},'boundary':'Dirichlet at .7 and12bohr, no absorber, positive radial interval, monitor edge probability','approximations':['two BO electronic states only','fixed molecular axis parallel to polarization, frozen rotations and COM','length gauge dipole, classical prescribed spatially uniform field','no ionization/higher electronic channels','no Born-Huang diagonal correction or intrinsic derivative nonadiabatic coupling','no electron spin transition, relativity or QED'],'propagator':'midpoint local Hermitian2x2 exponential + DST-I nuclear kinetic','state_shape':[2,self.n]}
    def allowed(self):return {'initial':{'center_R_bohr':[1.6,2.6],'sigma_R_bohr':[.15,.35],'channel':'g only'},'control':{'operation':'electric_pulse','amplitude_au':[0,.01],'duration_au':[50,500],'omega_ratio_to_local_gap':[.7,1.3],'optional_fixed_omega_au':[.1,1.5],'cep_rad':[-float(np.pi),float(np.pi)],'polarization':'parallel molecular axis'},'observables':['Pg','Pu','mean_R','coherence_gu','electric_field_au','work_input_Eh','edge_probability']}
    def initial_wavefunction(self,initial):
        c=float(initial['center_R_bohr']);sigma=float(initial['sigma_R_bohr'])
        if not(np.isfinite([c,sigma]).all() and 1.6<=c<=2.6 and .15<=sigma<=.35):raise ValueError('initial physical domain')
        g=np.exp(-(self.R-c)**2/(4*sigma**2))*np.sin(np.pi*(self.R-self.lower)/(self.upper-self.lower))
        return np.stack([g,np.zeros_like(g)]).astype(complex)
    def apply_to_state(self,state,control):
        if control.get('operation')!='electric_pulse':raise ValueError('only declared physical pulse')
        a=float(control['amplitude_au']);T=float(control['duration_au']);ratio=float(control['omega_ratio_to_local_gap']);cep=float(control['cep_rad'])
        if not(np.isfinite([a,T,ratio,cep]).all() and 0<=a<=.01 and 50<=T<=500 and .7<=ratio<=1.3 and abs(cep)<=np.pi):raise ValueError('pulse domain')
        c=state.initial['center_R_bohr'];gap=float(self.curves['Vu_Eh'](c)-self.curves['Vg_Eh'](c));omega=float(control.get('omega_au',ratio*gap))
        if not np.isfinite(omega) or not(.1<=omega<=1.5):raise ValueError('carrier domain')
        state.parameters['pulse']={'start_au':state.t,'amplitude_au':a,'duration_au':T,'omega_au':omega,'cep_rad':cep,'intensity_W_cm2':3.5094452e16*a*a,'carrier_source':'explicit frozen frequency' if 'omega_au' in control else 'actual electronic gap at initial nuclear center','envelope':'sin²(pi*t/T), cos carrier centered atT/2','polarization':'parallel z axis'}
    def observables(self,state):
        density=abs(state.psi)**2*self.dx;pg,pu=density.sum(axis=1);all_d=density.sum(axis=0);norm=pg+pu;coherence=np.sum(state.psi[0].conj()*state.psi[1])*self.dx;E,_=field(state.t,state.parameters.get('pulse'))
        return {'Pg':float(pg),'Pu':float(pu),'mean_R':float(np.sum(all_d*self.R)/norm),'coherence_gu':[float(coherence.real),float(coherence.imag)],'electric_field_au':E,'edge_probability':float(all_d[(self.R<1.)|(self.R>11.)].sum()),'channel_names':['1s sigma_g','2p sigma_u']}
