"""Thin physical semantics around unchanged Core-01; no new TDSE solver."""
import copy, math, types
import numpy as np
from router import digest
from world01.contracts import WorldError
from . import core_world as core
SCHEMA='QW_COLLINEAR_NUCLEAR_WAVEPACKET_01'
MODEL={'id':'QML_LSTH_COLLINEAR_H3_GROUND_DOUBLET','coordinates':['x=B-A','y=C-B'],'representation':'complex128 uniform 2D ordered-distance grid','Hilbert_space':'L2(dx dy), COM removed, x>0,y>0; finite FFT box discretization','Hamiltonian':'T=-(dxx+dyy-dxy)/m + V_LSTH(x,y,x+y) - i W(x,y)','mass_me':core.MASS,'surface':'single ground electronic doublet BO LSTH','energy_zero':'3 separated ground-state H atoms of the LSTH PES','units':{'position':'bohr','time':'atomic_time','energy':'Eh','momentum':'hbar/bohr'},'propagator':'Core-01 second-order Strang split FFT','normalization':'sum(abs(psi)^2)*dx^2','limitations':['No electronic excitation, rotation, nuclear permutation statistics or nonadiabatic coupling','Periodic numerical boundary is not periodic matter','Finite region populations are not asymptotic reaction probabilities','Finite-box conditional energy uses surviving norm with CAP','No measured material accuracy or W2 certification']}
OPS=['PREPARE_AND_EVOLVE_WAVEPACKET','PREPARE_WAVEPACKET','EVOLVE_WAVEPACKET','MEASURE_WAVEPACKET','APPLY_CONTROL','FORK_PHYSICAL_STATE']
OBS=['density','norm','time','position','momentum','energy','regional_population','absorbed','boundary_mass']
def require(ok,code):
 if not ok:raise WorldError(code)
def describe_model(n,dx,lower,cap):
 return {**copy.deepcopy(MODEL),'grid':{'n':n,'dx_bohr':dx,'lower_bohr':lower,'length_bohr':n*dx},'boundary':{'FFT':'periodic computational box','CAP':bool(cap),'W':'0.04*max((x-11.5)/2.9,0)^4 + same(y), Eh' if cap else 'zero','lower_boundary':'no absorber; monitor edge mass; no wraparound claim'}}
def engine_from_arrays(a,model):
 n=model['grid']['n'];dx=model['grid']['dx_bohr'];e=core.PhysicsEngine.__new__(core.PhysicsEngine)
 e.n=n;e.dx=dx;e.axis=a['axis'].copy();e.x,e.y=np.meshgrid(e.axis,e.axis,indexing='ij');e.V=a['V'].copy();e.W=a['W'].copy();e.K=a['K'].copy();return e

def validate_arrays(a,m):
 n=m['grid']['n'];dx=m['grid']['dx_bohr'];require(type(n) is int and n in (128,256,512),'GRID_OUT_OF_DOMAIN');require(math.isfinite(dx) and dx>0,'INVALID_GRID')
 require(m['id']==MODEL['id'] and m['mass_me']==core.MASS and m['Hamiltonian']==MODEL['Hamiltonian'],'MODEL_MISMATCH')
 require(set(a)=={'psi','axis','V','W','K'},'ARRAY_KEYS_MISMATCH')
 require(a['psi'].shape==(n,n) and np.iscomplexobj(a['psi']),'PSI_REPRESENTATION_INVALID')
 require(a['axis'].shape==(n,) and all(a[k].shape==(n,n) for k in ('V','W','K')),'ARRAY_SHAPE_MISMATCH')
 require(all(np.isfinite(v).all() for v in a.values()),'NONFINITE_ARRAY')
 require(np.allclose(a['axis'],m['grid']['lower_bohr']+np.arange(n)*dx,rtol=0,atol=1e-12),'AXIS_MISMATCH')
 k=2*np.pi*np.fft.fftfreq(n,d=dx);u,v=np.meshgrid(k,k,indexing='ij');require(np.allclose(a['K'],(u*u+v*v-u*v)/core.MASS,rtol=0,atol=1e-12),'KINETIC_METRIC_MISMATCH')
 X,Y=np.meshgrid(a['axis'],a['axis'],indexing='ij');W=(.04*np.maximum((X-11.5)/2.9,0)**4+.04*np.maximum((Y-11.5)/2.9,0)**4) if m['boundary']['CAP'] else np.zeros((n,n))
 require(np.allclose(a['W'],W,rtol=0,atol=1e-13),'CAP_MISMATCH')
 norm=float(np.vdot(a['psi'],a['psi']).real*dx*dx);require(0<norm<=1+1e-7,'INVALID_NORM')
 return norm

def observe_arrays(a,p):
 m=p['model'];validate_arrays(a,m);e=engine_from_arrays(a,m)
 s=core.WorldState(a['psi'].copy(),t=p['time_au'],absorbed=p['absorbed'],controls=p['controls'],initial=p['initial'])
 o=core.ObservableEngine.measure(e,s)
 k=2*np.pi*np.fft.fftfreq(e.n,d=e.dx);kx,ky=np.meshgrid(k,k,indexing='ij');f=np.fft.fft2(s.psi);weight=abs(f)**2*e.dx**2/e.n**2/o['norm']
 return {'time':{'value':p['time_au'],'unit':'atomic_time','time_fs':o['time_fs']},'norm':{'value':o['norm'],'unit':'dimensionless','definition':'unnormalized surviving probability'},'density':{'array':'psi','derive':'abs(psi)^2','unit':'bohr^-2','array_ref':p['arrays']},'position':{'value':[o['mean_x'],o['mean_y']],'unit':'bohr','definition':'conditional means for surviving norm'},'momentum':{'value':[float((weight*kx).sum()),float((weight*ky).sum())],'unit':'hbar/bohr','definition':'FFT canonical px,py; NOT velocities or Cartesian nuclear momenta'},'energy':{'value':o['energy_Eh'],'unit':'Eh','reference':m['energy_zero'],'definition':'Re(<T+V>)/norm; excludes imaginary CAP; survival-conditioned'},'regional_population':{'value':{k:o[k] for k in ('reactant_region','product_region','interaction_region')},'unit':'dimensionless','definition':'raw probability in Core x/y<3,>3 partitions; remaining quadrant omitted; NOT asymptotic S-matrix'},'absorbed':{'value':o['absorbed'],'unit':'dimensionless','probability_balance':o['probability_balance'],'definition':'Core integrated exact CAP half-step losses'},'boundary_mass':{'value':o['edge_probability'],'unit':'dimensionless','definition':'Core x/y<0.65 or>13.5 bohr; finite-box diagnostic not scattering result'}}

def validate_operation(p,action):
 kind=action.get('type');require(kind in OPS,'DYNAMICS_OPERATION_OUT_OF_DOMAIN')
 require(action.get('source_state_sha256') is not None,'PHYSICAL_PARENT_REQUIRED')
 allowed={'type','source_state_sha256'}
 if kind=='PREPARE_AND_EVOLVE_WAVEPACKET':
  allowed|={'preparation','evolution'};parent=action['source_state_sha256'];validate_operation(p,{'type':'PREPARE_WAVEPACKET','source_state_sha256':parent,**action['preparation']});validate_operation(p,{'type':'EVOLVE_WAVEPACKET','source_state_sha256':parent,**action['evolution']})
 elif kind=='EVOLVE_WAVEPACKET':
  allowed|={'dt_au','steps'};dt=action.get('dt_au');steps=action.get('steps');require(type(dt) in (float,int) and math.isfinite(dt) and 0<dt<=.5 and type(steps) is int and 1<=steps<=20000,'TIME_STEP_OUT_OF_DOMAIN')
 elif kind=='APPLY_CONTROL':
  allowed|={'operation','delta_k_bohr_inv'};v=action.get('delta_k_bohr_inv');require(action.get('operation')=='momentum_kick' and type(v) in (float,int) and math.isfinite(v) and abs(v)<=1,'CONTROL_OUT_OF_DOMAIN')
 elif kind=='PREPARE_WAVEPACKET':
  allowed|={'energy_eV','center_R_bohr','sigma_R_bohr'}
  for key,lo,hi in [('energy_eV',.05,1.2),('center_R_bohr',4.5,8),('sigma_R_bohr',.45,1)]:require(type(action.get(key)) in (float,int) and math.isfinite(action[key]) and lo<=action[key]<=hi,'PREPARATION_OUT_OF_DOMAIN')
 elif kind=='FORK_PHYSICAL_STATE':allowed|={'reason'};require(bool(action.get('reason')),'FORK_REASON_REQUIRED')
 elif kind=='MEASURE_WAVEPACKET':allowed|={'observables'};require(bool(action.get('observables')) and not set(action['observables'])-set(OBS),'OBSERVABLE_OUT_OF_DOMAIN')
 require(set(action)==allowed,'UNDECLARED_ACTION_FIELDS')
 return kind

def transition_arrays(a,p,action):
 """Compute only AFTER broker/worker admission. No hidden initial-state regeneration."""
 kind=validate_operation(p,action);e=engine_from_arrays(a,p['model']);w=core.ExperimentControl(e);w.state=core.WorldState(a['psi'].copy(),p['time_au'],p['absorbed'],copy.deepcopy(p['controls']),copy.deepcopy(p['initial']))
 if kind in ('PREPARE_WAVEPACKET','PREPARE_AND_EVOLVE_WAVEPACKET'):
  prep=action['preparation'] if kind=='PREPARE_AND_EVOLVE_WAVEPACKET' else action
  # Original engine prepares same-PES diatom ground state; do not approximate it from a final packet.
  e=core.PhysicsEngine(n=p['model']['grid']['n'],length=p['model']['grid']['length_bohr'],lower=p['model']['grid']['lower_bohr'],cap=p['model']['boundary']['CAP']);w=core.ExperimentControl(e);w.prepare(prep['energy_eV'],prep['center_R_bohr'],prep['sigma_R_bohr'])
  if kind=='PREPARE_AND_EVOLVE_WAVEPACKET':w.step(action['evolution']['steps'],action['evolution']['dt_au'])
 elif kind=='EVOLVE_WAVEPACKET':w.step(action['steps'],action['dt_au'])
 elif kind=='APPLY_CONTROL':w.apply('momentum_kick',delta_k=action['delta_k_bohr_inv'])
 else:require(False,'READ_OR_FORK_HAS_NO_SOLVER_TRANSITION')
 arrays={'psi':w.state.psi,'axis':e.axis,'V':e.V,'W':e.W,'K':e.K}
 return arrays,{'time_au':w.state.t,'absorbed':w.state.absorbed,'controls':w.state.controls,'initial':w.state.initial,'time_origin_au':0.,'physical_continuity':'NEW_PREPARATION_NOT_CONTINUATION' if kind in ('PREPARE_WAVEPACKET','PREPARE_AND_EVOLVE_WAVEPACKET') else 'CONTINUED_PARENT_PSI' if kind=='EVOLVE_WAVEPACKET' else 'INSTANTANEOUS_MOMENTUM_KICK_PARENT_PSI','operation':copy.deepcopy(action)}

LIVE_BOUNDS={'grid_n':256,'lower_bohr':.4,'length_bohr':14,'CAP':True,'mass_me':core.MASS,'preparation_energy_eV':[.05,1.2],'center_R_bohr':[4.5,8.0],'sigma_R_bohr':[.45,1.0],'dt_au_choices':[.25,.5],'first_duration_au_max':2000,'second_duration_au_max':400,'continuous_physical_time_au_max':2400}
def screen_live_action(p,action,used):
 kind=validate_operation(p,action);require(kind in ('PREPARE_AND_EVOLVE_WAVEPACKET','EVOLVE_WAVEPACKET'),'ACTION_OUTSIDE_FIRST_LIVE_SCOPE');require(p['model']['grid']=={'n':256,'dx_bohr':14/256,'lower_bohr':.4,'length_bohr':14} and p['model']['boundary']['CAP'] is True,'LIVE_MODEL_GRID_MISMATCH')
 ev=action['evolution'] if kind=='PREPARE_AND_EVOLVE_WAVEPACKET' else action;duration=ev['dt_au']*ev['steps'];require(ev['dt_au'] in LIVE_BOUNDS['dt_au_choices'] and duration<=(2000 if used==0 else 400),'LIVE_DURATION_OUT_OF_SCOPE');after=duration if kind=='PREPARE_AND_EVOLVE_WAVEPACKET' else p['time_au']+duration;require(after<=2400,'LIVE_PHYSICAL_TIME_OUT_OF_SCOPE');return duration
