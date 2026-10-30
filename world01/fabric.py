"""Versioned manifests, model admission, translations and physical comparison."""
import copy,math
from router import digest
from interactive01.world import validate
from .contracts import WorldError

def manifest(ident,domain,representation,ops,obs,unavailable,hamiltonian,evidence,limits,adapter,reference):
    return {'schema':'QW_CAPABILITY_MANIFEST_01','id':ident,'domain':domain,'representation':representation,
            'Hamiltonian_approximation':hamiltonian,'supported_operations':ops,'supported_observables':obs,'unavailable_observables':unavailable,
            'units_reference':reference,'numerical_quality_requirements':'Retain original convergence flags/residuals/actual settings; no inherited material accuracy',
            'dependencies':{'cloud':'Python3.12/NumPy2.2.6/SciPy1.15.3/PySCF2.8.0/ASE3.29.0; effective domain additionally QuTiP5.2.1','local_engine_availability':'UNKNOWN_NOT_REQUIRED_FOR_E00'},
            'evidence_level':'HISTORICAL_REAL_EXECUTION_WITH_BOUNDED_SCOPE','evidence':evidence,'physical_qualification':'MODEL_ONLY_NOT_MATERIAL_CERTIFIED',
            'independent_validation':'W2_INCOMPLETE; same PySCF family not independent','resource_envelope':{'science_CPU':1,'threads':1,'memory_bytes':1073741824,'extra_swap':0,'network':'none','job_minutes_max':15,'current_E00_science_jobs':0,'new_cost':0},
            'model_limitations':limits,'existing_adapter':adapter,'schema_is_not_installation_proof':True}
MANIFESTS={
 'molecular':manifest('molecular','Nonperiodic H..Ne <=8atoms <=30electrons, RHF/UHF STO-3G/cc-pVDZ','Geometry plus SCF observation',['DISPLACE_ATOM','MEASURE_OBSERVABLE'],['energy','forces'],['lifetime','nuclear_dynamics','reaction_rate'],'Fixed-nuclei nonrelativistic Coulomb mean field','Existing molecular observations; results/frontier01 RHF reference and W1 historical source',['Finite-basis/method error','No arbitrary matter','Analytic molecular force only when actually exported'],'state_space01.world_runtime.act','Molecular total BO energy Eh; forces per original result units'),
 'periodic':manifest('periodic','Neutral closed-shell <=4atoms <=30electrons3DPBC, PBE cc-pVDZ','Periodic SCF observation',['DISPLACE_ATOM','AFFINE_STRAIN_CELL','MEASURE_OBSERVABLE'],['energy'],['forces','stress','stability','dynamics'],'PBC RKS/KRKS/PBE GDF,weigend; Gamma or1/8 admitted k points','results/interactive01/EXECUTION_REPORT.json; periodic03/EXECUTION_REPORT.json',['Actual GDF/grid co-variation','Not pure k convergence','No force from finite differences'],'state_space01.world_runtime.act','Eh per primitive input cell, Ewald convention, no cross-composition ranking'),
 'effective':manifest('effective','Declared two-state response-derived electronic model','Complex2ket with physical time',['APPLY_EXTERNAL_FIELD','PREPARE_ELECTRONIC_STATE','EVOLVE_QUANTUM_STATE','MEASURE_STATE_POPULATION'],['population','norm','time','model'],['full_electron_density','ionization','bath_rate'],'H(t)=diag(0,gap)-E(t)mu, closed sesolve effective model','results/state_space01/EXECUTION_REPORT.json; state_space01/MODEL_BRIDGE.json',['Two-state truncation','TDA labels not exact eigenstates','No continuum/nuclei/bath','Root phase and length gauge retained'],'state_space01.world_runtime.act','Atomic time/field/dipole, relative ground label E0=0; not molecular absolute energy'),
 'correlated':manifest('correlated','Neutral singlet 2/4/6H STO-3G <=400 determinants; real-run evidence H4 only','FCI alpha/beta determinant tensor,1/2RDM',['DISPLACE_ATOM','OBSERVE_CORRELATIONS'],['energy','natural_occupations','double_occupancy','spin_correlations','charge_covariance'],['forces','material_magnetism','real_time_dynamics'],'Fixed-nuclei finite-basis singlet full Coulomb FCI, RHF reference separately labeled','results/frontier01/EXECUTION_REPORT.json',['Lowdin partition nonunique','Static eigenstate not time dynamics','No basis/UHF/material certification'],'frontier01.world_runtime.act','Eh total BO; spin hbar^2; occupation dimensionless; Lowdin convention')}
def select(state):
    p=state['payload'];k=p['schema']
    if k=='QW_COLLINEAR_NUCLEAR_WAVEPACKET_01':
        from dynamics01.integration import MANIFESTS as registered
        return copy.deepcopy(registered['dynamics'])
    validate_object(p['world_spec'])
    if k=='QW_EFFECTIVE_QUANTUM_STATE_01':
        from state_space01.contract import validate_system,model_check
        try:validate_system(p['world_spec']);model_check(p['model'])
        except (ValueError,KeyError,TypeError) as e:raise WorldError('MODEL_OUT_OF_DOMAIN',str(e)) from e
        ident='effective'
    elif k=='QW_CORRELATED_ELECTRONIC_STATE_01':
        from frontier01.contract import validate as validate_correlated
        try:validate_correlated({'world_spec':p['world_spec'],'correlation_model':p['correlation_model']})
        except (ValueError,KeyError,TypeError) as e:raise WorldError('MODEL_OUT_OF_DOMAIN',str(e)) from e
        ident='correlated'
    elif k=='QW_PHYSICAL_STATE_01':
        ident='periodic' if p['world_spec']['matter']['periodic'] else 'molecular'
        if ident=='molecular' and (p['world_spec']['physics']['engine'] not in ('pyscf','ase-pyscf') or p['world_spec']['physics']['method'] not in ('RHF','UHF')):
            raise WorldError('MODEL_UNAVAILABLE','Empirical or unknown models cannot inherit quantum capability/evidence')
    else:raise WorldError('UNSUPPORTED_STATE_KIND')
    return copy.deepcopy(MANIFESTS[ident])
def validate_object(spec):
    try:validate(spec)
    except (ValueError,KeyError,TypeError) as e:
        text=str(e);code='INVALID_ELECTRON_SPIN' if 'PARITY' in text or 'SPIN' in text else 'COLLISION' if 'COLLISION' in text or 'COINCIDENT' in text else 'INVALID_CELL' if 'lattice' in text or 'CELL' in text else 'OUT_OF_DOMAIN'
        raise WorldError(code,text) from e
def admit(state,action,observables=(),*,execute=False,authority=None):
    m=select(state)
    if set(observables)-set(m['supported_observables']):
        raise WorldError('FORCE_NOT_AVAILABLE' if 'forces' in observables else 'UNSUPPORTED_OBSERVABLE')
    if action not in m['supported_operations']:raise WorldError('OPERATION_OUT_OF_DOMAIN')
    if execute:raise WorldError('AUTHORITY_MISSING','E00 hard-denies all new SCF/FCI/propagation; historical permissions cannot be inherited')
    return {'status':'ADMITTED_SEMANTICS_ONLY','manifest':m,'adapter':m['existing_adapter'],'science_executed':False}
def translation(state,target):
    p=state['payload'];k=p['schema']
    if target==k:return {'status':'INPUT_VALID','mapping':'IDENTITY_REFERENCE_ONLY','losses':[],'source_hash':state['sha256']}
    if k=='QW_EFFECTIVE_QUANTUM_STATE_01' and target=='QUTIP_TWO_STATE_PARAMETERS':
        from state_space01.contract import model_check
        model_check(p['model'])
        if p['model']['source_type']!='PYSCF_RHF_TDA_RESPONSE_DERIVED':raise WorldError('UNVERIFIED_MODEL_SOURCE')
        return {'status':'APPROXIMATION_LOSS','mapping':'Retain existing computed TDA response parameter descriptor; NOT convert exact full electronic wavefunction','source_hash':state['sha256'],'parameters':copy.deepcopy(p['model']),'time_origin':p['control_origin_au'],'gauge_phase':'Inherited length gauge and selected root phase; state_space01/MODEL_BRIDGE.json','energy_zero':'Effective reference0, not absolute molecular energy','losses':['Other electronic states','Continuum/ionization','Nuclear motion','Bath/decoherence','Exact molecular eigenstate interpretation'],'new_calculation':False}
    if target=='MATTER_SPEC':return {'status':'APPROXIMATION_LOSS','mapping':'EXPLICIT_GEOMETRY_PROJECTION_ONLY','matter':copy.deepcopy(p['world_spec']['matter']),'losses':['All electronic amplitudes/RDM','Physical time/control','Observations are not transferred'],'source_hash':state['sha256']}
    raise WorldError('TRANSLATION_FORBIDDEN','No proven physical projection/phase/normalization/time mapping')
def _energy(state,method=None):
    p=state['payload'];o=p.get('observation') or {}
    if o.get('synthetic'):raise WorldError('SYNTHETIC_MISLABEL_BLOCKED')
    if p['schema']=='QW_CORRELATED_ELECTRONIC_STATE_01':
        if o.get('status')!='CALCULATED':raise WorldError('UNVERIFIED')
        observation_values(state)
        return o['energy_RHF_Eh' if method=='RHF' else 'energy_FCI_Eh'],'MOLECULAR_BO_TOTAL_Eh',o.get('quality',{})
    if p['schema']!='QW_PHYSICAL_STATE_01':raise WorldError('INCOMPARABLE','Relative effective energy not molecular total')
    if o.get('status')!='CALCULATED':raise WorldError('UNVERIFIED')
    values=observation_values(state)
    v=o['observation'];e=values['energy']['value']
    if e is None or not math.isfinite(e):raise WorldError('UNVERIFIED_ENERGY')
    ref=v.get('energy_zero')
    if not ref:raise WorldError('ENERGY_REFERENCE_UNKNOWN')
    return e,ref,{k:v.get(k) for k in ['density_fitting','integration','numerics','sampling']}
def compare(a,b,contract=None):
    contract=contract or {};pa,pb=a['payload'],b['payload'];sa,sb=pa['world_spec'],pb['world_spec']
    for k in ['periodic','charge','spin_2S']:
        if sa['matter'][k]!=sb['matter'][k]:raise WorldError('INCOMPARABLE','Boundary/charge/spin mismatch')
    if [x['element'] for x in sa['matter']['atoms']]!=[x['element'] for x in sb['matter']['atoms']]:raise WorldError('INCOMPARABLE','Chemical composition mismatch; no ranking')
    if contract.get('independent_W2'):raise WorldError('INDEPENDENCE_INSUFFICIENT','Same PySCF family; no W2 upgrade')
    if contract.get('pure_k_convergence'):raise WorldError('NUMERICAL_SETTING_COVARIATION','Actual GDF settings changed; not isolated k convergence')
    if contract.get('kind') not in (None,'SAME_MODEL_IDENTITY','SAME_MODEL_GEOMETRY_PATH','RHF_FCI_SAME_STATE'):raise WorldError('COMPARISON_CONTRACT_UNSUPPORTED')
    if contract.get('kind')=='SAME_MODEL_IDENTITY' and a['sha256']!=b['sha256']:raise WorldError('INCOMPARABLE','Identity contract requires the same state')
    internal=contract.get('kind')=='RHF_FCI_SAME_STATE'
    if internal:
        if a['sha256']!=b['sha256'] or pa['schema']!='QW_CORRELATED_ELECTRONIC_STATE_01':raise WorldError('INCOMPARABLE','Explicit same correlated state required')
        ea,ra,qa=_energy(a,'RHF');eb,rb,qb=_energy(b,'FCI');status='MODEL_INTERNAL_NOT_INDEPENDENT'
    else:
        if pa['schema']!=pb['schema'] or sa['physics']!=sb['physics'] or pa.get('correlation_model')!=pb.get('correlation_model'):raise WorldError('INCOMPARABLE','Model/basis/state representation mismatch')
        if sa['matter'].get('periodic') and sa['matter'].get('cell_angstrom')!=sb['matter'].get('cell_angstrom') and not contract.get('allow_cell_change'):raise WorldError('INCOMPARABLE','Cell change requires explicit path contract')
        ea,ra,qa=_energy(a);eb,rb,qb=_energy(b);status='MODEL_INTERNAL_GEOMETRY_PATH'
    if ra!=rb:raise WorldError('INCOMPARABLE','Energy zero mismatch')
    if digest(qa)!=digest(qb) and sa['matter']['periodic']:
        if not contract.get('allow_realized_numerical_covariation'):raise WorldError('NUMERICAL_SETTING_COVARIATION')
    return {'status':status,'delta_energy_Eh':eb-ea,'units':'Eh/cell' if sa['matter']['periodic'] else 'Eh','reference':ra,'numerical_details':[qa,qb],'interpretation':'Finite-model path only; not force, stability, convergence certification or W2','checked_semantics':{'composition_charge_spin_boundary':'Explicit input equality checked','Hamiltonian_approximation_basis':'Same declared physics/correlation model, or explicit same-state RHF/FCI contract','state_representation':pa['schema'],'units':'Eh/cell' if sa['matter']['periodic'] else 'Eh','energy_zero':ra,'time_gauge_environment':'Not applicable to these static BO comparisons; effective dynamic-state absolute energies are rejected','declared_numerical_settings':sa['physics'].get('numerics','INHERITED_MODEL_DEFAULTS'),'unreported_realized_settings':'UNKNOWN; not inferred equal, not a numerical-precision certificate','comparison_contract':contract.get('kind','INHERITED_FINITE_MODEL_PATH')}}
def validate_claim(kind,**kwargs):
    codes={'periodic_force':'FORCE_NOT_AVAILABLE','independent_RHF_FCI':'INDEPENDENCE_INSUFFICIENT','pure_k_convergence':'NUMERICAL_SETTING_COVARIATION','unique_atomic_lowdin':'PARTITION_DEPENDENT_CLAIM_BLOCKED','fixture_calculated':'SYNTHETIC_MISLABEL_BLOCKED','historical_verdict_rewrite':'HISTORICAL_VERDICT_CONFLICT','implicit_retry':'NO_IMPLICIT_RETRY','new_science':'AUTHORITY_MISSING','static_to_dynamics':'TRANSLATION_FORBIDDEN','full_electron_from_two_state':'TRANSLATION_FORBIDDEN'}
    if kind in codes:raise WorldError(codes[kind])
    raise WorldError('UNSUPPORTED_CLAIM','No default scientific promotion')

def observation_values(state):
    """Available computed values, with explicit schema-defined units/references."""
    p=state['payload'];o=p.get('observation') or {};out={}
    def scalar(v):return type(v) in (int,float) and math.isfinite(v)
    if p['schema']=='QW_PHYSICAL_STATE_01':
        data=o['observation'];e=data.get('energy_Eh_per_cell',data.get('energy'));expected='Eh/cell' if p['world_spec']['matter']['periodic'] else 'Eh'
        if not scalar(e) or data.get('energy_unit')!=expected or not data.get('energy_zero'):raise WorldError('INVALID_OBSERVATION_UNITS_OR_REFERENCE')
        if data.get('SCF_converged',data.get('converged')) is not True:raise WorldError('SCF_RESULT_UNVERIFIED')
        out['energy']={'value':e,'unit':expected,'reference':data['energy_zero'],'definition':'Original total BO energy including nuclear terms, within the declared approximation'}
        if not p['world_spec']['matter']['periodic'] and 'forces_Eh_per_bohr' in data:
            f=data['forces_Eh_per_bohr'];n=len(p['world_spec']['matter']['atoms'])
            if not isinstance(f,list) or len(f)!=n or any(not isinstance(v,list) or len(v)!=3 or not all(scalar(x) for x in v) for v in f):raise WorldError('INVALID_FORCE_OBSERVATION')
            out['forces']={'value':f,'unit':'Eh/bohr','definition':'Negative analytic BO nuclear gradient in input atom order'}
    elif p['schema']=='QW_CORRELATED_ELECTRONIC_STATE_01':
        if not all(scalar(o[k]) for k in ('energy_RHF_Eh','energy_FCI_Eh')):raise WorldError('INVALID_ENERGY_OBSERVATION')
        out['energy']={'value':o['energy_FCI_Eh'],'unit':'Eh','reference':'MOLECULAR_BO_TOTAL_Eh','definition':'Finite-basis FCI total BO energy; RHF stored separately'}
        for k,key,unit in [('natural_occupations','natural_occupations','dimensionless'),('double_occupancy','site_double_occupancy','dimensionless'),('spin_correlations','spin_dot_matrix_hbar2','hbar^2'),('charge_covariance','connected_charge_covariance','dimensionless')]:
            if key in o.get('FCI_observables',{}):out[k]={'value':o['FCI_observables'][key],'unit':unit,'definition':'Original symmetric Lowdin partition, not unique atomic measurement'}
    return out
