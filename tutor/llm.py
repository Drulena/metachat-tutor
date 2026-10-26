"""LLM integration service for tutor feedback."""

import html as html_mod
import logging
import os
from typing import NamedTuple, Optional

import requests

from .data import THEORETICAL_BASE
from .scenarios import ROLEPLAY_ERROR_TEMPLATES, ROLEPLAY_ERROR_DEFAULT

logger = logging.getLogger(__name__)

_MAX_ANSWER_LENGTH = 2000
_MAX_OUTPUT_TOKENS = 150
_PRIMARY_TIMEOUT = 15
_FALLBACK_TIMEOUT = 10

# The owner tuned the prompt by hand (issue #15); the character budget is
# the one number meant to be tuned, so it lives here, not in the text.
_MAX_FEEDBACK_CHARS = 500

_OUTPUT_RULES = (
    "Always use English to respond.\n"
    "When discussing emojis, use the actual Unicode emoji character "
    "(e.g., \U0001f642 not the word 'smiley').\n"
)

# The demo banner's tuned answer hints, keyed by the task marker in the
# task question; the default is the generic coaching nudge.
_TASK_HINTS = (
    ("TASK 1",
     "Adding a friendly emoji like \U0001f642 or \U0001f60a can make "
     "criticism feel more supportive."),
    ("TASK 2",
     "Combining multiple metagrapheme techniques creates stronger effects."),
)
_TASK_HINT_DEFAULT = (
    "Review the criteria and check if your response addresses all requirements."
)


def _instruction() -> str:
    """The owner-tuned ask; the budget follows ``_MAX_FEEDBACK_CHARS``."""
    return (
        "--- INSTRUCTION ---\n"
        "Evaluate the student's answer based on the theoretical framework above. "
        "Check whether they identified/applied metagrapheme tools correctly for their level. "
        f"Give brief constructive feedback (max {_MAX_FEEDBACK_CHARS} characters). "
        "Be supportive and specific. "
        "Return only the feedback text the student should read. "
        "No reasoning, no analysis notes, no preamble."
    )


def _build_prompt(
    user_name: str,
    level: str,
    role_name: Optional[str],
    task_question: str,
    answer: str,
) -> str:
    """Assemble the feedback prompt: theory, rules, context, ask."""
    return (
        f"{THEORETICAL_BASE}\n\n"
        f"{_OUTPUT_RULES}"
        f"Student: {user_name}\nLevel: {level}\n"
        f"Selected role: {role_name or 'none'}\n\n"
        f"--- TASK QUESTION ---\n{task_question}\n\n"
        f"--- STUDENT ANSWER ---\n{answer}\n\n"
        f"{_instruction()}"
    )


def _task_hint(task_question: str) -> str:
    """Pick the demo banner's hint by the task marker in the question."""
    for marker, hint in _TASK_HINTS:
        if marker in task_question:
            return hint
    return _TASK_HINT_DEFAULT

# Three wire protocols, not one SDK per vendor: "openai" covers every
# OpenAI-compatible endpoint (OpenAI, Mistral, OpenRouter, Cerebras,
# DeepSeek, local servers); "anthropic" answers the vendor's own
# protocol (x-api-key, /v1/messages, content blocks); "mistral"
# answers Mistral's native Conversations API (inputs/outputs) — the
# owner's key answers there while chat/completions 429s.
_ANTHROPIC_VERSION = "2023-06-01"
# Endpoints owners paste from provider docs; the API base is recovered
# from any of them (issue #15: a Mistral /v1/conversations URL shipped
# in .env and every attempt 404'd behind it).
_URL_SUFFIXES = ("/chat/completions", "/completions", "/messages",
                 "/conversations")


class _Attempt(NamedTuple):
    """One labelled wire call: endpoint, headers, payload, timeout."""

    label: str
    url: str
    headers: dict
    payload: dict
    timeout: int


def _api_base(llm_url: str) -> str:
    """Return the provider's API base from any docs-pasted endpoint URL."""
    base = llm_url.rstrip("/")
    for suffix in _URL_SUFFIXES:
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    return base


def _bearer(api_key: str) -> dict:
    """Bearer-auth headers shared by the OpenAI-compatible protocols."""
    return {"Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"}


def _openai_attempts(base: str, model: str, api_key: str,
                     prompt: str) -> list[_Attempt]:
    """The OpenAI-compatible shape, plus the legacy /completions probe."""
    bearer = _bearer(api_key)
    return [
        _Attempt("chat", base + "/chat/completions", bearer,
                 {"model": model,
                  "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": _MAX_OUTPUT_TOKENS},
                 _PRIMARY_TIMEOUT),
        _Attempt("legacy", base + "/completions", bearer,
                 {"prompt": prompt, "max_tokens": _MAX_OUTPUT_TOKENS},
                 _FALLBACK_TIMEOUT),
    ]


def _anthropic_attempts(base: str, model: str, api_key: str,
                        prompt: str) -> list[_Attempt]:
    """Anthropic's own protocol: x-api-key auth, /v1/messages."""
    return [
        _Attempt("anthropic", base + "/messages",
                 {"x-api-key": api_key,
                  "anthropic-version": _ANTHROPIC_VERSION,
                  "Content-Type": "application/json"},
                 {"model": model,
                  "max_tokens": _MAX_OUTPUT_TOKENS,
                  "messages": [{"role": "user", "content": prompt}]},
                 _PRIMARY_TIMEOUT),
    ]


def _mistral_attempts(base: str, model: str, api_key: str,
                      prompt: str) -> list[_Attempt]:
    """Mistral's native Conversations API: inputs in, outputs out."""
    return [
        _Attempt("mistral", base + "/conversations", _bearer(api_key),
                 {"model": model,
                  "inputs": [{"role": "user", "content": prompt}],
                  "tools": [],
                  "completion_args": {"max_tokens": _MAX_OUTPUT_TOKENS},
                  "instructions": ""},
                 _PRIMARY_TIMEOUT),
    ]


# Provider → attempt builder; unlisted providers speak the OpenAI shape.
_ATTEMPTS_BY_PROVIDER = {"anthropic": _anthropic_attempts,
                         "mistral": _mistral_attempts}


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


def _openai_text(result: dict) -> Optional[str]:
    """The OpenAI-compatible answer: choices[0]'s content, legacy text
    field as fallback — the ``reasoning`` field is never surfaced."""
    choices = result.get("choices")
    if not choices:
        return None
    choice = choices[0]
    msg = choice.get("message") or {}
    text = choice.get("text") or msg.get("content") or ""
    if text.strip():
        return html_mod.unescape(text.strip())
    return None


# Provider → text extractor; unlisted providers speak the OpenAI shape.
_TEXT_BY_PROVIDER = {"anthropic": _anthropic_text, "mistral": _mistral_text}


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
    return _TEXT_BY_PROVIDER.get(provider, _openai_text)(result)


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
    prompt = _build_prompt(user_name, level, role_name, task_question,
                           truncated_answer)

    llm_url = os.getenv("LLM_URL", "https://vedai.by/api/v1")
    llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()

    base = _api_base(llm_url)
    build_attempts = _ATTEMPTS_BY_PROVIDER.get(provider, _openai_attempts)
    attempts = build_attempts(base, llm_model, api_key, prompt)

    errors: list[str] = []
    for attempt in attempts:
        try:
            resp = requests.post(attempt.url, headers=attempt.headers,
                                 json=attempt.payload, timeout=attempt.timeout)
            logger.debug("LLM %s at %s -> status=%d",
                         attempt.label, attempt.url, resp.status_code)

            if resp.status_code != 200:
                errors.append(f"{attempt.label}: HTTP {resp.status_code}")
                continue

            result = resp.json()
            text = _response_text(result, provider)
            if text:
                return text, False

            errors.append(f"{attempt.label}: no student-facing text in response")
            logger.debug(
                "LLM %s response keys=%s preview=%s",
                attempt.label,
                list(result.keys()),
                str(result)[:300],
            )

        except Exception as exc:
            errors.append(f"{attempt.label}: {exc}")
            logger.debug("LLM %s error: %s", attempt.label, exc)

    safe = truncated_answer[:200]
    detail = errors[0] if errors else "unknown"
    logger.debug("LLM fell back to demo, errors=%s", errors)

    if role_name is not None:
        fallback_text = get_roleplay_fallback(level, role_name, detail)
    else:
        fallback_text = (
            f"**\U0001f916 LLM Feedback (API failed \u2014 {detail}):** "
            f'You wrote: "{safe}". {_task_hint(task_question)}'
        )
    return html_mod.unescape(fallback_text), True
