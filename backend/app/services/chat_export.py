import json
import re
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.config import settings


def plain_text(chat, messages, reports, recommendations) -> str:
    lines = ["MedAssist AI — Chat Export", f"Conversation: {chat.title}", f"Exported: {chat.updated_at.isoformat()}", ""]
    for message in messages:
        role = "You" if message.role.value == "user" else "MedAssist AI"
        lines.extend([f"{role} · {message.created_at.isoformat()}", message.content])
        if message.citations:
            lines.append("Sources:")
            for citation in message.citations:
                lines.append(f"- {citation.get('report_name', 'Report')} · {citation.get('section', 'Section')} · {citation.get('excerpt', '')}")
        lines.append("")
    lines.append("Report summaries")
    for report in reports:
        lines.append(f"\n{report.file_name}")
        lines.append(json.dumps(report.summary_data or {"status": report.processing_status}, ensure_ascii=False, indent=2))
    lines.append("\nRecommendations")
    for item in recommendations:
        lines.append(f"\n{item.kind.title()} · {item.created_at.isoformat()}")
        lines.append(json.dumps(item.payload, ensure_ascii=False, indent=2))
    lines.append("\nThis export is informational and is not a substitute for professional medical advice.")
    return "\n".join(lines)


def _pdf_safe(value: str, unicode_font: bool) -> str:
    if unicode_font:
        return escape(value).replace("\n", "<br/>")
    safe = value.encode("latin-1", errors="replace").decode("latin-1")
    return escape(safe).replace("\n", "<br/>")


def create_pdf(chat, messages, reports, recommendations) -> bytes:
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=LETTER, rightMargin=0.65*inch, leftMargin=0.65*inch, topMargin=0.7*inch, bottomMargin=0.7*inch, title=f"MedAssist — {chat.title}")
    styles = getSampleStyleSheet()
    font_name = "Helvetica"
    unicode_font = False
    if settings.export_font_path:
        pdfmetrics.registerFont(TTFont("MedAssistUnicode", settings.export_font_path))
        font_name, unicode_font = "MedAssistUnicode", True
    title_style = ParagraphStyle("MedTitle", parent=styles["Title"], fontName=font_name, textColor=colors.HexColor("#155eef"), alignment=TA_CENTER, spaceAfter=10)
    heading = ParagraphStyle("MedHeading", parent=styles["Heading2"], fontName=font_name, textColor=colors.HexColor("#123458"), spaceBefore=12, spaceAfter=6)
    body = ParagraphStyle("MedBody", parent=styles["BodyText"], fontName=font_name, fontSize=9, leading=13, spaceAfter=5)
    story = [Paragraph("MedAssist AI · Chat Export", title_style), Paragraph(_pdf_safe(chat.title, unicode_font), heading), Paragraph(f"Exported: {_pdf_safe(chat.updated_at.isoformat(), unicode_font)}", body), Spacer(1, 8)]
    for message in messages:
        who = "You" if message.role.value == "user" else "MedAssist AI"
        story.append(Paragraph(f"<b>{who}</b> · {_pdf_safe(message.created_at.isoformat(), unicode_font)}", body))
        story.append(Paragraph(_pdf_safe(message.content, unicode_font), body))
        for citation in message.citations or []:
            label = f"Source: {citation.get('report_name', 'Report')} · {citation.get('section', 'Section')} · {citation.get('excerpt', '')}"
            story.append(Paragraph(_pdf_safe(label, unicode_font), ParagraphStyle("Citation", parent=body, textColor=colors.HexColor("#526780"), leftIndent=12, fontSize=8)))
        story.append(Spacer(1, 6))
    story.append(Paragraph("Report summaries", heading))
    for report in reports:
        story.append(Paragraph(_pdf_safe(report.file_name, unicode_font), body))
        data = report.summary_data or {"processing_status": report.processing_status}
        story.append(Paragraph(_pdf_safe(json.dumps(data, ensure_ascii=False, indent=2), unicode_font), body))
    story.append(Paragraph("Recommendations and specialist suggestions", heading))
    for item in recommendations:
        story.append(Paragraph(f"<b>{item.kind.title()}</b> · {_pdf_safe(item.created_at.isoformat(), unicode_font)}", body))
        story.append(Paragraph(_pdf_safe(json.dumps(item.payload, ensure_ascii=False, indent=2), unicode_font), body))
    story.append(Spacer(1, 10))
    story.append(Paragraph("This export is informational and is not a substitute for professional medical advice.", ParagraphStyle("Disclaimer", parent=body, textColor=colors.HexColor("#526780"), alignment=TA_CENTER)))
    document.build(story)
    return output.getvalue()


def safe_filename(title: str, extension: str) -> str:
    base = re.sub(r"[^A-Za-z0-9_-]+", "-", title).strip("-")[:60] or "medassist-chat"
    return f"{base}.{extension}"
