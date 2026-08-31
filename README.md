---
title: UrbanRoof HR Assistant
emoji: 🤝
colorFrom: green
colorTo: gray
sdk: gradio
sdk_version: 6.24.0
app_file: gradio_app.py
pinned: false
---

# UrbanRoof HR Assistant

An employee-facing chatbot that answers HR policy questions (leave, attendance, WFH,
payroll, conduct…) and HROne how-to questions from **official sources only**, cites
where each answer came from, and escalates to a human in HR when it doesn't know.

Phase 1 of the plan in the
[HROne Chatbot Playbook](https://claude.ai/code/artifact/e7cfdd96-5d86-44c5-81ad-44ec1327c4a1):
no HROne API needed — knowledge comes from the Employee Handbook, HROne help articles,
and an HR-maintained FAQ.

## How it works

```
Employee (web chat) ──► Gradio  (gradio_app.py)  ─┐
                    └─► FastAPI (app/main.py)  ───┤
                                                  ▼
                                          app/bot.py ──► LLM (Claude / Gemini / …)
                                            │ system prompt contains the FULL
                                            │ knowledge base, prompt-cached
                                            │ (~90% discount after 1st request)
                        data/escalations.jsonl ◄── "Send to HR" (+ optional email)
                        data/feedback.jsonl    ◄── 👍/👎 buttons
```

Two front-ends, one brain. `gradio_app.py` is what Hugging Face's free tier runs;
`app/main.py` is the FastAPI/SSE version for self-hosting. Both call the same
`HRAssistant` in `app/bot.py`, so knowledge and behaviour never diverge.

No vector database: the whole knowledge base (~20K tokens) fits in context and is served
from the provider's prompt cache. Add retrieval only if `knowledge/` ever grows past
~100K tokens.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install gradio==6.24.0  # only if you want to run the Gradio UI locally
cp .env.example .env        # then put your provider's API key inside
```

Then run whichever front-end you want:

```bash
python gradio_app.py                  # Gradio UI  → http://localhost:7860
uvicorn app.main:app --reload         # FastAPI UI → http://localhost:8000
```

## The knowledge base (`knowledge/`)

| File | What it is | Who maintains it |
|---|---|---|
| `handbook.md` | Cleaned, structured Employee Handbook. Contradictions in the original are marked `⚠️ AMBIGUITY` — the bot presents both versions and points to HR. | Engineering re-generates when HR revises the handbook |
| `faq.md` | Official HR answers, **overrides the handbook**. This is where HR resolves the ambiguities and answers escalated questions. | HR |
| `hrone_howto.md` | Step-by-step HROne guides. Currently a placeholder — fill it via the crawler below or HR's own write-ups. | Engineering + HR |

After editing knowledge files, call `POST /api/reload` (or restart the server).

### Filling in HROne how-tos

From a network that can reach the portal (office/home, not a cloud sandbox):

```bash
pip install requests beautifulsoup4
python scripts/crawl_help_portal.py --out knowledge/hrone_howto_crawled.md
```

Review the output (the script flags articles whose steps are only screenshots), curate
the useful ones into `knowledge/hrone_howto.md`, then `POST /api/reload`.

## Escalation & feedback

- **Send to HR** button → appends the question + full transcript to
  `data/escalations.jsonl`, and emails HR if SMTP is configured in `.env`.
- 👍/👎 → `data/feedback.jsonl`.
- **Pilot routine for HR:** skim escalations + 👎 feedback weekly; every recurring
  question becomes a new entry in `knowledge/faq.md`. That's the improvement loop.

## Configuration (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `BOT_PROVIDER` | `gemini` | `anthropic` \| `gemini` \| `groq` \| `openrouter` \| `custom` |
| `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` / … | — | Key for the chosen provider |
| `BOT_MODEL` | per provider | `claude-opus-5` (anthropic) / `gemini-2.5-flash` (gemini) |
| `BOT_EFFORT` | `medium` | anthropic only: `low` / `medium` / `high` |
| `BOT_MAX_TOKENS` | `2048` | Max answer length |
| `HR_EMAIL`, `SMTP_*` | unset | Enable escalation emails |

### Running it for free

- **LLM**: `BOT_PROVIDER=gemini` with a free key from https://aistudio.google.com/apikey.
  Use **`gemini-2.5-flash`** (~250 free requests/day, 1M context, free implicit caching).
  Avoid the `gemini-flash-latest` alias: it resolves to the newest model, whose free quota
  is ~20 requests/day — too small for a chatbot. ⚠️ **Google's free tier uses prompts for
  training and may involve human review** — acceptable for a pilot; before company-wide
  rollout either enable Gemini billing (a few $/month removes the training clause) or
  switch back to `anthropic`. Groq is the free+private option but only after a retrieval
  mode shrinks prompts (planned; not needed at current knowledge size). NVIDIA's free
  endpoints are trial-only by their terms — not for production.
- **Hosting** (both free, both documented in [DEPLOY.md](DEPLOY.md)):
  - **Vercel** runs the FastAPI front-end straight from this repo — `api/index.py` plus
    `vercel.json` are all it needs, and every push to this branch redeploys.
  - **Hugging Face Spaces** runs the Gradio front-end on the **Gradio** SDK (free CPU).
    Docker Spaces are now a paid feature, which is why `gradio_app.py` exists.
  - The `Dockerfile` still covers **Render**'s free tier (sleeps after 15 min idle,
    ~1 min cold start) or any container host.

  Set the `.env` values as the host's secrets. No GPU needed anywhere — the model runs
  provider-side.

## Tests & code quality

```bash
python tests/e2e_smoke.py   # full end-to-end test with a mock LLM — no API key needed
ruff check . && ruff format --check .   # lint + formatting
```

The smoke test spins up a fake LLM server, then exercises the real app against it:
UI serving, streamed chat, multi-turn history, feedback logging, escalation with
transcript capture, and knowledge reload. Run it after any change.

## Pilot checklist (before company-wide rollout)

- [ ] HR resolves the `⚠️ AMBIGUITY` items in `handbook.md` via `faq.md`
      (notice period, full-time hours, maternity/paternity, probation-leave pay)
- [ ] HROne how-tos filled in (`scripts/crawl_help_portal.py` or manual)
- [ ] 10–20 pilot users; HR reviews every transcript in week 1
- [ ] Decide transcript retention policy with HR (data/ folder)

## Roadmap (from the Playbook)

- **Phase 2** — personal data ("my leave balance") via the HROne external API, behind
  company SSO. Blocked on: API key + endpoint confirmation from HROne.
- **Phase 3** — actions (apply leave, raise tickets) and Teams/WhatsApp channels.
