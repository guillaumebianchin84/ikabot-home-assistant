"""Tests unitaires sans Home Assistant ni accès Gemini."""
import runpy
import unittest
from pathlib import Path
from types import SimpleNamespace


def _decorator(*_args, **_kwargs):
    return lambda func: func


MODULE = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "pyscript" / "ikabot_auto_memory.py"),
    init_globals={"time_trigger": _decorator},
)


def ev(kind, data=None):
    return SimpleNamespace(type=kind, data=data or {})


def answer(text):
    return SimpleNamespace(response=SimpleNamespace(speech={"plain": {"speech": text}}))


class TestCapture(unittest.TestCase):
    def test_pairing_voice(self):
        events = [
            ev("run-start"), ev("stt-end", {"stt_output": {"text": "Bonjour"}}),
            ev("intent-start", {"engine": "conversation.ikabot", "intent_input": "Projet Orion"}),
            ev("intent-end", {"intent_output": answer("On en parle.")}),
            ev("run-end"),
        ]
        self.assertEqual(MODULE["_extract"](events), {
            "question": "Projet Orion",
            "answer": "On en parle.",
            "engine": "conversation.ikabot",
        })

    def test_pairing_text_only(self):
        events = [
            ev("intent-start", {"engine": "conversation.ikabot", "intent_input": "J'ai reçu l'écran."}),
            ev("intent-end", {"intent_output": answer("Fort bien.")}),
            ev("run-end"),
        ]
        self.assertEqual(MODULE["_extract"](events)["question"], "J'ai reçu l'écran.")

    def test_unfinished_run_does_not_pair(self):
        events = [
            ev("intent-start", {"engine": "conversation.ikabot", "intent_input": "Orion"}),
            ev("intent-end", {"intent_output": answer("Réponse")}),
        ]
        self.assertIsNone(MODULE["_extract"](events))

    def test_error_does_not_pair(self):
        events = [
            ev("intent-start", {"engine": "conversation.ikabot", "intent_input": "Orion"}),
            ev("error", {"code": "intent-failed"}), ev("run-end"),
        ]
        self.assertIsNone(MODULE["_extract"](events))

    def test_dict_response(self):
        events = [
            ev("intent-start", {"engine": "conversation.ikabot", "intent_input": "Orion"}),
            ev("intent-end", {"intent_output": {"response": {"speech": {"plain": {"speech": "Ok"}}}}}),
            ev("run-end"),
        ]
        self.assertEqual(MODULE["_extract"](events)["answer"], "Ok")


class TestCandidate(unittest.TestCase):
    def test_valid_candidate(self):
        val = {"remember": True, "key": "projet_orion_ecran",
               "value": "Écran tactile reçu pour le projet Orion.",
               "tags": "orion ecran tactile"}
        self.assertEqual(MODULE["_safe_candidate"](val)["key"], "projet_orion_ecran")

    def test_reject_user_private_key(self):
        val = {"remember": True, "key": "sante_enfant",
               "value": "Information qui ne doit pas être enregistrée.",
               "tags": "sante"}
        self.assertIsNone(MODULE["_safe_candidate"](val))

    def test_reject_empty_or_malformed(self):
        self.assertIsNone(MODULE["_safe_candidate"]({"remember": False}))
        self.assertIsNone(MODULE["_safe_candidate"]({"remember": True}))
        self.assertIsNone(MODULE["_safe_candidate"]({"remember": True,
            "key": "projet_orion", "value": "oui", "tags": "orion"}))


if __name__ == "__main__":
    unittest.main()
