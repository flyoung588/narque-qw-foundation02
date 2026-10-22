"""Backward compatible requests; deliberately no arbitrary k mesh or smearing."""
import copy,itertools,math
from periodic02.admission import route_capability
from qw_next.periodic_world import validate_cell
SAMPLING={'generator':'cell.make_kpts','with_gamma_point':True,'wrap_around':True,'symmetry_reduction':False,'weights':'uniform','coordinate_unit':'1/Bohr'}
NUMERICS={'Becke_level':1,'cell_precision':1e-6,'conv_tol':1e-8,'max_cycle':80}
def validate(spec):
 if not isinstance(spec,dict) or not isinstance(spec.get('physics'),dict) or not isinstance(spec.get('matter'),dict):raise ValueError('OUT_OF_MODEL_DOMAIN: structured physics/matter required')
 s=copy.deepcopy(spec);p=s['physics'];sampling=p.pop('k_sampling',None);numerics=p.pop('numerics',None)
 method=p.get('method')
 if method not in ('RKS','KRKS'):raise ValueError('OUT_OF_MODEL_DOMAIN: RKS/KRKS only')
 if method=='RKS' and ('k_sampling' in spec['physics'] or numerics is not None):raise ValueError('OUT_OF_MODEL_DOMAIN: legacy RKS unchanged; explicit sampling uses KRKS')
 if sampling is None:
  if method=='KRKS':raise ValueError('OUT_OF_MODEL_DOMAIN: KRKS requires explicit sampling')
  sampling={**SAMPLING,'mesh':[1,1,1]}
 if not isinstance(sampling,dict) or set(sampling)!={'mesh',*SAMPLING}:raise ValueError('OUT_OF_MODEL_DOMAIN: sampling fields')
 if any(sampling[k]!=v or type(sampling[k]) is not type(v) for k,v in SAMPLING.items()):raise ValueError('OUT_OF_MODEL_DOMAIN: only full Gamma-centered equal-weight mesh')
 mesh=sampling['mesh']
 if not isinstance(mesh,list) or any(type(n) is not int for n in mesh) or mesh not in ([1,1,1],[2,2,2]):raise ValueError('OUT_OF_MODEL_DOMAIN: admitted mesh only1^3 or2^3')
 if method=='RKS' and mesh!=[1,1,1]:raise ValueError('OUT_OF_MODEL_DOMAIN: multi-k requires KRKS, not repeated RKS')
 if numerics is not None and (not isinstance(numerics,dict) or set(numerics)!=set(NUMERICS) or any(numerics[k]!=v or type(numerics[k]) is not type(v) for k,v in NUMERICS.items())):raise ValueError('OUT_OF_MODEL_DOMAIN: numerical settings frozen in this tranche')
 p['method']='RKS';base=validate_cell(s)
 return {'base_spec':s,'method':method,'sampling':sampling,'numerics':dict(NUMERICS),'nkpts':math.prod(mesh),'base_validation':base,'legacy_request':method=='RKS' and 'k_sampling' not in spec['physics'] and numerics is None}
def reduced_points(mesh):
 """Expected fractional reciprocal grid; actual generation must use Cell.make_kpts."""
 return [[(i/n if i/n<.5 else i/n-1) for i,n in zip(point,mesh)] for point in itertools.product(*(range(n) for n in mesh))]
def route(spec,available=None,resource_ok=None):
 if not isinstance(spec,dict) or not isinstance(spec.get('matter'),dict) or not isinstance(spec.get('physics'),dict):return {'status':'OUT_OF_MODEL_DOMAIN','reason':'malformed structured request'}
 if spec.get('matter',{}).get('type')!='periodic_cell':return route_capability(spec,available,resource_ok)
 try:meta=validate(spec)
 except (KeyError,TypeError,ValueError) as e:return {'status':'UNSUPPORTED_OBSERVABLE' if spec.get('physics',{}).get('observables')!=['energy'] else 'OUT_OF_MODEL_DOMAIN','reason':str(e)}
 status='ENGINE_UNAVAILABLE' if available is not None and 'pyscf-pbc' not in available else 'RESOURCE_BLOCKED' if resource_ok is False else 'SUPPORTED'
 n=meta['nkpts']
 return {'status':status,'engine':'pyscf-pbc','solver':meta['method'],'family':'PySCF','sampling':meta['sampling'],'nkpts':n,'availability':'UNKNOWN' if available is None else 'CHECKED','resource_admission':'RUNTIME_PENDING' if resource_ok is None else 'CALLER_REPORTED','cost_screen':{'kpoints':n,'ordered_kpair_upper_count':n*n,'relative_cost':'Not linear prediction; GDF, memory and temp runtime checks required'},'uncertainty':'KPOINT/QUADRATURE/BASIS_SENSITIVITY_UNKNOWN','most_informative':'Compare KRKS1^3 and2^3 with fixed geometry/model/grid; not convergence certification','actual_physics':'NOT_IMPLIED','W2':'INCOMPLETE'}
def scope_valid(scope,phase,plan):
 from router import digest
 expected='NOT_GRANTED' if phase=='prepare' else 'GRANTED_FOR_PERIODIC03_ONCE' if phase=='execute' else None
 return expected is not None and scope.get('authority')==expected and scope.get('plan_sha256')==digest(plan) and all(scope.get(k)==v for k,v in {'max_jobs':1,'max_SCFs':2,'no_retry':True,'Job_minutes':15,'science_CPU':1,'threads':1,'memory_bytes':1073741824,'extra_swap':0,'network':'none','purchases':0}.items())
