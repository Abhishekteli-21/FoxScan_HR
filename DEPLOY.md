# Deploy to Hugging Face Spaces (free) — 5 minutes

Hugging Face made **Docker** Spaces a paid feature, so the free path is the **Gradio**
SDK. That's what `gradio_app.py` and the README frontmatter are set up for — same bot,
same knowledge base, just Gradio instead of FastAPI serving the UI.

You do three things: create an empty Gradio Space, push this folder to it, add your API
key as a secret.

## Step 1 — Create the Space (in your browser)

1. Go to https://huggingface.co/new-space
2. Space name: `FoxScan_HR`
3. Select SDK: **Gradio** → template: **Blank**
4. Hardware: **CPU basic — free**
5. Visibility: **Public** for easy pilot testing (anyone with the link can chat;
   switch to Private later if HR prefers — private needs viewers to log in to HF)
6. Click **Create Space**

Ignore the "Docker" option even though it looks tempting: it now carries a *Paid* badge.

## Step 2 — Push this folder to the Space (in your terminal, inside this folder)

Replace `YOUR_USERNAME` (your HF username) and `hf_XXXX` (a **fresh** write token from
https://huggingface.co/settings/tokens — revoke any token you've shared anywhere):

```bash
git remote add hf https://YOUR_USERNAME:hf_XXXX@huggingface.co/spaces/YOUR_USERNAME/FoxScan_HR
git push hf claude/current-model-e83gvk:main --force
```

HF builds from the `main` branch, which is why the push maps our branch onto `main`.

## Step 3 — Add your Gemini key as a secret (in your browser)

1. Open your Space → **Settings** → **Variables and secrets**
2. Add **secret**: name `GEMINI_API_KEY`, value = your key from
   https://aistudio.google.com/apikey
3. Add **variable**: name `BOT_PROVIDER`, value `gemini`
4. The Space rebuilds automatically (~2–3 minutes)

Secrets are injected as environment variables, which is exactly what `app/bot.py` reads —
no `.env` file is needed (and `.env` is git-ignored, so it never reaches the Space).

## Done

Your bot is live at:
`https://YOUR_USERNAME-foxscan-hr.hf.space`

(HF lowercases the URL and turns `_` into `-`.)

Open it, ask "How many earned leaves do I get?", and share the link with whoever
should pilot it.

## If the build fails

Check the Space's **Logs** tab:

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: gradio` | Space built with the wrong SDK | README frontmatter must say `sdk: gradio` and `app_file: gradio_app.py` |
| Gradio version errors on startup | HF picked a different Gradio version | The frontmatter pins `sdk_version: 6.24.0`, the version this UI is tested on |
| Chat replies "AI service is busy" | Free Gemini quota hit, or key missing | Confirm the `GEMINI_API_KEY` secret and `BOT_PROVIDER=gemini` variable; free tier is ~250 requests/day on `gemini-2.5-flash` |

## Updating later

Any time the code or knowledge files change, just:

```bash
git push hf claude/current-model-e83gvk:main --force
```

## Also push to GitHub (separate from the Space)

```bash
git push -u origin claude/current-model-e83gvk
```
