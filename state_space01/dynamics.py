"""Mature QuTiP propagation of a declared effective Hamiltonian, no new TDSE solver."""
import numpy as np
from .contract import field_check,model_check

def field_value(t,c,origin):
    x=t-origin;T=c['duration_au']
    if x<0 or x>T:return 0.0
    return c['amplitude_au']*np.sin(np.pi*x/T)**2*np.cos(c['omega_au']*x+c['phase_rad'])

def propagate(model,ket,control,t0,duration,origin=0,fixture=False,evidence_dir=None):
    import qutip as qt
    from scipy.constants import physical_constants
    h,mu=model_check(model,allow_fixture=fixture);field_check(control)
    axis=np.array(control['polarization']);m=np.einsum('a,aij->ij',axis,mu);gap=float(h[1,1].real)
    coupling=control['amplitude_au']*np.linalg.norm(m,2)
    separation=model['selected'].get('nearest_computed_omitted_root_separation_Eh')
    if coupling/gap>.02 or (separation is not None and coupling/separation>.02):raise ValueError('WEAK_TRUNCATION_SCREEN_FAILED')
    c={**control,'omega_au':control['carrier_ratio']*gap};times=np.linspace(t0,t0+duration,801)
    step=min(2*np.pi/c['omega_au']/24,duration/100)
    H=qt.QobjEvo([qt.Qobj(h),[-qt.Qobj(m),lambda t,args:field_value(t,c,origin)]])
    options={'method':'dop853','rtol':1e-9,'atol':1e-11,'max_step':step,'nsteps':20000,'normalize_output':False,'store_states':True,'progress_bar':''}
    # Exactly one predeclared tighter-tolerance replica; not retries/scanning.
    first=qt.sesolve(H,qt.Qobj(np.asarray(ket,complex)),times,options=options)
    psi=np.array([s.full().ravel() for s in first.states])
    if evidence_dir is not None:
        import pathlib
        p=pathlib.Path(evidence_dir);p.mkdir(parents=True,exist_ok=True)
        np.savez_compressed(p/'completed_primary_propagation.npz',time_au=times,kets=psi)
    tight=qt.sesolve(H,qt.Qobj(np.asarray(ket,complex)),times,options={**options,'rtol':1e-11,'atol':1e-13})
    psi2=np.array([s.full().ravel() for s in tight.states])
    norms=np.sum(np.abs(psi)**2,axis=1);pop=np.abs(psi)**2;coherence=psi[:,0]*psi[:,1].conj()
    mu_expect=np.einsum('ti,ij,tj->t',psi.conj(),m,psi).real
    E0=np.einsum('ti,ij,tj->t',psi.conj(),h,psi).real;field=np.array([field_value(t,c,origin) for t in times]);Edriven=E0-field*mu_expect
    qa={'norm_error_max':float(np.max(np.abs(norms-1))),'population_sum_error_max':float(np.max(np.abs(pop.sum(axis=1)-1))),
        'population_tolerance_difference_max':float(np.max(np.abs(pop-np.abs(psi2)**2))),
        'state_vector_tolerance_difference_max':float(np.max(np.abs(psi-psi2))),
        'derived_density_trace_error_max':float(np.max(np.abs(norms-1))),'derived_density_hermitian':'Outer-product construction; algebraic consistency, not an independent physics test',
        'Hermitian_Hamiltonian':bool(np.allclose(h,h.conj().T) and np.allclose(m,m.conj().T)),
        'energy_check':'Driven H(t): neither H0 nor instantaneous H(t) expectation is required constant. Zero-field constant-H conservation is software-tested separately.',
        'basis_truncation':'NOT_CERTIFIED','physical_molecular_accuracy':'NOT_CERTIFIED','integrator_options':options,'tighter_replica':{'rtol':1e-11,'atol':1e-13},'propagations':2,'effective_coupling_over_gap':float(coupling/gap),'engine':'QuTiP','version':qt.__version__}
    quality_ok=qa['norm_error_max']<=1e-7 and qa['population_tolerance_difference_max']<=1e-6
    au_fs=physical_constants['atomic unit of time'][0]*1e15
    arrays={'time_au':times,'time_fs':times*au_fs,'kets':psi,'tighter_kets':psi2,'populations':pop,'coherence_01':coherence,'field_au':field,'dipole_projection_au':mu_expect,'H0_expectation_Eh':E0,'instantaneous_H_expectation_Eh':Edriven}
    obs={'status':'CALCULATED_EFFECTIVE_MODEL' if quality_ok else 'NUMERICALLY_UNVERIFIED','population_max':float(pop[:,1].max()),'population_final':float(pop[-1,1]),'coherence_abs_max':float(np.abs(coherence).max()),'start_time_au':float(t0),'end_time_au':float(times[-1]),'atomic_time_in_fs':au_fs,'quality':qa,'interpretation':'Two-state effective amplitudes/population, not exact many-electron population or electron density'}
    return psi[-1],arrays,obs
