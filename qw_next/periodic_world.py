"""WorldSpec extension: bounded neutral 3D cells, not a new matter protocol.
Only semantic validation/scaling is stdlib-testable; real solver is lazy imported.
"""
import copy,json,math,pathlib,sys,time,traceback
from router import digest,save
Z={s:i+1 for i,s in enumerate(['H','He','Li','Be','B','C','N','O','F','Ne','Na','Mg','Al','Si','P','S','Cl','Ar'])}
def det(a):return a[0][0]*(a[1][1]*a[2][2]-a[1][2]*a[2][1])-a[0][1]*(a[1][0]*a[2][2]-a[1][2]*a[2][0])+a[0][2]*(a[1][0]*a[2][1]-a[1][1]*a[2][0])
def vector(v):return isinstance(v,list) and len(v)==3 and all(type(x) in (int,float) and math.isfinite(x) for x in v)
def validate_cell(spec):
 if spec.get('version')!='QW-WORLDSPEC-0.1' or spec.get('epistemic_mode')!='GROUNDED':raise ValueError('OUT_OF_MODEL_DOMAIN: version/mode')
 if not isinstance(spec.get('object_id'),str) or not spec['object_id']:raise ValueError('PHYSICALLY_INVALID: missing identity')
 if set(spec)-{'version','object_id','epistemic_mode','matter','physics','experiment'}:raise ValueError('OUT_OF_MODEL_DOMAIN: unknown envelope field')
 m=spec['matter'];p=spec['physics']
 if m.get('type')!='periodic_cell' or m.get('periodic') is not True:raise ValueError('OUT_OF_MODEL_DOMAIN: requires explicit3D periodic_cell')
 if set(m)-{'type','periodic','atoms','charge','spin_2S','cell_angstrom','source'}:raise ValueError('OUT_OF_MODEL_DOMAIN: unsupported matter field')
 if type(m.get('charge')) is not int or m['charge']!=0 or type(m.get('spin_2S')) is not int or m['spin_2S']!=0:raise ValueError('OUT_OF_MODEL_DOMAIN: neutral closed-shell cells only')
 atoms=m.get('atoms',[])
 if not 1<=len(atoms)<=4:raise ValueError('OUT_OF_MODEL_DOMAIN: max4 atoms per cell')
 for a in atoms:
  if set(a)!={'element','xyz_angstrom'} or a.get('element') not in Z or not vector(a.get('xyz_angstrom')):raise ValueError('PHYSICALLY_INVALID: atom or element')
  if max(abs(x) for x in a['xyz_angstrom'])>1000:raise ValueError('OUT_OF_MODEL_DOMAIN: coordinates')
 electrons=sum(Z[a['element']] for a in atoms)
 if electrons>30 or electrons%2:raise ValueError('OUT_OF_MODEL_DOMAIN: <=30 all-electron even closed-shell count')
 a=m.get('cell_angstrom')
 if not isinstance(a,list) or len(a)!=3 or not all(vector(v) for v in a):raise ValueError('PHYSICALLY_INVALID: lattice')
 volume=det(a)
 if not 1<=volume<=15625:raise ValueError('PHYSICALLY_INVALID: right-handed nondegenerate bounded lattice')
 lengths=[math.sqrt(sum(x*x for x in v)) for v in a]
 if not all(2<=x<=25 for x in lengths):raise ValueError('OUT_OF_MODEL_DOMAIN: lattice length2..25A')
 for i,j in [(0,1),(0,2),(1,2)]:
  if abs(sum(x*y for x,y in zip(a[i],a[j]))/lengths[i]/lengths[j])>.75:raise ValueError('OUT_OF_MODEL_DOMAIN: excessive skew')
 if set(p)-{'engine','method','basis','xc','observables'}:raise ValueError('OUT_OF_MODEL_DOMAIN: unsupported physics field')
 if p.get('engine')!='pyscf-pbc' or p.get('method')!='RKS' or p.get('basis')!='cc-pvdz' or p.get('xc')!='PBE' or p.get('observables')!=['energy']:raise ValueError('OUT_OF_MODEL_DOMAIN: Gamma RKS/PBE/cc-pVDZ energy only; forces/stress not implemented')
 if spec.get('experiment',{}).get('action','single_point')!='single_point':raise ValueError('OUT_OF_MODEL_DOMAIN: no dynamics/optimizer')
 return {'all_electron_count':electrons,'cell_volume_A3':volume,'pbc':[True]*3,'geometry_collision_check':'required actual ASE neighbor check at construction, not yet performed by stdlib validation'}
def scale_cell(spec,factor):
 validate_cell(spec)
 if type(factor) not in (int,float) or not math.isfinite(factor) or not .9<=factor<=1.1:raise ValueError('OUT_OF_MODEL_DOMAIN: bounded affine strain factor')
 result=copy.deepcopy(spec);m=result['matter'];m['cell_angstrom']=[[factor*x for x in row] for row in m['cell_angstrom']]
 for atom in m['atoms']:atom['xyz_angstrom']=[factor*x for x in atom['xyz_angstrom']]
 result['object_id']+='_strained';validate_cell(result);return result
def compatible_cell_energy(a,b):
 if a.get('status')!='CALCULATED' or b.get('status')!='CALCULATED':return False
 sa=a['spec'];sb=b['spec']
 try:validate_cell(sa);validate_cell(sb)
 except (ValueError,KeyError):return False
 return sa['physics']==sb['physics'] and [x['element'] for x in sa['matter']['atoms']]==[x['element'] for x in sb['matter']['atoms']] and a['observation']['energy_zero']==b['observation']['energy_zero']
def solve_cell(spec,out):
 meta=validate_cell(spec)
 from qw_next.periodic_evidence import stage,plain,cell_evidence,resource_preflight
 out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
 stage(out,'WORLD_SPEC_VALIDATED',spec=spec,validation=meta)
 # Actual scientific execution remains bounded even if invoked outside its CLI.
 import os
 cg=pathlib.Path('/sys/fs/cgroup')
 if not cg.is_dir():raise RuntimeError('RESOURCE_ADMISSION_BLOCKED: periodic scientific execution requires isolated Linuxcgroup')
 mem=(cg/'memory.max').read_text().strip();quota,period=(cg/'cpu.max').read_text().split()
 if mem=='max' or int(mem)>1024**3 or (cg/'memory.swap.max').read_text().strip()!='0' or quota=='max' or int(quota)>int(period) or len(os.sched_getaffinity(0))!=1 or os.listdir('/sys/class/net')!=['lo']:raise RuntimeError('RESOURCE_ADMISSION_BLOCKED: need<=1CPU,<=1GiB,0swap,no-network')
 import numpy as np
 import ase,pyscf
 from ase import Atoms
 from ase.neighborlist import neighbor_list
 from pyscf import lib
 from pyscf.pbc import gto,dft
 from pyscf.pbc.dft.gen_grid import BeckeGrids
 lib.num_threads(1);m=spec['matter'];out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
 atoms=Atoms([a['element'] for a in m['atoms']],positions=[a['xyz_angstrom'] for a in m['atoms']],cell=m['cell_angstrom'],pbc=True)
 if len(neighbor_list('d',atoms,.35,self_interaction=False)):raise ValueError('PHYSICALLY_INVALID: periodic nucleus separation<.35A')
 # Enumerate periodic neighbors within one shortest lattice-vector radius.
 ii,dist=neighbor_list('id',atoms,min(atoms.cell.lengths())*1.01,self_interaction=False)
 near=[]
 for i in range(len(atoms)):
  ds=dist[ii==i];r=float(ds.min()) if len(ds) else None
  near.append({'atom':i,'distance_A':r,'count':int(np.sum(np.isclose(ds,r,atol=1e-9,rtol=0))) if r is not None else 0})
 stage(out,'ASE_PERIODIC_ATOMS_CONSTRUCTED',symbols=atoms.get_chemical_symbols(),positions_A=plain(atoms.positions),cell_A=plain(atoms.cell.array),volume_A3=float(atoms.get_volume()),pbc=plain(atoms.pbc),neighbors=near)
 cell=gto.Cell();cell.atom=[(a['element'],a['xyz_angstrom']) for a in m['atoms']];cell.a=m['cell_angstrom'];cell.unit='Angstrom';cell.dimension=3;cell.charge=0;cell.spin=0;cell.basis='cc-pvdz';cell.precision=1e-6;cell.max_memory=400;cell.verbose=4;cell.output=str(out/'pbc.log');cell.build()
 if cell.nao_nr()>80:raise ValueError('OUT_OF_MODEL_DOMAIN: AO count>80, no computation')
 stage(out,'PYSCF_CELL_BUILT',lattice_vectors_Bohr=plain(cell.lattice_vectors()),atom_coords_Bohr=plain(cell.atom_coords(unit='Bohr')),nelectron=cell.nelectron,AO_count=cell.nao_nr())
 from pyscf.lib.parameters import BOHR
 evidence=cell_evidence(spec,atoms,cell,near,BOHR)
 save(out/'construction.json',evidence);stage(out,'CONSTRUCTION_EVIDENCE_SAVED',path='construction.json')
 mf=dft.RKS(cell,kpt=np.zeros(3)).density_fit(auxbasis='weigend');mf.xc='PBE';mf.grids=BeckeGrids(cell);mf.grids.level=1;mf.conv_tol=1e-8;mf.max_cycle=80
 resource_preflight(cell,mf,out)
 stage(out,'GDF_INITIALIZATION_STARTED')
 mf.with_df.build()
 stage(out,'GDF_INITIALIZATION_FINISHED',aux_AO_count=mf.with_df.auxcell.nao_nr())
 mf.grids.build()
 stage(out,'PERIODIC_SCF_STARTED',XC=mf.xc,kpt=plain(mf.kpt),Becke_level=mf.grids.level,Becke_points=len(mf.grids.weights),conv_tol=mf.conv_tol,max_cycle=mf.max_cycle)
 def iteration(env):
  stage(out,'SCF_ITERATION_'+str(env.get('cycle',-1)),cycle=int(env.get('cycle',-1)),energy_Eh=float(env['e_tot']))
 mf.callback=iteration
 energy=float(mf.kernel());obs={'engine':'PySCF-PBC','engine_version':pyscf.__version__,'ASE_version':ase.__version__,'ASE_Atoms_constructed':True,'method':'Gamma-only RKS/PBE','basis':'cc-pvdz all-electron','density_fitting':'GDF weigend auxiliary basis','integration':'Becke level1, NOT convergence certified','kmesh':[1,1,1],'cell_precision':cell.precision,'AO_count':cell.nao_nr(),'energy_Eh_per_cell':energy,'energy_unit':'Eh/cell','energy_zero':'neutral3D periodic all-electron BO/PBE total per primitive input cell with Ewald convention; NOT molecular HF absolute reference','SCF_converged':bool(mf.converged),'forces':None,'forces_status':'NOT_IMPLEMENTED','stress_status':'NOT_IMPLEMENTED','basis_kmesh_grid_convergence':'NOT_TESTED','physical_precision':'NOT_CERTIFIED','construction':meta,'scope':'periodic scalar ground-state density/energy only, not atomistic dynamics or full many-body wavefunction'}
 stage(out,'PERIODIC_SCF_FINISHED',converged=bool(mf.converged),finite_energy=math.isfinite(energy),energy_Eh=energy if math.isfinite(energy) else None)
 if not math.isfinite(energy):raise RuntimeError('NUMERICAL_NONFINITE_ENERGY')
 save(out/'raw_observation.json',obs);stage(out,'OBSERVATION_SAVED',converged=bool(mf.converged),path='raw_observation.json')
 return {'status':'CALCULATED' if mf.converged and math.isfinite(energy) else 'UNVERIFIED','spec':spec,'observation':obs}
def route_world(spec,out):
 t=time.monotonic()
 if spec.get('matter',{}).get('type')=='molecule':
  from router import run
  return run(spec,out)
 try:result=solve_cell(spec,out)
 except ImportError as exc:result={'status':'ENGINE_UNAVAILABLE','error':str(exc),'spec':spec}
 except RuntimeError as exc:result={'status':'BLOCKED' if str(exc).startswith('RESOURCE_ADMISSION_BLOCKED') else 'UNVERIFIED','error':str(exc),'spec':spec}
 except ValueError as exc:result={'status':'OUT_OF_MODEL_DOMAIN' if str(exc).startswith('OUT_OF_MODEL_DOMAIN') else 'PHYSICALLY_INVALID','error':str(exc),'spec':spec}
 except Exception as exc:result={'status':'UNVERIFIED','error':str(exc),'traceback':traceback.format_exc(),'spec':spec}
 result.update(world_spec_sha256=digest(spec),wall_seconds=time.monotonic()-t);save(pathlib.Path(out)/'world_return.json',result);return result
if __name__=='__main__':print(json.dumps(route_world(json.loads(pathlib.Path(sys.argv[1]).read_text()),sys.argv[2]),indent=2))
