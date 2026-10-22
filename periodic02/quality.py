"""Evidence-conditioned accuracy and comparison semantics.

SCF convergence and agreement with itself are NOT physical accuracy. Never
compare absolute total energies of different compositions for material ranking.
"""
from collections import Counter
import math


def quality_from_observation(result):
    if not isinstance(result,dict) or result.get('status')!='CALCULATED':
        return {'status':'UNVERIFIED','accuracy':'NOT_CERTIFIED','reason':'NO_CALCULATED_OBSERVATION'}
    if result.get('synthetic') is True or result.get('simulated') is True:
        return {'status':'TEST_FIXTURE_ONLY','accuracy':'NOT_CERTIFIED','reason':'NOT_ACTUAL_PHYSICAL_OUTPUT'}
    spec=result.get('spec',{})
    obs=result.get('observation',{})
    if spec.get('matter',{}).get('type')=='periodic_cell':
        if obs.get('SCF_converged') is not True:
            return {'status':'UNVERIFIED','accuracy':'NOT_CERTIFIED','reason':'SCF_NOT_CONVERGED'}
        energy=obs.get('energy_Eh_per_cell')
        if type(energy) not in (int,float) or not math.isfinite(energy):
            return {'status':'UNVERIFIED','accuracy':'NOT_CERTIFIED','reason':'NO_FINITE_PERIODIC_ENERGY'}
        if obs.get('energy_unit')!='Eh/cell' or obs.get('kmesh')!=[1,1,1]:
            return {'status':'UNVERIFIED','accuracy':'NOT_CERTIFIED','reason':'ENERGY_OR_KMESH_SEMANTICS_MISMATCH'}
        return {'status':'BOUNDED_CALCULATED','accuracy':'NOT_CERTIFIED',
                'scf_converged':True,'energy_Eh_per_cell':energy,
                'basis_sensitivity':'NOT_TESTED','kpoint_sensitivity':'NOT_TESTED',
                'grid_sensitivity':'NOT_TESTED','forces':'NOT_IMPLEMENTED',
                'stress':'NOT_IMPLEMENTED','material_stability':'NOT_PROVEN',
                'original_discovery':'NOT_TESTED',
                'note':'Same-model energy exists; accuracy requires independent, justified numerical and reality checks.'}
    if obs.get('converged') is True:
        return {'status':'BOUNDED_CALCULATED','accuracy':'NOT_CERTIFIED',
                'model':'NONPERIODIC_FINITE_BASIS'}
    return {'status':'UNVERIFIED','accuracy':'NOT_CERTIFIED','reason':'NO_MATCHING_SOLVER_DATA'}


def periodic_energy_comparison(x,y):
    """Permit same-composition, same-model, same-cell-size comparisons only.

    The result is an internal model comparison; no equilibrium or stability claim.
    """
    q1=quality_from_observation(x);q2=quality_from_observation(y)
    if q1['status']!='BOUNDED_CALCULATED' or q2['status']!='BOUNDED_CALCULATED':
        return {'status':'INCOMPARABLE','reason':'UNVERIFIED_INPUT'}
    a,b=x['spec'],y['spec']
    if a['matter'].get('type')!='periodic_cell' or b['matter'].get('type')!='periodic_cell':
        return {'status':'INCOMPARABLE','reason':'NOT_TWO_PERIODIC_OBJECTS'}
    ca=Counter(v['element'] for v in a['matter']['atoms'])
    cb=Counter(v['element'] for v in b['matter']['atoms'])
    if ca!=cb or a['matter'].get('charge')!=b['matter'].get('charge') or a['matter'].get('spin_2S')!=b['matter'].get('spin_2S'):
        return {'status':'INCOMPARABLE','reason':'DIFFERENT_COMPOSITION_OR_QUANTUM_NUMBERS'}
    if a['physics']!=b['physics']:
        return {'status':'INCOMPARABLE','reason':'DIFFERENT_THEORY_OR_NUMERICAL_REQUEST'}
    oa,ob=x['observation'],y['observation']
    for k in ('energy_zero','energy_unit','method','basis','kmesh','density_fitting','integration','cell_precision'):
        if k not in oa or k not in ob or oa[k]!=ob[k]:
            return {'status':'INCOMPARABLE','reason':'NUMERICAL_OR_ENERGY_REFERENCE_MISMATCH:'+k}
    # Require difference in actual structure, not only labels.
    if a['matter']['cell_angstrom']==b['matter']['cell_angstrom'] and a['matter']['atoms']==b['matter']['atoms']:
        return {'status':'SAME_GEOMETRY','delta_energy_Eh_per_cell':0.0,
                'accuracy':'NOT_CERTIFIED'}
    return {'status':'MODEL_INTERNAL_PERIODIC_GEOMETRY_DIFFERENCE',
            'delta_energy_Eh_per_cell':ob['energy_Eh_per_cell']-oa['energy_Eh_per_cell'],
            'accuracy':'NOT_CERTIFIED', 'equilibrium':'NOT_PROVEN',
            'kpoint_grid_basis_convergence':'NOT_CERTIFIED',
            'no_cross_composition_ranking':True}
