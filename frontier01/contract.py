"""Explicit post-HF model envelope, preserving the existing WorldSpec."""
import math
from interactive01.world import validate as validate_world
MODEL={'method':'FCI','solver':'direct_spin0','basis':'sto-3g','conv_tol':1e-10,'max_cycle':100,'max_memory_MB':400,'nroots':1,'partition':'SYMMETRIC_LOWDIN_AO'}
def validate(request):
    if set(request)!={'world_spec','correlation_model'}:raise ValueError('REQUEST_FIELDS')
    spec=request['world_spec'];validate_world(spec)
    if request['correlation_model']!=MODEL:raise ValueError('MODEL_NOT_ADMITTED')
    m=spec['matter'];p=spec['physics'];n=len(m['atoms'])
    if m['periodic'] or m['charge']!=0 or m['spin_2S']!=0:raise ValueError('CLOSED_SHELL_NEUTRAL_DOMAIN')
    if n not in (2,4,6) or any(a['element']!='H' for a in m['atoms']):raise ValueError('BOUNDED_H_ASSEMBLY_DOMAIN')
    if p!={'engine':'pyscf','method':'RHF','basis':'sto-3g','observables':['energy']}:raise ValueError('REFERENCE_MODEL')
    if math.comb(n,n//2)**2>400:raise ValueError('DETERMINANT_BOUND')
    return spec
