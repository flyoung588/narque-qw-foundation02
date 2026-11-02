"""Keep radial measure, complete psi[2,N], absolute pulse clock and work history."""
import copy,hashlib,json,math
from pathlib import Path
import numpy as np
from router import digest
from world01.contracts import WorldError
from .vendor.runtime import QuantumWorld,QuantumState,clean
from .vendor.h2plus_adapter import H2PlusSystem

SCHEMA='QW_COUPLED_RADIAL_NUCLEAR_STATE_01'
DOMAIN='core03_coupled'
CURVE=Path(__file__).parent/'data/curve.json'
CURVE_SHA='12b4765d965fd36357c398e3b5b8faaabf33eed692c419d9fa621580cc600f91'
OPS=['PREPARE_COUPLED_STATE','APPLY_ELECTRIC_PULSE','EVOLVE_COUPLED_STATE','PULSE_AND_EVOLVE_COUPLED_STATE']
OBS=['Pg','Pu','coherence_gu','radial_density','mean_R','norm','energy_Eh','work_input_Eh','electric_field_au','edge_probability','time_au']
QUALIFICATION={'W2':'INCOMPLETE','physical_accuracy':'NOT_CERTIFIED','novelty':'NOT_PROVEN','model':'Two BO channels, fixed axis/COM, finite radial Dirichlet box; no ionization, rotations or intrinsic nonadiabatic derivative couplings'}
def require(ok,code):
 if not ok:raise WorldError(code)
def finite_number(v):return type(v) in (int,float) and math.isfinite(v)
def system():
 require(hashlib.sha256(CURVE.read_bytes()).hexdigest()==CURVE_SHA,'CORE03_CURVE_BYTES_CHANGED')
 return H2PlusSystem(CURVE,n=255,stride=1)
def arrays_of(w):
 h=w.system.hamiltonian
 return {'psi':w.state.psi.copy(),'R':w.system.R.copy(),'Vg':h.vg.copy(),'Vu':h.vu.copy(),'mu_gu':h.mu.copy(),'K':h.K.copy()}
def state_fields(w):
 s=w.state
 return clean({'time_au':s.t,'absorbed':s.absorbed,'initial':s.initial,'controls':s.controls,'timeline':s.timeline,'parameters':s.parameters,'work_input_Eh':s.work_input,'model_id':s.model_id})
def validate_arrays(a,p):
 require(set(a)=={'psi','R','Vg','Vu','mu_gu','K'},'COUPLED_ARRAY_KEYS_INVALID')
 require(a['psi'].shape==(2,255) and a['psi'].dtype==np.complex128,'COUPLED_PSI_REPRESENTATION_INVALID')
 require(all(np.isfinite(v).all() for v in a.values()),'COUPLED_NONFINITE_ARRAY')
 e=system();h=e.hamiltonian
 for key,expected in [('R',e.R),('Vg',h.vg),('Vu',h.vu),('mu_gu',h.mu),('K',h.K)]:
  require(a[key].dtype==np.float64 and np.array_equal(a[key],expected),'COUPLED_MODEL_ARRAY_MISMATCH')
 require(p['model']==e.metadata() and p['model_id']==e.identity,'COUPLED_MODEL_ID_MISMATCH')
 require(finite_number(p['time_au']) and p['time_au']>=0 and finite_number(p['work_input_Eh']) and p['absorbed']==0,'COUPLED_TIME_WORK_INVALID')
 norm=float(np.vdot(a['psi'],a['psi']).real*e.dv)
 require(abs(norm-1)<=1e-9,'COUPLED_NORM_INVALID')
 require(set(p['initial'])=={'center_R_bohr','sigma_R_bohr'},'COUPLED_INITIAL_METADATA_INVALID')
 # Original domain validation; no new physical preparation is used on restoration.
 c=p['initial']['center_R_bohr'];s=p['initial']['sigma_R_bohr']
 require(finite_number(c) and finite_number(s) and 1.6<=c<=2.6 and .15<=s<=.35,'COUPLED_INITIAL_DOMAIN')
 require(isinstance(p['parameters'],dict) and set(p['parameters'])<= {'pulse'},'COUPLED_PARAMETERS_INVALID')
 pulse=p['parameters'].get('pulse')
 if pulse:
  require(all(finite_number(pulse.get(k)) for k in ('start_au','amplitude_au','duration_au','omega_au','cep_rad')),'COUPLED_PULSE_NONFINITE')
  require(0<=pulse['start_au']<=p['time_au']+1e-9 and 0<=pulse['amplitude_au']<=.01 and 50<=pulse['duration_au']<=500 and .1<=pulse['omega_au']<=1.5 and abs(pulse['cep_rad'])<=np.pi,'COUPLED_PULSE_OUT_OF_DOMAIN')
 return e,norm
def restore(a,p):
 e,_=validate_arrays(a,p);w=QuantumWorld(e)
 w.state=QuantumState(a['psi'].copy(),p['model_id'],p['time_au'],p['absorbed'],copy.deepcopy(p['initial']),copy.deepcopy(p['controls']),copy.deepcopy(p['timeline']),copy.deepcopy(p['parameters']),p['work_input_Eh'])
 return w
def observe(a,p):
 w=restore(a,p);out=w.observe();den=np.abs(a['psi'])**2
 out['radial_density']={'R_bohr':a['R'].tolist(),'channel_density_per_bohr':den.tolist(),'definition':'|chi_g/u|^2; integral sum*deltaR, not 3D |psi|^2 or r^2dr'}
 return clean({k:out[k] for k in OBS})
def validate_action(p,action):
 kind=action.get('type');require(kind in OPS,'COUPLED_OPERATION_OUT_OF_DOMAIN')
 require(isinstance(action.get('source_state_sha256'),str),'COUPLED_PARENT_REQUIRED')
 keys={'type','source_state_sha256'}
 if kind=='PREPARE_COUPLED_STATE':
  keys|={'initial'};v=action['initial'];require(set(v)=={'center_R_bohr','sigma_R_bohr'} and all(finite_number(x) for x in v.values()),'COUPLED_PREPARATION_INVALID')
  require(1.6<=v['center_R_bohr']<=2.6 and .15<=v['sigma_R_bohr']<=.35,'COUPLED_PREPARATION_OUT_OF_DOMAIN')
 if kind in ('APPLY_ELECTRIC_PULSE','PULSE_AND_EVOLVE_COUPLED_STATE'):
  keys|={'control'};v=action['control'];required={'operation','amplitude_au','duration_au','omega_ratio_to_local_gap','cep_rad'}
  require(set(v) in (required,required|{'omega_au'}) and v['operation']=='electric_pulse','COUPLED_CONTROL_FIELDS_INVALID')
  require(all(finite_number(v[k]) for k in required-{'operation'}) and ('omega_au' not in v or finite_number(v['omega_au'])),'COUPLED_CONTROL_NONFINITE')
  require(0<=v['amplitude_au']<=.01 and 50<=v['duration_au']<=500 and .7<=v['omega_ratio_to_local_gap']<=1.3 and abs(v['cep_rad'])<=np.pi and ('omega_au' not in v or .1<=v['omega_au']<=1.5),'COUPLED_CONTROL_OUT_OF_DOMAIN')
  pulse=p['parameters'].get('pulse');require(not pulse or p['time_au']+1e-9>=pulse['start_au']+pulse['duration_au'],'ACTIVE_PULSE_REPLACEMENT_FORBIDDEN')
 if kind in ('EVOLVE_COUPLED_STATE','PULSE_AND_EVOLVE_COUPLED_STATE'):
  keys|={'dt_au','steps'};require(finite_number(action['dt_au']) and 0<action['dt_au']<=.1 and type(action['steps']) is int and 1<=action['steps']<=20000,'COUPLED_TIME_STEP_OUT_OF_DOMAIN')
 require(set(action)==keys,'COUPLED_UNDECLARED_ACTION_FIELD')
 return kind
def transition(a,p,action):
 """Only worker calls after actual execution admission; restoration never initializes psi."""
 kind=validate_action(p,action);w=restore(a,p)
 if kind=='PREPARE_COUPLED_STATE':w.prepare(action['initial'])
 if kind in ('APPLY_ELECTRIC_PULSE','PULSE_AND_EVOLVE_COUPLED_STATE'):w.apply(action['control'])
 if kind in ('EVOLVE_COUPLED_STATE','PULSE_AND_EVOLVE_COUPLED_STATE'):w.step(dt=action['dt_au'],count=action['steps'])
 return arrays_of(w),state_fields(w)
