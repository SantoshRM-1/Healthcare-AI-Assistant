import html

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.message import Message
from app.models.session_memory import RecommendationRecord
from app.models.uploaded_report import UploadedReport


def render_chat_email(chat, messages, reports, recommendations) -> tuple[str, str]:
    title = html.escape(chat.title)
    rows = []
    for message in messages:
        role = "You" if message.role.value == "user" else "MedAssist AI"
        citations = "".join(
            f'<div style="margin-top:8px;padding:10px;border-left:3px solid #8db8ff;background:#f4f8ff;color:#405570;font-size:12px"><b>{html.escape(str(item.get("report_name", "Report")))}</b> · {html.escape(str(item.get("section", "Section")))}<br>{html.escape(str(item.get("excerpt", "")))}</div>'
            for item in (message.citations or [])
        )
        rows.append(f'<div style="padding:16px;margin:12px 0;border:1px solid #e5edf7;border-radius:14px;background:#fff"><div style="font:600 12px Arial;color:#3971bd;margin-bottom:8px">{role}</div><div style="font:14px/1.6 Arial;color:#26384d;white-space:pre-wrap">{html.escape(message.content)}</div>{citations}</div>')
    summary_rows = []
    for report in reports:
        summary = report.summary_data or {"status": report.processing_status}
        summary_rows.append(f'<div style="padding:14px;margin:8px 0;background:#f5f9ff;border-radius:12px"><b>{html.escape(report.file_name)}</b><pre style="white-space:pre-wrap;font:12px/1.5 Arial;color:#42556c">{html.escape(str(summary))}</pre></div>')
    recommendation_rows = []
    for record in recommendations:
        recommendation_rows.append(f'<div style="padding:12px;margin:8px 0;border:1px solid #dcebe4;border-radius:12px"><b>{html.escape(record.kind.title())}</b><pre style="white-space:pre-wrap;font:12px/1.5 Arial;color:#42556c">{html.escape(str(record.payload))}</pre></div>')
    text_lines = [f"MedAssist AI chat summary: {chat.title}", ""]
    for message in messages:
        text_lines.extend([f"{'You' if message.role.value == 'user' else 'MedAssist AI'}:", message.content, ""])
        for citation in message.citations or []:
            text_lines.append(f"Source: {citation.get('report_name')} · {citation.get('section')} — {citation.get('excerpt')}")
    text_lines += ["", "Report summaries:"]
    text_lines.extend(f"{item.file_name}: {item.summary_data or item.processing_status}" for item in reports)
    text_lines += ["", "Recommendations:"]
    text_lines.extend(f"{item.kind.title()}: {item.payload}" for item in recommendations)
    text_lines += ["", "This information is based on documents shared by the sender and is not a substitute for professional medical advice."]
    plain = "\n".join(text_lines)
    html_body = f'''<!doctype html><html><body style="margin:0;background:#f4f7fb;padding:24px;font-family:Arial,sans-serif"><div style="max-width:680px;margin:auto"><header style="padding:24px;border-radius:18px;background:#1459c7;color:#fff"><div style="font-size:12px;opacity:.8">MEDASSIST AI · PATIENT CHAT SUMMARY</div><h1 style="font-size:22px;margin:10px 0 0">{title}</h1></header><main style="padding:12px 0"><h2 style="font-size:16px;color:#173553">Conversation</h2>{''.join(rows)}<h2 style="font-size:16px;color:#173553;margin-top:28px">Report summaries</h2>{''.join(summary_rows) or '<p style="color:#65778d;font-size:13px">No saved report summaries in this chat.</p>'}<h2 style="font-size:16px;color:#173553;margin-top:28px">Recommendations and specialist suggestions</h2>{''.join(recommendation_rows) or '<p style="color:#65778d;font-size:13px">No recommendations in this chat.</p>'}<p style="padding:14px;border-radius:12px;background:#fff8e7;color:#6c5727;font-size:12px;line-height:1.6">This information is based on documents shared by the sender and is not a substitute for professional medical advice.</p></main><footer style="text-align:center;color:#8290a1;font-size:11px">Shared from MedAssist AI at the sender’s request.</footer></div></body></html>'''
    return html_body, plain


async def send_chat_email(session: AsyncSession, chat, recipient: str, include_summaries: bool) -> None:
    if not settings.resend_api_key or not settings.email_from:
        raise RuntimeError("Email sharing is not configured")
    messages = await session.scalars(select(Message).where(Message.session_id == chat.id).order_by(Message.created_at.asc()))
    reports = await session.scalars(select(UploadedReport).where(UploadedReport.session_id == chat.id, UploadedReport.user_id == chat.user_id).order_by(UploadedReport.upload_date))
    recommendations = await session.scalars(select(RecommendationRecord).where(RecommendationRecord.session_id == chat.id, RecommendationRecord.user_id == chat.user_id).order_by(RecommendationRecord.created_at.asc()))
    body_html, body_text = render_chat_email(chat, messages.all(), reports.all() if include_summaries else [], recommendations.all())
    payload = {"from": settings.email_from, "to": [recipient], "subject": f"MedAssist AI chat summary: {chat.title[:120]}", "html": body_html, "text": body_text}
    if settings.email_reply_to:
        payload["reply_to"] = settings.email_reply_to
    async with httpx.AsyncClient(timeout=httpx.Timeout(20, connect=5)) as client:
        response = await client.post("https://api.resend.com/emails", headers={"Authorization": f"Bearer {settings.resend_api_key}", "Content-Type": "application/json"}, json=payload)
        response.raise_for_status()
