"""Static execution-contract checks; NO cloud or physics invocation."""
import json
import pathlib
import unittest
from periodic02.io import digest

ROOT=pathlib.Path(__file__).resolve().parents[1]

class CloudContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scope=json.loads((ROOT/'periodic02/EXECUTION_SCOPE_TEMPLATE.json').read_text())
        cls.decision=json.loads((ROOT/'decisions/PREOBSERVATION_FROZEN.json').read_text())
    def test_no_authority_presumption(self):
        self.assertEqual(self.scope['authority'],'NOT_GRANTED')
    def test_exact_selected_input_binding(self):
        selected=[x for x in self.decision['candidates'] if x['proposal']['id']==self.decision['selected_first_candidate_id']]
        self.assertEqual(len(selected),1)
        self.assertEqual(digest(selected[0]['worldspec']),self.scope['worldspec_sha256'])
    def test_no_double_science_job(self):
        self.assertEqual(self.scope['max_jobs'],1)
        self.assertTrue(self.scope['no_automatic_retry'])
    def test_bounded_resources(self):
        c=self.scope['scientific_container']
        self.assertEqual((c['cpu_count'],c['threads'],c['memory_bytes'],c['swap_extra_bytes'],c['network']),
                         (1,1,1073741824,0,'none'))
    def test_no_second_candidate_in_same_scope(self):
        self.assertIn('MgO second science calculation',self.scope['forbidden'])
    def test_static_workflow_no_push_schedule(self):
        y=(ROOT/'.github/workflows/periodic02-once.yml').read_text()
        self.assertIn('workflow_dispatch',y)
        self.assertNotIn('schedule:',y)
        self.assertNotIn('  push:',y)
        self.assertIn('timeout-minutes: 15',y)
        self.assertIn('contents: read',y)

if __name__=='__main__':unittest.main()
