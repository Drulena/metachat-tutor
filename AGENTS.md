# MetaChat Tutor

Single-file Streamlit chatbot for linguodidactics research.

## Run

```powershell
.\venv\Scripts\Activate.ps1; streamlit run app.py
```

## Structure

- `app.py` — single entry point (~1300 lines), state machine in `SCENARIO['states']`, and Streamlit UI
- `requirements.txt` — `streamlit`, `python-dotenv`, `numpy`, `Pillow`
- `packages.txt` + `runtime.txt` — Streamlit Cloud deployment (system dep: `zlib1g-dev`, Python 3.11)
- `.env` — contains `LLM_API_KEY`, `LLM_URL`, `LLM_MODEL` (never commit). Example at `.env.example`.
- `metachat_tutor/`, `tutor/migrations/` — empty/unused directories

## Key facts

- `load_dotenv(override=True)` — required for Streamlit hot-reload to pick up env changes
- LLM integration is **optional**: when `LLM_API_KEY is None`, `get_llm_feedback()` returns demo text. It tries `/chat/completions` first, falls back to `/completions`.
- `randomize_scenario()` deep-copies `SCENARIO` and substitutes random variants from `TASK_VARIANTS` for pre-test messages, analysis tasks, and role-play scenarios
- `'back'` at any text input returns to previous menu — but the exact target state varies by current state (handled in `process_input()`)
- State machine keys follow convention: `analysis_task_{1|2}_{level}`, `analysis_feedback_{1|2}_{level}`, `role_{slug}`, `roleplay_feedback_{slug}`
- UI labels are in English with emoji markers (📋 PRE-TEST:, 📊 Self-Assessment:, 📝 TASK:, 🎭 ROLE:, etc.)
- No tests, no linting, no type checking
- Code comments and variable names are in Russian
- Session data exported as JSON from sidebar (`st.download_button` inside `st.button`)
