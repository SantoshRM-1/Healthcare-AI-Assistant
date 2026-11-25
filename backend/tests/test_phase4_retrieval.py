import json
from pathlib import Path
from unittest import TestCase
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from app.services.medical_query import (
    classify_medical_intent,
    expand_medical_query,
    rerank_retrieval_results,
)
from app.services.rag_evaluation import mean_retrieval_scores, score_retrieval
from app.services.medical_query import compact_conversation_history
from app.services.medical_qa import detect_language
from app.api.v1.routes.ai import _sse, _emergency_response
from app.services.chat_export import PDFUnicodeFontError, create_pdf


class MedicalQueryTests(TestCase):
    def test_phase4_evaluation_fixture(self):
        cases = json.loads((Path(__file__).parent / "fixtures" / "phase4_evaluation.json").read_text(encoding="utf-8"))
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertEqual(classify_medical_intent(case["question"], case["history"]), case["intent"])
                self.assertEqual(detect_language(case["question"]), case["language"])
                emergency = _emergency_response(case["question"], case["language"])
                self.assertEqual(emergency is not None, case["emergency"])

    def test_intent_routes_cover_existing_intelligence_modules(self):
        cases = {
            "Summarize my reports": "report_summary",
            "What does my blood report indicate?": "report_summary",
            "Is my HbA1c high?": "laboratory",
            "What does this prescription say?": "prescription",
            "Nange yava food thinnabeku?": "nutrition",
            "What precautions should I take?": "precautions",
            "Can you suggest a hospital?": "hospital",
            "Which doctor should I see?": "specialist",
            "I have a headache": "symptoms",
            "What does dysuria mean?": "terminology",
        }
        for query, expected in cases.items():
            with self.subTest(query=query):
                self.assertEqual(classify_medical_intent(query), expected)

    def test_follow_up_uses_only_passed_same_chat_history(self):
        history = [
            {"role": "user", "content": "My creatinine is 1.8 mg/dL"},
            {"role": "assistant", "content": "We discussed the reported value."},
        ]
        self.assertEqual(classify_medical_intent("What does it mean?", history), "follow_up")
        self.assertEqual(classify_medical_intent("What does it mean?", []), "terminology")
        memory = {"last_topic": "my creatinine result", "reported_symptoms": "kidney concern"}
        self.assertEqual(classify_medical_intent("What does it mean?", [], memory), "follow_up")

    def test_query_expansion_preserves_user_text_and_adds_multilingual_aliases(self):
        for query in ("creatinine jasthi ide", "ಕ್ರಿಯಾಟಿನಿನ್ ಹೆಚ್ಚಾಗಿದೆ", "my creatinine is high"):
            with self.subTest(query=query):
                expanded = expand_medical_query(query)
                self.assertIn(query, expanded)
                self.assertIn("renal function", expanded)
        self.assertIn("HbA1c", expand_medical_query("ನನ್ನ ಸಕ್ಕರೆ ಪ್ರಮಾಣ ಹೆಚ್ಚಾಗಿದೆ"))

    def test_history_compaction_keeps_recent_turns_and_bounds_prompt_size(self):
        history = [{"role": "user", "content": str(index) * 2000} for index in range(6)]
        compacted = compact_conversation_history(history, max_messages=4, max_chars=1500, per_message_chars=500)
        self.assertLessEqual(len(compacted), 4)
        self.assertLessEqual(sum(len(item["content"]) for item in compacted), 1500)
        self.assertTrue(compacted[-1]["content"].endswith("5"))

    def test_language_and_sse_preserve_kannada_unicode(self):
        self.assertEqual(detect_language("ನನ್ನ ಕ್ರಿಯಾಟಿನಿನ್ ಹೆಚ್ಚಾಗಿದೆ"), "kannada")
        self.assertIn("ಕನ್ನಡ", _sse({"type": "token", "content": "ಕನ್ನಡ ಉತ್ತರ"}).decode("utf-8"))

    def test_emergency_gate_catches_kannada_and_romanized_stroke_phrases(self):
        self.assertIsNotNone(_emergency_response("ಮುಖ ಒಂದು ಕಡೆ ವಾಲಿದೆ ಮತ್ತು ಮಾತನಾಡಲು ಕಷ್ಟವಾಗುತ್ತಿದೆ", "kannada"))
        self.assertIsNotNone(_emergency_response("mukha ondu kade vaalide mathanadakke agtilla", "english"))

    def test_kannada_pdf_export_refuses_lossy_fallback_without_font(self):
        chat = SimpleNamespace(title="ಕನ್ನಡ ಸಂಭಾಷಣೆ", updated_at=datetime.now(timezone.utc))
        with patch("app.services.chat_export._unicode_font_path", return_value=None):
            with self.assertRaisesRegex(PDFUnicodeFontError, "EXPORT_FONT_PATH"):
                create_pdf(chat, [], [], [])

    def test_reranker_uses_bounded_lexical_tiebreak_and_deduplicates(self):
        candidates = [
            {"id": "semantic", "text": "The renal laboratory result is outside range.", "distance": 0.30},
            {"id": "lexical", "text": "Creatinine is a kidney function test result.", "distance": 0.34},
            {"id": "duplicate", "text": "Creatinine is a kidney function test result.", "distance": 0.25},
            {"id": "irrelevant", "text": "Unrelated skin care passage.", "distance": 0.80},
        ]
        ranked = rerank_retrieval_results(candidates, "creatinine kidney", limit=3, max_distance=0.65)
        self.assertEqual([item["id"] for item in ranked], ["lexical", "semantic"])

    def test_retrieval_metrics_are_transparent_and_macro_averaged(self):
        first = score_retrieval(["a", "b", "c"], {"b", "c"}, k=3)
        second = score_retrieval(["x", "y"], {"z"}, k=3)
        self.assertEqual(first, {"precision@3": 2 / 3, "recall@3": 1.0, "mrr": 0.5})
        mean = mean_retrieval_scores([first, second])
        self.assertAlmostEqual(mean["precision@3"], (2 / 3 + 0) / 2)
        self.assertAlmostEqual(mean["recall@3"], (1 + 0) / 2)
        self.assertAlmostEqual(mean["mrr"], 0.25)
        self.assertEqual(mean_retrieval_scores([]), {"precision": 0.0, "recall": 0.0, "mrr": 0.0})
