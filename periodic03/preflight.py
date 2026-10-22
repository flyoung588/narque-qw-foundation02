"""Default PySCF2.8 GDF resource screening, no manually reduced mesh."""
import math,pathlib,shutil
from router import save
def check(cell,mf,out):
 import numpy as np
 from pyscf.pbc.df import df,rsdf_builder as rs
 if mf.with_df.__class__ is not df.GDF or mf.with_df._prefer_ccdf or cell.omega!=0:raise RuntimeError('RESOURCE_BLOCKED: unaudited density fitting path')
 kpts=np.asarray(mf.kpts);nk=len(kpts);aux=df.make_modrho_basis(cell,'weigend',mf.with_df.exp_to_discard)
 omega,mesh,ke=rs._guess_omega(aux,kpts,None)
 nuc_omega=1/(1+nk**(1/9))
 nuc=cell.symmetrize_mesh(cell.cutoff_to_mesh(rs.estimate_ke_cutoff_for_omega(cell,nuc_omega)))
 metric=cell.symmetrize_mesh(aux.cutoff_to_mesh(rs.estimate_ke_cutoff_for_omega(aux,omega,1e-12)))
 meshes={'primary_default':cell.symmetrize_mesh(mesh).tolist(),'nuclear_default':nuc.tolist(),'metric_conservative':metric.tolist()}
 pts=max(math.prod(x) for x in meshes.values());na=cell.nao_nr();nx=aux.nao_nr();pairs=na*(na+1)//2
 tensor=nk*nk*nx*pairs*16 # deliberately all ordered k-pairs, complex payload allowance
 workspace=pts*(pairs*(nk+1)+nx+16)*32
 free=shutil.disk_usage('/tmp').free
 rec={'GDF_path':'default _RSGDFBuilder / _RSNucBuilder, no FFTDF substitution','nkpts':nk,'aux_AO_count':nx,'estimated_meshes':meshes,'all_ordered_kpair_complex3c_bytes':tensor,'3c_four_copy_allowance':tensor*4,'reciprocal_screen_bytes':workspace,'tmp_free_bytes':free,'estimate_ceiling':'Screening estimate only; compact/smooth/image and block overhead not rigorously bounded. cgroup authoritative; OOM can still happen. No manual mesh/precision relaxation.','actual_temp_peak':'NOT_YET_MEASURED','admission':'PENDING'}
 # Small allocation screen plus physical free tmp; not a material accuracy threshold.
 rec['admission']='RESOURCE_BLOCKED' if workspace>256*1024**2 or tensor*4>free//2 else 'CONDITIONAL_ALLOW_UNDER_HARD_LIMITS'
 save(pathlib.Path(out)/'resource_preflight.json',rec)
 if rec['admission']=='RESOURCE_BLOCKED':raise RuntimeError('RESOURCE_BLOCKED: predicted workspace/temp exceeds fixed screening budget')
 return rec
