"""Scenario data and randomization logic for MetaChat Tutor.

This module contains the core scenario definitions (SCENARIO, TASK_VARIANTS,
LEVELS, THEORETICAL_BASE) and the ``randomize_scenario`` function that
substitutes random variant data into a deep copy of the scenario template.
"""

from __future__ import annotations

import copy
import random
from typing import Any

# ---------------------------------------------------------------------------
# Data constants
# ---------------------------------------------------------------------------

LEVELS: dict[str, str] = {
    "beginner": "Beginner (I rarely participate in online discussions)",
    "intermediate": "Intermediate (I read regularly, sometimes post)",
    "advanced": "Advanced (I actively participate in professional discussions)",
}

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
                "context": "A beginner student's first peer review attempt.",
                "message": "'This essay has many problems. You need to work harder.'",
                "hint": "Even simple feedback can be softened with the right emoji.",
            }
        ],
        "intermediate": [
            {
                "context": "A discussion about a project proposal.",
                "message": "'Your data here is outdated and unreliable. You need to redo the entire analysis.'",
                "hint": "Consider emojis that convey neutrality and thoughtfulness.",
            }
        ],
        "advanced": [
            {
                "context": "Feedback on a complex research proposal.",
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
            "context": "A professional online forum.",
            "aggressor": "Alex",
            "quote": "'Working from home is just an excuse for being lazy! #offtopic'",
            "task": "Write a mediator response that de-escalates the conflict.",
        }
    ],
    "role_logical": [
        {
            "scenario": "Language learning methods",
            "context": "A debate in a linguistics forum.",
            "user1": "Sam: 'Grammar is useless.'",
            "user2": "Taylor: 'But without grammar, you'll sound incomprehensible.'",
            "task": "Highlight logical gaps in the arguments.",
        }
    ],
    "role_idea_generator": [
        {
            "scenario": "University language exchange program",
            "context": "Students discussing in a group chat how to improve the exchange.",
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
            "context": "International student forum.",
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
            "context": "Students fighting about group project grade in a chat.",
            "conflict": "Personal accusations escalating.",
            "user1": "Anna: 'This is your fault. You never listen!'",
            "user2": "Peter: 'Maybe it's because you command TOO much?!'",
            "task": "Help the students to find a constructive way forward.",
        }
    ],
    "role_empath": [
        {
            "scenario": "A student with imposter syndrome",
            "context": "First-year student posts on a social media platform about his feelings.",
            "emotional_state": "Vulnerability and anxiety",
            "user1": "Graduate student: You just need to study more. Stop complaining.",
            "task": "Provide genuine emotional support without immediately offering advice.",
        }
    ],
}

SCENARIO: dict[str, Any] = {
    "bot_name": "MetaChat Tutor",
    "welcome_message": "🔬 **WELCOME TO METACHAT TUTOR - RESEARCH EDITION**\n\n📝 **Type down your name and group (e.g., Stacy V. 101 bsufl):**",
    "states": {
        "start": {
            "message": "Nice to meet you, {user_name}!\n\n▶️ **Type your name and group again to confirm:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "pretest",
        },
        "pretest": {
            "message": "**📋 PRE-TEST: Diagnostic Assessment**\n\nBefore we begin the training, please rate these three messages on a scale from 1 (destructive) to 5 (constructive):\n\n1▪️'Your idea is wrong. Fix it.'\n\n2▪️'I see your point, but have you considered... 🤔'\n\n3▪️'THIS IS TERRIBLE!!!'\n\n▶️ **Type three numbers separated by spaces (e.g., '1 5 2') and press Enter:**",
            "input_type": "text",
            "validation": "^[1-5] [1-5] [1-5]$",
            "next_state": "level_assessment",
        },
        "level_assessment": {
            "message": "**📊 Self-Assessment: Your Experience Level**\n\nPlease evaluate your experience with online discussions in English:\n\n▫️1▫️ Beginner = I rarely participate in online discussions\n\n▫️2▫️ Intermediate = I read regularly, sometimes post\n\n▫️3▫️ Advanced = I actively participate in professional discussions\n\n▶️ **Press the button below👇**",
            "options": {"1": "Beginner", "2": "Intermediate", "3": "Advanced"},
            "next_state": {
                "1": "after_registration_beginner",
                "2": "after_registration_intermediate",
                "3": "after_registration_advanced",
            },
        },
        "after_registration_beginner": {
            "message": "Thank you, {user_name}! (Level: Beginner)\n\n**📌 IMPORTANT INSTRUCTIONS:**\n• You can return any time to previous menu by typing 'back', or pressing the gray button below.\n\nChoose where to start your practice👇\n\n",
            "options": {"1": "Step1️⃣: ANALYSIS", "2": "Step2️⃣: ROLE-PLAY"},
            "next_state": {"1": "analysis_intro_beginner", "2": "roleplay_intro"},
        },
        "after_registration_intermediate": {
            "message": "Thank you, {user_name}! (Level: Intermediate)\n\n**📌 IMPORTANT INSTRUCTIONS:**\n• You can return any time to previous menu by pressing the gray button below\n\nChoose where to start your practice👇\n\n",
            "options": {"1": "Step1️⃣: ANALYSIS", "2": "Step2️⃣: ROLE-PLAY"},
            "next_state": {"1": "analysis_intro_intermediate", "2": "roleplay_intro"},
        },
        "after_registration_advanced": {
            "message": "Thank you, {user_name}! (Level: Advanced)\n\n**📌 IMPORTANT INSTRUCTIONS:**\n• You can return any time to previous menu by pressing the gray button below\n\nChoose where to start your practice👇\n\n",
            "options": {"1": "Step1️⃣: ANALYSIS", "2": "Step2️⃣: ROLE-PLAY"},
            "next_state": {"1": "analysis_intro_advanced", "2": "roleplay_intro"},
        },
        "analysis_intro_beginner": {
            "message": "**Step1️⃣: ANALYSIS**\n\nYou'll learn to identify basic metagrapheme functions and practice softening simple criticism using examples of online comments.\n\n▶️ **Press 'yes' to start or 'back' to return to menu👇**",
            "options": {"yes": "Yes, proceed", "back": "Back to menu"},
            "next_state": {
                "yes": "analysis_task_1_beginner",
                "back": "after_registration_beginner",
            },
        },
        "analysis_intro_intermediate": {
            "message": "**Step1️⃣: ANALYSIS**\n\nYou'll analyze more complex examples of online comments and practice nuanced use of metagraphemes.\n\n▶️ **Press 'yes' to start or 'back' to return to menu👇**",
            "options": {"yes": "Yes, proceed", "back": "Back to menu"},
            "next_state": {
                "yes": "analysis_task_1_intermediate",
                "back": "after_registration_intermediate",
            },
        },
        "analysis_intro_advanced": {
            "message": "**Step1️⃣: ANALYSIS**\n\nYou'll work with complex, multi-layered examples of online comments and cultural comparisons.\n\n▶️ **Press 'yes' to start or 'back' to return to menu👇**",
            "options": {"yes": "Yes, proceed", "back": "Back to menu"},
            "next_state": {
                "yes": "analysis_task_1_advanced",
                "back": "after_registration_advanced",
            },
        },
        "analysis_task_1_beginner": {
            "message": "**📝 TASK 1: Softening Criticism (Beginner)**\n\nContext: {context}\n\nOriginal message: {message}\n\n❓ **Question:** Which emoji(s) would you add to the END of this message to make it sound kinder? Explain your choice.\n\n*Hint: {hint}*\n\n▶️ **Type your answer and press Enter:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "analysis_feedback_1_beginner",
        },
        "analysis_task_2_beginner": {
            "message": "**📝 TASK 2: Recognizing Aggressive Formatting (Beginner)**\n\nMessage: {message}\n\n❓ **Question:** What makes this message feel aggressive? Identify ONE technique.\n\n*Hint: {hint}*\n\n▶️ **Type your answer and press Enter:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "analysis_feedback_2_beginner",
        },
        "analysis_task_1_intermediate": {
            "message": "**📝 TASK 1: Softening Criticism (Intermediate)**\n\nContext: {context}\n\nOriginal message: {message}\n\n❓ **Question:** Which emoji(s) would you add to signal openness to dialogue?\n\n*Hint: {hint}*\n\n▶️ **Type your answer:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "analysis_feedback_1_intermediate",
        },
        "analysis_task_2_intermediate": {
            "message": "**📝 TASK 2: Recognizing Aggressive Formatting (Intermediate)**\n\nMessage: {message}\n\n❓ **Question:** Identify TWO metagrapheme techniques used here.\n\n*Hint: {hint}*\n\n▶️ **Type your answer:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "analysis_feedback_2_intermediate",
        },
        "analysis_task_1_advanced": {
            "message": "**📝 TASK 1: Softening Criticism (Advanced)**\n\nContext: {context}\n\nOriginal message: {message}\n\n❓ **Question:** Where would you place emojis to maintain professionalism?\n\n*Hint: {hint}*\n\n▶️ **Type your answer:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "analysis_feedback_1_advanced",
        },
        "analysis_feedback_1_advanced": {
            "message": "📖 **Read the feedback for you, {user_name} (Advanced), carefully and make notes:**\n\nFor complex feedback, emoji after the main critique softens tone.\n\n▶️ **Type 'next' to continue:**",
            "options": {"next": "Next Task", "back": "Back to menu"},
            "next_state": {
                "next": "analysis_task_2_advanced",
                "back": "analysis_intro_advanced",
            },
        },
        "analysis_task_2_advanced": {
            "message": "**📝 TASK 2: Recognizing Aggressive Formatting (Advanced)**\n\nMessage: {message}\n\n❓ **Question:** Analyze ALL metagrapheme techniques used here.\n\n▶️ **Type your analysis:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "analysis_feedback_2_advanced",
        },
        "analysis_feedback_2_advanced": {
            "message": "📖 **Read the feedback for you, {user_name} (Advanced), carefully and make notes:**\n\nTechniques: ALL CAPS (irony), ellipsis (dramatic pause), 🙄 emoji (sarcasm), #facepalm (meta-commentary).\n\n▶️ **Type 'next' to proceed:**",
            "options": {"next": "Proceed to Step2️⃣", "back": "Back to menu"},
            "next_state": {"next": "roleplay_intro", "back": "analysis_intro_advanced"},
        },
        "analysis_feedback_1_beginner": {
            "message": "📖 **Read the feedback for you, {user_name} (Beginner), carefully and make notes:**\n\nGreat start! Adding a friendly emoji like 🙂 or 😊 can make criticism feel more supportive.\n\n**📋 Model answer:** 'This essay has some areas to work on 🙂. Let's look at them together.'\n\n▶️ **Type 'next' to continue to Task 2:**",
            "options": {"next": "Next Task", "back": "Back to menu"},
            "next_state": {
                "next": "analysis_task_2_beginner",
                "back": "analysis_intro_beginner",
            },
        },
        "analysis_feedback_2_beginner": {
            "message": "📖 **Read the feedback for you, {user_name} (Beginner), carefully and make notes:**\n\nYou're right! **ALL CAPS** feels like shouting online.\n\n**📋 Model answer:** 'The message uses ALL CAPS, which is like shouting online.'\n\n▶️ **Type 'next' to proceed to Step 2:**",
            "options": {"next": "Proceed to Step2️⃣", "back": "Back to menu"},
            "next_state": {"next": "roleplay_intro", "back": "analysis_intro_beginner"},
        },
        "analysis_feedback_1_intermediate": {
            "message": "📖 **Read the feedback for you, {user_name} (Intermediate), carefully and make notes:**\n\nGood approach! A friendly emoji like 🙂 or 🤔 acts as an 'emotional cushion'.\n\n**📋 Model answer:** 'I think the data in this part might need a second look 🤔.'\n\n▶️ **Type 'next' to continue:**",
            "options": {"next": "Next Task", "back": "Back to menu"},
            "next_state": {
                "next": "analysis_task_2_intermediate",
                "back": "analysis_intro_intermediate",
            },
        },
        "analysis_feedback_2_intermediate": {
            "message": "📖 **Read the feedback for you, {user_name} (Intermediate), carefully and make notes:**\n\nKey techniques: Alternating caps (mockery) and multiple exclamation marks (shouting).\n\n**📋 Model answer:** 'The message uses **tHaT's NoT** with alternating caps to mock, and **!!!** to shout.'\n\n▶️ **Type 'next' to proceed:**",
            "options": {"next": "Proceed to Step2️⃣", "back": "Back to menu"},
            "next_state": {
                "next": "roleplay_intro",
                "back": "analysis_intro_intermediate",
            },
        },
        "roleplay_intro": {
            "message": "**Step2️⃣: ROLE-PLAY**\n\nIn this stage, you'll practice constructive communication roles in simulated online discussions.\n\n",
            "options": {
                "continue": "View Available Roles",
                "back": "Back to Main Menu",
            },
            "next_state": {
                "continue": "role_menu",
                "back": "after_registration_{level}",
            },
        },
        "role_menu": {
            "message": "**❇️ CONSTRUCTIVE COMMUNICATIVE ROLES**\n\nChoose a role to practice:\n\n**CONFLICT REGULATORS:**\n🔹1 - Mediator (de-escalates conflicts)\n🔹2 - Logical Expert (highlights contradictions)\n🔹3 - Advocate (defends a person/idea)\n🔹4 - Judge (evaluates arguments)\n🔹5 - Peacemaker (offers compromise)\n\n**SUPPORTING ROLES:**\n🔹6 - Idea Generator (creative thinking)\n🔹7 - Researcher (cultural inquiry)\n🔹8 - Interpreter (cultural bridging)\n\n**EMOTIONAL ROLES:**\n🔹9 - Empath (emotional support)\n\n📌 **Type the number (1-9) or press the button below to choose a role👇 When you complete all the roles, press 'Finish roles' to proceed to reflection🏁**",
            "options": {
                "1": "Mediator",
                "2": "Logical Expert",
                "3": "Advocate",
                "4": "Judge",
                "5": "Peacemaker",
                "6": "Idea Generator",
                "7": "Researcher",
                "8": "Interpeter",
                "9": "Empath",
                "finish": "Finish roles",
                "back": "Back to Role-Play Intro",
            },
            "next_state": {
                "1": "role_mediator",
                "2": "role_logical",
                "3": "role_advocate",
                "4": "role_judge",
                "5": "role_peacemaker",
                "6": "role_idea_generator",
                "7": "role_researcher",
                "8": "role_interpreterer",
                "9": "role_empath",
                "finish": "reflection",
                "back": "roleplay_intro",
            },
        },
        "role_mediator": {
            "message": "**🎭 ROLE: Mediator**\n\n**Scenario:** {scenario}\n\n**Context** {context}\n\n**Aggressor** {aggressor} says: *{quote}*\n\n**Task:** {task}\n\n*You MUST:*\n🔺use @mention to address the aggressor\n 🔺acknowledge their concern before redirecting\n 🔺propose a constructive way forward\n 🔺insert a calm/peaceful emoji (🕊️, 🤝, 🌿)\n\n▶️ **Type your response:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "roleplay_feedback_mediator",
        },
        "roleplay_feedback_mediator": {
            "message": "📖 **Read the feedback for you, {user_name} (Mediator), carefully and make notes:**\n\n**Criteria check:**\n✅ @mention used correctly?\n✅ Acknowledged concern before redirecting?\n✅ Proposed constructive next step?\n✅ Used calm emoji (🕊️, 🤝)?\n\n**📋 Model answer:** *'@ {aggressor}, I see your concern about productivity. 🤝 Let's look at the research together and find a balanced approach that works for everyone.'*\n\n▶️ **Type 'revise' to improve your answer, 'next' to choose the next Role, or 'back' to return to menu:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "role_menu",
        },
        "role_logical": {
            "message": "**🎭 ROLE: Logical Expert**\n\n**Scenario:** {scenario} \n\n**Context:** {context} \n\n**Debate:** *{user1}*\n*{user2}*\n\n**Task:** {task}\n\n*You MUST:*\n 🔺use **bold** (\*-symbol at the beginning and the end of the word, e.g. \*\*hello\*\*) to identify each logical flaw\n 🔺ask at least ONE clarifying question\n 🔺add a thinking emoji (🤔, 🧐, 📊)\n\n▶️ **Type your response:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "roleplay_feedback_logical",
        },
        "roleplay_feedback_logical": {
            "message": "📖 **Read the feedback for you, {user_name} (Logical Expert), carefully and make notes:**\n\n**Criteria check:**\n✅ Used **bold** to highlight flaws?\n✅ Asked clarifying question?\n✅ Used thinking emoji (🤔, 🧐)?\n\n**📋 Model answer:** *'**'Grammar is useless'** is an overgeneralization. 🤔 Could you clarify what you mean? Research shows grammar instruction helps accuracy, while immersion builds fluency. Both have value.'*\n\n▶️ **Type 'revise' to improve your answer, 'next' to choose the next Role, or 'back' to return to menu:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "role_menu",
        },
        "role_idea_generator": {
            "message": "**🎭 ROLE: Idea Generator**\n\n**Scenario:** {scenario}\n\n**Context:** {context}\n\n**Current discussion:** *{quote}*\n\n**Task:** {task}\n\n*You MUST:*\n 🔺use **bold** or *italics* (\*-symbol at the beginning and the end of the word, e.g. \*\*bold\*\* or \*italics\*) to emphasize your key innovative idea\n 🔺add at least ONE creativity emoji (💡, 🚀, ✨)\n 🔺propose at least TWO distinct new ideas\n\n▶️ **Type your response:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "roleplay_feedback_idea",
        },
        "roleplay_feedback_idea": {
            "message": "📖 **Read the feedback for you, {user_name} (Idea Generator), carefully and make notes:**\n\n**Criteria check:**\n✅ Used **bold** or *italics* for key ideas?\n✅ Used creativity emoji (💡, 🚀, ✨)?\n✅ Proposed at least TWO distinct ideas?\n\n**📋 Model answer:** *'What if we tried **a gamified approach** with points and levels? 🚀 Or we could create **cross-cultural conversation pairs** where partners teach each other phrases in their languages? ✨ Both could increase engagement significantly.'*\n\n▶️ **Type 'revise' to improve your answer, 'next' to choose the next Role, or 'back' to return to menu:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "role_menu",
        },
        "role_researcher": {
            "message": "**🎭 ROLE: Researcher**\n\n**Scenario:** {scenario}\n\n**Context:** {context}\n\n**Discussion:** *{user1}*\n*{user2}*\n\n**Task:** {task}\n\n*You MUST:*\n 🔺use @mention to address the person\n 🔺ask at least TWO specific questions about cultural practices\n 🔺add a thoughtful emoji (🤔, 🧐, 📚)\n\n▶️ **Type your response:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "roleplay_feedback_researcher",
        },
        "roleplay_feedback_researcher": {
            "message": "📖 **Read the feedback for you, {user_name} (Researcher), carefully and make notes:**\n\n**Criteria check:**\n✅ Used @mention correctly?\n✅ Asked TWO specific cultural questions?\n✅ Used thoughtful emoji (🤔, 🧐, 📚)?\n\n**📋 Model answer:** *'@speaker, you mentioned directness is respectful in your culture. 📚 Could you tell me how criticism is typically framed in professional settings there? And are there situations where indirectness might be preferred?'*\n\n▶️ **Type 'revise' to improve your answer, 'next' to choose the next Role, or 'back' to return to menu:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "role_menu",
        },
        "role_interpreter": {
            "message": "**🎭 ROLE: Interpreter**\n\n**Scenario:** {scenario}\n\n**Context:** {context}\n\n**Discussion:** *{user1}*\n*{user2}*\n\n**Task:** {task}\n\n*You MUST:*\n 🔺use **bold** (\*-symbol at the beginning and the end of the word, e.g. \*\*hello\*\*) to highlight the key cultural difference\n 🔺explain both intended meaning AND how it was misinterpreted\n 🔺add a bridging emoji (🤝, 🌉, 💬)\n\n▶️ **Type your response:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "roleplay_feedback_interpreter",
        },
        "roleplay_feedback_interpreter": {
            "message": "📖 **Read the feedback for you, {user_name} (Interpreter), carefully and make notes:**\n\n**Criteria check:**\n✅ Used **bold** for cultural difference?\n✅ Explained intended AND misinterpreted meaning?\n✅ Used bridging emoji (🤝, 🌉)?\n\n**📋 Model answer:** *'I think there's a cultural nuance here. **'Requires more careful consideration'** in Japanese often means polite disagreement. 🌉 The German preference for directness isn't wrong — it's just a different cultural expectation.'*\n\n▶️ **Type 'revise' to improve your answer, 'next' to choose the next Role, or 'back' to return to menu:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "role_menu",
        },
        "role_advocate": {
            "message": "**🎭 ROLE: Advocate**\n\n**Scenario:** {scenario}\n\n**Context:** {context}\n\n**Person under criticism:** {user1}\n\n**Quote:** *{critic}*\n\n**Task:** {task}\n\n*You MUST:*\n 🔺use @mention to acknowledge the critic first\n 🔺provide at least TWO reasons for fair consideration\n 🔺add a protective emoji (🛡️, 💪, 🤲)\n\n▶️ **Type your response:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "roleplay_feedback_advocate",
        },
        "roleplay_feedback_advocate": {
            "message": "📖 **Read the feedback for you, {user_name} (Advocate), carefully and make notes:**\n\n**Criteria check:**\n✅ Used @mention to acknowledge critic?\n✅ Provided TWO reasons for defense?\n✅ Used protective emoji (🛡️, 💪)?\n\n**📋 Model answer:** *'@ Sarah, I understand your concern about missed deadlines. 🛡️ However, Alex has been dealing with a family emergency. Also, when Alex has contributed, the quality has been excellent. Let's check in privately before judging.'*\n\n▶️ **Type 'revise' to improve your answer, 'next' to choose the next Role, or 'back' to return to menu:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "role_menu",
        },
        "role_judge": {
            "message": "**🎭 ROLE: Judge**\n\n**Scenario:** {scenario}\n\n*Context:* {context}\n\n**Discussion:** {discussion}\n\n**POVs:** *{points}*\n\n**Task:** {task}\n\n*You MUST:*\n 🔺use **bold** (\*-symbol at the beginning and the end of the word, e.g. \*\*hello\*\*) for the strongest point from each side\n 🔺identify what's valid in BOTH perspectives\n 🔺add a balanced emoji (⚖️, 📊, ✅)\n\n▶️ **Type your response:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "roleplay_feedback_judge",
        },
        "roleplay_feedback_judge": {
            "message": "📖 **Read the feedback for you, {user_name} (Judge), carefully and make notes:**\n\n**Criteria check:**\n✅ Used **bold** for strongest points?\n✅ Found merit in BOTH sides?\n✅ Used balanced emoji (⚖️, 📊)?\n\n**📋 Model answer:** *'Let me assess both sides. ⚖️ Team A's **30% productivity increase** is supported by Stanford. Team B's **collaboration suffers** is backed by MIT. A hybrid model likely addresses both valid concerns.'*\n\n▶️ **Type 'revise' to improve your answer, 'next' to choose the next Role, or 'back' to return to menu:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "role_menu",
        },
        "role_peacemaker": {
            "message": "**🎭 ROLE: Peacemaker**\n\n**Scenario:** {scenario}\n\n**Context:** {context}\n\n**Conflict:** {conflict}\n\n**Discussion:** *{user1}*\n*{user2}*\n\n**Task:** {task}\n\n*You MUST:*\n 🔺use @mention to address both parties\n 🔺identify the VALID concern behind each position\n 🔺propose a specific compromise\n 🔺add a peace emoji (🕊️, ☮️, 🤝)\n\n▶️ **Type your response:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "roleplay_feedback_peacemaker",
        },
        "roleplay_feedback_peacemaker": {
            "message": "📖 **Read the feedback for you, {user_name} (Peacemaker), carefully and make notes:**\n\n**Criteria check:**\n✅ Used @mention for both parties?\n✅ Identified valid concerns?\n✅ Proposed specific compromise?\n✅ Used peace emoji (🕊️, 🤝)?\n\n**📋 Model answer:** *'@ Student A and @ Student B, I hear both of you. 🤝 Student A, your concern about fair contribution is valid. Student B, your feeling of being controlled is also valid. Let's create a shared task list where responsibilities are visible to all.'*\n\n▶️ **Type 'revise' to improve your answer, 'next' to choose the next Role, or 'back' to return to menu:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "role_menu",
        },
        "role_empath": {
            "message": "**🎭 ROLE: Empath**\n\n**Scenario:** {scenario}\n\n**Context:** {context}\n\n**Emotional state:** {emotional_state}\n\n*Comment section:** *{user1}*\n\n**Task:** {task}\n\n*You MUST:*\n 🔺use @mention to address the person\n 🔺explicitly VALIDATE their feelings\n 🔺offer support WITHOUT giving advice\n 🔺add a warm emoji (❤️, 🤗, 💗)\n\n▶️ **Type your response:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "roleplay_feedback_empath",
        },
        "roleplay_feedback_empath": {
            "message": "📖 **Read the feedback for you, {user_name} (Empath), carefully and make notes:**\n\n**Criteria check:**\n✅ Used @mention to address them?\n✅ Explicitly validated feelings?\n✅ Offered support without advice?\n✅ Used warm emoji (❤️, 🤗)?\n\n**📋 Model answer:** *'@ student, that sounds incredibly hard. ❤️ It's completely understandable to feel hurt after such direct criticism. Your feelings are valid, and it's okay to take time to process this. I'm here to listen.'*\n\n▶️ **Type 'revise' to improve your answer, 'next' to choose the next Role, or 'back' to return to menu:**",
            "input_type": "text",
            "validation": ".+",
            "options": {
                "revise": "✏️ Revise",
                "next": "➡️ Next Role",
                "back": "⬅️ Back to Menu",
            },
            "next_state": "role_menu",
        },
        "reflection": {
            "message": "**💭 REFLECTION**\n\nPlease answer briefly:\n\n🅰️Which role was most challenging? Why?\n\n🅱️What new insight about metagraphemes did you gain?\n\n▶️ **Type your reflection:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "posttest",
        },
        "posttest": {
            "message": "**📋 POST-TEST**\n\nRate the same three messages again:\n\n1▪️'Your idea is wrong. Fix it.'\n\n2▪️'I see your point, but have you considered... 🤔'\n\n3▪️'THIS IS TERRIBLE!!!'\n\n▶️ **Type three numbers (e.g., '1 5 2'):**",
            "input_type": "text",
            "validation": "^[1-5] [1-5] [1-5]$",
            "next_state": "data_collection",
        },
        "data_collection": {
            "message": "🎓 **🎉 RESEARCH SESSION COMPLETE, {user_name}!**\n\nThank you for participating!\n\n---\n\n**📤 TO SUBMIT YOUR WORK:**\n\n1️⃣Click the **Export Chat History** button in the left sidebar\n2️⃣Save the downloaded JSON file\n3️⃣Upload the file to this Google Form:\n🔗 **https://forms.gle/V2eyTz1kJRXJxv266**\n\nYour chat history contains:\n✅ Your name\n✅ Pre-test and post-test scores\n✅ All your answers with timestamps\n✅ Your reflection\n\n---\n\n🏁 **That's it! You can exit this chat now and return to your study course. Good luck!**\n\n▶️ **Type 'exit' to finish the interaction:**",
            "options": {"exit": "Exit"},
            "next_state": {"exit": "end"},
        },
        "end": {
            "message": "Goodbye, {user_name}! Don't forget to export your chat history from the sidebar."
        },
    },
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


# ---------------------------------------------------------------------------
# Scenario randomization
# ---------------------------------------------------------------------------


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
