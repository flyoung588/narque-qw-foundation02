"""Thin PySCF FCI bridge. No molecule-specific solver, no fallback/retry."""
import pathlib
import numpy as np
from interactive01.world import freeze
from router import digest
from frontier01.contract import validate
from frontier01.observables import wick,rotate,measure,diagnostics
def solve(request,out):
    out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True);spec=validate(request)
    def log(x):print(x,flush=True)
    log('IMPORT');import pyscf
    from pyscf import gto,scf,ao2mo,fci
    from pyscf.fci import cistring,spin_op
    log('MOLECULE_BUILD')
    mol=gto.M(atom=[(a['element'],a['xyz_angstrom']) for a in spec['matter']['atoms']],unit='Angstrom',basis='sto-3g',charge=0,spin=0,verbose=4,max_memory=400,output=str(out/'pyscf.log'))
    n=mol.nao_nr();ne=(mol.nelectron//2,)*2
    if n!=len(spec['matter']['atoms']) or n>6:raise ValueError('ACTUAL_ORBITAL_BOUND')
    log('SCF_START');mf=scf.RHF(mol);mf.conv_tol=1e-11;mf.max_cycle=100;erhf=float(mf.kernel());log('SCF_END')
    freeze(out/'rhf_reference.json',{'energy_Eh':erhf,'converged':bool(mf.converged),'world_spec_sha256':digest(spec),'role':'REFERENCE_NOT_FCI_LABEL'})
    if not mf.converged:raise RuntimeError('RHF_NOT_CONVERGED')
    c=mf.mo_coeff;s=mf.get_ovlp();h=c.T@mf.get_hcore()@c;eri=ao2mo.restore(1,ao2mo.kernel(mol,c),n)
    np.savez_compressed(out/'integrals.npz',h1_Eh=h,eri_Eh=eri,overlap=s,mo_coeff=c)
    log('FCI_START');solver=fci.direct_spin0.FCI(mol);solver.conv_tol=1e-10;solver.max_cycle=100;solver.max_memory=400;solver.nroots=1
    energy,ci=solver.kernel(h,eri,n,ne,ecore=mol.energy_nuc());energy=float(energy);ci=np.asarray(ci);log('FCI_END')
    # Save solved wavefunction before diagnostics; later failures preserve it.
    np.savez_compressed(out/'ci_raw.npz',ci=ci,strings_alpha=cistring.make_strings(range(n),ne[0]),strings_beta=cistring.make_strings(range(n),ne[1]))
    rdms=solver.make_rdm12s(ci,n,ne)
    hc=solver.contract_2e(solver.absorb_h1e(h,eri,n,ne,.5),ci,n,ne)
    residual=float(np.linalg.norm(hc-(energy-mol.energy_nuc())*ci));s2,mult=spin_op.spin_square(ci,n,ne)
    eig,vec=np.linalg.eigh(s)
    if eig.min()<=1e-8:raise ValueError('OVERLAP_ILL_CONDITIONED')
    u=(vec*np.sqrt(eig))@vec.T@c
    local=rotate(rdms,u);fci_obs=measure(local,singlet=True)
    da=np.diag((mf.mo_occ>0).astype(float));rhf_local=rotate(wick(da,da),u);rhf_obs=measure(rhf_local,singlet=True)
    qa=diagnostics(rdms,ne);occ=np.asarray(fci_obs['natural_occupations'])
    # RDM energy independent from the solver-reported scalar energy.
    dm1=rdms[0][0]+rdms[0][1];aa,ab,bb=rdms[1]
    dm2=aa+bb+ab+ab.transpose(2,3,0,1)
    rdm_energy=float(np.einsum('pq,qp',h,dm1)+.5*np.einsum('pqrs,pqrs',eri,dm2)+mol.energy_nuc())
    qa.update({'FCI_converged':bool(solver.converged),'RHF_converged':bool(mf.converged),'Hamiltonian_residual_Eh':residual,'norm_error':float(abs(np.vdot(ci,ci)-1)),'S2_hbar2':float(s2),'multiplicity':float(mult),'RDM_energy_error_Eh':abs(rdm_energy-energy),'site_spin_sum_error':abs(fci_obs['total_spin_square_from_sites']-s2),'occupation_min':float(occ.min()),'occupation_max':float(occ.max())})
    valid=(qa['FCI_converged'] and residual<1e-8 and qa['norm_error']<1e-9 and abs(s2)<1e-7 and qa['RDM_energy_error_Eh']<1e-8 and qa['site_spin_sum_error']<1e-7 and max(qa[k] for k in qa if k.endswith('contraction_error') or k.startswith('trace_'))<1e-8 and occ.min()>-1e-8 and occ.max()<2+1e-8 and energy<=erhf+1e-8)
    result={'status':'CALCULATED' if valid else 'UNVERIFIED','request_sha256':digest(request),'world_spec_sha256':digest(spec),'engine':'PySCF','engine_version':pyscf.__version__,'actual_model':'Singlet full CI over all STO-3G molecular orbitals; RHF is reference only','energy_FCI_Eh':energy,'energy_RHF_Eh':erhf,'correlation_energy_vs_RHF_Eh':energy-erhf,'FCI_observables':fci_obs,'RHF_same_partition_observables':rhf_obs,'quality':qa,'prediction_supported':bool(energy-erhf<-.001 and fci_obs['nonidempotency']>.05),'limits':['Finite basis not converged; no material accuracy','Local spin/charge partition is defined, not unique','Static correlated electronic eigenstate, not dynamics','Negative pair correlation alone is not beyond-RHF evidence','No unrestricted-HF comparison or novelty claim']}
    arrays={'ci':ci,'h1_Eh':h,'eri_Eh':eri,'overlap':s,'mo_coeff':c,'MO_to_Lowdin':u,'dm1a_MO':rdms[0][0],'dm1b_MO':rdms[0][1],'dm2aa_MO':aa,'dm2ab_MO':ab,'dm2bb_MO':bb,'strings_alpha':cistring.make_strings(range(n),ne[0]),'strings_beta':cistring.make_strings(range(n),ne[1])}
    np.savez_compressed(out/'scientific_arrays.npz',**arrays);freeze(out/'observation.json',result)
    if not valid:raise RuntimeError('NUMERICAL_QUALITY_FAILED_NO_RETRY')
    return result,arrays
