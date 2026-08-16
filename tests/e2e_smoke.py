"""End-to-end smoke test — no API key needed.

Starts a tiny mock OpenAI-compatible LLM server, points the app at it
(BOT_PROVIDER=custom), then exercises every endpoint like a real browser would:
chat (streaming), feedback, escalation, and knowledge reload.

Run:  python tests/e2e_smoke.py
Exits 0 and prints PASS lines if everything works.
"""

import json
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MOCK_PORT = 9401
APP_PORT = 9402
MOCK_REPLY = [
    "You get ",
    "12 sick leaves ",
    "per year. ",
    "Source: Employee Handbook — Sick Leave",
]

# ── Mock OpenAI-compatible server ───────────────────────────────────────────
os.environ.update(
    BOT_PROVIDER="custom",
    BOT_BASE_URL=f"http://127.0.0.1:{MOCK_PORT}/v1",
    BOT_API_KEY="test-key",
    BOT_MODEL="mock-model",
)

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

mock = FastAPI()


@mock.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    assert body["model"] == "mock-model"
    assert body["messages"][0]["role"] == "system"
    assert "KNOWLEDGE SOURCES" in body["messages"][0]["content"]

    def gen():
        for piece in MOCK_REPLY:
            chunk = {
                "id": "mock-1",
                "object": "chat.completion.chunk",
                "created": 0,
                "model": "mock-model",
                "choices": [
                    {"index": 0, "delta": {"content": piece}, "finish_reason": None}
                ],
            }
            yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


def run_server(app, port):
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(50):
        if server.started:
            return server
        time.sleep(0.1)
    raise RuntimeError(f"server on :{port} did not start")


def main() -> None:
    run_server(mock, MOCK_PORT)

    from app.main import app as hr_app  # imported after env is set

    run_server(hr_app, APP_PORT)

    import httpx

    base = f"http://127.0.0.1:{APP_PORT}"
    client = httpx.Client(timeout=15)

    # 1. UI serves
    resp = client.get(base + "/")
    assert resp.status_code == 200 and "UrbanRoof HR Assistant" in resp.text
    print("PASS  GET /              → chat UI served")

    # 2. Chat streams the mock answer through the full pipeline
    collected = []
    with client.stream(
        "POST",
        base + "/api/chat",
        json={"session_id": "e2e", "message": "How many sick leaves do I get?"},
    ) as resp:
        assert resp.status_code == 200
        for line in resp.iter_lines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                assert "error" not in data, f"chat returned error: {data}"
                if "text" in data:
                    collected.append(data["text"])
    answer = "".join(collected)
    assert answer == "".join(MOCK_REPLY), f"unexpected answer: {answer!r}"
    print(f"PASS  POST /api/chat     → streamed {len(collected)} chunks: {answer!r}")

    # 3. Second turn keeps history (mock sees 3 messages: sys + 2 user + 1 assistant)
    with client.stream(
        "POST",
        base + "/api/chat",
        json={"session_id": "e2e", "message": "and earned leave?"},
    ) as resp:
        list(resp.iter_lines())
    print("PASS  POST /api/chat     → multi-turn works")

    # 4. Feedback logs
    resp = client.post(
        base + "/api/feedback", json={"session_id": "e2e", "verdict": "up"}
    )
    assert resp.json()["ok"] is True
    print("PASS  POST /api/feedback → logged")

    # 5. Escalation captures the transcript
    resp = client.post(
        base + "/api/escalate",
        json={
            "session_id": "e2e",
            "question": "test escalation",
            "employee_name": "E2E",
        },
    )
    assert resp.json()["ok"] is True
    logged = (
        Path("data/escalations.jsonl")
        .read_text(encoding="utf-8")
        .strip()
        .splitlines()[-1]
    )
    record = json.loads(logged)
    assert record["question"] == "test escalation"
    assert any(m["role"] == "assistant" for m in record["transcript"])
    print("PASS  POST /api/escalate → transcript captured")

    # 6. Knowledge reload
    resp = client.post(base + "/api/reload")
    assert resp.json()["ok"] is True
    print("PASS  POST /api/reload   → knowledge reloaded")

    print("\nAll end-to-end checks passed.")


if __name__ == "__main__":
    main()
