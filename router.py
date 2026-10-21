"""Minimal WorldSpec engine extension; all physics delegated to mature engines."""
import copy,hashlib,json,math,time,traceback
ENGINES=('pyscf','ase-pyscf','psi4')
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def validate(spec):
 from foundation01.contract import validate as original
 if spec.get('physics',{}).get('engine') not in ENGINES:raise ValueError('OUT_OF_MODEL_DOMAIN: unsupported engine')
 shadow=copy.deepcopy(spec)
 if shadow['physics']['engine']=='psi4':shadow['physics']['engine']='pyscf'
 return original(shadow)
def physical_key(spec):
 x=copy.deepcopy(spec);x.pop('object_id',None);x.pop('experiment',None);x['physics'].pop('engine',None);x['matter'].pop('source',None)
 return x
def run(spec,outdir):
 from pathlib import Path
 out=Path(outdir);out.mkdir(parents=True,exist_ok=True);t=time.monotonic()
 result={'spec':spec,'world_spec_sha256':digest(spec),'status':'UNVERIFIED','raw_source':str(out),'precision_qualified':False}
 try:
  validate(spec);engine=spec['physics']['engine']
  if engine=='psi4':
   from psi4_adapter import solve
  else:
   from pyscf_adapter import solve
  result['observation']=solve(spec,out);result['status']=result['observation'].get('status','CALCULATED')
 except (ImportError,ModuleNotFoundError) as exc:result.update(status='ENGINE_UNAVAILABLE',error=repr(exc))
 except ValueError as exc:
  text=str(exc);result.update(status='OUT_OF_MODEL_DOMAIN' if any(v in text for v in ['DOMAIN','UNSUPPORTED','INCOMPATIBLE','NOT_EXECUTABLE']) else 'PHYSICALLY_INVALID',error=text)
 except Exception as exc:result.update(status='UNVERIFIED',error=repr(exc),traceback=traceback.format_exc())
 result['wall_seconds']=time.monotonic()-t
 save(out/'observation.json',result);return result
def save(path,data):
 from pathlib import Path
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.tmp');tmp.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n');tmp.replace(p)
def compare(a,b):
 if a.get('status')!='CALCULATED' or b.get('status')!='CALCULATED':return {'status':'UNVERIFIED','reason':'no two converged observations'}
 if physical_key(a['spec'])!=physical_key(b['spec']):return {'status':'INCOMPARABLE','reason':'composition, geometry, spin, charge or model differs; no absolute ranking'}
 x,y=a['observation'],b['observation']
 if x['energy_zero']!=y['energy_zero'] or x['energy_unit']!=y['energy_unit']:return {'status':'INCOMPARABLE','reason':'energy reference mismatch'}
 de=y['energy_Eh']-x['energy_Eh'];df=max(abs(u-v) for row,other in zip(x['forces_Eh_per_bohr'],y['forces_Eh_per_bohr']) for u,v in zip(row,other))
 return {'status':'SAME_THEORY_DIFFERENCE_RECORDED','different_code_sources':x['engine']!=y['engine'],'delta_energy_Eh':de,'max_force_difference_Eh_per_bohr':df,'energy_within_diagnostic_1e_7':abs(de)<1e-7,'force_within_diagnostic_1e_5':df<1e-5,'same_AO_count':x['basis_AO_count']==y['basis_AO_count'],'independent_numerical_qualification':'NOT_CERTIFIED: named basis/AO count and explicit settings support a comparison, but raw contractions/normalization require review; no physical accuracy claim'}
