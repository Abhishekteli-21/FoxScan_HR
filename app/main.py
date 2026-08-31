"""FastAPI server for the UrbanRoof HR Assistant.

Endpoints:
  GET  /               → chat UI (static/index.html)
  POST /api/chat       → SSE stream of the assistant's reply
  POST /api/escalate   → send the conversation to HR (JSONL log + optional email)
  POST /api/feedback   → 👍/👎 on an answer (JSONL log)

Run:  uvicorn app.main:app --reload
(For Hugging Face's free tier, use the Gradio front-end instead: python app.py)
"""

import json
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

load_dotenv()

from .bot import MODEL, PROVIDER, HRAssistant  # noqa: E402  (needs env loaded first)
from .notify import (  # noqa: E402
    EPHEMERAL_STORAGE,
    append_jsonl,
    escalation_email_body,
    friendly_error,
    send_hr_email,
)

ROOT = Path(__file__).resolve().parent.parent

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


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/portal")
def portal(path: str = "/"):
    """TEMPORARY knowledge-building helper — see app/portal.py. Remove when done."""
    from .portal import read

    return read(path)


@app.get("/api/health")
def health():
    """Deploy check: is a provider key actually reachable from this instance?

    Answers the question a hosted deploy always raises — did the secret land? —
    without sending a chat message. Never returns the key itself.
    """
    try:
        assistant._ensure_client()
        ok, detail = True, ""
    except Exception as exc:
        ok, detail = False, friendly_error(exc)
    return {
        "ok": ok,
        "provider": PROVIDER,
        "model": assistant.model or MODEL or "(unset)",
        "knowledge_chars": len(assistant.knowledge),
        "storage": "ephemeral" if EPHEMERAL_STORAGE else "persistent",
        "detail": detail,
    }


@app.post("/api/chat")
def chat(body: ChatIn):
    def event_stream():
        try:
            for chunk in assistant.stream_reply(body.session_id, body.message):
                yield f"data: {json.dumps({'text': chunk})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as exc:  # surface config/provider errors readably in the UI
            yield f"data: {json.dumps({'error': friendly_error(exc)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/escalate")
def escalate(body: EscalateIn):
    transcript = assistant.transcript(body.session_id)
    append_jsonl(
        "escalations.jsonl",
        {
            "session_id": body.session_id,
            "question": body.question,
            "employee_name": body.employee_name,
            "employee_contact": body.employee_contact,
            "transcript": transcript,
        },
    )
    emailed = send_hr_email(
        subject=f"[HR Assistant] Escalation: {body.question[:80] or 'employee needs help'}",
        body=escalation_email_body(
            body.question, body.employee_name, body.employee_contact, transcript
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
