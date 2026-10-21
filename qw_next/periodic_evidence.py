"""Evidence and admission only; no new physical model or altered solver settings."""
import datetime,json,os,pathlib
from router import save
def plain(value):
 import numpy as np
 return np.asarray(value).tolist()
def stage(out,name,**details):
 out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
 event={'stage':name,'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),**details}
 save(out/(name+'.json'),event)
 with (out/'stages.jsonl').open('a') as f:
  f.write(json.dumps(event,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
def cell_evidence(spec,atoms,cell,neighbors,bohr):
 import numpy as np
 a=cell.lattice_vectors() # PySCF2.8.0: no unit kwarg; explicitly returns Bohr.
 coords=cell.atom_coords(unit='Bohr')
 if not np.allclose(a*bohr,np.asarray(spec['matter']['cell_angstrom']),rtol=1e-12,atol=1e-12):raise ValueError('UNIT_CHECK_FAILED: lattice conversion')
 if not np.allclose(coords*bohr,atoms.positions,rtol=1e-12,atol=1e-12):raise ValueError('UNIT_CHECK_FAILED: atom conversion')
 return {'spec':spec,'ASE':{'symbols':atoms.get_chemical_symbols(),'positions_A':plain(atoms.positions),'cell_A':plain(atoms.cell.array),'pbc':plain(atoms.pbc),'volume_A3':float(atoms.get_volume()),'nearest_neighbor':neighbors},'PySCF_Cell':{'input_a':plain(cell.a),'input_unit':cell.unit,'lattice_vectors_Bohr':plain(a),'atom_coords_Bohr':plain(coords),'volume_Bohr3':float(cell.vol),'nelectron':cell.nelectron,'spin':cell.spin,'dimension':cell.dimension,'AO_count':cell.nao_nr(),'default_mesh_not_allocated':plain(cell.mesh),'precision':cell.precision,'max_memory_MB_advisory':cell.max_memory},'unit_checks':'PASS; original/ASE Angstrom vs actual PySCF Bohr explicitly converted'}
def resource_preflight(cell,mf,out):
 """Inspect pinned default RS-GDF mesh estimates WITHOUT building full FFT arrays."""
 import math,shutil
 import numpy as np
 from pyscf.pbc.df import df,rsdf_builder as rs
 if mf.with_df.__class__ is not df.GDF or mf.with_df._prefer_ccdf or cell.omega!=0:raise RuntimeError('RESOURCE_ADMISSION_BLOCKED: unaudited DF path')
 aux=df.make_modrho_basis(cell,'weigend',mf.with_df.exp_to_discard)
 kpts=np.zeros((1,3));omega,mesh,ke=rs._guess_omega(aux,kpts,None)
 # Nuc builder default omega for one kpoint is 1/(1+1**(1/9)) = .5.
 nucmesh=cell.symmetrize_mesh(cell.cutoff_to_mesh(rs.estimate_ke_cutoff_for_omega(cell,.5)))
 # 2c metric may tighten reciprocal mesh; use 1e-12 only as conservative estimate,
 # not a changed solver parameter. Actual solver precision remains untouched.
 metric=cell.symmetrize_mesh(aux.cutoff_to_mesh(rs.estimate_ke_cutoff_for_omega(aux,omega,1e-12)))
 meshes={'GDF_default_estimate':plain(cell.symmetrize_mesh(mesh)),'nuclear_default_estimate':plain(nucmesh),'metric_conservative_estimate':plain(metric)}
 points=max(math.prod(x) for x in meshes.values());na=cell.nao_nr();nx=aux.nao_nr()
 # Screening allowance, NOT a proven total upper bound. Refuse clearly huge arrays.
 workspace=points*16*(na*(na+1)//2+nx+16)*2
 tensor=nx*(na*(na+1)//2)*8
 free=shutil.disk_usage('/tmp').free
 record={'path':'PySCF2.8 default _RSGDFBuilder and _RSNucBuilder, not FFTDF','auxiliary':'weigend','aux_AO_count':nx,'meshes':meshes,'largest_mesh_points':points,'screen_workspace_bytes':workspace,'screen_definition':'2 complex buffers over max estimated grid times AO-pairs+aux+16; conservative screening estimate, not validated peak bound','packed3c_payload_bytes':tensor,'3c_multiple_copy_allowance_bytes':tensor*16,'tmp_free_bytes':free,'tmpfs_counts_inside_1GiB':True,'memory_floor_warning':'library max_memory includes 1000/2000MB floors; small AO/grid bounds do not prove total demand, cgroup remains authoritative','Becke':'level1 atom-centered, not cell.mesh uniform grid','model_or_precision_changed':False,'admission':'PENDING'}
 if workspace>256*1024**2 or tensor*16>free//2:
  record['admission']='RESOURCE_BLOCKED';save(pathlib.Path(out)/'resource_preflight.json',record);raise RuntimeError('RESOURCE_ADMISSION_BLOCKED: estimated workspace/temp burden exceeds conservative admission budget')
 record['admission']='CONDITIONAL_ALLOW_UNDER_HARD_CGROUP';save(pathlib.Path(out)/'resource_preflight.json',record)
 return record
