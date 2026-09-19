import json
import os
import sys
import unittest
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from integrations import adapter_outlook as outlook


class _Response:
    def __init__(self, value):
        self.value = json.dumps(value).encode("utf-8")
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, _limit=-1): return self.value


class OutlookBridgeTests(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"DEPUTY_OUTLOOK_BRIDGE_URL": "http://127.0.0.1:8766"}, clear=False)
        self.env.start()

    def tearDown(self): self.env.stop()

    def test_probe_uses_localhost_bridge_without_powershell(self):
        payload = {"ok": True, "version": "16", "inbox_count": 3, "calendar_count": 1,
                   "accounts": [{"address": "gev@housenet.am", "display": "Gev"}],
                   "current_user": {"address": "gev@housenet.am", "name": "Gev"}}
        with mock.patch.object(outlook.urllib.request, "urlopen", return_value=_Response(payload)) as call:
            got = outlook.probe()
        self.assertEqual(got["inbox_count"], 3)
        self.assertIn("/probe", call.call_args.args[0])

    def test_mail_bridge_is_filtered_and_normalized(self):
        payload = {"ok": True, "records": [
            {"entry_id": "1", "subject": "Approval", "sender": "a@example.com", "received": "2026-09-19T10:00:00", "preview": "Please approve", "unread": True, "folder": "Inbox"},
            {"entry_id": "2", "subject": "FYI", "sender": "b@example.com", "received": "2026-09-18T10:00:00", "preview": "noise", "unread": False, "folder": "Inbox"}],
                   "accounts": [], "current_user": {}}
        with mock.patch.object(outlook.urllib.request, "urlopen", return_value=_Response(payload)):
            got = outlook.read("mail.search", {"query": "approval", "unread_only": True, "limit": 10}, integration_id="INT-OL-MAIL")
        self.assertEqual(len(got["records"]), 1)
        self.assertEqual(got["records"][0]["subject"], "Approval")

    def test_bridge_rejects_non_local_endpoint(self):
        with mock.patch.dict(os.environ, {"DEPUTY_OUTLOOK_BRIDGE_URL": "http://10.0.0.2:8766"}):
            with self.assertRaises(Exception) as ctx:
                outlook.probe()
        self.assertEqual(getattr(ctx.exception, "code", None), "NOT_CONFIGURED")


if __name__ == "__main__": unittest.main()
