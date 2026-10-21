"""Shared scenario data: bot name, levels, the theoretical base, role
state keys and roleplay error templates.

Split out of the former single-file ``tutor/scenarios.py``; see
:mod:`tutor.scenarios`.
"""

from __future__ import annotations

from typing import Any

BOT_NAME: str = 'MetaChat Tutor'
WELCOME_MESSAGE: str = '🔬 **WELCOME TO METACHAT TUTOR - RESEARCH EDITION**\n\n⌨️**Type down your name and group (e.g., Stacy V. 101 bsufl):**'

LEVELS: dict[str, str] = {
    "beginner": "Beginner (I rarely participate in online discussions)",
    "intermediate": "Intermediate (I read regularly, sometimes post)",
    "advanced": "Advanced (I actively participate in professional discussions)",
}

THEORETICAL_BASE: str = "\nTHEORETICAL FRAMEWORK FOR EVALUATING STUDENT RESPONSES:\n\n1. METAGRAPHEME MEANS OF CRITICISM MITIGATION:\n   - Emoji shock absorbers at the end of the message: 🙂, 😊, 🤔, 😅\n   - Parentheses and ellipsis to simulate voice lowering/pause: (just my impression though)...\n   - Avoiding ALL CAPS and multiple exclamation marks!!!\n\n2. METAGRAPHEME MEANS OF INTENSIFICATION AND SARCASM:\n   - ALL CAPS = shouting\n   - Alternating caps (tHaT's NoT) = mockery\n   - Multiple punctuation marks: !!!, ??! – emotional hyperbolization\n   - Letter duplication: Noooooo – emphasis\n   - Sarcasm emojis: 👏, 🙄, 😒, 🤦\n\n3. MEANS OF STRUCTURAL AND LOGICAL EMPHASIS:\n   - Bold font, italics, underlining – emphasis on key thesis\n   - Quoting (@Name) – precise addressing of criticism\n   - Hashtags (#offtopic, #strawman) – markers of logical violations\n\n4. COMMUNICATIVE ROLES (constructive):\n   - Logician: analysis, clarifying questions\n   - Idea Generator: creativity, new ideas\n   - Researcher: clarifying cultural context\n   - Interpreter: translating cultural codes\n   - Advocate: defending a participant/idea\n   - Judge: evaluating arguments, drawing conclusions\n   - Peacemaker: proposing compromises\n    - Empath: providing support, reducing tension\n"


# Pre-computed list of role-play state keys for iteration.
ROLE_STATE_KEYS: list[str] = [
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

# Role-play error templates by skill level and role.
# Used as fallback when LLM request fails.
ROLEPLAY_ERROR_TEMPLATES: dict[str, dict[str, str]] = {
    "beginner": {
        "role_mediator": "Nice try! As a Mediator, remember to acknowledge the other person's feelings first, then gently suggest a path forward. A calm emoji like 🤝 or 🕊️ helps a lot!",
        "role_logical": "Good effort! When acting as a Logical Expert, try pointing out ONE clear contradiction using **bold** text, then ask a friendly question like 'Could you clarify what you mean?' 🤔",
        "role_idea_generator": "Creative start! As an Idea Generator, try proposing at least TWO different ideas and use a fun emoji like 💡 or 🚀 to show your enthusiasm!",
        "role_researcher": "Great curiosity! As a Researcher, ask ONE specific question about the other person's culture or background. A thoughtful emoji like 🤔 or 📚 shows you're interested!",
        "role_interpreter": "Well done! As an Interpreter, explain what the person probably meant and how it might have been misunderstood. A bridging emoji like 🤝 or 🌉 ties it together!",
        "role_advocate": "Good defense! As an Advocate, try giving at least TWO reasons why the person deserves a fair chance. A protective emoji like 🛡️ or 💪 shows support!",
        "role_judge": "Fair assessment! As a Judge, try to find something valid in BOTH sides of the argument and use **bold** for the strongest point. A balanced emoji like ⚖️ works well!",
        "role_peacemaker": "Kind approach! As a Peacemaker, acknowledge BOTH people's concerns and suggest a simple compromise. A peace emoji like 🕊️ or 🤝 brings warmth!",
        "role_empath": "Compassionate! As an Empath, try to VALIDATE the person's feelings first — just say 'I hear you' or 'That sounds hard'. A warm emoji like ❤️ or 🤗 means a lot!",
    },
    "intermediate": {
        "role_mediator": "Solid attempt! As a Mediator, try using @mention to directly address the aggressor, acknowledge their concern, then redirect to a constructive solution. 🤝",
        "role_logical": "Good analysis! As a Logical Expert, identify the SPECIFIC logical flaw (overgeneralization, false dilemma, etc.) and back it up with a clarifying question. 🤔",
        "role_idea_generator": "Nice creativity! As an Idea Generator, develop your ideas with more detail — explain WHY each idea could work. Use **bold** for your best concept. 💡",
        "role_researcher": "Good inquiry! As a Researcher, ask TWO specific questions about cultural practices and try to connect them to the discussion. 📚",
        "role_interpreter": "Strong bridging! As an Interpreter, explain the cultural difference clearly — what was INTENDED vs. how it was MISINTERPRETED. Use **bold** for the key phrase. 🌉",
        "role_advocate": "Fair defense! As an Advocate, use @mention to acknowledge the critic FIRST, then provide TWO concrete reasons for fair consideration. 🛡️",
        "role_judge": "Balanced view! As a Judge, use **bold** to highlight the STRONGEST point from each side and draw a nuanced conclusion. ⚖️",
        "role_peacemaker": "Constructive! As a Peacemaker, address BOTH parties with @mention, identify the valid concern behind EACH position, and propose a specific compromise. 🕊️",
        "role_empath": "Empathetic! As an Empath, VALIDATE their feelings explicitly ('I understand that must be hard') and offer support WITHOUT giving advice. ❤️",
    },
    "advanced": {
        "role_mediator": "Effective de-escalation! As a Mediator, demonstrate that you understand the aggressor's UNDERLYING concern (not just their words), then propose a solution that preserves everyone's dignity. 🤝",
        "role_logical": "Sharp analysis! As a Logical Expert, categorize the fallacy precisely (ad hominem, straw man, false equivalence, etc.), then reframe the argument constructively. 🤔",
        "role_idea_generator": "Innovative thinking! As an Idea Generator, propose ideas that combine MULTIPLE metagrapheme tools (emoji + bold + structure) and explain the reasoning behind each. 💡",
        "role_researcher": "Thorough research! As a Researcher, demonstrate awareness of cultural NUANCES — ask questions that reveal assumptions, not just facts. Use @mention strategically. 📚",
        "role_interpreter": "Nuanced interpretation! As an Interpreter, explain the cultural FRAMEWORK behind the communication style, not just the surface meaning. Show how both parties can adapt. 🌉",
        "role_advocate": "Strategic defense! As an Advocate, use @mention to acknowledge the critic's point, then build a case using EVIDENCE-based reasoning and systemic perspective. 🛡️",
        "role_judge": "Incisive evaluation! As a Judge, identify the underlying ASSUMPTIONS in each argument, assess their validity with **bold** emphasis, and offer a synthesis. ⚖️",
        "role_peacemaker": "Diplomatic solution! As a Peacemaker, demonstrate that you understand the EMOTIONAL stakes for both parties, then propose a compromise that addresses core needs, not just positions. 🕊️",
        "role_empath": "Deep empathy! As an Empath, VALIDATE their experience with specificity ('It makes sense you'd feel that way because...'), mirror their emotional state, and hold space without rushing to fix. ❤️",
    },
}

ROLEPLAY_ERROR_DEFAULT: str = "Review the role criteria and check if your response addresses all requirements. Try again with more detail!"
