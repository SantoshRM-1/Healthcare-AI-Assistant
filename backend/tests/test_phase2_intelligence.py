import unittest
from uuid import UUID

from app.services.laboratory_intelligence import parse_laboratory_results
from app.services.medical_qa import (
    analyze_clinical_context_node,
    detect_language,
    medical_qa_graph,
)
from app.services.medical_terminology import normalize_medical_terms
from app.services.prescription_intelligence import extract_prescription_items
from app.services.symptom_intelligence import analyze_patient_text
from app.services.vector_store import report_retrieval_filter

LAB_CASES = [
    ("Hemoglobin", "hemoglobin"),
    ("Haemoglobin", "hemoglobin"),
    ("Hgb", "hemoglobin"),
    ("Hb", "hemoglobin"),
    ("RBC", "red blood cell count"),
    ("WBC", "white blood cell count"),
    ("TLC", "white blood cell count"),
    ("Platelets", "platelet count"),
    ("PCV", "hematocrit"),
    ("MCV", "mean corpuscular volume"),
    ("MCH", "mean corpuscular hemoglobin"),
    ("MCHC", "mean corpuscular hemoglobin concentration"),
    ("Neutrophils", "neutrophils"),
    ("Lymphocytes", "lymphocytes"),
    ("Eosinophils", "eosinophils"),
    ("ESR", "erythrocyte sedimentation rate"),
    ("Creatinine", "creatinine"),
    ("BUN", "blood urea nitrogen"),
    ("Urea", "urea"),
    ("eGFR", "estimated glomerular filtration rate"),
    ("Uric acid", "uric acid"),
    ("Urine protein", "urine protein"),
    ("ALT", "alanine aminotransferase"),
    ("SGPT", "alanine aminotransferase"),
    ("AST", "aspartate aminotransferase"),
    ("SGOT", "aspartate aminotransferase"),
    ("ALP", "alkaline phosphatase"),
    ("Bilirubin", "bilirubin"),
    ("Albumin", "albumin"),
    ("GGT", "gamma-glutamyl transferase"),
    ("Cholesterol", "total cholesterol"),
    ("LDL", "low-density lipoprotein"),
    ("HDL", "high-density lipoprotein"),
    ("Triglycerides", "triglycerides"),
    ("TSH", "thyroid-stimulating hormone"),
    ("T3", "triiodothyronine"),
    ("T4", "thyroxine"),
    ("FBS", "fasting blood glucose"),
    ("PPBS", "postprandial blood glucose"),
    ("RBS", "random blood glucose"),
    ("HbA1c", "glycated hemoglobin"),
    ("Sodium", "sodium"),
    ("Potassium", "potassium"),
    ("Calcium", "calcium"),
    ("Vitamin D", "vitamin d"),
    ("Vitamin B12", "vitamin b12"),
    ("CRP", "c-reactive protein"),
    ("Troponin", "troponin"),
    ("PT", "prothrombin time"),
    ("INR", "international normalized ratio"),
]

SYMPTOMS = [
    "fever",
    "nange fever ide",
    "jwara",
    "chest pain",
    "edeyalli novu",
    "burning while urinating",
    "mootra madovaga uritha ide",
    "stomach pain",
    "hotte novu",
    "headache",
    "tale novu",
    "kai novu",
    "arm pain",
    "back pain",
    "bennu novu",
    "joint pain",
    "cough",
    "kemmu",
    "rash",
    "daddu",
    "itching",
    "turike",
    "dizzy",
    "tale suttu",
    "difficulty breathing",
    "usiraadakke kashta",
    "nausea",
    "vomiting",
    "vanti",
    "diarrhea",
    "loose motions",
    "constipation",
    "fatigue",
    "sustu",
    "palpitations",
    "numbness",
    "swelling",
    "dark urine",
    "sore throat",
    "ear pain",
]

TERMS = [
    "sugar level",
    "blood sugar",
    "sugar level jasthi",
    "sugar jasthi",
    "sakkare jaasti",
    "BP high",
    "high BP",
    "blood pressure high",
    "BP tumba high",
    "pressure jasthi",
    "kidney problem",
    "renal problem",
    "kidney issue",
    "kidney problem ide",
    "heart blockage",
    "heart problem",
    "low blood count",
    "blood count low",
    "yellow eyes",
    "eyes are yellow",
    "bone crack",
    "broken bone",
    "urine infection",
    "urinary infection",
    "mootra infection",
    "thyroid problem",
    "thyroid report abnormal",
    "jwara",
    "jvaram",
    "fever ide",
    "chest pain",
    "edeyalli novu",
    "uritha ide",
    "mootra madovaga uri",
    "novu",
    "tired all the time",
    "kai novu",
    "hotte novu",
    "tale novu",
    "sustu",
]

LANGUAGE_CASES = [
    ("Hello, what is this?", "english"),
    ("Explain this report", "english"),
    ("ಕನ್ನಡದಲ್ಲಿ ಉತ್ತರಿಸಿ", "kannada"),
    ("ನನಗೆ ಜ್ವರ ಇದೆ", "kannada"),
    ("ಕನ್ನಡ ಮತ್ತು English", "bilingual"),
    ("Answer in Kannada", "kannada"),
    ("Answer in English", "english"),
    ("Answer in both English and Kannada", "bilingual"),
    ("Nanage jwara ide", "kannada"),
    ("nange fever ide", "bilingual"),
    ("Nanna kai novu agtha ide", "kannada"),
    ("My kai novu ide", "bilingual"),
    ("Sugar level jasthi ide", "bilingual"),
    ("My sugar level jasthi ide", "bilingual"),
    ("Kidney problem ide antha report alli ide", "bilingual"),
    ("My kidney problem ide", "bilingual"),
    ("BP tumba high ide", "bilingual"),
    ("My BP tumba high ide", "bilingual"),
    ("Mootra madovaga uritha ide", "kannada"),
    ("My mootra burning ide", "bilingual"),
]


class Phase2IntelligenceTests(unittest.TestCase):
    def test_laboratory_extraction_and_range_classification_cases(self):
        self.assertGreaterEqual(len(LAB_CASES), 30)
        for index, (alias, canonical) in enumerate(LAB_CASES):
            with self.subTest(alias=alias):
                result = parse_laboratory_results(f"--- Page 2 ---\n{alias}: 5 u (0 - 10)")
                self.assertEqual(len(result.findings), 1)
                self.assertEqual(result.findings[0].canonical_name, canonical)
                self.assertEqual(result.findings[0].status, "normal")
                self.assertEqual(result.findings[0].page, 2)
                self.assertEqual(result.findings[0].original_text, f"{alias}: 5 u (0 - 10)")

    def test_lab_missing_ranges_units_duplicates_and_unreadable_values(self):
        no_range = parse_laboratory_results("Creatinine: 76 mg/dL").findings[0]
        self.assertEqual(no_range.status, "unassessed")
        self.assertIsNone(no_range.reference_range)
        low = parse_laboratory_results("Hemoglobin: 4 g/dL (10 - 15)").findings[0]
        self.assertEqual(low.status, "low")
        high = parse_laboratory_results("Hemoglobin: 20 g/dL (10 - 15)").findings[0]
        self.assertEqual(high.status, "high")
        unit_mismatch = parse_laboratory_results("Hemoglobin: 12 g/dL (10 - 15) mg/L").findings[0]
        self.assertEqual(unit_mismatch.status, "unassessed")
        qualified = parse_laboratory_results("CRP: <5 mg/L (0 - 10)").findings[0]
        self.assertEqual(qualified.status, "unassessed")
        unreadable = parse_laboratory_results("Platelets: unreadable").findings[0]
        self.assertEqual(unreadable.status, "unreadable")
        missing = parse_laboratory_results("Platelets:").findings[0]
        self.assertEqual(missing.status, "unreadable")
        conflict = parse_laboratory_results("TSH: 2 mIU/L (0 - 5)\nTSH: 9 mIU/L (0 - 5)")
        self.assertEqual([item.status for item in conflict.findings], ["ambiguous", "ambiguous"])
        self.assertTrue(conflict.warnings)
        self.assertTrue(
            all(
                item.critical_status == "not_assessed_no_configured_rules"
                for item in conflict.findings
            )
        )

    def test_oxalate_report_value_is_preserved_and_flagged_against_printed_range(self):
        result = parse_laboratory_results(
            "--- Page 2 ---\nOxalate: 32.37 mg/g creatinine (5.90 - 28.60)"
        ).findings[0]
        self.assertEqual(result.canonical_name, "urine oxalate")
        self.assertEqual(result.value, "32.37")
        self.assertEqual(result.unit, "mg/g creatinine")
        self.assertEqual(result.reference_range, "5.90 - 28.60")
        self.assertEqual(result.status, "high")
        self.assertEqual(result.page, 2)

    def test_numeric_part_of_parameter_name_is_not_treated_as_result(self):
        result = parse_laboratory_results("25-OH Vitamin D: 32 ng/mL (20 to 50)").findings[0]
        self.assertEqual(result.canonical_name, "vitamin d")
        self.assertEqual(result.value, "32")
        self.assertEqual(result.status, "normal")

    def test_missing_value_does_not_read_reference_range_as_result(self):
        result = parse_laboratory_results("Creatinine: (0 - 5) mg/dL").findings[0]
        self.assertIsNone(result.value)
        self.assertEqual(result.status, "unreadable")

    def test_symptom_and_condition_understanding_cases(self):
        self.assertGreaterEqual(len(SYMPTOMS), 30)
        for phrase in SYMPTOMS:
            with self.subTest(phrase=phrase):
                result = analyze_patient_text(f"I have {phrase} for 3 days")
                self.assertTrue(result.symptoms)
                self.assertTrue(
                    all(item.status == "patient_reported_not_diagnosis" for item in result.symptoms)
                )
                self.assertEqual(result.symptoms[0].duration_as_reported, "3 days")

    def test_symptoms_do_not_become_confirmed_diagnoses(self):
        result = analyze_patient_text("I feel chest pain and bone pain")
        self.assertTrue(result.symptoms)
        self.assertTrue(
            all(item.status == "patient_reported_not_diagnosis" for item in result.symptoms)
        )

    def test_prescription_extraction_cases(self):
        for index in range(20):
            with self.subTest(index=index):
                frequency = ("OD", "BD", "TDS", "QID", "SOS", "HS", "AC", "PC")[index % 8]
                text = (
                    f"--- Page 1 ---\nTab. Medicine{index} 500 mg {frequency} after food for 5 days"
                )
                result = extract_prescription_items(text)
                self.assertEqual(len(result.items), 1)
                item = result.items[0]
                self.assertEqual(item.generic_name, None)
                self.assertEqual(item.page, 1)
                self.assertIn(f"Medicine{index}", item.medicine_name_as_written)
                self.assertEqual(item.frequency_as_written.casefold(), frequency.casefold())
                self.assertEqual(item.duration_as_written, "for 5 days")
                self.assertEqual(item.food_instructions_as_written, "after food")
                self.assertEqual(item.original_text, text.splitlines()[1])
                self.assertIn("requires_original_prescription_confirmation", item.extraction_status)

    def test_prescription_missing_unclear_and_unknown_generic_are_safe(self):
        missing = extract_prescription_items("Medicine 250 mg").items[0]
        self.assertIsNone(missing.frequency_as_written)
        unclear = extract_prescription_items("Tab. ?? 250 mg BD").items[0]
        self.assertIsNone(unclear.medicine_name_as_written)
        self.assertIsNone(unclear.generic_name)
        self.assertIn("unclear_name", unclear.extraction_status)
        self.assertEqual(extract_prescription_items("No medication data here").items, [])

    def test_terminology_synonym_cases(self):
        self.assertGreaterEqual(len(TERMS), 30)
        for phrase in TERMS:
            with self.subTest(phrase=phrase):
                mentions = normalize_medical_terms(phrase)
                self.assertTrue(mentions)
                self.assertTrue(
                    all("not a diagnosis" in item["interpretation"] for item in mentions)
                )

    def test_terminology_respects_basic_negation(self):
        self.assertEqual(normalize_medical_terms("I have no chest pain"), [])

    def test_language_cases(self):
        self.assertEqual(len(LANGUAGE_CASES), 20)
        for phrase, expected in LANGUAGE_CASES:
            with self.subTest(phrase=phrase):
                self.assertEqual(detect_language(phrase), expected)

    def test_report_retrieval_filter_is_user_and_session_scoped(self):
        for number in range(20):
            user_id = UUID(int=number + 1)
            session_id = UUID(int=number + 100)
            where = report_retrieval_filter(user_id, session_id)
            self.assertEqual(where["$and"][0], {"user_id": str(user_id)})
            self.assertEqual(where["$and"][1], {"session_id": str(session_id)})
            self.assertNotEqual(where["$and"][0]["user_id"], where["$and"][1]["session_id"])

    def test_langgraph_compiles_with_conditional_intelligence_node(self):
        graph = medical_qa_graph()
        self.assertIn("analyze_clinical_context", graph.get_graph().nodes)

    def test_clinical_analysis_node_structures_report_and_user_context(self):
        result = analyze_clinical_context_node(
            {
                "question": "What does my creatinine show?",
                "history": [{"role": "user", "content": "I have burning while urinating"}],
                "context": "Report: Lab.pdf\nSection: Kidney\nCreatinine: 76 mg/dL (24 - 392)",
            }
        )
        analysis = result["clinical_analysis"]
        self.assertEqual(analysis["laboratory"]["findings"][0]["status"], "normal")
        self.assertEqual(
            analysis["patient_reported"]["symptoms"][0]["status"],
            "patient_reported_not_diagnosis",
        )


if __name__ == "__main__":
    unittest.main()
