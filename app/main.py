"""FastAPI server for the UrbanRoof HR Assistant.

Endpoints:
  GET  /               → chat UI (static/index.html)
  POST /api/chat       → SSE stream of the assistant's reply
  POST /api/escalate   → send the conversation to HR (JSONL log + optional email)
  POST /api/feedback   → 👍/👎 on an answer (JSONL log)

Run:  uvicorn app.main:app --reload
"""

import json
import os
import smtplib
import time
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

load_dotenv()

from .bot import HRAssistant  # noqa: E402  (needs env loaded first)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

app = FastAPI(title="UrbanRoof HR Assistant")
assistant = HRAssistant()


class ChatIn(BaseModel):
    session_id: str
    message: str


class EscalateIn(BaseModel):
    session_id: str
    question: str = ""
    employee_name: str = ""
    employee_contact: str = ""


class FeedbackIn(BaseModel):
    session_id: str
    verdict: str  # "up" | "down"
    answer_snippet: str = ""


def append_jsonl(filename: str, record: dict) -> None:
    record["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(DATA_DIR / filename, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def send_hr_email(subject: str, body: str) -> bool:
    """Email HR if SMTP is configured in .env; otherwise skip quietly."""
    host = os.environ.get("SMTP_HOST")
    to = os.environ.get("HR_EMAIL")
    if not host or not to:
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ.get("SMTP_FROM", "hr-assistant@localhost")
    msg["To"] = to
    msg.set_content(body)
    with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", "587"))) as smtp:
        smtp.starttls()
        user = os.environ.get("SMTP_USER")
        if user:
            smtp.login(user, os.environ.get("SMTP_PASSWORD", ""))
        smtp.send_message(msg)
    return True


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.post("/api/chat")
def chat(body: ChatIn):
    def event_stream():
        try:
            for chunk in assistant.stream_reply(body.session_id, body.message):
                yield f"data: {json.dumps({'text': chunk})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except (
            Exception
        ) as exc:  # surface config errors (e.g. missing API key) to the UI
            msg = str(exc)
            if any(t in msg for t in ("503", "429", "UNAVAILABLE", "overloaded")):
                msg = (
                    "The AI service is busy right now (free-tier limit). "
                    "Please try again in a few seconds."
                )
            yield f"data: {json.dumps({'error': msg})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/escalate")
def escalate(body: EscalateIn):
    transcript = assistant.transcript(body.session_id)
    record = {
        "session_id": body.session_id,
        "question": body.question,
        "employee_name": body.employee_name,
        "employee_contact": body.employee_contact,
        "transcript": transcript,
    }
    append_jsonl("escalations.jsonl", record)

    lines = [f"{m['role'].upper()}: {m['content']}" for m in transcript]
    emailed = send_hr_email(
        subject=f"[HR Assistant] Escalation: {body.question[:80] or 'employee needs help'}",
        body=(
            f"Employee: {body.employee_name or 'not given'} ({body.employee_contact or 'no contact'})\n"
            f"Question: {body.question}\n\nConversation so far:\n\n"
            + "\n\n".join(lines)
        ),
    )
    return {"ok": True, "emailed": emailed}


@app.post("/api/feedback")
def feedback(body: FeedbackIn):
    append_jsonl("feedback.jsonl", body.model_dump())
    return {"ok": True}


@app.post("/api/reload")
def reload_knowledge():
    """Call after editing files in knowledge/ to pick up changes without a restart."""
    assistant.reload_knowledge()
    return {"ok": True}
