import copy
import json
import os
import pathlib
import tempfile
import unittest
from periodic02.construct import from_prototype,min_periodic_separation
from periodic02.admission import check_domain,select_engine,compare_priority
from periodic02.decisions import freeze_initial_ai_decision,freeze_post_observation_decision
from periodic02.io import digest,freeze_json,file_sha256
from periodic02.quality import quality_from_observation,periodic_energy_comparison
from periodic02.run_once import execute_once

ROOT=pathlib.Path(__file__).resolve().parents[1]


def choices():
    return json.loads((ROOT/'decisions/AI_PRECOMPUTE_CHOICES.json').read_text())


def first():
    return from_prototype(choices()['candidates'][0])


def second():
    return from_prototype(choices()['candidates'][1])


def historical_ne_replay():
    # Source-derived excerpt of accepted P1/P2 FCC-Ne result, NOT newly run science.
    v={'version':'QW-WORLDSPEC-0.1','object_id':'fcc_ne_a4p46',
       'epistemic_mode':'GROUNDED',
       'matter':{'type':'periodic_cell','periodic':True,'charge':0,'spin_2S':0,
                 'cell_angstrom':[[0,2.23,2.23],[2.23,0,2.23],[2.23,2.23,0]],
                 'atoms':[{'element':'Ne','xyz_angstrom':[0,0,0]}]},
       'physics':{'engine':'pyscf-pbc','method':'RKS','basis':'cc-pvdz','xc':'PBE',
                  'observables':['energy']},
       'experiment':{'action':'single_point'}}
    return {'status':'CALCULATED','spec':v,
            'evidence_kind':'HISTORIC_ACCEPTED_NE_EXCERPT_NOT_RECOMPUTED',
            'source_url':'https://github.com/flyoung588/narque-qw-foundation02/blob/qw-periodic01r/results/periodic01r/base/observation.json',
            'observation':{'SCF_converged':True,'energy_Eh_per_cell':-128.75069034579442,
            'energy_unit':'Eh/cell','energy_zero':'neutral3D periodic all-electron BO/PBE total per primitive input cell with Ewald convention; NOT molecular HF absolute reference',
            'kmesh':[1,1,1],'method':'Gamma-only RKS/PBE','basis':'cc-pvdz all-electron',
            'density_fitting':'GDF weigend auxiliary basis',
            'integration':'Becke level1, NOT convergence certified','cell_precision':1e-6}}


class Constructor(unittest.TestCase):
    def test_diamond_two_sites(self):
        o=first();self.assertEqual([a['element'] for a in o['spec']['matter']['atoms']],['C','C'])
    def test_ionic_two_sites(self):
        o=second();self.assertEqual([a['element'] for a in o['spec']['matter']['atoms']],['Mg','O'])
    def test_diamond_nearest(self):
        self.assertTrue(1.5<first()['preflight_nearest_distance_A']<1.6)
    def test_mgo_nearest(self):
        self.assertAlmostEqual(second()['preflight_nearest_distance_A'],4.21/2,places=5)
    def test_strict_13_domain(self):
        self.assertEqual(first()['electron_count'],12)
        self.assertEqual(second()['electron_count'],20)
    def test_no_material_specific_engine(self):
        self.assertEqual(first()['spec']['physics'],second()['spec']['physics'])
    def test_stable_digest(self):
        self.assertEqual(first()['sha256'],digest(first()['spec']))
    def test_no_missing_rationale(self):
        a=copy.deepcopy(choices()['candidates'][0]);del a['falsifier']
        with self.assertRaises(ValueError):from_prototype(a)
    def test_bad_bravais(self):
        a=copy.deepcopy(choices()['candidates'][0]);a['bravais']='unknown'
        with self.assertRaises(ValueError):from_prototype(a)
    def test_bad_lattice_scale(self):
        a=copy.deepcopy(choices()['candidates'][0]);a['lattice_a_angstrom']=200
        with self.assertRaises(ValueError):from_prototype(a)
    def test_duplicate_basis(self):
        a=copy.deepcopy(choices()['candidates'][0]);a['basis'][1]['fractional']=[0,0,0]
        with self.assertRaises(ValueError):from_prototype(a)
    def test_odd_electrons(self):
        a=copy.deepcopy(choices()['candidates'][0]);a['basis']=[{'element':'Li','fractional':[0,0,0]}]
        with self.assertRaises(ValueError):from_prototype(a)
    def test_nonfinite(self):
        a=copy.deepcopy(choices()['candidates'][0]);a['basis'][0]['fractional']=[float('nan'),0,0]
        with self.assertRaises(ValueError):from_prototype(a)
    def test_fractional_site_range(self):
        a=copy.deepcopy(choices()['candidates'][0]);a['basis'][1]['fractional']=[1,0,0]
        with self.assertRaises(ValueError):from_prototype(a)
    def test_geometry_screen_only(self):
        self.assertEqual(first()['geometry_screening'],'LOCAL_FINITE_IMAGE_ONLY_ASE_NOT_RUN')


class Admission(unittest.TestCase):
    def test_two_admitted(self):
        for z in (first(),second()):
            self.assertIsNone(check_domain(z['spec']))
            self.assertEqual(select_engine(z['spec'])['status'],'ELIGIBLE_FOR_RESOURCE_PREFLIGHT')
    def test_not_physical_compute(self):
        self.assertFalse(select_engine(first()['spec'])['physical_calculation'])
    def test_no_W2_claim(self):
        self.assertEqual(select_engine(first()['spec'])['W2_independent_solver'],'INCOMPLETE')
    def test_no_forces(self):
        a=first()['spec'];a['physics']['observables']=['forces']
        self.assertEqual(select_engine(a)['status'],'REJECTED')
    def test_no_spin(self):
        a=first()['spec'];a['matter']['spin_2S']=2
        self.assertEqual(select_engine(a)['status'],'REJECTED')
    def test_no_charge(self):
        a=first()['spec'];a['matter']['charge']=1
        self.assertEqual(select_engine(a)['status'],'REJECTED')
    def test_no_gamma_kmesh_extension(self):
        a=first()['spec'];a['physics']['kmesh']=[2,2,2]
        self.assertEqual(select_engine(a)['status'],'REJECTED')
        self.assertEqual(select_engine(a)['reason'],'UNSUPPORTED_PERIODIC_PHYSICS_FIELDS')
    def test_unsupported_element(self):
        a=first()['spec'];a['matter']['atoms'][0]['element']='Au'
        self.assertEqual(select_engine(a)['status'],'REJECTED')
    def test_priority_only_rough_cost(self):
        arr=compare_priority([select_engine(second()['spec']),select_engine(first()['spec'])]);self.assertEqual(arr[0]['electron_count'],12)
    def test_cross_composition_absolute_rank_forbidden(self):
        self.assertTrue(select_engine(first()['spec'])['no_cross_composition_absolute_energy_ranking'])


class EvidenceAndQuality(unittest.TestCase):
    def test_synthetic_never_accepted_as_physical(self):
        x=historical_ne_replay();x['synthetic']=True
        self.assertEqual(quality_from_observation(x)['status'],'TEST_FIXTURE_ONLY')
    def test_failure_not_quality(self):
        self.assertEqual(quality_from_observation({'status':'UNVERIFIED'})['status'],'UNVERIFIED')
    def test_only_historical_software_fixture(self):
        x=historical_ne_replay();self.assertEqual(quality_from_observation(x)['status'],'BOUNDED_CALCULATED')
        self.assertEqual(quality_from_observation(x)['accuracy'],'NOT_CERTIFIED')
    def test_no_stability(self):
        self.assertEqual(quality_from_observation(historical_ne_replay())['material_stability'],'NOT_PROVEN')
    def test_no_invalid_energy(self):
        x=historical_ne_replay();x['observation']['energy_Eh_per_cell']=float('nan')
        self.assertEqual(quality_from_observation(x)['status'],'UNVERIFIED')
    def test_no_cross_composition_comparison(self):
        x=historical_ne_replay();y=copy.deepcopy(x);y['spec']=second()['spec']
        self.assertEqual(periodic_energy_comparison(x,y)['reason'],'DIFFERENT_COMPOSITION_OR_QUANTUM_NUMBERS')
    def test_same_material_different_geometry(self):
        x=historical_ne_replay();y=copy.deepcopy(x)
        for row in y['spec']['matter']['cell_angstrom']:
            row[:]=[v*1.02 for v in row]
        y['observation']['energy_Eh_per_cell']=-128.70069034579442
        z=periodic_energy_comparison(x,y)
        self.assertEqual(z['status'],'MODEL_INTERNAL_PERIODIC_GEOMETRY_DIFFERENCE')
        self.assertEqual(z['equilibrium'],'NOT_PROVEN')
    def test_different_kpoints_rejected(self):
        x=historical_ne_replay();y=copy.deepcopy(x);y['observation']['kmesh']=[2,2,2]
        self.assertEqual(periodic_energy_comparison(x,y)['status'],'INCOMPARABLE')
    def test_different_grid_rejected(self):
        x=historical_ne_replay();y=copy.deepcopy(x);y['observation']['integration']='Becke level5'
        self.assertEqual(periodic_energy_comparison(x,y)['status'],'INCOMPARABLE')
    def test_prevent_evidence_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            p=pathlib.Path(t)/'r.json';freeze_json(p,{'hello':'world'})
            with self.assertRaises(FileExistsError):freeze_json(p,{'hello':'changed'})
    def test_nonfinite_evidence_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):freeze_json(pathlib.Path(t)/'bad.json',{'v':float('nan')})


class AIProvenance(unittest.TestCase):
    def test_freeze_two(self):
        with tempfile.TemporaryDirectory() as t:
            h,o=freeze_initial_ai_decision(choices(),pathlib.Path(t)/'choices.json')
            self.assertEqual(o['candidate_count'],2)
            self.assertEqual(len(o['candidates']),2)
            self.assertEqual(o['W3_periodic_feedback'],'NOT_TESTED')
    def test_same_composition_duplicates_rejected(self):
        z=choices();z['candidates'][1]=copy.deepcopy(z['candidates'][0]);z['candidates'][1]['id']='different_id'
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):freeze_initial_ai_decision(z,pathlib.Path(t)/'a.json')
    def test_fake_initial_author_rejected(self):
        z=choices();z['authorship']='UNATTENDED_AI'
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):freeze_initial_ai_decision(z,pathlib.Path(t)/'a.json')
    def test_feedback_no_observation(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):freeze_post_observation_decision({'status':'UNVERIFIED'},{},pathlib.Path(t)/'a.json')
    def test_feedback_wrong_digest(self):
        x=historical_ne_replay();p={'based_on_observation_sha256':'wrong','action':'stop',
            'AI_analysis_after_observation':'This result is conditional on the PBE model.',
            'decision_rationale':'Stop because no more useful information now.',
            'alternative_explanations':'Other approximate models can disagree.'}
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):freeze_post_observation_decision(x,p,pathlib.Path(t)/'a.json')
    def test_feedback_stopping_records_zero_jobs(self):
        x=historical_ne_replay();p={'based_on_observation_sha256':digest(x),'action':'stop',
            'AI_analysis_after_observation':'This was only a source-bound first energy.',
            'decision_rationale':'Stop without a newly authorized scientific job.',
            'alternative_explanations':'Physical error and convergence were not independently checked.'}
        with tempfile.TemporaryDirectory() as t:
            h,o=freeze_post_observation_decision(x,p,pathlib.Path(t)/'a.json')
            self.assertTrue(o['decision_does_not_trigger_science_job'])
    def test_feedback_compute_requires_new_geometry(self):
        x=historical_ne_replay();p={'based_on_observation_sha256':digest(x),'action':'compute',
            'AI_analysis_after_observation':'Observed energy suggests a new test may be useful.',
            'decision_rationale':'Compare a different lattice point later with authority.',
            'alternative_explanations':'The grid may be underconverged and cannot certify trends.',
            'next_worldspec':copy.deepcopy(x['spec']),
            'prediction_before_compute':'Different strain may produce an energy variation.',
            'falsifier':'No energy variation under a different geometry.'}
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):freeze_post_observation_decision(x,p,pathlib.Path(t)/'a.json')
    def test_run_without_external_authority_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(PermissionError):execute_once(first()['spec'],pathlib.Path(t)/'out',{})
    def test_unbound_authority_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            scope={'authority':'GRANTED_FOR_QW_PERIODIC02_SINGLE_RUN','max_jobs':1,'no_automatic_retry':True,
                   'worldspec_sha256':digest(first()['spec'])}
            with self.assertRaises(PermissionError):execute_once(first()['spec'],pathlib.Path(t)/'out',scope)


if __name__=='__main__':unittest.main()
