"""LLM integration service for tutor feedback."""

import html as html_mod
import logging
import os
from typing import Optional

import requests

from .data import THEORETICAL_BASE
from .scenarios import ROLEPLAY_ERROR_TEMPLATES, ROLEPLAY_ERROR_DEFAULT

logger = logging.getLogger(__name__)

_MAX_ANSWER_LENGTH = 2000
_PRIMARY_TIMEOUT = 15
_FALLBACK_TIMEOUT = 10


def get_roleplay_fallback(level: str, role_name: str, detail: str) -> str:
    """Build a role-aware fallback message for role-play mode."""
    normalized = role_name if role_name.startswith("role_") else f"role_{role_name}"
    templates = ROLEPLAY_ERROR_TEMPLATES.get(level, {})
    hint = templates.get(normalized, ROLEPLAY_ERROR_DEFAULT)
    return f"**🤖 LLM Feedback (API failed — {detail}):** {hint}"


def get_llm_feedback(
    user_answer: str,
    role_name: Optional[str],
    user_name: str,
    level: str,
    task_question: Optional[str] = None,
) -> tuple[str, bool]:
    """Get LLM feedback on a student's answer.

    Args:
        user_answer: The student's response text.
        role_name: The role the student selected (e.g. 'mediator').
        user_name: The student's display name.
        level: Student proficiency level (beginner/intermediate/advanced).
        task_question: The original task question for context.

    Returns:
        Tuple of (feedback_string, failed). ``failed`` is True when the
        LLM was unreachable or returned an error, indicating the user
        may want to retry.
    """
    if task_question is None:
        task_question = "(task context unknown)"

    api_key = os.getenv("LLM_API_KEY")
    if api_key is None:
        return (
            "**\U0001f916 LLM Feedback (API not configured):** "
            "Set LLM_API_KEY in .env to enable AI feedback.",
            True,
        )

    truncated_answer = user_answer[:_MAX_ANSWER_LENGTH]

    prompt = (
        f"{THEORETICAL_BASE}\n\n"
        "Always use English to respond.\n"
        "When discussing emojis, use the actual Unicode emoji character "
        "(e.g., \U0001f642 not the word 'smiley').\n"
        f"Student: {user_name}\nLevel: {level}\n"
        f"Selected role: {role_name or 'none'}\n\n"
        f"--- TASK QUESTION ---\n{task_question}\n\n"
        f"--- STUDENT ANSWER ---\n{truncated_answer}\n\n"
        "--- INSTRUCTION ---\n"
        "Evaluate the student's answer based on the theoretical framework above. "
        "Check whether they identified/applied metagrapheme tools correctly for their level. "
        "Give brief constructive feedback (max 500 characters). "
        "Be supportive and specific."
    )

    llm_url = os.getenv("LLM_URL", "https://vedai.by/api/v1")
    llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    base = llm_url.rstrip("/")
    for suffix in ("/chat/completions", "/completions"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    chat_url = base + "/chat/completions"
    legacy_url = base + "/completions"

    attempts = [
        (
            "chat",
            chat_url,
            {
                "model": llm_model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 150,
            },
            _PRIMARY_TIMEOUT,
        ),
        (
            "legacy",
            legacy_url,
            {"prompt": prompt, "max_tokens": 150},
            _FALLBACK_TIMEOUT,
        ),
    ]

    errors: list[str] = []
    for label, url, payload, timeout in attempts:
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            logger.debug("LLM %s at %s -> status=%d", label, url, resp.status_code)

            if resp.status_code != 200:
                errors.append(f"{label}: HTTP {resp.status_code}")
                continue

            result = resp.json()
            choices = result.get("choices")
            if choices and len(choices) > 0:
                choice = choices[0]
                msg = choice.get("message") or {}
                text = (
                    choice.get("text")
                    or msg.get("content")
                    or msg.get("reasoning")
                    or ""
                )
                if text.strip():
                    return html_mod.unescape(text.strip()), False

            errors.append(f"{label}: no valid choices in response")
            logger.debug(
                "LLM %s response keys=%s preview=%s",
                label,
                list(result.keys()),
                str(result)[:300],
            )
            if choices is not None:
                logger.debug("LLM %s choices=%s", label, choices)

        except Exception as exc:
            errors.append(f"{label}: {exc}")
            logger.debug("LLM %s error: %s", label, exc)

    safe = truncated_answer[:200]
    detail = errors[0] if errors else "unknown"
    logger.debug("LLM fell back to demo, errors=%s", errors)

    if role_name is not None:
        fallback_text = get_roleplay_fallback(level, role_name, detail)
    else:
        if "TASK 1" in task_question:
            hint = "Adding a friendly emoji like \U0001f642 or \U0001f60a can make criticism feel more supportive."
        elif "TASK 2" in task_question:
            hint = (
                "Combining multiple metagrapheme techniques creates stronger effects."
            )
        else:
            hint = "Review the criteria and check if your response addresses all requirements."
        fallback_text = (
            f"**\U0001f916 LLM Feedback (API failed \u2014 {detail}):** "
            f'You wrote: "{safe}". {hint}'
        )
    return html_mod.unescape(fallback_text), True
