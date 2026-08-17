"""Gradio front-end for the UrbanRoof HR Assistant.

This is the entry point Hugging Face Spaces runs on the free tier (Docker Spaces
are paid). Same brain as the FastAPI app — app/bot.py with the full knowledge
base — different UI layer.

Run locally:  python gradio_app.py   →  http://localhost:7860
"""

import uuid

import gradio as gr
from dotenv import load_dotenv

load_dotenv()

from app.bot import HRAssistant  # noqa: E402
from app.notify import (  # noqa: E402
    append_jsonl,
    escalation_email_body,
    friendly_error,
    send_hr_email,
)

assistant = HRAssistant()

WELCOME = (
    "Hi! I can answer questions about UrbanRoof policies — leave, attendance, "
    "work from home, payroll, dress code — and help you find your way around HROne. "
    "What would you like to know?\n\n"
    "*Answers come from the Employee Handbook and HR-approved sources. "
    "Please don't type personal details (ID numbers, medical information) here. "
    "For your own records (leave balance, payslips) check the HROne app.*"
)

EXAMPLES = [
    "How many earned leaves do I get per year?",
    "What is the sandwich leave rule?",
    "How do I request work from home?",
    "When is salary credited?",
]


def add_user_message(message, history):
    message = (message or "").strip()
    if not message:
        return "", history
    return "", history + [{"role": "user", "content": message}]


def bot_reply(history, session_id):
    if not history or history[-1]["role"] != "user":
        yield history
        return
    message = history[-1]["content"]
    history = history + [{"role": "assistant", "content": ""}]
    try:
        for chunk in assistant.stream_reply(session_id, message):
            history[-1]["content"] += chunk
            yield history
    except Exception as exc:
        history[-1]["content"] = "⚠️ " + friendly_error(exc)
        yield history


def record_vote(session_id, evt: gr.LikeData):
    append_jsonl(
        "feedback.jsonl",
        {
            "session_id": session_id,
            "verdict": "up" if evt.liked else "down",
            "answer_snippet": str(evt.value)[:200],
        },
    )


def escalate(name, contact, question, session_id):
    transcript = assistant.transcript(session_id)
    question = (question or "").strip() or (
        transcript[-2]["content"] if len(transcript) >= 2 else ""
    )
    append_jsonl(
        "escalations.jsonl",
        {
            "session_id": session_id,
            "question": question,
            "employee_name": name,
            "employee_contact": contact,
            "transcript": transcript,
        },
    )
    emailed = send_hr_email(
        subject=f"[HR Assistant] Escalation: {question[:80] or 'employee needs help'}",
        body=escalation_email_body(question, name, contact, transcript),
    )
    how = "and emailed to HR" if emailed else "for HR to review"
    return f"✅ Sent {how}. HR will get back to you — thanks, {name or 'there'}!"


with gr.Blocks(title="UrbanRoof HR Assistant") as demo:
    session_id = gr.State(lambda: uuid.uuid4().hex)

    gr.Markdown("# 🤝 UrbanRoof HR Assistant")
    chatbot = gr.Chatbot(
        value=[{"role": "assistant", "content": WELCOME}],
        height=460,
        show_label=False,
    )
    msg = gr.Textbox(
        placeholder="Ask about leave, WFH, payroll, HROne…",
        show_label=False,
        submit_btn=True,
    )
    gr.Examples(examples=EXAMPLES, inputs=msg)

    msg.submit(add_user_message, [msg, chatbot], [msg, chatbot], queue=False).then(
        bot_reply, [chatbot, session_id], chatbot
    )
    chatbot.like(record_vote, [session_id], None)

    with gr.Accordion("🙋 Didn't get your answer? Send it to HR", open=False):
        gr.Markdown(
            "A human from HR will pick this up. Your conversation above is attached."
        )
        esc_name = gr.Textbox(label="Your name")
        esc_contact = gr.Textbox(label="Your email or phone")
        esc_question = gr.Textbox(
            label="Your question (leave empty to use your last question)"
        )
        esc_btn = gr.Button("Send to HR", variant="primary")
        esc_status = gr.Markdown()
        esc_btn.click(
            escalate,
            [esc_name, esc_contact, esc_question, session_id],
            esc_status,
        )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
