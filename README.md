# MetaChat Tutor

Adaptive Streamlit chatbot for linguodidactics research — teaches constructive communication roles, tactics and metagraheme use (emojis, formatting, hashtags) in online polylogues.

## Run

```powershell
.\venv\Scripts\Activate.ps1; streamlit run app.py
```

## Structure

- `app.py` — single entry point; state machine in `SCENARIO['states']` drives all flows
- `requirements.txt` — `streamlit`, `python-dotenv`
- `.env` — contains `VEDAI_API_KEY` (never commit)
- JSON export via sidebar — contains full session data for research

## Session Flow

1. **Registration** — name + group
2. **Pre-Test** — rate 3 messages (1–5 scale)
3. **Self-Assessment** — choose level (Beginner / Intermediate / Advanced)
4. **Step 1: Analysis** — 2 tasks per level (softening criticism + recognizing aggressive formatting)
5. **Step 2: Role-Play** — choose from 9 constructive roles (Mediator, Logical Expert, Idea Generator, Researcher, Interpreter, Advocate, Judge, Peacemaker, Empath)
6. **Reflection** — brief written reflection
7. **Post-Test** — rate the same 3 messages again
8. **Export** — download JSON and submit via Google Form

## Notes

- `randomize_scenario()` randomizes task variants and role scenarios per session
- `TASK_VARIANTS` holds all content variants; `SCENARIO['states']` holds UI strings
- No tests, no linting, no type checking
- `USE_LLM = False` by default; set `True` and implement `get_llm_feedback()` to add AI-powered feedback (theoretical base is in `THEORETICAL_BASE`)
- Chat history + user data exported as JSON from sidebar at session end
- Use `'back'` at any time to return to previous step

## Run application in local

```sh
source venv/bin/activate
# or .\venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Open `http://127.0.0.1:8000` in a browser. Set `SECRET_KEY` and `ALLOWED_HOSTS` in `.env` or env vars if you get errors (the defaults in settings.py work for local dev as-is).

## PythonAnywhere deploy steps

```sh
git pull  # on PA
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

Then in PA web config:
- WSGI: `/home/youruser/metachat-tutor/tutor_project/wsgi.py`
- Static: `/static/` → `/home/youruser/metachat-tutor/staticfiles/`
- Env vars (or .env): `SECRET_KEY`, `ALLOWED_HOSTS=youruser.pythonanywhere.com`, `DEBUG=0`

```html
<div style="border-left: 3px solid #008080; padding-left: 12px; margin: 12px 0; background: #f0f8f8; border-radius: 4px;">
⚠️ <strong>Post-migration note:</strong> <code>streamlit</code> was removed from requirements. The old <code>app.py</code> still exists but is inert — remove it when you're confident the Django version is working.
</div>
```
