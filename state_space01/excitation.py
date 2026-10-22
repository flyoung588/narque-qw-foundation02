"""Thin mature PySCF TDA adapter. No electronic eigensolver implemented here."""
import pathlib,hashlib
import numpy as np
from interactive01.world import freeze
from router import digest
from .contract import validate_system,select_root

def build_model(spec,out,axis):
    validate_system(spec);out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
    import pyscf
    from pyscf import gto,scf,tdscf,lib
    lib.num_threads(1);freeze(out/'START.json',{'spec_sha256':digest(spec),'engine':'PySCF','version':pyscf.__version__})
    mol=gto.M(atom=[(a['element'],a['xyz_angstrom']) for a in spec['matter']['atoms']],unit='Angstrom',charge=0,spin=0,basis='cc-pvdz',symmetry=True,verbose=4,output=str(out/'electronic.log'),max_memory=400)
    mf=scf.RHF(mol);mf.conv_tol=1e-10;mf.max_cycle=80;mf.kernel()
    ground_mu=np.asarray(mf.dip_moment(unit='AU',verbose=0),float)
    freeze(out/'SCF.json',{'converged':bool(mf.converged),'energy_Eh':float(mf.e_tot),'permanent_dipole_au':ground_mu.tolist(),'point_group':mol.topgroup})
    if not mf.converged:raise RuntimeError('SCF_NOT_CONVERGED')
    if not np.isfinite(ground_mu).all() or np.linalg.norm(ground_mu)>1e-7:raise RuntimeError('GROUND_PARITY_DIPOLE_ASSUMPTION_FAILED')
    td=tdscf.TDA(mf);td.singlet=True;td.nstates=min(6,(mol.nelectron//2)*(mol.nao_nr()-mol.nelectron//2));td.conv_tol=1e-9;td.max_cycle=80;td.kernel()
    e=np.asarray(td.e,float);dip=np.asarray(td.transition_dipole(),float);conv=np.asarray(td.converged,bool)
    x=np.asarray([xy[0] for xy in td.xy]);vind,_=td.gen_vind(mf)
    # PySCF singlet X convention 2X^dagger X=1, documented in fixed source.
    flat=x.reshape(len(x),-1)*np.sqrt(2);res=np.linalg.norm(vind(flat)-e[:,None]*flat,axis=1)
    np.savez_compressed(out/'electronic_response.npz',excitation_Eh=e,transition_position_moments_au=dip,TDA_X=x,mo_coeff=mf.mo_coeff,mo_energy=mf.mo_energy,overlap=mf.get_ovlp(),TDA_residuals=res)
    freeze(out/'TDA.json',{'energies_Eh':e.tolist(),'transition_moments_au':dip.tolist(),'converged':conv.tolist(),'residuals':res.tolist(),'source':'PySCF2.8 RHF TDA singlet length-gauge transition data; finite basis/linear response, not exact levels'})
    selected=select_root(e,dip,conv,axis);i=selected['root_index']
    if res[i]>1e-7:raise RuntimeError('TDA_RESIDUAL_FAILED')
    if abs(np.linalg.norm(flat[i])-1)>1e-7:raise RuntimeError('TDA_NORMALIZATION_FAILED')
    mu=np.zeros((3,2,2));mu[:,0,1]=selected['transition_dipole_au'];mu[:,1,0]=selected['transition_dipole_au']
    model={'source_type':'PYSCF_RHF_TDA_RESPONSE_DERIVED','world_spec_sha256':digest(spec),'engine':'PySCF','engine_version':pyscf.__version__,'H0_Eh':[[0,0],[0,selected['gap_Eh']]],'dipole_au':mu.tolist(),'selected':selected,
           'source_files_sha256':{name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in ['SCF.json','TDA.json','electronic_response.npz']},
           'source_SCF_energy_Eh':float(mf.e_tot),'source_TDA_residual':float(res[i]),'model_space':'Reference+one isolated bright TDA singlet, phase fixed by positive projected moment','energy_zero':'RHF-reference effective level set0; excitation relative to that reference',
           'dipole_sign':'PySCF length transition uses electronic position; chosen effective root phase absorbs overall electronic minus sign, and dipole projection is positive. Recorded coherence is in this declared gauge.',
           'diagonal_dipoles':'Zero by centrosymmetric parity-state assumption, not fitted excited-state moments. Selected root required isolated among computed roots.',
           'omissions':['all other electronic levels and continuum','excited-excited dipoles','nuclear motion','ionization','relativity','decoherence/dissipation','self-consistent real-time electron density'],
           'truncation_validity':'Weak coupling screens against computed gaps only; uncomputed roots/multiphoton/ionization errors UNKNOWN. Not a certified low-energy reduction.'}
    freeze(out/'MODEL.json',model);return model
