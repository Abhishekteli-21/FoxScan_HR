"""Escalation/feedback logging and optional HR email — shared by both front-ends
(FastAPI in app/main.py and Gradio in app.py)."""

import json
import os
import smtplib
import time
from email.message import EmailMessage
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)


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


def friendly_error(exc: Exception) -> str:
    msg = str(exc)
    if any(t in msg for t in ("503", "429", "UNAVAILABLE", "overloaded")):
        return (
            "The AI service is busy right now (free-tier limit). "
            "Please try again in a few seconds."
        )
    return msg


def escalation_email_body(
    question: str, name: str, contact: str, transcript: list[dict]
) -> str:
    lines = [f"{m['role'].upper()}: {m['content']}" for m in transcript]
    return (
        f"Employee: {name or 'not given'} ({contact or 'no contact'})\n"
        f"Question: {question}\n\nConversation so far:\n\n" + "\n\n".join(lines)
    )
