"""Durable continuity tests for conversations and confirmed identities."""
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "runtime"))
sys.path.insert(0, str(HERE / "skills"))
import engine
import state_snapshot
import store


class StateSnapshotContinuityTests(unittest.TestCase):
    def test_conversation_and_identity_survive_restore(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="deputy-snapshot-"))
        state = root / "state"
        old_state = engine.STATE_DIR
        try:
            engine.STATE_DIR = state
            store.reset()
            st = engine._store()
            st.record("channel_events", "conversation", {
                "kind": "CONVERSATION", "conversation_id": "CONV-1", "title": "Sales",
            })
            st.record("channel_events", "message", {
                "kind": "CONVERSATION_MESSAGE", "conversation_id": "CONV-1",
                "role": "user", "content": "Show sales blockers.",
            })
            st.upsert("identities", "telegram:42", {
                "link_id": "telegram:42", "person": "PERSON-1",
                "status": "CONFIRMED", "channel": "telegram", "external_id": "42",
            })
            state_snapshot.export(root=root, log=lambda *_: None)

            # Simulate host loss: the active Store and its journal are gone,
            # while the private durable snapshot remains available.
            for path in state.glob("*"):
                if path.is_file():
                    path.unlink()
            store.reset()
            restored = state_snapshot.import_(root=root, log=lambda *_: None)
            self.assertEqual(restored["channel_events"]["new"], 2)
            self.assertEqual(restored["identities"]["new"], 1)
            self.assertEqual(engine._store().get("channel_events", "message")["content"], "Show sales blockers.")
            self.assertEqual(engine._store().get("identities", "telegram:42")["status"], "CONFIRMED")
        finally:
            engine.STATE_DIR = old_state
            store.reset()


if __name__ == "__main__":
    unittest.main()
