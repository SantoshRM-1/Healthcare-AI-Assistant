import unittest

from app.services.recommendations import (
    derive_specialties,
    doctor_questions,
    recognize_regional_foods,
)


class Phase5RecommendationTests(unittest.TestCase):
    def test_recognizes_karnataka_food_names_in_english_and_kannada(self):
        found = recognize_regional_foods("Breakfast idli and sambar; ರಾತ್ರಿ ರಾಗಿ ಮುದ್ದೆ")
        self.assertEqual(found, ["ragi mudde", "idli", "sambar"])

    def test_specialty_uses_patient_reported_stone_and_urinary_symptom(self):
        specialties, _ = derive_specialties(
            "I have a 5mm kidney stone and pain while urinating for one week"
        )
        self.assertIn("Urologist", specialties)

    def test_persistent_stomach_symptom_suggests_general_first_contact(self):
        specialties, reasons = derive_specialties("I have stomach pain for one week")
        self.assertIn("General Physician", specialties)
        self.assertIn("Gastroenterologist", specialties)
        self.assertTrue(any("stomach pain" in reason for reason in reasons))

    def test_explicit_negation_does_not_create_specialty(self):
        specialties, _ = derive_specialties("I have no kidney stone and no urinary symptoms")
        self.assertNotIn("Urologist", specialties)

    def test_abnormal_lab_routes_to_general_physician_without_diagnosing(self):
        specialties, reasons = derive_specialties(
            "", "Creatinine 2.0 mg/dL (reference range 0.6 - 1.2)"
        )
        self.assertIn("General Physician", specialties)
        self.assertTrue(any("creatinine" in reason.lower() for reason in reasons))

    def test_report_and_symptom_generate_doctor_questions_in_kannada(self):
        questions = doctor_questions(
            "Creatinine 2.0 mg/dL (reference range 0.6 - 1.2). "
            "I have stomach pain for one week.",
            "kannada",
        )
        self.assertTrue(questions)
        self.assertTrue(any("ನನ್ನ" in question or "ನಾನು" in question for question in questions))

    def test_prescription_question_uses_medicine_name_as_written(self):
        questions = doctor_questions("Tab Metformin 500 mg twice daily after food for 30 days")
        self.assertTrue(any("Metformin" in question for question in questions))

    def test_no_evidence_does_not_generate_questions(self):
        self.assertEqual(doctor_questions("Hello, what can you do?"), [])



if __name__ == "__main__":
    unittest.main()
