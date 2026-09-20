import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import policy_coverage as coverage


class PolicyCoverageTests(unittest.TestCase):
    def test_machine_evidence_is_explicitly_mapped(self):
        policies = []
        for path in sorted((coverage.ROOT / "control-plane/policy").glob("*.json")):
            policies.extend(json.loads(path.read_text()).get("rules", []))
        machine = [r for r in policies if "owner_review" not in str(r.get("enforcement", {}).get("mechanism", ""))
                   and "repository_settings_audit" not in str(r.get("enforcement", {}).get("mechanism", ""))
                   and "registration_and_owner_review" not in str(r.get("enforcement", {}).get("mechanism", ""))]
        self.assertTrue(machine)
        self.assertTrue(all(r["id"] in coverage.EXPLICIT for r in machine))

    def test_rule_reordering_cannot_change_mapping(self):
        rules = [{"id": "HN-GOV-001", "enforcement": {"mechanism": "repository_validator"}},
                 {"id": "HN-PERMISSIONS", "enforcement": {"mechanism": "workflow_validator"}}]
        before = [coverage.evidence_for(r)["artifacts"] for r in rules]
        after = [coverage.evidence_for(r)["artifacts"] for r in reversed(rules)]
        self.assertEqual(before, list(reversed(after)))

    def test_unmapped_machine_mechanism_is_not_green(self):
        result = coverage.evidence_for({"id": "SYNTHETIC", "enforcement": {"mechanism": "new_machine_gate"}})
        self.assertEqual(result["classification"], "UNMAPPED_MACHINE_ENFORCEMENT")
        self.assertFalse(coverage.verify(result, "monorepo-governance"))


if __name__ == "__main__":
    unittest.main()
