import copy
import json
import os
import random
import re
from datetime import datetime

import markdown as md_lib
from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .data import LEVELS, SCENARIO, TASK_VARIANTS, THEORETICAL_BASE


def randomize_scenario(scenario, level="intermediate"):
    scenario_copy = copy.deepcopy(scenario)

    if "pretest_messages" in TASK_VARIANTS and TASK_VARIANTS["pretest_messages"]:
        pretest = random.choice(TASK_VARIANTS["pretest_messages"])
        for state_name in ["pretest", "posttest"]:
            if state_name in scenario_copy["states"]:
                msg = scenario_copy["states"][state_name]["message"]
                msg = msg.replace("'Your idea is wrong. Fix it.'", pretest["message1"])
                msg = msg.replace(
                    "'I see your point, but have you considered... 🤔'",
                    pretest["message2"],
                )
                msg = msg.replace("'THIS IS TERRIBLE!!!'", pretest["message3"])
                scenario_copy["states"][state_name]["message"] = msg

    for lvl in ["beginner", "intermediate", "advanced"]:
        for task_num in [1, 2]:
            task_state = f"analysis_task_{task_num}_{lvl}"
            if lvl in TASK_VARIANTS.get(f"analysis_task_{task_num}", {}):
                variants = TASK_VARIANTS[f"analysis_task_{task_num}"][lvl]
                if variants:
                    variant = random.choice(variants)
                    if task_state in scenario_copy["states"]:
                        msg = scenario_copy["states"][task_state]["message"]
                        for key, value in variant.items():
                            msg = msg.replace("{" + key + "}", str(value))
                        scenario_copy["states"][task_state]["message"] = msg

    role_keys = [
        "role_mediator",
        "role_logical",
        "role_idea_generator",
        "role_researcher",
        "role_interpreter",
        "role_advocate",
        "role_judge",
        "role_peacemaker",
        "role_empath",
    ]

    for role_key in role_keys:
        if role_key in TASK_VARIANTS and TASK_VARIANTS[role_key]:
            variant = random.choice(TASK_VARIANTS[role_key])
            if role_key in scenario_copy["states"]:
                msg = scenario_copy["states"][role_key]["message"]
                for key, value in variant.items():
                    placeholder = "{" + key + "}"
                    if placeholder in msg:
                        msg = msg.replace(placeholder, str(value))
                scenario_copy["states"][role_key]["message"] = msg

    return scenario_copy


def get_llm_feedback(user_answer, role_name, user_name, level, task_question=None):
    if task_question is None:
        task_question = "(task context unknown)"

    api_key = os.getenv("LLM_API_KEY")
    if api_key is None:
        return (
            f'**🤖 LLM Feedback (API not configured):** '
            f'Set LLM_API_KEY in .env to enable AI feedback.'
        )

    import requests

    prompt = (
        f"{THEORETICAL_BASE}\n\n"
        "Always use English to respond.\n"
        "When discussing emojis, use the actual Unicode emoji character (e.g., 🙂 not the word 'smiley').\n"
        f"Student: {user_name}\nLevel: {level}\nSelected role: {role_name or 'none'}\n\n"
        f"--- TASK QUESTION ---\n{task_question}\n\n"
        f"--- STUDENT ANSWER ---\n{user_answer}\n\n"
        f"--- INSTRUCTION ---\n"
        f"Evaluate the student's answer based on the theoretical framework above. "
        f"Check whether they identified/applied metagraheme tools correctly for their level. "
        f"Give brief constructive feedback (max 500 characters). "
        f"Be supportive and specific."
    )

    llm_url = os.getenv("LLM_URL", "https://vedai.by/api/v1")
    llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    base = llm_url.rstrip("/")
    for suffix in ["/chat/completions", "/completions"]:
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
        ),
        ("legacy", legacy_url, {"prompt": prompt, "max_tokens": 150}),
    ]

    errors = []
    for label, url, payload in attempts:
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            result = resp.json()
            print(f"LLM DEBUG: {label} at {url} → status={resp.status_code}")
            if result.get("choices") and len(result["choices"]) > 0:
                choice = result["choices"][0]
                text = (
                    choice.get("text")
                    or choice.get("message", {}).get("content")
                    or ""
                )
                if text.strip():
                    return text.strip()
            errors.append(f"{label}: {resp.status_code} no valid choices")
            print(f"LLM DEBUG: {label} response: {result}")
        except Exception as e:
            errors.append(f"{label}: {e}")
            print(f"LLM DEBUG: {label} error: {e}")

    safe = user_answer[:200]
    if "TASK 1" in task_question:
        hint = "Adding a friendly emoji like 🙂 or 😊 can make criticism feel more supportive."
    elif "TASK 2" in task_question:
        hint = "Combining multiple metagraheme techniques creates stronger effects."
    else:
        hint = "Review the criteria and check if your response addresses all requirements."
    return (
        f'**🤖 LLM Feedback (API failed — {errors[0] if errors else "unknown"}):** '
        f'You wrote: "{safe}". {hint}'
    )


def _init_session(request):
    if "current_state" not in request.session:
        request.session["chat_history"] = []
        request.session["current_state"] = "start"
        request.session["user_data"] = {
            "user_name": None,
            "level": None,
            "pretest_scores": None,
            "posttest_scores": None,
            "current_role": None,
            "current_role_variant": None,
        }
        request.session["scenario"] = randomize_scenario(SCENARIO)
        request.session["session_id"] = datetime.now().strftime("%Y%m%d_%H%M%S")
        request.session.modified = True


def _get_current_message(request):
    state = request.session["scenario"]["states"][request.session["current_state"]]
    message = state["message"]

    task_context = None
    cs = request.session["current_state"]
    if "analysis_feedback_1" in cs:
        task_state = cs.replace("feedback_1", "task_1")
        if task_state in request.session["scenario"]["states"]:
            task_context = request.session["scenario"]["states"][task_state][
                "message"
            ]
    elif "analysis_feedback_2" in cs:
        task_state = cs.replace("feedback_2", "task_2")
        if task_state in request.session["scenario"]["states"]:
            task_context = request.session["scenario"]["states"][task_state][
                "message"
            ]
    elif "roleplay_feedback" in cs:
        role_slug = cs.replace("roleplay_feedback_", "")
        task_state = f"role_{role_slug}"
        if task_state in request.session["scenario"]["states"]:
            task_context = request.session["scenario"]["states"][task_state]["message"]

    user_answer = request.session["chat_history"][-1]["content"]

    user_data = request.session["user_data"]
    if task_context and user_data["user_name"] and user_data["level"]:
        llm_out = get_llm_feedback(
            user_name=user_data["user_name"],
            level=user_data["level"],
            role_name=user_data["current_role"],
            user_answer=user_answer,
            task_question=task_context,
        )
        if llm_out:
            for marker in ["\n\n**📋 Model answer:**", "\n\n▶️"]:
                parts = message.split(marker, 1)
                if len(parts) == 2:
                    header = parts[0].split("\n\n", 1)[0]
                    message = header + "\n\n" + llm_out + marker + parts[1]
                    break
            else:
                message = message.split("\n\n", 1)[0] + "\n\n" + llm_out

    if user_data["user_name"]:
        message = message.replace("{user_name}", user_data["user_name"])

    if "{level}" in message and user_data["level"]:
        message = message.replace("{level}", user_data["level"])

    return message


def _process_input(request, user_input):
    current_state_obj = request.session["scenario"]["states"][
        request.session["current_state"]
    ]
    user_data = request.session["user_data"]

    if user_input.lower() == "back":
        level = user_data.get("level", "beginner")
        if "analysis_task_" in request.session["current_state"]:
            request.session["current_state"] = f"analysis_intro_{level}"
        elif "analysis_intro_" in request.session["current_state"]:
            request.session["current_state"] = f"after_registration_{level}"
        elif request.session["current_state"] == "role_menu":
            request.session["current_state"] = "roleplay_intro"
        elif request.session["current_state"] == "roleplay_intro":
            request.session["current_state"] = f"after_registration_{level}"
        elif "roleplay_feedback" in request.session["current_state"]:
            request.session["current_state"] = "role_menu"
        else:
            request.session["current_state"] = f"after_registration_{level}"
        request.session["chat_history"].append(
            {
                "role": "assistant",
                "content": _get_current_message(request),
                "state": request.session["current_state"],
                "timestamp": datetime.now().isoformat(),
            }
        )
        request.session.modified = True
        return

    request.session["chat_history"].append(
        {
            "role": "user",
            "content": user_input,
            "state": request.session["current_state"],
            "timestamp": datetime.now().isoformat(),
        }
    )

    if "validation" in current_state_obj:
        if not re.match(current_state_obj["validation"], user_input):
            messages.warning(
                request, "⚠️ Please enter the data in the correct format. Try again."
            )
            request.session.modified = True
            return

    if request.session["current_state"] == "start":
        user_data["user_name"] = (
            user_input.split()[0] if user_input.split() else user_input
        )
        request.session["current_state"] = "pretest"
        request.session.modified = True
        request.session["chat_history"].append(
            {
                "role": "assistant",
                "content": _get_current_message(request),
                "state": request.session["current_state"],
                "timestamp": datetime.now().isoformat(),
            }
        )
        request.session.modified = True
        return

    if request.session["current_state"] == "pretest":
        try:
            scores = list(map(int, user_input.split()))
            if len(scores) == 3 and all(1 <= s <= 5 for s in scores):
                user_data["pretest_scores"] = scores
                request.session["current_state"] = "level_assessment"
                request.session.modified = True
                request.session["chat_history"].append(
                    {
                        "role": "assistant",
                        "content": _get_current_message(request),
                        "state": request.session["current_state"],
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                request.session.modified = True
                return
            else:
                messages.warning(
                    request,
                    "⚠️ Please enter three numbers between 1 and 5, separated by spaces.",
                )
                request.session.modified = True
                return
        except Exception:
            messages.warning(
                request,
                "⚠️ Please enter three numbers between 1 and 5, separated by spaces.",
            )
            request.session.modified = True
            return

    if request.session["current_state"] == "level_assessment":
        if user_input in ["1", "2", "3"]:
            level_map = {"1": "beginner", "2": "intermediate", "3": "advanced"}
            user_data["level"] = level_map[user_input]
            request.session["current_state"] = (
                f"after_registration_{level_map[user_input]}"
            )
            request.session.modified = True
            request.session["chat_history"].append(
                {
                    "role": "assistant",
                    "content": _get_current_message(request),
                    "state": request.session["current_state"],
                    "timestamp": datetime.now().isoformat(),
                }
            )
            request.session.modified = True
            return
        else:
            messages.warning(request, "⚠️ Please enter 1, 2, or 3.")
            request.session.modified = True
            return

    if request.session["current_state"] == "posttest":
        try:
            scores = list(map(int, user_input.split()))
            if len(scores) == 3 and all(1 <= s <= 5 for s in scores):
                user_data["posttest_scores"] = scores
                request.session["current_state"] = "data_collection"
                request.session.modified = True
                request.session["chat_history"].append(
                    {
                        "role": "assistant",
                        "content": _get_current_message(request),
                        "state": request.session["current_state"],
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                request.session.modified = True
                return
            else:
                messages.warning(
                    request,
                    "⚠️ Please enter three numbers between 1 and 5, separated by spaces.",
                )
                request.session.modified = True
                return
        except Exception:
            messages.warning(
                request,
                "⚠️ Please enter three numbers between 1 and 5, separated by spaces.",
            )
            request.session.modified = True
            return

    if "roleplay_feedback" in request.session["current_state"]:
        cmd = user_input.lower()
        current_role = user_data.get("current_role", "role_mediator")
        if cmd == "revise":
            request.session["current_state"] = current_role
        elif cmd == "next":
            request.session["current_state"] = "role_menu"
        elif cmd == "back":
            request.session["current_state"] = "role_menu"
        else:
            messages.warning(
                request, "⚠️ Please type 'revise', 'next', or 'back'."
            )
            request.session.modified = True
            return
        request.session["chat_history"].append(
            {
                "role": "assistant",
                "content": _get_current_message(request),
                "state": request.session["current_state"],
                "timestamp": datetime.now().isoformat(),
            }
        )
        request.session.modified = True
        return

    if "analysis_feedback_" in request.session["current_state"]:
        if user_input.lower() == "next":
            if "feedback_1" in request.session["current_state"]:
                new_state = request.session["current_state"].replace(
                    "feedback_1", "task_2"
                )
                request.session["current_state"] = new_state
            elif "feedback_2" in request.session["current_state"]:
                request.session["current_state"] = "roleplay_intro"
            request.session["chat_history"].append(
                {
                    "role": "assistant",
                    "content": _get_current_message(request),
                    "state": request.session["current_state"],
                    "timestamp": datetime.now().isoformat(),
                }
            )
            request.session.modified = True
            return
        elif user_input.lower() == "back":
            level = user_data.get("level", "beginner")
            request.session["current_state"] = f"analysis_intro_{level}"
            request.session["chat_history"].append(
                {
                    "role": "assistant",
                    "content": _get_current_message(request),
                    "state": request.session["current_state"],
                    "timestamp": datetime.now().isoformat(),
                }
            )
            request.session.modified = True
            return
        else:
            messages.warning(
                request, "⚠️ Please type 'next' to continue or 'back' to return."
            )
            request.session.modified = True
            return

    if "after_registration_" in request.session["current_state"]:
        if user_input in ["1", "2"]:
            if user_input == "1":
                level = user_data.get("level", "beginner")
                request.session["current_state"] = f"analysis_intro_{level}"
            else:
                request.session["current_state"] = "roleplay_intro"
            request.session["chat_history"].append(
                {
                    "role": "assistant",
                    "content": _get_current_message(request),
                    "state": request.session["current_state"],
                    "timestamp": datetime.now().isoformat(),
                }
            )
            request.session.modified = True
            return
        elif user_input.lower() == "back":
            request.session["current_state"] = "level_assessment"
            request.session["chat_history"].append(
                {
                    "role": "assistant",
                    "content": _get_current_message(request),
                    "state": request.session["current_state"],
                    "timestamp": datetime.now().isoformat(),
                }
            )
            request.session.modified = True
            return
        else:
            messages.warning(
                request, "⚠️ Please type 1 (ANALYSIS) or 2 (ROLE-PLAY)."
            )
            request.session.modified = True
            return

    if request.session["current_state"] == "role_menu":
        print(
            f"DEBUG role_menu: input='{user_input}', lower='{user_input.lower()}'"
        )
        if user_input.lower() == "finish":
            request.session["current_state"] = "reflection"
        elif user_input.lower() == "back":
            request.session["current_state"] = "roleplay_intro"
        elif user_input in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]:
            role_map = {
                "1": "role_mediator",
                "2": "role_logical",
                "3": "role_idea_generator",
                "4": "role_researcher",
                "5": "role_interpreter",
                "6": "role_advocate",
                "7": "role_judge",
                "8": "role_peacemaker",
                "9": "role_empath",
            }
            user_data["current_role"] = role_map[user_input]
            request.session["current_state"] = role_map[user_input]
        else:
            messages.warning(
                request, "⚠️ Please type a number from 1 to 9, or 'finish'."
            )
            request.session.modified = True
            return
        request.session["chat_history"].append(
            {
                "role": "assistant",
                "content": _get_current_message(request),
                "state": request.session["current_state"],
                "timestamp": datetime.now().isoformat(),
            }
        )
        request.session.modified = True
        return

    if request.session["current_state"] == "roleplay_intro":
        if user_input.lower() == "continue":
            request.session["current_state"] = "role_menu"
        elif user_input.lower() == "back":
            level = user_data.get("level", "beginner")
            request.session["current_state"] = f"after_registration_{level}"
        else:
            messages.warning(
                request,
                "⚠️ Please type 'continue' to proceed or 'back' to return.",
            )
            request.session.modified = True
            return
        request.session["chat_history"].append(
            {
                "role": "assistant",
                "content": _get_current_message(request),
                "state": request.session["current_state"],
                "timestamp": datetime.now().isoformat(),
            }
        )
        request.session.modified = True
        return

    if "analysis_intro_" in request.session["current_state"]:
        if user_input.lower() == "yes":
            current = request.session["current_state"]
            task_state = current.replace("intro", "task_1")
            request.session["current_state"] = task_state
            request.session["chat_history"].append(
                {
                    "role": "assistant",
                    "content": _get_current_message(request),
                    "state": request.session["current_state"],
                    "timestamp": datetime.now().isoformat(),
                }
            )
            request.session.modified = True
            return

    if "analysis_task_" in request.session["current_state"]:
        feedback_state = request.session["current_state"].replace("task", "feedback")
        request.session["current_state"] = feedback_state
        request.session["chat_history"].append(
            {
                "role": "assistant",
                "content": _get_current_message(request),
                "state": request.session["current_state"],
                "timestamp": datetime.now().isoformat(),
            }
        )
        request.session.modified = True
        return

    if request.session["current_state"] == "data_collection":
        if user_input.lower() == "exit":
            request.session["current_state"] = "end"
            request.session["chat_history"].append(
                {
                    "role": "assistant",
                    "content": _get_current_message(request),
                    "state": request.session["current_state"],
                    "timestamp": datetime.now().isoformat(),
                }
            )
            request.session.modified = True
            return
        else:
            messages.warning(request, "⚠️ Please type 'exit' to close the session.")
            request.session.modified = True
            return

    if "next_state" in current_state_obj:
        next_state = current_state_obj["next_state"]
        if isinstance(next_state, dict):
            if user_input in next_state:
                request.session["current_state"] = next_state[user_input]
            elif "default" in next_state:
                request.session["current_state"] = next_state["default"]
            else:
                request.session["current_state"] = "end"
        else:
            request.session["current_state"] = next_state
    elif (
        "options" in current_state_obj
        and user_input in current_state_obj["options"]
    ):
        request.session["current_state"] = current_state_obj["next_state"][
            user_input
        ]

    if request.session["current_state"] != "end":
        request.session["chat_history"].append(
            {
                "role": "assistant",
                "content": _get_current_message(request),
                "state": request.session["current_state"],
                "timestamp": datetime.now().isoformat(),
            }
        )
    request.session.modified = True


def _render_message(text):
    return md_lib.markdown(text, extensions=["nl2br"])


def chat_view(request):
    _init_session(request)

    if request.method == "POST":
        user_input = request.POST.get("user_input", "").strip()
        if user_input:
            _process_input(request, user_input)

    history = request.session.get("chat_history", [])
    user_data = request.session.get("user_data", {})
    current_state = request.session.get("current_state", "start")

    display_history = []
    for msg in history:
        entry = {"role": msg["role"]}
        if msg["role"] == "assistant":
            entry["content"] = _render_message(msg["content"])
        else:
            entry["content"] = msg["content"]
        display_history.append(entry)

    context = {
        "chat_history": display_history,
        "welcome_message": _render_message(SCENARIO["welcome_message"]),
        "is_end": current_state == "end",
        "user_data": user_data,
        "session_id": request.session.get("session_id", ""),
    }

    context["debug"] = settings.DEBUG

    return render(request, "tutor/chat.html", context)


def reset_view(request):
    request.session.flush()
    return redirect("chat")


def export_view(request):
    data = {
        "session_id": request.session.get("session_id"),
        "user_data": request.session.get("user_data"),
        "chat_history": request.session.get("chat_history"),
        "export_time": datetime.now().isoformat(),
    }
    response = JsonResponse(
        data, json_dumps_params={"indent": 2, "ensure_ascii": False}
    )
    response["Content-Disposition"] = (
        f'attachment; filename="metachat_session_{request.session.get("session_id")}.json"'
    )
    return response
