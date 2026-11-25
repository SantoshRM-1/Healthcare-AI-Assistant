import json
import os
import re
import threading
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.core.config import settings


class PDFUnicodeFontError(ValueError):
    """Raised when a Kannada export cannot be rendered without losing glyphs."""


_FONT_LOCK = threading.Lock()
_KANNADA_RANGE = range(0x0C80, 0x0D00)


def _unicode_font_path() -> Path | None:
    configured = settings.export_font_path
    if configured:
        path = Path(configured).expanduser()
        if not path.is_file():
            raise PDFUnicodeFontError("EXPORT_FONT_PATH must point to a readable Kannada-capable TrueType font")
        return path

    windows_dir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    candidates = (
        windows_dir / "Fonts" / "Nirmala.ttc",
        Path("/usr/share/fonts/truetype/noto/NotoSansKannada-Regular.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansKannada-Regular.ttf"),
        Path(__file__).resolve().parents[1] / "assets" / "fonts" / "NotoSansKannada-Regular.ttf",
    )
    return next((path for path in candidates if path.is_file()), None)


def _register_unicode_font(path: Path) -> str:
    """Register a Unicode font once; ReportLab keeps a process-wide font registry."""
    name = "MedAssistUnicode"
    with _FONT_LOCK:
        if name not in pdfmetrics._fonts:
            try:
                font = TTFont(name, str(path), subfontIndex=0, shapable=True)
                pdfmetrics.registerFont(font)
                registerFontFamily(name, normal=name, bold=name, italic=name, boldItalic=name)
            except Exception as exc:
                raise PDFUnicodeFontError("The configured export font could not be loaded") from exc
        return name


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
    if not unicode_font and any(ord(char) in _KANNADA_RANGE for char in value):
        raise PDFUnicodeFontError("Kannada PDF export needs a Unicode font with Kannada glyphs")
    return escape(value).replace("\n", "<br/>")


def _append_readable_text(story, text: str, body: ParagraphStyle, heading: ParagraphStyle) -> None:
    """Render simple chat Markdown as readable paragraphs without markup tokens."""
    for line in text.splitlines():
        value = line.strip()
        if not value:
            story.append(Spacer(1, 3))
            continue
        heading_match = re.match(r"^#{1,3}\s+(.+)$", value)
        if heading_match:
            story.append(Paragraph(_pdf_safe(heading_match.group(1), True), heading))
            continue
        bullet_match = re.match(r"^(?:[-*]|\d+[.)])\s+(.+)$", value)
        if bullet_match:
            value = f"- {bullet_match.group(1)}"
        escaped = _pdf_safe(value, True)
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
        escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", escaped)
        story.append(Paragraph(escaped, body))


def create_pdf(chat, messages, reports, recommendations) -> bytes:
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=LETTER, rightMargin=0.65*inch, leftMargin=0.65*inch, topMargin=0.7*inch, bottomMargin=0.7*inch, title=f"MedAssist — {chat.title}")
    styles = getSampleStyleSheet()
    font_name = "Helvetica"
    unicode_font = False
    export_text = plain_text(chat, messages, reports, recommendations)
    has_kannada = any("\u0c80" <= char <= "\u0cff" for char in export_text)
    font_path = _unicode_font_path()
    if font_path:
        font_name, unicode_font = _register_unicode_font(font_path), True
    if has_kannada:
        if not font_path:
            raise PDFUnicodeFontError("Kannada PDF export needs EXPORT_FONT_PATH set to a Kannada-capable TrueType font")
        font = pdfmetrics.getFont(font_name)
        if not font.shapable:
            raise PDFUnicodeFontError("Kannada PDF export requires the uharfbuzz package for correct character shaping")
        try:
            missing = {ord(char) for char in export_text if ord(char) in _KANNADA_RANGE and ord(char) not in font.face.charWidths}
        except Exception as exc:
            raise PDFUnicodeFontError("The configured export font does not expose its Kannada glyph coverage") from exc
        if missing:
            raise PDFUnicodeFontError("The configured export font does not contain every Kannada glyph used in this chat")
    shaping = int(has_kannada)
    title_style = ParagraphStyle("MedTitle", parent=styles["Title"], fontName=font_name, textColor=colors.HexColor("#155eef"), alignment=TA_CENTER, spaceAfter=10, shaping=shaping)
    heading = ParagraphStyle("MedHeading", parent=styles["Heading2"], fontName=font_name, textColor=colors.HexColor("#123458"), spaceBefore=12, spaceAfter=6, shaping=shaping)
    body = ParagraphStyle("MedBody", parent=styles["BodyText"], fontName=font_name, fontSize=9, leading=13, spaceAfter=5, shaping=shaping)
    story = [Paragraph("MedAssist AI · Chat Export", title_style), Paragraph(_pdf_safe(chat.title, unicode_font), heading), Paragraph(f"Exported: {_pdf_safe(chat.updated_at.isoformat(), unicode_font)}", body), Spacer(1, 8)]
    for message in messages:
        who = "You" if message.role.value == "user" else "MedAssist AI"
        story.append(Paragraph(f"<b>{who}</b> · {_pdf_safe(message.created_at.isoformat(), unicode_font)}", body))
        _append_readable_text(story, message.content, body, heading)
        for citation in message.citations or []:
            label_parts = [citation.get("report_name") or "Report", citation.get("section")]
            if citation.get("page"):
                label_parts.append(f"Page {citation['page']}")
            label = "Source: " + " · ".join(part for part in label_parts if part)
            story.append(Paragraph(_pdf_safe(label, unicode_font), ParagraphStyle("Citation", parent=body, textColor=colors.HexColor("#526780"), leftIndent=12, fontSize=8)))
        story.append(Spacer(1, 6))
    story.append(Paragraph("Report summaries", heading))
    for report in reports:
        story.append(Paragraph(_pdf_safe(report.file_name, unicode_font), body))
        data = report.summary_data or {"processing_status": report.processing_status}
        _append_readable_text(story, json.dumps(data, ensure_ascii=False, indent=2), body, heading)
    story.append(Paragraph("Recommendations and specialist suggestions", heading))
    for item in recommendations:
        story.append(Paragraph(f"<b>{item.kind.title()}</b> · {_pdf_safe(item.created_at.isoformat(), unicode_font)}", body))
        _append_readable_text(story, json.dumps(item.payload, ensure_ascii=False, indent=2), body, heading)
    story.append(Spacer(1, 10))
    story.append(Paragraph("This export is informational and is not a substitute for professional medical advice.", ParagraphStyle("Disclaimer", parent=body, textColor=colors.HexColor("#526780"), alignment=TA_CENTER)))
    document.build(story)
    return output.getvalue()


def safe_filename(title: str, extension: str) -> str:
    base = re.sub(r"[^A-Za-z0-9_-]+", "-", title).strip("-")[:60] or "medassist-chat"
    return f"{base}.{extension}"
