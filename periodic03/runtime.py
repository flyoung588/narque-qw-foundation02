"""Thin KRKS adapter using established ASE/Cell/GDF/Becke machinery, no solver."""
import json,math,os,pathlib,time,traceback
from router import digest,save
from qw_next.periodic_evidence import stage,plain,cell_evidence
from .contract import validate,reduced_points
from .preflight import check
from .quality import electron_counts,labels
ENERGY_ZERO='neutral3D periodic all-electron BO/PBE total per primitive input cell with Ewald convention; NOT molecular HF absolute reference'
def solve(spec,out):
 meta=validate(spec);out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
 if meta['method']!='KRKS':
  if not meta['legacy_request']:raise ValueError('OUT_OF_MODEL_DOMAIN: explicit RKS numeric extension not implemented; use legacy request or KRKS')
  from qw_next.periodic_world import route_world
  return route_world(spec,out)
 stage(out,'WORLD_SPEC_VALIDATED',spec=spec,metadata=meta)
 cg=pathlib.Path('/sys/fs/cgroup')
 mem=(cg/'memory.max').read_text().strip();quota,period=(cg/'cpu.max').read_text().split()
 if mem=='max' or int(mem)>1024**3 or (cg/'memory.swap.max').read_text().strip()!='0' or quota=='max' or int(quota)>int(period) or len(os.sched_getaffinity(0))!=1 or os.listdir('/sys/class/net')!=['lo']:raise RuntimeError('RESOURCE_BLOCKED: need1CPU/1GiB/0extraSwap/noNetwork')
 import numpy as np
 import ase,pyscf
 from ase import Atoms
 from ase.neighborlist import neighbor_list
 from pyscf import lib
 from pyscf.lib.parameters import BOHR
 from pyscf.pbc import gto,dft
 from pyscf.pbc.dft.gen_grid import BeckeGrids
 lib.num_threads(1);m=spec['matter'];n=meta['numerics'];t=time.monotonic()
 atoms=Atoms([x['element'] for x in m['atoms']],positions=[x['xyz_angstrom'] for x in m['atoms']],cell=m['cell_angstrom'],pbc=True)
 if len(neighbor_list('d',atoms,.35,self_interaction=False)):raise ValueError('PHYSICALLY_INVALID: collision')
 ii,dd=neighbor_list('id',atoms,min(atoms.cell.lengths())*1.01,self_interaction=False);near=[]
 for i in range(len(atoms)):
  ds=dd[ii==i];distance=float(ds.min());near.append({'atom':i,'distance_A':distance,'count':int(np.sum(np.isclose(ds,distance,atol=1e-9,rtol=0)))})
 stage(out,'ASE_PERIODIC_ATOMS_CONSTRUCTED',cell_A=plain(atoms.cell.array),positions_A=plain(atoms.positions),pbc=plain(atoms.pbc),nearest_neighbors=near)
 cell=gto.Cell();cell.atom=[(x['element'],x['xyz_angstrom']) for x in m['atoms']];cell.a=m['cell_angstrom'];cell.unit='Angstrom';cell.dimension=3;cell.charge=0;cell.spin=0;cell.basis='cc-pvdz';cell.precision=n['cell_precision'];cell.max_memory=400;cell.verbose=4;cell.output=str(out/'pbc.log');cell.build()
 stage(out,'PYSCF_CELL_BUILT',AO_count=cell.nao_nr(),nelectron=cell.nelectron)
 if cell.nao_nr()>80:raise ValueError('OUT_OF_MODEL_DOMAIN: AO>80')
 save(out/'construction.json',cell_evidence(spec,atoms,cell,near,BOHR));stage(out,'CONSTRUCTION_EVIDENCE_SAVED')
 sampling=meta['sampling'];kpts=cell.make_kpts(sampling['mesh'],with_gamma_point=True,wrap_around=True,space_group_symmetry=False,time_reversal_symmetry=False)
 scaled=cell.get_scaled_kpts(kpts);expected=np.asarray(reduced_points(sampling['mesh']))
 if not np.allclose(scaled,expected,atol=1e-12) or len(kpts)!=meta['nkpts']:raise RuntimeError('ACTUAL_KPOINT_GENERATION_MISMATCH')
 weights=np.ones(len(kpts))/len(kpts)
 krecord={**sampling,'actual_kpts_absolute_1_per_Bohr':plain(kpts),'actual_fractional_reciprocal_kpts':plain(scaled),'actual_weights':plain(weights),'Gamma_included':bool(np.any(np.linalg.norm(kpts,axis=1)<1e-12)),'definition':'fractional coordinates multiply primitive reciprocal vectors including2pi; absolute rad/Bohr. Even2mesh uses fractions0,-1/2, not half-shifted Monkhorst-Pack. No IBZ/symmetry reduction.'}
 save(out/'k_sampling.json',krecord)
 mf=dft.KRKS(cell,kpts=kpts).density_fit(auxbasis='weigend');mf.xc='PBE';mf.grids=BeckeGrids(cell);mf.grids.level=n['Becke_level'];mf.conv_tol=n['conv_tol'];mf.max_cycle=n['max_cycle']
 check(cell,mf,out);stage(out,'GDF_INITIALIZATION_STARTED');mf.with_df.build();stage(out,'GDF_INITIALIZATION_FINISHED',aux_AO_count=mf.with_df.auxcell.nao_nr())
 mf.grids.build();stage(out,'PERIODIC_SCF_STARTED',solver='KRKS',nkpts=len(kpts),Becke_points=len(mf.grids.weights),numerics=n)
 history=[];last={}
 def callback(env):
  dm=np.asarray(env['dm']);e=float(env['e_tot']);prev=last.get('dm')
  row={'cycle':int(env.get('cycle',-1)),'energy_Eh':e,'delta_Eh':e-last['energy'] if 'energy' in last else None,'density_step_Frobenius':float(np.linalg.norm(dm-prev)) if prev is not None else None,'orbital_gradient_norm':float(env['norm_gorb']) if 'norm_gorb' in env else None,'PySCF_density_norm':float(env['norm_ddm']) if 'norm_ddm' in env else None}
  history.append(row);last.update(dm=dm.copy(),energy=e);stage(out,'SCF_ITERATION_'+str(row['cycle']),**row)
 mf.callback=callback
 energy=float(mf.kernel());stage(out,'PERIODIC_SCF_FINISHED',converged=bool(mf.converged),energy_Eh=energy if math.isfinite(energy) else None)
 if not math.isfinite(energy):raise RuntimeError('NUMERICALLY_UNVERIFIED: nonfinite energy')
 # Save bounded energy immediately; later diagnostic failure cannot erase completed SCF.
 base={'status':'CALCULATED' if mf.converged else 'UNVERIFIED','spec':spec,'world_spec_sha256':digest(spec),'observation':{'engine':'PySCF-PBC','solver':'KRKS','SCF_converged':bool(mf.converged),'energy_Eh_per_cell':energy,'energy_unit':'Eh/cell','energy_zero':ENERGY_ZERO,'method':'KRKS/PBE','basis':'cc-pvdz all-electron','density_fitting':'GDF weigend','integration':'Becke level1','sampling':krecord,'numerics':n,'forces_status':'NOT_IMPLEMENTED','stress_status':'NOT_IMPLEMENTED','physical_accuracy':'NOT_CERTIFIED'},'numerical_quality':'PENDING_POST_SCF_DIAGNOSTICS'}
 save(out/'SCF_RESULT.json',base)
 if not mf.converged:
  base['numerical_quality']='NUMERICALLY_UNVERIFIED; post-SCF diagnostics not continued after nonconvergence';save(out/'observation.json',base);return base
 dm=np.asarray(mf.make_rdm1());ovlp=np.asarray(mf.get_ovlp());occ=np.asarray(mf.mo_occ)
 rho=mf.get_rho(dm=dm,grids=mf.grids)
 counts=electron_counts(occ,dm,ovlp,weights,rho,mf.grids.weights)
 np.savez_compressed(out/'final_density_evidence.npz',dm=dm,overlap=ovlp,occupations=occ,mo_energy=np.asarray(mf.mo_energy),kpts=kpts,weights=weights,realspace_density=rho,grid_weights=mf.grids.weights)
 integer=bool(np.all(np.isclose(occ,0,atol=1e-10)|np.isclose(occ,2,atol=1e-10)))
 diag={**counts,'theoretical_electrons':cell.nelectron,'quadrature_minus_trace':counts['realspace_integrated_electrons']-counts['density_overlap_trace_electrons'],'occupation_minus_trace':counts['occupation_electrons']-counts['density_overlap_trace_electrons'],'integer_closed_shell_occupations':integer,'SCF_iterations':history,'final_vs_last_callback_delta_Eh':energy-last['energy'] if 'energy' in last else None,'final_vs_last_callback_density_Frobenius':float(np.linalg.norm(dm-last['dm'])) if 'dm' in last else None,'SCF_converged':bool(mf.converged),'k_sampling':krecord,'basis':'cc-pVDZ all-electron','aux_basis':'weigend','aux_AO_count':mf.with_df.auxcell.nao_nr(),'Becke_level':mf.grids.level,'Becke_points':len(mf.grids.weights),'grid_weight_volume_Bohr3':float(mf.grids.weights.sum()),'cell_volume_Bohr3':float(cell.vol),'cost':{'scientific_wall_seconds':time.monotonic()-t,'temporary_3c_file_bytes':os.path.getsize(mf.with_df._cderi) if isinstance(mf.with_df._cderi,str) and os.path.isfile(mf.with_df._cderi) else None},'sensitivity_checks_performed':[],'labels':labels(mf.converged),'diagnostic_only_thresholds':{'electron_trace_abs_1e_6':'screening algebraic identity, not material accuracy; no automatic resource allocation','quadrature_abs_1e_3':'warning only, not material accuracy or execution gate'},'physics_limits':'PBE, finite Gaussian basis, finite full k mesh; no independent reference; quadrature/momentum/basis errors distinct and coupled'}
 diag['warnings']=[]
 if abs(counts['density_overlap_trace_electrons']-cell.nelectron)>1e-6:diag['warnings'].append('ALGEBRAIC_ELECTRON_TRACE_SCREEN')
 if abs(diag['quadrature_minus_trace'])>1e-3:diag['warnings'].append('QUADRATURE_ELECTRON_SCREEN')
 if not integer:diag['warnings'].append('UNSUPPORTED_FRACTIONAL_OCCUPATIONS')
 save(out/'numerical_quality.json',diag);base['numerical_quality']=diag;base['observation']['versions']={'PySCF':pyscf.__version__,'ASE':ase.__version__,'NumPy':np.__version__};base['observation']['AO_count']=cell.nao_nr()
 if not integer:base['status']='UNVERIFIED'
 save(out/'observation.json',base);stage(out,'OBSERVATION_SAVED',status=base['status']);return base
def run(spec,out):
 try:return solve(spec,out)
 except BaseException as e:
  text=str(e);status='ENGINE_UNAVAILABLE' if isinstance(e,ImportError) else 'RESOURCE_BLOCKED' if text.startswith('RESOURCE_BLOCKED') else 'OUT_OF_MODEL_DOMAIN' if text.startswith(('OUT_OF_MODEL_DOMAIN','PHYSICALLY_INVALID')) else 'NUMERICALLY_UNVERIFIED'
  rec={'status':status,'spec':spec,'error':text,'type':type(e).__name__,'traceback':traceback.format_exc()};save(pathlib.Path(out)/'failure.json',rec);return rec
