import json, pathlib, unittest

ROOT = pathlib.Path(__file__).parents[1]

class DataClassificationContractTests(unittest.TestCase):
    def test_classes_have_one_consistent_git_policy(self):
        d=json.loads((ROOT/'docs/governance/data-classification.json').read_text())
        self.assertEqual(set(d['classes']), {'PUBLIC','INTERNAL','CONFIDENTIAL','RESTRICTED'})
        self.assertEqual(d['classes']['CONFIDENTIAL']['git'], 'forbidden')
        self.assertEqual(d['classes']['RESTRICTED']['git'], 'forbidden')
        self.assertTrue(all(not v['raw_operational_payload'] for v in d['classes'].values()))

if __name__ == '__main__': unittest.main()
