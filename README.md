# OakTree Req Readiness — Streamlit App

A web-accessible version of the req-readiness dashboard. Hosted on Streamlit
Community Cloud, fed from a GitHub repo, refreshed daily by the existing
pipeline on Phil's machine.

> ⚠️ **The data file contains candidate names, resume excerpts, and client
> manager feedback.** This is currently configured as a public app per Phil's
> decision (2026-06-09). If that changes, set the app to require email auth
> in the Streamlit Cloud admin and remove the disclaimer banner.

## Architecture

```
Phil's machine                  GitHub                    Streamlit Cloud
─────────────────              ────────                  ──────────────────
req-readiness pipeline   ──>   private repo    ────>    https://...streamlit.app
(daily 7am + 1pm)              with this code            (auto-redeploy on push)
└─ writes req-scores.json      └─ data/req-scores.json  └─ reads from repo
   then push_to_github.ps1
```

No AI runs in Streamlit Cloud. The app is a thin read-only renderer of the
JSON that the local pipeline already produces. **Total monthly Streamlit Cloud
cost: $0** (free tier).

## One-time setup

### 1. Create the GitHub repo

```bash
# From inside this folder
git init
git add .
git commit -m "Initial commit: Streamlit dashboard for OakTree Req Readiness"
git branch -M main

# Create the repo on GitHub (using the gh CLI — or do it in the browser):
gh repo create oaktree-req-readiness --private --source=. --remote=origin --push
```

(If you prefer the browser: create an empty repo at
`https://github.com/<your-org>/oaktree-req-readiness`, then
`git remote add origin git@github.com:<your-org>/oaktree-req-readiness.git`
and `git push -u origin main`.)

### 2. Generate a deploy key for the auto-push job

In PowerShell on Phil's machine:

```powershell
ssh-keygen -t ed25519 -f "$HOME\.ssh\oaktree_streamlit_deploy_key" -N '""' -C "oaktree-readiness-pipeline"
Get-Content "$HOME\.ssh\oaktree_streamlit_deploy_key.pub"
```

Copy the printed public key. In GitHub: **Settings → Deploy keys → Add deploy
key**. Paste it, give it a name (`oaktree-pipeline`), and **check "Allow write
access"**. Save.

Test the connection:

```powershell
$env:GIT_SSH_COMMAND = "ssh -i `"$HOME\.ssh\oaktree_streamlit_deploy_key`" -o StrictHostKeyChecking=accept-new"
git ls-remote origin
```

Should list the remote refs without prompting.

### 3. Deploy to Streamlit Cloud

1. Sign in to https://share.streamlit.io with the GitHub account that owns the repo.
2. Click **New app**.
3. Pick the repo, branch `main`, main file `app.py`.
4. Click **Deploy**.
5. Note the URL (something like `https://oaktree-req-readiness.streamlit.app`).

The free tier will sleep the app after a few hours of inactivity; the first
load after a wake takes ~30 seconds.

### 4. Wire push_to_github.ps1 into the daily scheduled task

Update the Claude scheduled task `req-readiness-daily` so its final step calls
this script. The SKILL.md already does `python run.py`; just append:

```powershell
powershell -ExecutionPolicy Bypass -File "<TOOL_DIR>\..\req-readiness-streamlit\push_to_github.ps1"
```

From then on, every daily run pulls fresh Snowflake data → scores → commits the
updated `data/req-scores.json` to GitHub → Streamlit Cloud auto-redeploys
within ~1 minute.

## Running locally for development

```powershell
cd jarvis-phil\req-readiness-streamlit
python -m streamlit run app.py
# Opens http://localhost:8501
```

The app reads `data/req-scores.json` (already seeded from the pipeline's
current state). Edit `app.py` → Streamlit hot-reloads on save.

## Files

| File | Purpose |
|---|---|
| `app.py` | The Streamlit dashboard. Renders `data/req-scores.json`. |
| `data/req-scores.json` | The pipeline's output, committed daily by the auto-push. |
| `requirements.txt` | `streamlit + pandas`. That's all the Cloud installs. |
| `.streamlit/config.toml` | Theme + privacy settings. |
| `push_to_github.ps1` | Copies the fresh JSON from the pipeline and pushes to GitHub. |
| `.gitignore` | Keeps caches and the (unused) secrets.toml out of git. |

## Updating the data manually

If you ever need to push fresh data outside the schedule:

```powershell
powershell -ExecutionPolicy Bypass -File push_to_github.ps1
```

Or just edit a file, commit, push — Streamlit Cloud redeploys on any change to
`main`.

## If you ever want to make this private

In Streamlit Cloud → app settings → **Authentication**:
- Add an allowlist of OakTree team emails (Streamlit handles Google auth)
- Or restrict to a Google Workspace domain

Then delete the yellow disclaimer banner from the top of `app.py`.
