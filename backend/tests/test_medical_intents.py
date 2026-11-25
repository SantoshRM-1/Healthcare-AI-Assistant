import unittest

from app.api.v1.routes.ai import _chat_intent, _emergency_response
from app.services.medical_qa import detect_language
from app.services.medical_taxonomy import load_taxonomy, match_reported_conditions


class LanguageAndIntentTests(unittest.TestCase):
    def test_romanized_kannada_is_detected(self):
        self.assertEqual(detect_language("nanna report summary kannadadalli heli"), "kannada")

    def test_romanized_kannada_recommendation_intents(self):
        self.assertEqual(_chat_intent("nanna kidney stone ge yava oota tinnabeku", {}), "medical_recommendation")
        self.assertEqual(_chat_intent("nanna kidney problem ge yava doctor", {}), "doctor_recommendation")
        self.assertEqual(_chat_intent("bengaluru alli hospital suggest maadi", {}), "hospital")

    def test_emergency_gate_is_language_aware(self):
        response = _emergency_response("I have a kidney stone and fever", "kannada")
        self.assertIsNotNone(response)
        self.assertIn("ತುರ್ತು", response)

    def test_emergency_gate_catches_breathing_symptoms_without_hospital_intent(self):
        response = _emergency_response("I have severe difficulty breathing", "english")
        self.assertIn("112", response)

    def test_non_emergency_kidney_stone_does_not_trigger_emergency(self):
        self.assertIsNone(_emergency_response("I have a 5mm kidney stone", "english"))

    def test_taxonomy_contains_25_sectors_and_matches_singular_condition(self):
        self.assertEqual(len(load_taxonomy()), 25)
        matches = match_reported_conditions("I was told I have a kidney stone")
        self.assertTrue(any("Urologist" in item["specialties"] for item in matches))

    def test_taxonomy_ignores_explicitly_negated_condition(self):
        self.assertEqual(match_reported_conditions("The report says no kidney stones"), [])


if __name__ == "__main__":
    unittest.main()
