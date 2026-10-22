"""Thin unified dispatch over inherited structural and new quantum states."""
from interactive01.world import verify,transition
from interactive01.runtime import execute as structural_execute
from .runtime import operate

def act(store,state,action,*,authority=False,resources=False,fixture=False):
    verify(state)
    if state['payload']['schema']=='QW_PHYSICAL_STATE_01':
        return transition(store,state,action,structural_execute,authority,resources,synthetic=fixture)
    if state['payload']['schema']=='QW_EFFECTIVE_QUANTUM_STATE_01':
        if not fixture and not (authority and resources):raise ValueError('EXECUTION_ADMISSION_REQUIRED')
        return operate(store,state,action,fixture=fixture)
    raise ValueError('UNSUPPORTED_PHYSICAL_STATE_DOMAIN')
