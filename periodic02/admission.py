"""Physical-domain routing and resource screening; no hidden physics solver.

The second independently implemented electronic-structure solver W2 remains
INCOMPLETE. ASE is a structure/calculator facade, not a second physics engine.
"""
import math

_Z = {s:i+1 for i,s in enumerate(
    ('H','He','Li','Be','B','C','N','O','F','Ne','Na','Mg','Al','Si','P','S','Cl','Ar'))}
_MOL = {k:v for k,v in _Z.items() if v<=10}


def _volume(v):
    a,b,c = v
    return a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0])


def _valid_vector(v):
    return isinstance(v,list) and len(v)==3 and all(
        type(x) in (int,float) and math.isfinite(x) for x in v)


def check_domain(spec):
    """Conservative preflight. Real periodic execution ALSO uses source-owned
    qw_next.periodic_world.validate_cell and its true ASE neighbour check.
    """
    if not isinstance(spec,dict) or spec.get('version')!='QW-WORLDSPEC-0.1':
        return 'WORLD_SPEC_VERSION_UNSUPPORTED'
    if spec.get('epistemic_mode')!='GROUNDED':
        return 'NON_GROUNDED_REQUIRES_SEPARATE_PHYSICS_AUTHORIZATION'
    if set(spec)-{'version','object_id','epistemic_mode','matter','physics','experiment'}:
        return 'UNKNOWN_WORLDSPEC_ENVELOPE_FIELDS'
    if not isinstance(spec.get('object_id'),str) or not 1<=len(spec['object_id'])<=100:
        return 'INVALID_OBJECT_ID'
    m=spec.get('matter');p=spec.get('physics')
    if not isinstance(m,dict) or not isinstance(p,dict):
        return 'INVALID_MATTER_OR_PHYSICS'
    atoms=m.get('atoms')
    if not isinstance(atoms,list) or not atoms:
        return 'NO_ATOMS'
    for a in atoms:
        if not isinstance(a,dict) or not isinstance(a.get('element'),str) or not _valid_vector(a.get('xyz_angstrom')):
            return 'MALFORMED_ATOM'
    if m.get('type')=='periodic_cell':
        if set(m)-{'type','periodic','atoms','charge','spin_2S','cell_angstrom','source'}:
            return 'UNSUPPORTED_PERIODIC_MATTER_FIELDS'
        if set(p)-{'engine','method','basis','xc','observables'}:
            return 'UNSUPPORTED_PERIODIC_PHYSICS_FIELDS'
        if any(set(a)!={'element','xyz_angstrom'} for a in atoms):
            return 'UNSUPPORTED_ATOM_FIELDS'
        if not m.get('periodic') is True:
            return 'PERIODICITY_NOT_EXPLICIT'
        if type(m.get('charge')) is not int or type(m.get('spin_2S')) is not int or m.get('charge')!=0 or m.get('spin_2S')!=0 or len(atoms)>4:
            return 'PERIODIC_CHARGE_SPIN_OR_SIZE_UNSUPPORTED'
        if any(a['element'] not in _Z for a in atoms):
            return 'PERIODIC_ELEMENT_UNSUPPORTED'
        electrons=sum(_Z[a['element']] for a in atoms)
        if electrons>30 or electrons%2:
            return 'PERIODIC_ELECTRON_DOMAIN_UNSUPPORTED'
        cell=m.get('cell_angstrom')
        if not isinstance(cell,list) or len(cell)!=3 or not all(_valid_vector(row) for row in cell):
            return 'PERIODIC_CELL_INVALID'
        vol=_volume(cell)
        if not 1<=vol<=15625:
            return 'PERIODIC_CELL_HANDNESS_OR_VOLUME'
        norm=[math.sqrt(sum(v*v for v in row)) for row in cell]
        if not all(2<=v<=25 for v in norm):
            return 'PERIODIC_LENGTH_OUT_OF_DOMAIN'
        for i,j in ((0,1),(0,2),(1,2)):
            c=sum(a*b for a,b in zip(cell[i],cell[j]))/(norm[i]*norm[j])
            if abs(c)>.75:
                return 'PERIODIC_EXCESSIVE_SKEW'
        if (p.get('engine')!='pyscf-pbc' or p.get('method')!='RKS' or
            p.get('basis')!='cc-pvdz' or p.get('xc')!='PBE' or
            p.get('observables')!=['energy']):
            return 'PERIODIC_MODEL_OR_OBSERVABLE_UNSUPPORTED'
        experiment=spec.get('experiment',{})
        if not isinstance(experiment,dict) or set(experiment)-{'action','description'}:
            return 'UNSUPPORTED_PERIODIC_EXPERIMENT_FIELDS'
        if experiment.get('action','single_point')!='single_point':
            return 'PERIODIC_DYNAMICS_NOT_SUPPORTED'
        return None
    if m.get('type')=='molecule':
        if set(m)-{'type','periodic','atoms','charge','spin_2S','source','bonds','smiles'}:
            return 'UNSUPPORTED_MOLECULAR_FIELDS'
        if set(p)-{'engine','method','basis','xc','observables'}:
            return 'UNSUPPORTED_MOLECULAR_PHYSICS_FIELDS'
        if m.get('periodic') is not False or len(atoms)>8:
            return 'MOLECULAR_PERIODICITY_OR_SIZE_UNSUPPORTED'
        if any(a['element'] not in _MOL for a in atoms):
            return 'MOLECULAR_ELEMENT_UNSUPPORTED'
        charge,spin=m.get('charge'),m.get('spin_2S')
        if type(charge) is not int or type(spin) is not int:
            return 'MOLECULAR_QUANTUM_NUMBERS_INVALID'
        ne=sum(_MOL[a['element']] for a in atoms)-charge
        if not 1<=ne<=30 or spin<0 or spin>ne or (ne-spin)%2:
            return 'MOLECULAR_ELECTRON_SPIN_PARITY_INVALID'
        if (p.get('engine') not in ('pyscf','ase-pyscf') or
            p.get('method') not in ('RHF','UHF') or
            p.get('basis') not in ('sto-3g','cc-pvdz') or
            p.get('observables') not in (['energy'],['forces'],['energy','forces'])):
            return 'MOLECULAR_METHOD_OR_ENGINE_UNSUPPORTED'
        if p.get('method')=='RHF' and spin:
            return 'RESTRICTED_METHOD_REQUIRES_SINGLET'
        return None
    return 'MATTER_TYPE_UNSUPPORTED'


def select_engine(spec):
    """Return one executable candidate and explicit physics/quality ceilings.

    This is capability admission, NOT measured cost or independent verification.
    Exact source-domain revalidation occurs inside the physics worker.
    """
    error=check_domain(spec)
    if error:
        return {'status':'REJECTED','reason':error,'engine':None,
                'physical_calculation':False}
    m,p=spec['matter'],spec['physics']
    if m['type']=='periodic_cell':
        ne=sum(_Z[a['element']] for a in m['atoms'])
        return {
            'status':'ELIGIBLE_FOR_RESOURCE_PREFLIGHT',
            'engine':'pyscf-pbc','actual_solver_family':'PySCF',
            'matter_type':'periodic_cell',
            'method':'Gamma RKS/PBE cc-pVDZ GDF/weigend Becke level1',
            'energy_reference':'periodic total energy Eh/cell (Ewald; not molecular total)',
            'current_observables':['energy'],
            'unavailable_observables':['forces','stress','phonons','dynamics'],
            'electron_count':ne,
            'cost_screening':('HIGHER_UNVERIFIED_COMPLEXITY' if ne>16 else 'SMALL_CELL_UNVERIFIED_COMPLEXITY'),
            'actual_runtime_preflight':'REQUIRED_BEFORE_SCF',
            'grid_k_basis_convergence':'NOT_CERTIFIED',
            'material_stability':'NOT_PROVEN',
            'physics_precision':'NOT_CERTIFIED',
            'W2_independent_solver':'INCOMPLETE',
            'physical_calculation':False,
            'no_cross_composition_absolute_energy_ranking':True,
            'note':'Only FCC-Ne has run successfully in this code domain. No cost or convergence guarantee for this new cell.'
        }
    return {
        'status':'ELIGIBLE_FOR_RESOURCE_PREFLIGHT',
        'engine':p['engine'], 'actual_solver_family':'PySCF',
        'matter_type':'molecule','electron_count':sum(_MOL[a['element']] for a in m['atoms'])-m['charge'],
        'current_observables':p['observables'],
        'method':p['method']+'/'+p['basis'],
        'actual_runtime_preflight':'REQUIRED',
        'physics_precision':'NOT_CERTIFIED',
        'W2_independent_solver':'INCOMPLETE',
        'physical_calculation':False,
        'no_cross_composition_absolute_energy_ranking':True
    }


def compare_priority(admissions):
    """Pre-execution triage only. Electron count is a crude resource indicator.
    It is NOT a scientific value score and never mandates a research allocation.
    """
    allowed=[x for x in admissions if x['status']=='ELIGIBLE_FOR_RESOURCE_PREFLIGHT']
    return sorted(allowed,key=lambda x:(x.get('electron_count',1000),x.get('engine','')))


def route_capability(spec, available_engines=None, resource_available=None):
    """Normalized public status; preserve original frozen select_engine semantics.

    SUPPORTED means model capability only, never a completed calculation or
    measured resource admission. Missing availability/resource evidence stays UNKNOWN.
    """
    admitted=select_engine(spec)
    if admitted['status']=='REJECTED':
        fields=spec if isinstance(spec,dict) else {}
        physics=fields.get('physics',{});matter=fields.get('matter',{})
        requested=physics.get('observables') if isinstance(physics,dict) else None
        periodic=isinstance(matter,dict) and matter.get('type')=='periodic_cell'
        status='UNSUPPORTED_OBSERVABLE' if periodic and requested!=['energy'] else 'OUT_OF_MODEL_DOMAIN'
        return {**admitted,'status':status}
    if available_engines is not None and admitted['engine'] not in available_engines:
        return {**admitted,'status':'ENGINE_UNAVAILABLE'}
    if resource_available is False:
        return {**admitted,'status':'RESOURCE_BLOCKED'}
    return {**admitted,'status':'SUPPORTED','availability':'UNKNOWN' if available_engines is None else 'CHECKED','resource_admission':'PENDING_RUNTIME' if resource_available is None else 'CALLER_REPORTED'}


def result_route_status(result):
    """Map actual worker return without replacing raw solver evidence."""
    status=result.get('status')
    if status=='CALCULATED':return 'SUPPORTED'
    if status=='ENGINE_UNAVAILABLE':return 'ENGINE_UNAVAILABLE'
    if status=='BLOCKED' and str(result.get('error','')).startswith('RESOURCE_ADMISSION_BLOCKED'):return 'RESOURCE_BLOCKED'
    if status in ('OUT_OF_MODEL_DOMAIN','PHYSICALLY_INVALID'):return 'OUT_OF_MODEL_DOMAIN'
    return 'NUMERICALLY_UNVERIFIED'
