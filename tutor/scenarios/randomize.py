"""Task randomization for the MetaChat Tutor scenario.

Split out of the former single-file ``tutor/scenarios.py``; see
:mod:`tutor.scenarios`.
"""

from __future__ import annotations

import copy
import random

from typing import Any

from .common import ROLE_STATE_KEYS
from .tasks import TASK_VARIANTS

def randomize_scenario(
    scenario: dict[str, Any],
    level: str = "intermediate",
) -> dict[str, Any]:
    """Return a deep copy of *scenario* with random variant data injected.

    The function performs three passes:

    1. **Pre-test / Post-test** -- randomly picks one set of alternate
       messages from ``TASK_VARIANTS["pretest_messages"]`` and substitutes
       them into the ``pretest`` and ``posttest`` states.
    2. **Analysis tasks** -- for each level and task number, picks one
       variant from ``TASK_VARIANTS["analysis_task_{1,2}"][level]`` and
       fills in the ``{placeholder}`` tokens in the corresponding state
       message.
    3. **Role-play tasks** -- for each role, picks one variant from
       ``TASK_VARIANTS[role_key]`` and fills in ``{placeholder}`` tokens.

    The original *scenario* dict is **never** modified.

    Args:
        scenario: The base scenario dict (as defined in ``SCENARIO``).
        level: One of ``"beginner"``, ``"intermediate"``, ``"advanced"``.
            Accepted but not currently used for conditional branching; all
            levels are randomized regardless.

    Returns:
        A new dict with randomized content.
    """
    scenario_copy = copy.deepcopy(scenario)

    # --- 1. Pre-test / Post-test messages ---
    pretest_variants = TASK_VARIANTS.get("pretest_messages", [])
    if pretest_variants:
        pretest = random.choice(pretest_variants)
        for state_name in ("pretest", "posttest"):
            if state_name in scenario_copy["states"]:
                msg = scenario_copy["states"][state_name]["message"]
                msg = msg.replace("'Your idea is wrong. Fix it.'", pretest["message1"])
                msg = msg.replace(
                    "'I see your point, but have you considered... 🤔'",
                    pretest["message2"],
                )
                msg = msg.replace("'THIS IS TERRIBLE!!!'", pretest["message3"])
                scenario_copy["states"][state_name]["message"] = msg

    # --- 2. Analysis tasks (all levels) ---
    for lvl in ("beginner", "intermediate", "advanced"):
        for task_num in (1, 2):
            task_state = f"analysis_task_{task_num}_{lvl}"
            variants = TASK_VARIANTS.get(f"analysis_task_{task_num}", {}).get(lvl, [])
            if variants and task_state in scenario_copy["states"]:
                variant = random.choice(variants)
                msg = scenario_copy["states"][task_state]["message"]
                for key, value in variant.items():
                    msg = msg.replace("{" + key + "}", str(value))
                scenario_copy["states"][task_state]["message"] = msg

    # --- 3. Role-play tasks ---
    for role_key in ROLE_STATE_KEYS:
        role_variants = TASK_VARIANTS.get(role_key, [])
        if role_variants and role_key in scenario_copy["states"]:
            variant = random.choice(role_variants)
            msg = scenario_copy["states"][role_key]["message"]
            for key, value in variant.items():
                placeholder = "{" + key + "}"
                if placeholder in msg:
                    msg = msg.replace(placeholder, str(value))
            scenario_copy["states"][role_key]["message"] = msg

    return scenario_copy
