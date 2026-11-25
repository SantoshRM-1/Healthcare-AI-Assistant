import json
import unittest
from pathlib import Path

from app.api.v1.routes.ai import _chat_intent, _emergency_response
from app.services.laboratory_intelligence import parse_laboratory_results
from app.services.medical_qa import detect_language
from app.services.recommendations import (
    derive_specialties,
    doctor_questions,
    recognize_regional_foods,
)

CASES = json.loads(
    (Path(__file__).parent / "fixtures" / "phase6_synthetic_evaluation.json").read_text(encoding="utf-8")
)


class Phase6SyntheticEvaluationTests(unittest.TestCase):
    def test_phase6_deterministic_synthetic_cases(self):
        for case in CASES:
            if case["status"] == "blocked":
                continue
            with self.subTest(case=case["id"]):
                module = case["module"]
                text = case["input"]
                if module == "route":
                    self.assertEqual(_chat_intent(text, {}), case["expected"])
                elif module == "language":
                    self.assertEqual(detect_language(text), case["expected"])
                elif module == "emergency":
                    response = _emergency_response(text, case["language"])
                    self.assertIsNotNone(response)
                    self.assertIn("112", response)
                elif module == "laboratory":
                    finding = parse_laboratory_results(text).findings[0]
                    self.assertEqual(finding.status, case["expected"])
                elif module == "specialist":
                    specialties, _ = derive_specialties(text)
                    if case["id"] == "negated-kidney-condition":
                        self.assertNotIn("Urologist", specialties)
                    else:
                        self.assertIn("Urologist", specialties)
                elif module == "nutrition":
                    found = recognize_regional_foods(text)
                    self.assertIn("ragi mudde", found)
                    self.assertIn("idli", found)
                elif module == "doctor_questions":
                    questions = doctor_questions(text, case["language"])
                    self.assertTrue(questions)
                    self.assertTrue(any("2.0" in question for question in questions))
                elif module == "prescription":
                    questions = doctor_questions(text)
                    self.assertTrue(any("Metformin" in question for question in questions))


if __name__ == "__main__":
    unittest.main()
