"""Real orthonormal orbital RDM conventions follow PySCF 2.8.0.

dm1[p,q]=<q+ p>; dm2[p,q,r,s]=<p+ r+ s q>.
Only singlets permit <Si.Sj>=3<Szi.Szj>. No unique atomic-spin claim.
"""
import numpy as np
def wick(da,db):
    aa=np.einsum('qp,sr->pqrs',da,da)-np.einsum('sp,qr->pqrs',da,da)
    bb=np.einsum('qp,sr->pqrs',db,db)-np.einsum('sp,qr->pqrs',db,db)
    ab=np.einsum('qp,sr->pqrs',da,db)
    return (da,db),(aa,ab,bb)
def rotate(rdms,u):
    if not np.allclose(u@u.T,np.eye(len(u)),atol=1e-9):raise ValueError('NONORTHOGONAL_ORBITAL_TRANSFORM')
    one,two=rdms
    return tuple(u@d@u.T for d in one),tuple(np.einsum('ip,jq,kr,ls,pqrs->ijkl',u,u,u,u,g,optimize=True) for g in two)
def measure(rdms,*,singlet):
    if singlet is not True:raise ValueError('SINGLET_REQUIRED_FOR_ISOTROPIC_SPIN')
    (a,b),(aa,ab,bb)=rdms;n=np.diag(a+b);dim=len(n)
    spin=np.empty((dim,dim));charge=np.empty_like(spin)
    for i in range(dim):
        for j in range(dim):
            same=aa[i,i,j,j]+bb[i,i,j,j];opposite=ab[i,i,j,j]+ab[j,j,i,i]
            delta=n[i] if i==j else 0.
            spin[i,j]=.75*(same-opposite+delta)
            charge[i,j]=same+opposite+delta-n[i]*n[j]
    occ=np.linalg.eigvalsh(a+b)[::-1]
    return {'natural_occupations':occ.tolist(),'nonidempotency':float(np.sum(occ*(2-occ))),
            'site_population':n.tolist(),'site_double_occupancy':[float(ab[i,i,i,i]) for i in range(dim)],
            'spin_dot_matrix_hbar2':spin.tolist(),'connected_charge_covariance':charge.tolist(),
            'total_spin_square_from_sites':float(spin.sum()),'partition':'SYMMETRIC_LOWDIN_AO; not unique atomic partition'}
def diagnostics(rdms,nelec):
    (a,b),(aa,ab,bb)=rdms;na,nb=nelec
    return {'trace_alpha_error':float(abs(np.trace(a)-na)),'trace_beta_error':float(abs(np.trace(b)-nb)),
            'aa_contraction_error':float(np.max(abs(np.einsum('pqrr->pq',aa)-(na-1)*a.T))),
            'ab_contraction_error':float(np.max(abs(np.einsum('pqrr->pq',ab)-nb*a.T))),
            'bb_contraction_error':float(np.max(abs(np.einsum('pqrr->pq',bb)-(nb-1)*b.T)))}
