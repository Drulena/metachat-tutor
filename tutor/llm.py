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
_MAX_OUTPUT_TOKENS = 150
_PRIMARY_TIMEOUT = 15
_FALLBACK_TIMEOUT = 10

# Three wire protocols, not one SDK per vendor: "openai" covers every
# OpenAI-compatible endpoint (OpenAI, Mistral, OpenRouter, Cerebras,
# DeepSeek, local servers); "anthropic" answers the vendor's own
# protocol (x-api-key, /v1/messages, content blocks); "mistral"
# answers Mistral's native Conversations API (inputs/outputs) — the
# owner's key answers there while chat/completions 429s.
_PROVIDER_ANTHROPIC = "anthropic"
_PROVIDER_MISTRAL = "mistral"
_ANTHROPIC_VERSION = "2023-06-01"
# Endpoints owners paste from provider docs; the API base is recovered
# from any of them (issue #15: a Mistral /v1/conversations URL shipped
# in .env and every attempt 404'd behind it).
_URL_SUFFIXES = ("/chat/completions", "/completions", "/messages",
                 "/conversations")


def _api_base(llm_url: str) -> str:
    """Return the provider's API base from any docs-pasted endpoint URL."""
    base = llm_url.rstrip("/")
    for suffix in _URL_SUFFIXES:
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    return base


def _anthropic_text(result: dict) -> Optional[str]:
    """Concatenate the text blocks of an anthropic message; thinking is not surfaced."""
    blocks = result.get("content")
    if not isinstance(blocks, list):
        return None
    texts = [block.get("text", "") for block in blocks
             if isinstance(block, dict) and block.get("type") == "text"]
    joined = "\n".join(text for text in texts if text.strip())
    if not joined.strip():
        return None
    return html_mod.unescape(joined.strip())


def _mistral_text(result: dict) -> Optional[str]:
    """Concatenate the assistant outputs of a conversations response."""
    entries = result.get("outputs")
    if not isinstance(entries, list):
        return None
    texts = [entry.get("content", "") for entry in entries
             if isinstance(entry, dict)
             and entry.get("type") == "message.output"
             and entry.get("role") == "assistant"
             and isinstance(entry.get("content"), str)]
    joined = "\n".join(text for text in texts if text.strip())
    if not joined.strip():
        return None
    return html_mod.unescape(joined.strip())


def _response_text(result: object, provider: str = "openai") -> Optional[str]:
    """Extract the student-facing text from a completions response.

    Only ``text``/``content`` are surfaced. A provider's ``reasoning``
    (openai-compatible) and ``thinking`` (anthropic) fields are the
    model's chain of thought — showing it to the learner is a defect
    (owner report, issue #15), so a reasoning-only answer is a miss:
    the caller falls through to the demo-failure path.
    """
    if not isinstance(result, dict):
        return None
    if provider == _PROVIDER_ANTHROPIC:
        return _anthropic_text(result)
    if provider == _PROVIDER_MISTRAL:
        return _mistral_text(result)
    choices = result.get("choices")
    if not choices:
        return None
    choice = choices[0]
    msg = choice.get("message") or {}
    text = choice.get("text") or msg.get("content") or ""
    if text.strip():
        return html_mod.unescape(text.strip())
    return None


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
        "Be supportive and specific. "
        "Return only the feedback text the student should read. "
        "No reasoning, no analysis notes, no preamble."
    )

    llm_url = os.getenv("LLM_URL", "https://vedai.by/api/v1")
    llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()

    base = _api_base(llm_url)
    bearer = {"Authorization": f"Bearer {api_key}",
              "Content-Type": "application/json"}
    if provider == _PROVIDER_ANTHROPIC:
        attempts = [
            (
                "anthropic",
                base + "/messages",
                {"x-api-key": api_key,
                 "anthropic-version": _ANTHROPIC_VERSION,
                 "Content-Type": "application/json"},
                {
                    "model": llm_model,
                    "max_tokens": _MAX_OUTPUT_TOKENS,
                    "messages": [{"role": "user", "content": prompt}],
                },
                _PRIMARY_TIMEOUT,
            ),
        ]
    elif provider == _PROVIDER_MISTRAL:
        attempts = [
            (
                "mistral",
                base + "/conversations",
                bearer,
                {
                    "model": llm_model,
                    "inputs": [{"role": "user", "content": prompt}],
                    "tools": [],
                    "completion_args": {"max_tokens": _MAX_OUTPUT_TOKENS},
                    "instructions": "",
                },
                _PRIMARY_TIMEOUT,
            ),
        ]
    else:
        attempts = [
            (
                "chat",
                base + "/chat/completions",
                bearer,
                {
                    "model": llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": _MAX_OUTPUT_TOKENS,
                },
                _PRIMARY_TIMEOUT,
            ),
            (
                "legacy",
                base + "/completions",
                bearer,
                {"prompt": prompt, "max_tokens": _MAX_OUTPUT_TOKENS},
                _FALLBACK_TIMEOUT,
            ),
        ]

    errors: list[str] = []
    for label, url, headers, payload, timeout in attempts:
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            logger.debug("LLM %s at %s -> status=%d", label, url, resp.status_code)

            if resp.status_code != 200:
                errors.append(f"{label}: HTTP {resp.status_code}")
                continue

            result = resp.json()
            text = _response_text(result, provider)
            if text:
                return text, False

            errors.append(f"{label}: no student-facing text in response")
            logger.debug(
                "LLM %s response keys=%s preview=%s",
                label,
                list(result.keys()),
                str(result)[:300],
            )

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
