"""Bounded new physics controls; existing molecular WorldSpec unchanged."""
import math
import numpy as np
from foundation01.contract import validate as validate_molecule
from router import digest

def validate_system(spec):
    validate_molecule(spec)
    m=spec['matter'];p=spec['physics']
    if m.get('periodic') or m['charge']!=0 or m['spin_2S']!=0 or p['engine']!='pyscf' or p['method']!='RHF' or p['basis']!='cc-pvdz' or p['observables']!=['energy']:raise ValueError('RESPONSE_DOMAIN_ENERGY_SOURCE_ONLY_NO_FORCE_PROMISE')
    if len(m['atoms'])>4:raise ValueError('RESPONSE_RESOURCE_DOMAIN')
    # Restrict this bridge to centrosymmetric geometry: parity eigenstates have
    # zero diagonal dipole. No unknown permanent moments filled with zero.
    atoms=m['atoms'];pos=np.array([a['xyz_angstrom'] for a in atoms],float)
    if not np.isfinite(pos).all():raise ValueError('GEOMETRY')
    for a in atoms:
        partners=[b for b in atoms if a['element']==b['element'] and np.linalg.norm(np.array(a['xyz_angstrom'])+np.array(b['xyz_angstrom']))<1e-10]
        if len(partners)!=1:raise ValueError('INVERSION_SYMMETRY_REQUIRED')
    for i in range(len(pos)):
        for j in range(i):
            if np.linalg.norm(pos[i]-pos[j])<.35:raise ValueError('COLLISION')
    return True

def field_check(control):
    required={'amplitude_au','polarization','duration_au','carrier_ratio','phase_rad','envelope','time_unit','field_unit'}
    if set(control)!=required:raise ValueError('FIELD_FIELDS')
    for k in ['amplitude_au','duration_au','carrier_ratio','phase_rad']:
        if type(control[k]) not in (int,float) or not math.isfinite(control[k]):raise ValueError('NONFINITE_CONTROL')
    if not 0<=control['amplitude_au']<=.002 or not 10<=control['duration_au']<=800 or not .9<=control['carrier_ratio']<=1.1 or abs(control['phase_rad'])>2*math.pi:raise ValueError('CONTROL_BOUND')
    axis=np.asarray(control['polarization'],float)
    if axis.shape!=(3,) or not np.isfinite(axis).all() or abs(np.linalg.norm(axis)-1)>1e-12:raise ValueError('POLARIZATION')
    if control['envelope']!='sin2' or control['field_unit']!='atomic_electric_field' or control['time_unit']!='atomic_time':raise ValueError('UNITS_ENVELOPE')
    return control

def select_root(energies,dipoles,converged,axis):
    e=np.asarray(energies,float);d=np.asarray(dipoles,float);c=np.asarray(converged,bool);a=np.asarray(axis,float)
    if e.ndim!=1 or not 1<=len(e)<=6 or d.shape!=(len(e),3) or c.shape!=e.shape or not np.isfinite(e).all() or not np.isfinite(d).all():raise ValueError('EXCITATION_DATA')
    candidates=[i for i in range(len(e)) if c[i] and e[i]>0 and abs(d[i]@a)>.1]
    if not candidates:raise ValueError('NO_POSITIVE_CONVERGED_BRIGHT_ROOT')
    i=min(candidates,key=lambda j:e[j]);seps=[abs(e[i]-v) for j,v in enumerate(e) if j!=i]
    isolation=min(seps,default=float('inf'))
    if isolation<1e-5:raise ValueError('NONDEGENERATE_ROOT_REQUIRED')
    # Root phase chosen so longitudinal transition moment is positive. Whether
    # PySCF uses electron-position or dipole sign is absorbed in this root gauge.
    phase=1 if d[i]@a>=0 else -1
    return {'root_index':i,'gap_Eh':float(e[i]),'transition_dipole_au':(phase*d[i]).tolist(),'effective_root_phase_relative_to_PySCF_X':-phase,'phase_convention':'physical dipole projection positive; electronic minus sign absorbed in root phase','nearest_computed_omitted_root_separation_Eh':None if not seps else float(isolation)}

def model_check(model,allow_fixture=False):
    if model['source_type'] not in (['PYSCF_RHF_TDA_RESPONSE_DERIVED','USER_DEFINED_EFFECTIVE_MODEL'] if allow_fixture else ['PYSCF_RHF_TDA_RESPONSE_DERIVED']):raise ValueError('MODEL_PROVENANCE')
    h=np.asarray(model['H0_Eh'],complex);mu=np.asarray(model['dipole_au'],complex)
    if h.shape!=(2,2) or mu.shape!=(3,2,2) or not np.isfinite(h).all() or not np.isfinite(mu).all() or not np.allclose(h,h.conj().T,atol=1e-12) or not all(np.allclose(x,x.conj().T,atol=1e-12) for x in mu):raise ValueError('HERMITIAN_MODEL')
    if h[0,0]!=0 or h[1,1].real<=0 or np.any(h-np.diag(np.diag(h))):raise ValueError('ENERGY_BASIS_REFERENCE')
    return h,mu

def validate_action(state,action):
    if action.get('source_state_sha256')!=state['sha256']:raise ValueError('STALE_STATE')
    k=action.get('type')
    common={'type','source_state_sha256'}
    allowed={'APPLY_EXTERNAL_FIELD':common|{'control'},'PREPARE_ELECTRONIC_STATE':common|{'basis_index'},'EVOLVE_QUANTUM_STATE':common|{'duration_au','time_unit'},'MEASURE_STATE_POPULATION':common}
    if k not in allowed or set(action)!=allowed[k]:raise ValueError('UNSUPPORTED_ACTION')
    if k=='APPLY_EXTERNAL_FIELD':field_check(action['control'])
    if k=='PREPARE_ELECTRONIC_STATE' and (type(action['basis_index']) is not int or action['basis_index'] not in [0,1]):raise ValueError('BASIS_STATE')
    if k=='EVOLVE_QUANTUM_STATE' and (type(action['duration_au']) not in [int,float] or not 10<=action['duration_au']<=800 or action['time_unit']!='atomic_time'):raise ValueError('TIME_BOUND')
    return k
