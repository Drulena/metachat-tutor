# MetaChat Tutor

Django web app for linguodidactics research.

## Run

```powershell
.\venv\Scripts\Activate.ps1; python manage.py runserver
```

## Structure

- `manage.py` — Django entry point (loads `.env` via `load_dotenv(override=True)`)
- `tutor_project/` — project config (`settings.py`, `urls.py`, `wsgi.py`)
- `tutor/` — app: `views.py`, `state_machine.py`, `scenarios.py`, `data.py`, `llm.py`, `models.py`, templates and static
- `requirements.txt` — `Django`, `python-dotenv`, `requests`, `markdown`
- `.env` — `LLM_API_KEY`, `LLM_URL`, `LLM_MODEL`, `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` (never commit). Example at `.env.example`.

## Key facts

- `load_dotenv(override=True)` — used in both `manage.py` and `settings.py`
- LLM integration is **optional**: when `LLM_API_KEY is None`, `get_llm_feedback()` returns demo text. It tries `/chat/completions` first, falls back to `/completions`.
- `randomize_scenario()` randomizes task variants from `TASK_VARIANTS` / `SCENARIO` for pre-test messages, analysis tasks, and role-play scenarios
- `'back'` at any text input returns to previous menu — exact target state varies by current state (handled in `process_input()`)
- State machine keys follow convention: `analysis_task_{1|2}_{level}`, `analysis_feedback_{1|2}_{level}`, `role_{slug}`, `roleplay_feedback_{slug}`
- UI labels are in English with emoji markers (📋 PRE-TEST:, 📊 Self-Assessment:, 📝 TASK:, 🎭 ROLE:, etc.)
- No tests, no linting, no type checking
- Code comments and variable names are in Russian
- Session data exported as JSON from the `export/` route