"""A human-authorized model's auditable decisions, NOT an internal unattended AI.

Candidates can be frozen before computing. Follow-up decisions cannot be
validated without a real, previously completed physical observation.
"""
from .construct import from_prototype
from .admission import select_engine
from .quality import quality_from_observation
from .io import digest, freeze_json, utc_now


def freeze_initial_ai_decision(decision, path):
    if decision.get('authorship')!='CURRENT_BCHAT_AI_IN_CURRENT_TURN':
        raise ValueError('AI_AUTHORSHIP_PROVENANCE_REQUIRED')
    if not isinstance(decision.get('candidates'),list) or len(decision['candidates'])<2:
        raise ValueError('AT_LEAST_TWO_DIFFERENT_CANDIDATES_REQUIRED')
    if not decision.get('selection_policy') or not decision.get('why_not_molecular_repeat'):
        raise ValueError('MISSING_EXPLORATION_SELECTION_REASON')
    candidates=[]
    compositions=set()
    for item in decision['candidates']:
        if not isinstance(item,dict):
            raise ValueError('INVALID_CANDIDATE')
        built=from_prototype(item)
        admission=select_engine(built['spec'])
        if admission['status']!='ELIGIBLE_FOR_RESOURCE_PREFLIGHT':
            raise ValueError('OUT_OF_MODEL_DOMAIN:'+admission['reason'])
        composition=tuple(sorted(a['element'] for a in built['spec']['matter']['atoms']))
        compositions.add(composition)
        candidates.append({'proposal':item,'worldspec':built['spec'],
                           'worldspec_sha256':built['sha256'],
                           'geometry_screening':built['preflight_nearest_distance_A'],
                           'admission':admission})
    if len(compositions)<2:
        raise ValueError('REQUIRES_DISTINCT_CHEMICAL_COMPOSITIONS')
    if decision.get('selected_first_candidate_id') not in {c['proposal']['id'] for c in candidates}:
        raise ValueError('SELECTED_CANDIDATE_ID_NOT_PRESENT')
    result={'artifact':'QW_PERIODIC02_PREOBSERVATION_AI_DECISION',
            'status':'AI_AUTHORED_UNEXECUTED',
            'authorship':'CURRENT_BCHAT_AI_IN_CURRENT_TURN',
            'frozen_at_UTC':utc_now(),
            'candidate_count':len(candidates),
            'candidates':candidates,
            'selected_first_candidate_id':decision['selected_first_candidate_id'],
            'selection_policy':decision['selection_policy'],
            'why_not_molecular_repeat':decision['why_not_molecular_repeat'],
            'prediction_cannot_be_rewritten_after_result':True,
            'human_approval_for_next_science_job':'NOT_GRANTED',
            'W2_independent_engine':'INCOMPLETE',
            'W3_periodic_feedback':'NOT_TESTED',
            'original_discovery':'NOT_TESTED',
            'absolute_energy_ranking_between_compositions':'FORBIDDEN'}
    return freeze_json(path,result),result


def freeze_post_observation_decision(prior_observation, proposal, path):
    """Only a real CALCULATED source can support a follow-up decision record.

    The record binds to the exact prior observation data and does not trigger
    a simulation. It does not independently prove AI model provenance.
    """
    qa=quality_from_observation(prior_observation)
    if qa.get('status')!='BOUNDED_CALCULATED':
        raise ValueError('NO_REAL_COMPLETED_OBSERVATION_FOR_FEEDBACK')
    if prior_observation.get('simulated') or prior_observation.get('synthetic'):
        raise ValueError('SYNTHETIC_OBSERVATION_NOT_ELIGIBLE')
    if proposal.get('based_on_observation_sha256')!=digest(prior_observation):
        raise ValueError('OBSERVATION_HASH_MISMATCH')
    if proposal.get('action') not in ('compute','stop'):
        raise ValueError('ACTION_UNSUPPORTED')
    if not all(isinstance(proposal.get(x),str) and len(proposal[x].strip())>=12
               for x in ('AI_analysis_after_observation','decision_rationale','alternative_explanations')):
        raise ValueError('EXPLICIT_AI_REASONING_MISSING')
    record={'artifact':'QW_PERIODIC02_POST_OBSERVATION_DECISION',
            'status':'FOLLOWUP_DECISION_ONLY_NOT_SCIENTIFIC_VERDICT',
            'authored_at_UTC':utc_now(),
            'prior_observation_sha256':digest(prior_observation),
            'decision':proposal,
            'decision_does_not_trigger_science_job':True,
            'autonomy_level':'HUMAN_AUTHORIZED_AI_WORKFLOW_NOT_UNATTENDED'}
    if proposal['action']=='compute':
        candidate=proposal.get('next_worldspec')
        if not candidate:
            raise ValueError('FOLLOWUP_WORLDSPEC_REQUIRED')
        admission=select_engine(candidate)
        if admission['status']!='ELIGIBLE_FOR_RESOURCE_PREFLIGHT':
            raise ValueError('FOLLOWUP_OUT_OF_SCOPE')
        if digest(candidate)==digest(prior_observation['spec']):
            raise ValueError('UNALTERED_EXPERIMENT_NOT_ADAPTIVE')
        if not isinstance(proposal.get('prediction_before_compute'),str) or not isinstance(proposal.get('falsifier'),str):
            raise ValueError('PRE_EXPERIMENT_PREDICTION_REQUIRED')
        record['next_worldspec_sha256']=digest(candidate)
        record['next_admission']=admission
    return freeze_json(path,record),record
