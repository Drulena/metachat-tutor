# MetaChat Tutor

Django web app for linguodidactics research — teaches constructive communication roles, tactics and metagrapheme use (emojis, formatting, hashtags) in online polylogues.

## Run

```powershell
uv sync                       # builds .venv from pyproject.toml + uv.lock
uv run manage.py migrate
uv run manage.py createsuperuser   # the maintainer account for /admin/
uv run manage.py runserver
```

uv manages the project environment: `pyproject.toml` lists the dependencies,
`uv.lock` pins them, `uv sync` creates `.venv`, and `uv run <command>` runs one
command inside it. `requirements.txt` is a pinned `uv export` for pip users -
regenerate it with the command written in its own header, never edit it by hand.

Open `http://127.0.0.1:8000` in a browser.

The repository's git hooks live in `scripts/hooks/`; install them once per
clone with `sh scripts/install-git-hooks.sh` (Git Bash or WSL on Windows). The
pre-commit hook refuses commits that edit migrations already committed.

## Structure

Django project `tutor_project/` with a single app `tutor/`:

- `tutor_project/settings.py` — project config; reads `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` from env
- `tutor/views.py` — session-driven chat view + `export/` (JSON download) and `reset/` routes
- `tutor/admin.py` — the research desk: the session ledger's list, filters, detail and cleanup actions
- `tutor/apps.py` — the desk's seats: the view-only `Researcher` group, kept in step on every migrate
- `tutor/ledger.py` — the one writer of the ledger: opened at intake, appended on every submission
- `tutor/tutor_session.py` — session behaviour: lifecycle, navigation options and progress (single source of behaviour)
- `tutor/session.py` — storage seam: state persistence behind a small `Storage` protocol
- `tutor/scenarios.py` — scenario content and variants
- `tutor/llm.py` — optional LLM feedback via `get_llm_feedback()`
- `tutor/templates/tutor/chat.html` — UI template (uses ChatML-style HTML)
- `requirements.txt` — pinned `uv export` of the runtime lock, for pip users
- `pyproject.toml` + `uv.lock` — the dependencies and their pins, managed by uv
- `tutor/test_browser.py` — the learner pages painted by a real headless browser

## Session Flow

1. **Intake form** — name, group and level on one page; the chat opens behind it
2. **Pre-Test** — rate 3 messages (1–5 scale)
3. **Step 1: Analysis** — 2 tasks per level (softening criticism + recognizing aggressive formatting)
4. **Step 2: Role-Play** — choose from constructive roles (e.g. Mediator, Logical Expert, Idea Generator, Empath)
5. **Reflection** — brief written reflection
6. **Post-Test** — rate the same 3 messages again
7. **Last screen** — download the session JSON and submit it via the Google Form

## Research Admin

`/admin/` is the desk the research is read from (ADR-0007 decision 9): the
session ledger, the gate answers, and the groups the ledger is cut by.

- **Sessions** — every row, in progress or finished: participant, group, level,
  the start / last-activity / finished stamps, the gate scores, the reflection's
  length. Sort by any column, search by session id or participant name, and
  filter by group, level, finished vs abandoned, and a from/to window on each
  of the three stamps.
- **A row's page** — the dialogue as the ledger kept it, escaped and in submit
  order, beside the gate answers it scored.
- **Two seats** — the `Researcher` group ships with the app: three view
  permissions and nothing else, so a researcher reads. The maintainer is a
  superuser, the only account that deletes, and it deletes the abandoned rows a
  filter has selected, through the standard confirmation.
- **The desk never writes** — the intake form opens a ledger row and the chat
  appends to it, so the admin's add views are closed. What a maintainer can
  repair by hand is what a learner typed: the name, the group, the level, a
  reset chain link.

To give a researcher access: create the account, set **Staff status**, and add
it to the **Researcher** group.

## Configuration

Copy `.env.example` to `.env` and fill in values:

- `LLM_API_KEY`, `LLM_URL`, `LLM_MODEL` — optional LLM integration. When `LLM_API_KEY` is unset, feedback falls back to a demo message.
- `SECRET_KEY` — Django secret (required when `DEBUG=0`)
- `DEBUG` — `1` for local development, `0` for production
- `ALLOWED_HOSTS` — comma-separated hostnames
- `CSRF_TRUSTED_ORIGINS` — comma-separated origins (e.g. `http://localhost:8000`)

Never commit `.env`.

## Notes

- `randomize_scenario()` randomizes task variants and role scenarios per session
- Session state lives in the Django session; chat history + user data export as JSON via the `export/` route
- Use `'back'` at any text input to return to the previous step
- `staticfiles/` is used only for `collectstatic`; local dev serves static via `django.contrib.staticfiles`
