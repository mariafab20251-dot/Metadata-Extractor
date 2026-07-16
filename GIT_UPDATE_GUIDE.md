# 📦 Git Update Guide — VideoTextExtractor

This guide explains how to get the latest code updates using Git,
whether you copied the portable folder to a new PC or are starting
from scratch.

---
## 📌 Quick Summary

| What | Command |
|------|---------|
| Update existing copy | `git pull` |
| Fresh clone (public repo) | `git clone <url>` |
| Fresh clone (private repo) | `git clone <url>` + login |
| Check current version | `git log --oneline -1` |
| See what changed | `git log --oneline -5` |

Remote URL (already set):
```
https://github.com/mariafab20251-dot/Metadata-Extractor.git
```

---
## A) IF YOU COPIED THE PORTABLE FOLDER (recommended)

If you copied the entire `VideoTextExtractor_PORTABLE` folder to your
new PC, everything is already set up. To get future updates:

1. Open **Command Prompt** (or PowerShell) inside the folder
2. Run:
   ```
   git pull
   ```

That's it. Git will fetch the latest code from GitHub and merge it
into your existing files. Your local data (downloads, cookies, DB,
Excel reports) is in the `data/` folder which is git-ignored — it
will NOT be touched by `git pull`.

### If git pull asks for username/password

The repo will be made **private** soon. Once it's private, you'll
need to authenticate. See Section C below.

---
## B) FRESH CLONE (start from scratch — no portable copy)

If you don't have the portable folder, you can download everything
directly from GitHub.

### B1 — Public repo (current state)

```
git clone https://github.com/mariafab20251-dot/Metadata-Extractor.git
```

This creates a folder called `Metadata-Extractor` with all the code.

### B2 — Private repo (after it's made private)

```
git clone https://github.com/mariafab20251-dot/Metadata-Extractor.git
```

Git will prompt you to log in. You have two options:

**Option 1 — Personal Access Token (PAT) — RECOMMENDED**
1. Go to GitHub.com → Settings → Developer settings → Personal access tokens
2. Click "Tokens (classic)" → "Generate new token (classic)"
3. Check the `repo` scope (full control of private repos)
4. Copy the token (looks like: `ghp_xxxxxxxxxxxxxxxxxxxx`)
5. When git asks for a password, paste the token (not your GitHub password)

**Option 2 — GitHub CLI**
1. Install GitHub CLI: https://cli.github.com/
2. Run `gh auth login` and follow the prompts
3. Then clone normally: `git clone https://github.com/mariafab20251-dot/Metadata-Extractor.git`

---
## C) GIT PULL ON A PRIVATE REPO

Once the repo is private, `git pull` will ask you to authenticate.

### For the portable folder (already has git set up):

If you copied the portable folder and now the repo went private:

```
git pull
```

→ Git will show a login prompt. Enter your GitHub username and
  Personal Access Token (not your password).

### To avoid logging in every time (cache credentials):

Run this ONCE:
```
git config credential.helper store
```

Or safer (cache for 1 hour):
```
git config credential.helper "cache --timeout=3600"
```

After running one of these, the next `git pull` will save your
credentials so you don't have to type them every time.

> ⚠️ On Windows, `git credential.helper store` saves credentials
> in plain text in your user folder. Only use on your personal
> laptop.

---
## D) AFTER CLONING / PULLING

1. Run `setup\install_dependencies.bat` to install/update Python packages
2. Run `run.bat` to start the app

If you get package errors after a pull, just re-run the install batch.

---
## E) TROUBLESHOOTING

### "I already made changes and git pull won't work"
```
git stash
git pull
git stash pop
```
This temporarily puts aside any local changes, pulls the update,
then restores your changes.

### "I want to see what version I'm on"
```
git log --oneline -1
```
Shows the latest commit ID and message.

### "I want to see all recent changes"
```
git log --oneline -10 --graph
```
Shows the last 10 commits with a visual branch graph.

### "There's a merge conflict"
If you modified the same file as a GitHub update, git may show a
conflict. Run:
```
git mergetool
```
Or just re-copy the portable folder fresh — it's often faster
than resolving conflicts manually.

---
## F) FOLDER STRUCTURE (what's tracked vs what's local)

| In git (will update on pull) | Not in git (your local data) |
|------------------------------|------------------------------|
| `core/` — all scripts        | `data/` — downloads, DB, Excel, cookies |
| `gui/` — dashboard UI        | `channels/` — downloaded channel videos |
| `platforms/` — Instagram etc | `venv/` — Python virtual env (recreate via install batch) |
| `setup/` — installers        | `*.mp4`, `*.mp3`, `*.wav` — media files |
| `main.py`                    | `cookies.txt`, `ig_username.txt` |
| `run.bat`                    | `__pycache__/` |
| `config.py`                  |  |

So `git pull` is safe — it will never delete your downloads, DB,
cookies, or Excel reports.
