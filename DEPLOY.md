# Deploy to Hugging Face Spaces (free) — 5 minutes

Everything is already prepared (Dockerfile + Space config in README). You only do
three things: create an empty Space, push this folder to it, add your API key as a
secret.

## Step 1 — Create the Space (in your browser)

1. Go to https://huggingface.co/new-space
2. Space name: `urbanroof-hr-assistant`
3. Select SDK: **Docker** → template: **Blank**
4. Visibility: **Public** for easy pilot testing (anyone with the link can chat;
   switch to Private later if HR prefers — private needs viewers to log in to HF)
5. Click **Create Space**

## Step 2 — Push this folder to the Space (in your terminal, inside this folder)

Replace `YOUR_USERNAME` (your HF username) and `hf_XXXX` (a **fresh** write token from
https://huggingface.co/settings/tokens — revoke any token you've shared anywhere):

```bash
git remote add hf https://YOUR_USERNAME:hf_XXXX@huggingface.co/spaces/YOUR_USERNAME/urbanroof-hr-assistant
git push hf claude/current-model-e83gvk:main --force
```

## Step 3 — Add your Gemini key as a secret (in your browser)

1. Open your Space → **Settings** → **Variables and secrets**
2. Add **secret**: name `GEMINI_API_KEY`, value = your key from
   https://aistudio.google.com/apikey
3. Add **variable**: name `BOT_PROVIDER`, value `gemini`
4. The Space rebuilds automatically (~2–3 minutes)

## Done

Your bot is live at:
`https://YOUR_USERNAME-urbanroof-hr-assistant.hf.space`

Open it, ask "How many earned leaves do I get?", and share the link with whoever
should pilot it.

## Updating later

Any time the code or knowledge files change, just:

```bash
git push hf claude/current-model-e83gvk:main --force
```

## Also push to GitHub (separate from the Space)

```bash
git push -u origin claude/current-model-e83gvk
```
