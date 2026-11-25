import io
import zipfile
from unittest import TestCase

from app.core.auth import is_knowledge_admin
from app.core.config import settings
from app.knowledge.policy import document_is_indexable, document_is_retrievable
from app.services.medical_knowledge_documents import chunk_document, extract_text_file, sha256
from app.services.medical_knowledge_citations import make_medical_citations


class VerifiedKnowledgeTests(TestCase):
    def test_approval_policy_fails_closed_for_unreviewed_and_retired_sources(self):
        self.assertFalse(document_is_indexable("pending_review", "approved"))
        self.assertFalse(document_is_indexable("retired", "approved"))
        self.assertTrue(document_is_indexable("approved", "approved"))

    def test_retrieval_requires_approved_source_active_version_and_completed_index(self):
        self.assertTrue(document_is_retrievable("approved", "approved", True, "indexed"))
        self.assertFalse(document_is_retrievable("pending_review", "approved", True, "indexed"))
        self.assertFalse(document_is_retrievable("approved", "pending_review", True, "indexed"))
        self.assertFalse(document_is_retrievable("approved", "approved", False, "indexed"))
        self.assertFalse(document_is_retrievable("approved", "approved", True, "index_queued"))

    def test_content_hash_is_stable_and_detects_changed_file(self):
        self.assertEqual(sha256(b"reference"), sha256(b"reference"))
        self.assertNotEqual(sha256(b"reference"), sha256(b"different"))

    def test_chunker_preserves_page_and_section_provenance(self):
        chunks = chunk_document(
            "--- Page 1 ---\nMEDICATIONS\nTake with food.\n--- Page 2 ---\n# Findings\nNo diagnosis stated.",
            chunk_size=100,
            overlap=0,
        )
        self.assertEqual([chunk.page for chunk in chunks], [1, 2])
        self.assertEqual(chunks[0].section, "MEDICATIONS")
        self.assertEqual(chunks[1].section, "Findings")
        self.assertIn("No diagnosis stated", chunks[1].content)

    def test_chunker_splits_long_lines_without_losing_text(self):
        source = "word " * 800
        chunks = chunk_document(source, chunk_size=100, overlap=0)
        self.assertGreater(len(chunks), 1)
        self.assertEqual(" ".join(chunk.content for chunk in chunks).split(), source.split())

    def test_utf8_text_extraction(self):
        self.assertEqual(extract_text_file("## Findings\nನಮಸ್ಕಾರ".encode(), "md"), "## Findings\nನಮಸ್ಕಾರ")
        self.assertIn('"reference"', extract_text_file(b'{"topic":"reference"}', "json"))
        self.assertEqual(extract_text_file(b"test,value\nA,1", "csv"), "test | value\nA | 1")

    def test_docx_extraction_uses_word_paragraphs(self):
        payload = io.BytesIO()
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body><w:p><w:r><w:t>Patient education</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>Reviewed section</w:t></w:r></w:p></w:body></w:document>'
        )
        with zipfile.ZipFile(payload, "w") as archive:
            archive.writestr("word/document.xml", xml)

        self.assertEqual(extract_text_file(payload.getvalue(), "docx"), "Patient education\nReviewed section")

    def test_admin_allowlist_fails_closed_and_matches_explicit_ids(self):
        original = settings.knowledge_admin_clerk_ids
        try:
            settings.knowledge_admin_clerk_ids = ""
            self.assertFalse(is_knowledge_admin("user_123"))
            settings.knowledge_admin_clerk_ids = "user_admin,user_other"
            self.assertTrue(is_knowledge_admin("user_admin"))
            self.assertFalse(is_knowledge_admin("user_123"))
        finally:
            settings.knowledge_admin_clerk_ids = original

    def test_medical_citation_keeps_explicit_source_provenance(self):
        citations = make_medical_citations([{
            "text": "Use only the guidance described in this passage.",
            "metadata": {
                "source_type": "guideline",
                "source_id": "source-1",
                "document_id": "doc-1",
                "version_id": "version-1",
                "source_title": "Reviewed Reference",
                "organization": "Example Health Body",
                "source_url": "https://example.org/reference",
                "section": "Precautions",
                "page": 4,
                "publication_date": "2025-01",
                "last_updated_date": "2025-06",
                "document_version": "2025.2",
                "jurisdiction": "IN",
                "language": "en",
            },
        }])
        self.assertEqual(len(citations), 1)
        self.assertEqual(citations[0]["source_type"], "medical_knowledge")
        self.assertEqual(citations[0]["source_url"], "https://example.org/reference")
        self.assertEqual(citations[0]["section"], "Precautions")
        self.assertEqual(citations[0]["page"], 4)

    def test_empty_knowledge_results_never_create_citations(self):
        self.assertEqual(make_medical_citations([]), [])

