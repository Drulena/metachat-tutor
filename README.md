# MetaChat Tutor

Django web app for linguodidactics research — teaches constructive communication roles, tactics and metagrapheme use (emojis, formatting, hashtags) in online polylogues.

## Run

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000` in a browser.

## Structure

Django project `tutor_project/` with a single app `tutor/`:

- `tutor_project/settings.py` — project config; reads `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` from env
- `tutor/views.py` — session-driven chat view + `export/` (JSON download) and `reset/` routes
- `tutor/state_machine.py` — conversation state machine (`init_session`, `process_input`)
- `tutor/scenarios.py` — scenario content and variants
- `tutor/llm.py` — optional LLM feedback via `get_llm_feedback()`
- `tutor/templates/tutor/chat.html` — UI template (uses ChatML-style HTML)
- `requirements.txt` — `Django`, `python-dotenv`, `requests`, `markdown`

## Session Flow

1. **Registration** — name + group
2. **Pre-Test** — rate 3 messages (1–5 scale)
3. **Self-Assessment** — choose level (Beginner / Intermediate / Advanced)
4. **Step 1: Analysis** — 2 tasks per level (softening criticism + recognizing aggressive formatting)
5. **Step 2: Role-Play** — choose from constructive roles (e.g. Mediator, Logical Expert, Idea Generator, Empath)
6. **Reflection** — brief written reflection
7. **Post-Test** — rate the same 3 messages again
8. **Export** — download session JSON and submit via Google Form

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
