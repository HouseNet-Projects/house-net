import json
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "runtime"))
from digital_memory import AccessDenied, Contradiction, DependencyUnavailable, DigitalMemory


def repo(root, name, validator, index, refs=None):
    p = root / name
    (p / "bin").mkdir(parents=True)
    (p / "knowledge/index" if name == "knowledge" else p / "vault").mkdir(parents=True)
    if name == "knowledge":
        (p / "knowledge/index/catalog.json").write_text(json.dumps({"version": 1, "generated": True, "items": []}))
    else:
        (p / "vault/index.json").write_text(json.dumps({"version": 1, "generated": True, "references": refs or []}))
    script = "#!/usr/bin/env python3\nimport json, pathlib\njson.loads((pathlib.Path(__file__).parents[1] / %r).read_text())\n" % index
    (p / "bin" / validator).write_text(script)
    (p / "bin" / validator).chmod(0o755)
    return p


class DigitalMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.knowledge = repo(self.tmp, "knowledge", "validate-knowledge", "knowledge/index/catalog.json")
        self.vault = repo(self.tmp, "vault", "validate-vault", "vault/index.json", refs=[])
        self.memory = DigitalMemory(self.knowledge, self.vault)

    def add_item(self, item, directory="canonical"):
        p = self.knowledge / "knowledge" / directory
        p.mkdir(parents=True, exist_ok=True)
        (p / (item["id"] + ".json")).write_text(json.dumps(item))

    def test_canonical_read_exposes_provenance_and_filters_draft(self):
        item = {"id": "HN-KNOW-OPS", "title": "Operations", "domain": "ops", "owner": "HOUSE_NET_OWNER",
                "status": "canonical", "source": {"type": "repository", "uri": "repo://x", "hash": "sha256:" + "a" * 64},
                "sensitivity": "PUBLIC", "language": ["en", "hy"], "last_verified": "2026-09-16",
                "freshness": {"state": "current"}}
        self.add_item(item)
        draft = dict(item, id="HN-KNOW-DRAFT", title="Draft", status="draft")
        self.add_item(draft, "intake")
        result = self.memory.get("HN-KNOW-OPS")
        self.assertEqual(result["source"]["uri"], "repo://x")
        self.assertEqual(self.memory.search("draft"), [])

    def test_stale_is_not_served_and_missing_dependency_blocks(self):
        item = {"id": "HN-KNOW-STALE", "title": "Stale", "domain": "ops", "owner": "HOUSE_NET_OWNER",
                "status": "canonical", "source": {"type": "repository", "uri": "repo://x", "hash": "a" * 64},
                "sensitivity": "PUBLIC", "language": ["en"], "last_verified": "2026-09-16",
                "freshness": {"state": "stale"}}
        self.add_item(item)
        with self.assertRaises(DependencyUnavailable): self.memory.get(item["id"])
        with self.assertRaises(DependencyUnavailable): DigitalMemory(self.tmp / "missing", self.vault).search("x")

    def test_conflicting_canonical_items_block(self):
        base = {"owner": "HOUSE_NET_OWNER", "status": "canonical", "source": {"type": "repository", "uri": "repo://x", "hash": "a" * 64}, "sensitivity": "PUBLIC", "language": ["en"], "last_verified": "2026-09-16", "freshness": {"state": "current"}}
        self.add_item(dict(base, id="HN-KNOW-A", title="Same", domain="ops"))
        self.add_item(dict(base, id="HN-KNOW-B", title="Same", domain="ops"))
        with self.assertRaises(Contradiction): self.memory.search("same")

    def test_vault_returns_metadata_only(self):
        ref = {"id": "HN-VAULT-REF", "purpose": "test", "owner_principal": "HOUSE_NET_OWNER", "target_system": "x", "secret_type": "opaque", "sensitivity": "RESTRICTED", "required_for_bootstrap": True, "recovery": {"available": False}}
        self.vault = repo(self.tmp, "vault2", "validate-vault", "vault/index.json", [ref])
        (self.vault / "vault/index.json").write_text(json.dumps({"version": 1, "generated": True, "references": [ref]}))
        result = DigitalMemory(self.knowledge, self.vault).vault_reference("HN-VAULT-REF")
        self.assertFalse(result["available"])
        self.assertNotIn("value", result)
        self.assertEqual(result["authority"], "vault-reference-metadata")

    def test_policy_is_not_knowledge_authority(self):
        self.assertNotIn("policy", DigitalMemory.__dict__)


if __name__ == "__main__": unittest.main()
