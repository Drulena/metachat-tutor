"""Task message variants for the MetaChat Tutor scenario.

Split out of the former single-file ``tutor/scenarios.py``; see
:mod:`tutor.scenarios`.
"""

from __future__ import annotations

from typing import Any

TASK_VARIANTS: dict[str, Any] = {
    "pretest_messages": [
        {
            "message1": "'Your idea is wrong. Fix it.'",
            "message2": "'I see your point, but have you considered... 🤔'",
            "message3": "'THIS IS TERRIBLE!!!'",
        }
    ],
    "analysis_task_1": {
        "beginner": [
            {
                "context": "A beginner student's first peer review attempt",
                "message": "'This essay has many problems. You need to work harder.'",
                "hint": "Even simple feedback can be softened with the right emoji.",
            }
        ],
        "intermediate": [
            {
                "context": "A discussion about a project proposal",
                "message": "'Your data here is outdated and unreliable. You need to redo the entire analysis.'",
                "hint": "Consider emojis that convey neutrality and thoughtfulness.",
            }
        ],
        "advanced": [
            {
                "context": "Feedback on a complex research proposal",
                "message": "'Your theoretical framework is problematic. The methodology doesn't align with your research questions.'",
                "hint": "Strategic emoji placement matters — consider where and how many to use.",
            }
        ],
    },
    "analysis_task_2": {
        "beginner": [
            {
                "message": "'WRONG!!!'",
                "hint": "Metagraphemic means in online discussions are non-standard graphic, typographic, and punctuation techniques used to enhance, alter, or clarify the emotional tone, emphasis, or meaning of a text-based message.",
            }
        ],
        "intermediate": [
            {
                "message": "'tHaT's NoT hOw iT wOrKs!!!'",
                "hint": "Metagraphemic means in online discussions are non-standard graphic, typographic, and punctuation techniques used to enhance, alter, or clarify the emotional tone, emphasis, or meaning of a text-based message.",
            }
        ],
        "advanced": [
            {
                "message": "'Your idea is BRILLIANT... if you're living in 1995 🙄 #facepalm'",
                "hint": "Metagraphemic means in online discussions are non-standard graphic, typographic, and punctuation techniques used to enhance, alter, or clarify the emotional tone, emphasis, or meaning of a text-based message.",
            }
        ],
    },
    "role_mediator": [
        {
            "scenario": "Remote Work vs. Office Work",
            "context": "A professional online forum",
            "aggressor": "Alex",
            "quote": "'Working from home is just an excuse for being lazy! #offtopic'",
            "task": "Write a mediator response that de-escalates the conflict.",
        }
    ],
    "role_logical": [
        {
            "scenario": "Language learning methods",
            "context": "A debate in a linguistics forum",
            "user1": "Sam: 'Grammar is useless.'",
            "user2": "Taylor: 'But without grammar, you'll sound incomprehensible.'",
            "task": "Highlight logical gaps in the arguments.",
        }
    ],
    "role_idea_generator": [
        {
            "scenario": "University language exchange program",
            "context": "Students discussing in a group chat how to improve the exchange",
            "quote": "Maybe we could just meet once a week and talk?",
            "task": "Generate innovative ideas to make the exchange more engaging.",
        }
    ],
    "role_researcher": [
        {
            "scenario": "Politeness in different cultures",
            "context": "Debate about direct criticism in a personal blog.",
            "cultural_claim": "In my culture, being direct is always respectful.",
            "comment": "We should just say what we think.",
            "task": "Ask questions to understand the cultural context.",
        }
    ],
    "role_interpreter": [
        {
            "scenario": "Japanese indirectness may seem evasive",
            "context": "International student forum",
            "user1": "Japanese student: 'This requires more careful consideration.'",
            "user2": "German student: 'Why? Be specific.'",
            "task": "Explain Japanese communication style to other commentators to avoid miscomprehension.",
        }
    ],
    "role_advocate": [
        {
            "scenario": "Team project evaluation",
            "context": "Criticism in a group chat",
            "user1": "Alex is being criticized for not contributing",
            "critic": "Sarah: 'Alex is clearly not committed to this project.'",
            "task": "Defend Alex by considering possible circumstances.",
        }
    ],
    "role_judge": [
        {
            "scenario": "Debate about remote work",
            "context": "Discussion on a social media platform",
            "discussion": "Team A: full remote. Team B: office-only.",
            "points": "Both sides present conflicting studies.",
            "quote": "The evidence is completely contradictory. Who's right?",
            "task": "Imagine potential arguments of both sides. Objectively evaluate them.",
        }
    ],
    "role_peacemaker": [
        {
            "scenario": "Argument about grading",
            "context": "Students fighting about group project grade in a chat",
            "conflict": "Personal accusations escalating.",
            "user1": "Anna: 'This is your fault. You never listen!'",
            "user2": "Peter: 'Maybe it's because you command TOO much?!'",
            "task": "Help the students to find a constructive way forward.",
        }
    ],
    "role_empath": [
        {
            "scenario": "A student with imposter syndrome",
            "context": "First-year student posts on a social media platform about his feelings",
            "emotional_state": "Vulnerability and anxiety",
            "user1": "Graduate student: You just need to study more. Stop complaining.",
            "task": "Provide genuine emotional support without immediately offering advice.",
        }
    ],
}
