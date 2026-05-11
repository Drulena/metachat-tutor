# MetaChat Tutor

Single-file Streamlit chatbot for linguodidactics research.

## Run

```powershell
.\venv\Scripts\Activate.ps1; streamlit run app.py
```

## Structure

- `app.py` — single entry point, state machine, and Streamlit UI
- `requirements.txt` — `streamlit`, `python-dotenv`
- `.env` — contains `VEDAI_API_KEY` (never commit this file)

## Notes

- No tests, no linting, no type checking
- State machine in `SCENARIO['states']` drives all user flows
- `TASK_VARIANTS` and `LEVELS` are randomized per session via `randomize_scenario()`
- UI labels are in English with emoji markers (📋 PRE-TEST:, 📊 Self-Assessment:, 📝 TASK:, 🎭 ROLE:, etc.)
- Chat history + user data exported as JSON from sidebar on session end