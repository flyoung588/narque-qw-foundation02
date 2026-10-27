import copy,json,math,pathlib,hashlib
from router import digest
from world01.contracts import WorldError
from world01 import fabric
from interactive01.world import apply
LIMITS={'max_jobs':2,'job_minutes':15,'CPU':1,'threads':1,'memory_bytes':2**30,'extra_swap':0,'science_network':'none','auto_retry':False,'purchases':0,'execution_model_calls_max':4}
SCOPE='QW-EXPLORER-E01'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def require(x,code):
 if not x:raise WorldError(code)
def admission(grant,prereg,review,manifest_sha):
 require(grant.get('scope')==SCOPE and grant.get('status')=='HUMAN_GRANTED_E01' and bool(grant.get('human_approval_reference')),'HUMAN_GATE_REQUIRED')
 require(review.get('status')=='PASS' and review.get('independent_context_review_performed') is True,'L1_INDEPENDENT_ACCEPTANCE_REQUIRED')
 require(grant.get('prereg_sha256')==digest(prereg) and grant.get('source_manifest_sha256')==manifest_sha,'AUTHORIZATION_SCOPE_MISMATCH')
 require(grant.get('limits')==LIMITS,'AUTHORIZATION_LIMITS_MISMATCH')
 require(prereg.get('first_world_spec') is not None and prereg.get('initial_model_receipt_sha256'),'INITIAL_MODEL_PLAN_NOT_FROZEN')
 require(grant.get('repository')=='flyoung588/narque-qw-foundation02' and grant.get('branch')=='qw-explorer-e01' and len(grant.get('code_commit',''))==40,'REMOTE_SCOPE_NOT_FROZEN')
 return True

def screen_spec(spec):
 # Reuse generic scientific contract. These bounds are resource restrictions,
 # not a statement that other domains or unknown hypotheses are false.
 fabric.validate_object(spec);m=spec['matter'];p=spec['physics']
 require(not m['periodic'],'DOMAIN_PIPELINE_NOT_READY')
 require(p['engine']=='pyscf' and p['method'] in ('RHF','UHF') and p['basis'].lower()=='cc-pvdz','MODEL_NOT_IN_ENVELOPE')
 require(p['method']!='RHF' or m['spin_2S']==0,'RHF_SPIN_MISMATCH')
 require(1<=len(m['atoms'])<=3,'ATOM_RESOURCE_LIMIT')
 zs={'H':1,'He':2,'Li':3,'Be':4,'B':5,'C':6,'N':7,'O':8,'F':9,'Ne':10}
 electrons=sum(zs[a['element']] for a in m['atoms'])-m['charge'];require(1<=electrons<=12,'ELECTRON_RESOURCE_LIMIT')
 # Contracted spherical cc-pVDZ counts under locked versions; actual reported AO size is checked on return.
 aos={'H':5,'He':5,'Li':14,'Be':14,'B':14,'C':14,'N':14,'O':14,'F':14,'Ne':14}
 require(sum(aos[a['element']] for a in m['atoms'])<=24,'AO_RESOURCE_LIMIT')
 require(set(p['observables'])<=set(['energy','forces']) and 'energy' in p['observables'],'OBSERVABLE_NOT_IN_ENVELOPE')
 return {'electrons':electrons,'AO_static_upper_bound':sum(aos[a['element']] for a in m['atoms']),'worker':'qw_next/native_worker.py','route':'molecular','accuracy':'FINITE_BASIS_MEAN_FIELD_ONLY'}
def successor(previous,parameters,choice):
 if choice=='CHANGE_OBJECT':spec=parameters['world_spec'];screen_spec(spec);return spec
 action=parameters['action'];require(action.get('source_state_sha256')==previous['sha256'],'STALE_PARENT')
 require(action.get('type') in ('DISPLACE_ATOM','MEASURE_OBSERVABLE'),'OPERATION_NOT_IN_ENVELOPE')
 # Mature action contract enforces <=0.05 Angstrom; do not use the old unexecuted0.08 draft.
 spec=apply(previous,action);screen_spec(spec)
 if 'world_spec' in parameters:require(parameters['world_spec']==spec,'ACTION_SPEC_MISMATCH')
 return spec

def check_remote_return(package,expected,grant,intent):
 require(package.get('source_kind')=='GITHUB_AUTHENTICATED_RUN','UNTRUSTED_SOLVER_TRANSPORT')
 meta=package['run'];require(meta['head_sha']==grant['code_commit'] and meta['head_branch']==grant['branch'] and meta['event']=='workflow_dispatch' and meta['run_attempt']==1,'REMOTE_RUN_SCOPE_MISMATCH')
 require(meta['status']=='completed' and meta['conclusion']=='success','REMOTE_JOB_FAILED')
 require(package['intent']==intent and package['input_sha256']==digest(expected),'PHYSICS_INPUT_BINDING_MISMATCH')
 raw=package['observation'];require(raw.get('status')=='CALCULATED' and not raw.get('synthetic'),'UNVERIFIED_PHYSICS_RETURN')
 require(raw.get('spec')==expected and raw['world_spec_sha256']==digest(expected),'PHYSICS_INPUT_BINDING_MISMATCH')
 o=raw['observation'];require(type(o.get('orbital_basis_size')) is int and 1<=o['orbital_basis_size']<=24,'ACTUAL_AO_RESOURCE_LIMIT');require(o.get('converged',o.get('SCF_converged')) is True,'SCF_NOT_CONVERGED')
 require(o.get('method')==expected['physics']['method'] and o.get('basis','').lower()==expected['physics']['basis'].lower() and o.get('engine')=='PySCF','PHYSICS_MODEL_BINDING_MISMATCH')
 require(type(o.get('energy')) in (int,float) and math.isfinite(o['energy']) and o.get('energy_unit')=='Eh' and bool(o.get('energy_zero')),'ENERGY_CONTRACT_INVALID')
 forces=o.get('forces_Eh_per_bohr');require(isinstance(forces,list) and len(forces)==len(expected['matter']['atoms']) and all(len(row)==3 and all(type(v) in (int,float) and math.isfinite(v) for v in row) for row in forces),'FORCE_CONTRACT_INVALID')
 require(max(abs(sum(row[j] for row in forces)) for j in range(3))<1e-5,'TRANSLATIONAL_FORCE_SCREEN_FAILED')
 require(package['native_process']['exit_code']==0 and package['native_process']['timed_out'] is False and package['native_process'].get('reason')=='SOLVER_RETURNED' and package['native_process'].get('synthetic') is False,'NATIVE_PROCESS_FAILURE')
 from birth01.preparation import resource_check
 resource_check(package['admission']);require(package['admission']['memory.swap.max']=='0','SWAP_NOT_ZERO')
 return raw
