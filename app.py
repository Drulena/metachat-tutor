# app.py - MetaChat Tutor for Streamlit (ФИНАЛЬНАЯ ВЕРСИЯ - ЧАСТЬ 1)
import json
import os
import random
import re
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

load_dotenv()  # Loads .env into os.environ (looks in current/working dir by default)

# ==================== НАСТРОЙКИ ====================
st.set_page_config(
    page_title="MetaChat Tutor - Research Edition", page_icon="🎓", layout="wide"
)

# ==================== CSS ДЛЯ ОФОРМЛЕНИЯ ====================
st.markdown(
    """
<style>
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .st-emotion-cache-1v0mbdj h1, .st-emotion-cache-1v0mbdj h2, .st-emotion-cache-1v0mbdj h3 {
    background-color: #f0f2f6;
    padding: 8px 12px;
    border-radius: 8px;
    display: inline-block;
    margin-bottom: 10px;
}
.stMarkdown ul, .stMarkdown ol {
    padding-left: 1.5rem;
}
</style>
""",
    unsafe_allow_html=True,
)

# ==================== НАСТРОЙКИ ====================
LLM_API_KEY = os.getenv("LLM_API_KEY", None)
LLM_URL = os.getenv("LLM_URL", "http://localhost:8080/v1/completions")

# ==================== ТЕОРЕТИЧЕСКАЯ БАЗА ДЛЯ LLM ====================
THEORETICAL_BASE = """
ТЕОРЕТИЧЕСКАЯ ОСНОВА ДЛЯ ОЦЕНКИ ОТВЕТОВ СТУДЕНТОВ:

1. МЕТАГРАФЕМНЫЕ СРЕДСТВА СМЯГЧЕНИЯ КРИТИКИ:
   - Эмодзи-амортизаторы в конце сообщения: 🙂, 😊, 🤔, 😅
   - Скобки и многоточия для имитации понижения голоса/паузы: (just my impression though)...
   - Избегание ЗАГЛАВНЫХ БУКВ и множественных !!!

2. МЕТАГРАФЕМНЫЕ СРЕДСТВА ИНТЕНСИФИКАЦИИ И САРКАЗМА:
   - ALL CAPS = крик
   - Alternating caps (tHaT's NoT) = насмешка
   - Множественные знаки: !!!, ??! – гиперболизация эмоций
   - Удвоение букв: Noooooo – эмфаза
   - Эмодзи-сарказм: 👏, 🙄, 😒, 🤦

3. СРЕДСТВА СТРУКТУРНО-ЛОГИЧЕСКОГО ВЫДЕЛЕНИЯ:
   - Жирный шрифт, курсив, подчёркивание – акцент на ключевом тезисе
   - Цитирование (@Name) – точная адресация критики
   - Хештеги (#offtopic, #strawman) – метки нарушения логики

4. КОММУНИКАТИВНЫЕ РОЛИ (конструктивные):
   - Логик: аналитика, уточняющие вопросы
   - Генератор идей: креативность, новые идеи
   - Исследователь: уточнение культурного контекста
   - Интерпретатор: перевод культурных кодов
   - Адвокат: защита участника/идеи
   - Судья: оценка аргументов, выводы
   - Миротворец: компромиссы
   - Эмпат: поддержка, снижение напряжения
"""

# ==================== ДАННЫЕ ====================
LEVELS = {
    "beginner": "Beginner (I rarely participate in online discussions)",
    "intermediate": "Intermediate (I read regularly, sometimes post)",
    "advanced": "Advanced (I actively participate in professional discussions)",
}

TASK_VARIANTS = {
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
                "hint": "Alternating caps = mockery.",
            }
        ],
        "advanced": [
            {
                "message": "'Your idea is BRILLIANT... if you're living in 1995 🙄 #facepalm'",
                "hint": "Multiple techniques: ALL CAPS, ellipsis, emoji, hashtag.",
            }
        ],
    },
    "role_mediator": [
        {
            "scenario": "Remote Work vs. Office Work",
            "aggressor": "Alex",
            "quote": "'Working from home is just an excuse for being lazy!'",
            "tag": "#offtopic",
            "context": "A professional online forum.",
        }
    ],
    "role_logical": [
        {
            "scenario": "Language learning methods",
            "user1": "Sam",
            "quote1": "'Grammar is useless.'",
            "user2": "Taylor",
            "quote2": "'But without grammar, you'll sound incomprehensible.'",
            "context": "A debate in linguistics forum.",
        }
    ],
    "role_idea_generator": [
        {
            "scenario": "University language exchange program",
            "context": "Students discussing how to improve the exchange.",
            "quote": "Maybe we could just meet once a week and talk?",
            "task": "Generate innovative ideas to make the exchange more engaging.",
        }
    ],
    "role_researcher": [
        {
            "scenario": "Politeness in different cultures",
            "context": "Debate about direct criticism.",
            "cultural_claim": "In my culture, being direct is always respectful.",
            "quote": "We should just say what we think.",
            "task": "Ask questions to understand the cultural context.",
        }
    ],
    "role_interpreter": [
        {
            "scenario": "International student forum",
            "context": "Japanese student: 'This requires more careful consideration.' German student: 'Why? Be specific.'",
            "cultural_note": "Japanese indirectness may seem evasive.",
            "task": "Explain Japanese communication style.",
        }
    ],
    "role_advocate": [
        {
            "scenario": "Team project evaluation",
            "context": "Alex is being criticized for not contributing.",
            "person_under_criticism": "Alex",
            "critic": "Sarah",
            "quote": "Alex is clearly not committed to this project.",
            "task": "Defend Alex by considering possible circumstances.",
        }
    ],
    "role_judge": [
        {
            "scenario": "Debate about remote work",
            "discussion": "Team A: full remote. Team B: office-only.",
            "points": "Both sides present conflicting studies.",
            "quote": "The evidence is completely contradictory. Who's right?",
            "task": "Objectively evaluate both sides.",
        }
    ],
    "role_peacemaker": [
        {
            "scenario": "Argument about grading",
            "context": "Students fighting about group project grade.",
            "conflict": "Personal accusations escalating.",
            "quote": "This is your fault. You never listen!",
            "user1": "Student A",
            "user2": "Student B",
            "task": "Help the students find a constructive way forward.",
        }
    ],
    "role_empath": [
        {
            "scenario": "Student with imposter syndrome",
            "context": "First-year grad student feels they don't belong.",
            "emotional_state": "Vulnerability and anxiety",
            "quote": "You just need to study more. Stop complaining.",
            "student": "the graduate student",
            "task": "Provide genuine emotional support without immediately offering advice.",
        }
    ],
}

SCENARIO = {
    "bot_name": "MetaChat Tutor",
    "welcome_message": "🔬 **WELCOME TO METACHAT TUTOR - RESEARCH EDITION**\n\n📝 **Type down your name and group (e.g., Aida V. 101 bsufl):**",
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
            "validation": r"^[1-5] [1-5] [1-5]$",
            "next_state": "level_assessment",
        },
        "level_assessment": {
            "message": "**📊 Self-Assessment: Your Experience Level**\n\nPlease evaluate your experience with online discussions in English:\n\n▫️1▫️ Beginner (I rarely participate in online discussions)\n\n▫️2▫️ Intermediate (I read regularly, sometimes post)\n\n▫️3▫️ Advanced (I actively participate in professional discussions)\n\n▶️ **Type the number (1, 2, or 3) and press Enter:**",
            "options": {"1": "Beginner", "2": "Intermediate", "3": "Advanced"},
            "next_state": {
                "1": "after_registration_beginner",
                "2": "after_registration_intermediate",
                "3": "after_registration_advanced",
            },
        },
        "after_registration_beginner": {
            "message": "Thank you, {user_name}! (Level: Beginner)\n\n**📌 IMPORTANT INSTRUCTIONS:**\n• Type **'back'** at any time to return to previous menu\n\nWe will practice in steps:\n🔹 **Step1️⃣** - ANALYSIS\n🔹 **Step2️⃣** - ROLE-PLAY\n\n▶️ **Type the number (1 or 2) and press Enter to choose:**",
            "options": {"1": "Step1️⃣: ANALYSIS", "2": "Step2️⃣: ROLE-PLAY"},
            "next_state": {"1": "analysis_intro_beginner", "2": "roleplay_intro"},
        },
        "after_registration_intermediate": {
            "message": "Thank you, {user_name}! (Level: Intermediate)\n\n**📌 IMPORTANT INSTRUCTIONS:**\n• Type **'back'** at any time\n\nWe will practice in steps:\n🔹 **Step1️⃣** - ANALYSIS\n🔹 **Step2️⃣** - ROLE-PLAY\n\n▶️ **Type the number (1 or 2) and press Enter to choose:**",
            "options": {"1": "Step1️⃣: ANALYSIS", "2": "Step2️⃣: ROLE-PLAY"},
            "next_state": {"1": "analysis_intro_intermediate", "2": "roleplay_intro"},
        },
        "after_registration_advanced": {
            "message": "Thank you, {user_name}! (Level: Advanced)\n\n**📌 IMPORTANT INSTRUCTIONS:**\n• Type **'back'** at any time\n\nWe will practice in steps:\n🔹 **Step1️⃣** - ANALYSIS\n🔹 **Step2️⃣** - ROLE-PLAY\n\n▶️ **Type the number (1 or 2) and press Enter to choose:**",
            "options": {"1": "Step1️⃣: ANALYSIS", "2": "Step2️⃣: ROLE-PLAY"},
            "next_state": {"1": "analysis_intro_advanced", "2": "roleplay_intro"},
        },
        "analysis_intro_beginner": {
            "message": "**Step1️⃣: ANALYSIS**\n\nYou'll learn to identify basic metagraheme functions and practice softening simple criticism using examples of online comments.\n\n▶️ **Type 'yes' to start or 'back' to return to menu:**",
            "options": {"yes": "Yes, proceed", "back": "Back to menu"},
            "next_state": {
                "yes": "analysis_task_1_beginner",
                "back": "after_registration_beginner",
            },
        },
        "analysis_intro_intermediate": {
            "message": "**Step1️⃣: ANALYSIS**\n\nYou'll analyze more complex examples of online comments and practice nuanced use of metagrahemes.\n\n▶️ **Type 'yes' to start or 'back' to return to menu:**",
            "options": {"yes": "Yes, proceed", "back": "Back to menu"},
            "next_state": {
                "yes": "analysis_task_1_intermediate",
                "back": "after_registration_intermediate",
            },
        },
        "analysis_intro_advanced": {
            "message": "**Step1️⃣: ANALYSIS**\n\nYou'll work with complex, multi-layered examples of online comments and cultural comparisons.\n\n▶️ **Type 'yes' to start or 'back' to return to menu:**",
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
            "message": "**📝 TASK 2: Recognizing Aggressive Formatting (Intermediate)**\n\nMessage: {message}\n\n❓ **Question:** Identify TWO metagraheme techniques used here.\n\n*Hint: {hint}*\n\n▶️ **Type your answer:**",
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
            "message": "**📝 TASK 2: Recognizing Aggressive Formatting (Advanced)**\n\nMessage: {message}\n\n❓ **Question:** Analyze ALL metagraheme techniques used here.\n\n▶️ **Type your analysis:**",
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
        # ==================== STEP 2: ROLE-PLAY ====================
        "roleplay_intro": {
            "message": "**Step2️⃣: ROLE-PLAY**\n\nIn this stage, you'll practice different communication roles in simulated online discussions.\n\n▶️ **Type 'continue' to see available roles or 'back' to return to menu:**",
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
            "message": "**❇️ CONSTRUCTIVE COMMUNICATIVE ROLES**\n\nChoose a role to practice:\n\n**CONFLICT REGULATORS:**\n🔹1 - Mediator (de-escalates conflicts)\n🔹2 - Logical Expert (highlights contradictions)\n🔹6 - Advocate (defends a person/idea)\n🔹7 - Judge (evaluates arguments)\n🔹8 - Peacemaker (offers compromise)\n\n**SUPPORTING ROLES:**\n🔹3 - Idea Generator (creative thinking)\n🔹4 - Researcher (cultural inquiry)\n🔹5 - Interpreter (cultural bridging)\n\n**EMOTIONAL ROLES:**\n🔹9 - Empath (emotional support)\n\n📌 **Type the number (1-9) to choose a role, or type 'finish' to proceed to reflection:**",
            "options": {
                "1": "Mediator",
                "2": "Logical Expert",
                "3": "Idea Generator",
                "4": "Researcher",
                "5": "Interpreter",
                "6": "Advocate",
                "7": "Judge",
                "8": "Peacemaker",
                "9": "Empath",
                "finish": "Finish roles",
                "back": "Back to Role-Play Intro",
            },
            "next_state": {
                "1": "role_mediator",
                "2": "role_logical",
                "3": "role_idea_generator",
                "4": "role_researcher",
                "5": "role_interpreter",
                "6": "role_advocate",
                "7": "role_judge",
                "8": "role_peacemaker",
                "9": "role_empath",
                "finish": "reflection",
                "back": "roleplay_intro",
            },
        },
        # РОЛЬ 1: MEDIATOR
        "role_mediator": {
            "message": "**🎭 ROLE: Mediator**\n\n**Scenario:** {scenario}\n\n**Aggressor:** {aggressor} says: {quote}\n\n**Tag:** {tag}\n\n**Task:** Write a mediator response that de-escalates the conflict.\n\n*You MUST:*\n🔺Use @mention to address the aggressor (space after @)\n 🔺Acknowledge their concern before redirecting\n 🔺Propose a constructive way forward\n 🔺Use a calm/peaceful emoji (🕊️, 🤝, 🌿)\n\n▶️ **Type your response:**",
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
        # РОЛЬ 2: LOGICAL EXPERT
        "role_logical": {
            "message": "**🎭 ROLE: Logical Expert**\n\n**Scenario:** {scenario}\n\n**Debate:** {user1}: {quote1}\n{user2}: {quote2}\n\n**Task:** Highlight logical gaps in the arguments.\n\n*You MUST:*\n 🔺Use **bold** to identify each logical flaw\n 🔺Ask at least ONE clarifying question\n 🔺Use a thinking emoji (🤔, 🧐, 📊)\n\n▶️ **Type your response:**",
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
        # РОЛЬ 3: IDEA GENERATOR
        "role_idea_generator": {
            "message": "**🎭 ROLE: Idea Generator**\n\n**Scenario:** {scenario}\n\n**Context:** {context}\n\n**Current discussion:** *{quote}*\n\n**Task:** {task}\n\n*You MUST:*\n 🔺Use **bold** or *italics* to emphasize your key innovative idea\n 🔺Use at least ONE creativity emoji (💡, 🚀, ✨)\n 🔺Propose at least TWO distinct new ideas\n\n▶️ **Type your response:**",
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
        # РОЛЬ 4: RESEARCHER
        "role_researcher": {
            "message": "**🎭 ROLE: Researcher**\n\n**Scenario:** {scenario}\n\n**Context:** {context}\n\n**Cultural claim:** *{cultural_claim}*\n\n**Quote:** {quote}\n\n**Task:** {task}\n\n*You MUST:*\n 🔺Use @mention to address the person (space after @)\n 🔺Ask at least TWO specific questions about cultural practices\n 🔺Use a thoughtful emoji (🤔, 🧐, 📚)\n\n▶️ **Type your response:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "roleplay_feedback_researcher",
        },
        "roleplay_feedback_researcher": {
            "message": "📖 **Read the feedback for you, {user_name} (Researcher), carefully and make notes:**\n\n**Criteria check:**\n✅ Used @mention correctly?\n✅ Asked TWO specific cultural questions?\n✅ Used thoughtful emoji (🤔, 🧐, 📚)?\n\n**📋 Model answer:** *'@ speaker, you mentioned directness is respectful in your culture. 📚 Could you tell me how criticism is typically framed in professional settings there? And are there situations where indirectness might be preferred?'*\n\n▶️ **Type 'revise' to improve your answer, 'next' to choose the next Role, or 'back' to return to menu:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "role_menu",
        },
        # РОЛЬ 5: INTERPRETER
        "role_interpreter": {
            "message": "**🎭 ROLE: Interpreter**\n\n**Scenario:** {scenario}\n\n**Context:** {context}\n\n**Cultural note:** {cultural_note}\n\n**Task:** {task}\n\n*You MUST:*\n 🔺Use **bold** to highlight the key cultural difference\n 🔺Explain both intended meaning AND how it was misinterpreted\n 🔺Use a bridging emoji (🤝, 🌉, 💬)\n\n▶️ **Type your response:**",
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
        # РОЛЬ 6: ADVOCATE
        "role_advocate": {
            "message": "**🎭 ROLE: Advocate**\n\n**Scenario:** {scenario}\n\n**Context:** {context}\n\n**Person under criticism:** {person_under_criticism}\n\n**Task:** {task}\n\n*You MUST:*\n 🔺Use @mention to acknowledge the critic first (space after @)\n 🔺Provide at least TWO reasons for fair consideration\n 🔺Use a protective emoji (🛡️, 💪, 🤲)\n\n▶️ **Type your response:**",
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
        # РОЛЬ 7: JUDGE
        "role_judge": {
            "message": "**🎭 ROLE: Judge**\n\n**Scenario:** {scenario}\n\n**Discussion:** {discussion}\n\n**Points:** {points}\n\n**Task:** {task}\n\n*You MUST:*\n 🔺Use **bold** for the strongest point from each side\n 🔺Identify what's valid in BOTH perspectives\n 🔺Use a balanced emoji (⚖️, 📊, ✅)\n\n▶️ **Type your response:**",
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
        # РОЛЬ 8: PEACEMAKER
        "role_peacemaker": {
            "message": "**🎭 ROLE: Peacemaker**\n\n**Scenario:** {scenario}\n\n**Context:** {context}\n\n**Conflict:** {conflict}\n\n**Task:** {task}\n\n*You MUST:*\n 🔺Use @mention to address both parties (space after @)\n 🔺Identify the VALID concern behind each position\n 🔺Propose a specific compromise\n 🔺Use a peace emoji (🕊️, ☮️, 🤝)\n\n▶️ **Type your response:**",
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
        # РОЛЬ 9: EMPATH
        "role_empath": {
            "message": "**🎭 ROLE: Empath**\n\n**Scenario:** {scenario}\n\n**Context:** {context}\n\n**Emotional state:** {emotional_state}\n\n**Task:** {task}\n\n*You MUST:*\n 🔺Use @mention to address the person (space after @)\n 🔺Explicitly VALIDATE their feelings\n 🔺Offer support WITHOUT giving advice\n 🔺Use a warm emoji (❤️, 🤗, 💗)\n\n▶️ **Type your response:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "roleplay_feedback_empath",
        },
        "roleplay_feedback_empath": {
            "message": "📖 **Read the feedback for you, {user_name} (Empath), carefully and make notes:**\n\n**Criteria check:**\n✅ Used @mention to address them?\n✅ Explicitly validated feelings?\n✅ Offered support without advice?\n✅ Used warm emoji (❤️, 🤗)?\n\n**📋 Model answer:** *'@ student, that sounds incredibly hard. ❤️ It's completely understandable to feel hurt after such direct criticism. Your feelings are valid, and it's okay to take time to process this. I'm here to listen.'*\n\n▶️ **Type 'revise' to improve your answer, 'next' to choose the next Role, or 'back' to return to menu:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "role_menu",
        },
        # ==================== REFLECTION & POST-TEST ====================
        "reflection": {
            "message": "**💭 REFLECTION**\n\nPlease answer briefly:\n\n🅰️Which role was most challenging? Why?\n\n🅱️What new insight about metagrahemes did you gain?\n\n▶️ **Type your reflection:**",
            "input_type": "text",
            "validation": ".+",
            "next_state": "posttest",
        },
        "posttest": {
            "message": "**📋 POST-TEST**\n\nRate the same three messages again:\n\n1▪️'Your idea is wrong. Fix it.'\n\n2▪️'I see your point, but have you considered... 🤔'\n\n3▪️'THIS IS TERRIBLE!!!'\n\n▶️ **Type three numbers (e.g., '1 5 2'):**",
            "input_type": "text",
            "validation": r"^[1-5] [1-5] [1-5]$",
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


# ==================== ФУНКЦИЯ РАНДОМИЗАЦИИ ====================
def randomize_scenario(scenario, level="intermediate"):
    """Подстановка случайных вариантов заданий с учётом уровня"""
    import copy

    scenario_copy = copy.deepcopy(scenario)

    # Рандомизация pre-test сообщений
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

    # Рандомизация заданий для анализа
    for lvl in ["beginner", "intermediate", "advanced"]:
        for task_num in [1, 2]:
            task_state = f"analysis_task_{task_num}_{lvl}"
            feedback_state = f"analysis_feedback_{task_num}_{lvl}"
            if lvl in TASK_VARIANTS.get(f"analysis_task_{task_num}", {}):
                variants = TASK_VARIANTS[f"analysis_task_{task_num}"][lvl]
                if variants:
                    variant = random.choice(variants)
                    if task_state in scenario_copy["states"]:
                        msg = scenario_copy["states"][task_state]["message"]
                        for key, value in variant.items():
                            msg = msg.replace("{" + key + "}", str(value))
                        scenario_copy["states"][task_state]["message"] = msg

    # Рандомизация всех 9 ролей
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


# ==================== ИНИЦИАЛИЗАЦИЯ СЕССИИ ====================
def init_session_state():
    """Инициализирует переменные состояния Streamlit"""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "current_state" not in st.session_state:
        st.session_state.current_state = "start"
    if "user_data" not in st.session_state:
        st.session_state.user_data = {
            "user_name": None,
            "level": None,
            "pretest_scores": None,
            "posttest_scores": None,
            "current_role": None,  # Текущая выбранная роль
            "current_role_variant": None,  # Вариант роли
        }
    if "scenario" not in st.session_state:
        st.session_state.scenario = randomize_scenario(SCENARIO, "intermediate")
    if "session_id" not in st.session_state:
        st.session_state.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")


def get_current_message():
    """Возвращает сообщение для текущего состояния с подстановкой переменных"""
    state = st.session_state.scenario["states"][st.session_state.current_state]
    message = state["message"]

    user_answer = st.session_state.chat_history[-1]["content"]
    print(
        f"DEBUG get_current_message: user_answer='{user_answer}', "
        f"user_name='{st.session_state.user_data['user_name']}', "
        f"level='{st.session_state.user_data['level']}', "
        f"current_role='{st.session_state.user_data['current_role']}'"
    )

    if (
        (
            "analysis_feedback" in st.session_state.current_state
            or "analysis_task" in st.session_state.current_state
        )
        and st.session_state.user_data["user_name"]
        and st.session_state.user_data["level"]
        # and st.session_state.user_data["current_role"]
    ):
        message += get_llm_feedback(
            user_name=st.session_state.user_data["user_name"],
            level=st.session_state.user_data["level"],
            role_name=st.session_state.user_data["current_role"],
            user_answer=user_answer,
        )

    # Подстановка имени пользователя
    if st.session_state.user_data["user_name"]:
        message = message.replace(
            "{user_name}", st.session_state.user_data["user_name"]
        )

    # Подстановка уровня в back-ссылках
    if "{level}" in message and st.session_state.user_data["level"]:
        message = message.replace("{level}", st.session_state.user_data["level"])

    return message


def process_input(user_input):
    """Обрабатывает ввод пользователя и обновляет состояние"""
    print(
        f"DEBUG process_input: user_input='{user_input}', current_state='{st.session_state.current_state}'"
    )
    current_state_obj = st.session_state.scenario["states"][
        st.session_state.current_state
    ]

    # ========== ОБРАБОТКА КОМАНДЫ 'back' ==========
    if user_input.lower() == "back":
        level = st.session_state.user_data.get("level", "beginner")
        print(
            f"DEBUG BACK: current_state={st.session_state.current_state}, level={level}"
        )
        if "analysis_task_" in st.session_state.current_state:
            st.session_state.current_state = f"analysis_intro_{level}"
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": get_current_message(),
                    "state": st.session_state.current_state,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return
        elif "analysis_intro_" in st.session_state.current_state:
            print(
                f"DEBUG BACK: matched analysis_intro_ pattern, going to after_registration_{level}"
            )
            st.session_state.current_state = f"after_registration_{level}"
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": get_current_message(),
                    "state": st.session_state.current_state,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return
        elif st.session_state.current_state == "role_menu":
            st.session_state.current_state = "roleplay_intro"
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": get_current_message(),
                    "state": st.session_state.current_state,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return
        elif st.session_state.current_state == "roleplay_intro":
            level = st.session_state.user_data.get("level", "beginner")
            st.session_state.current_state = f"after_registration_{level}"
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": get_current_message(),
                    "state": st.session_state.current_state,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return
        elif "roleplay_feedback" in st.session_state.current_state:
            st.session_state.current_state = "role_menu"
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": get_current_message(),
                    "state": st.session_state.current_state,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return
        else:
            level = st.session_state.user_data.get("level", "beginner")
            st.session_state.current_state = f"after_registration_{level}"
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": get_current_message(),
                    "state": st.session_state.current_state,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return

    # ========== СОХРАНЯЕМ ОТВЕТ В ИСТОРИЮ ==========
    st.session_state.chat_history.append(
        {
            "role": "user",
            "content": user_input,
            "state": st.session_state.current_state,
            "timestamp": datetime.now().isoformat(),
        }
    )

    # ========== ВАЛИДАЦИЯ ВВОДА ==========
    if "validation" in current_state_obj:
        if not re.match(current_state_obj["validation"], user_input):
            st.warning("⚠️ Please enter the data in the correct format. Try again.")
            return

    # ========== СОХРАНЯЕМ ДАННЫЕ ПОЛЬЗОВАТЕЛЯ ==========
    if st.session_state.current_state == "start":
        st.session_state.user_data["user_name"] = (
            user_input.split()[0] if user_input.split() else user_input
        )
        st.session_state.current_state = "pretest"
        st.session_state.chat_history.append(
            {
                "role": "assistant",
                "content": get_current_message(),
                "state": st.session_state.current_state,
                "timestamp": datetime.now().isoformat(),
            }
        )
        return

    # Для pretest с валидацией
    if st.session_state.current_state == "pretest":
        try:
            scores = list(map(int, user_input.split()))
            if len(scores) == 3 and all(1 <= s <= 5 for s in scores):
                st.session_state.user_data["pretest_scores"] = scores
                st.session_state.current_state = "level_assessment"
                st.session_state.chat_history.append(
                    {
                        "role": "assistant",
                        "content": get_current_message(),
                        "state": st.session_state.current_state,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                return
            else:
                st.warning(
                    "⚠️ Please enter three numbers between 1 and 5, separated by spaces."
                )
                return
        except:
            st.warning(
                "⚠️ Please enter three numbers between 1 and 5, separated by spaces."
            )
            return

    if st.session_state.current_state == "level_assessment":
        if user_input in ["1", "2", "3"]:
            level_map = {"1": "beginner", "2": "intermediate", "3": "advanced"}
            st.session_state.user_data["level"] = level_map[user_input]
            st.session_state.current_state = (
                f"after_registration_{level_map[user_input]}"
            )
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": get_current_message(),
                    "state": st.session_state.current_state,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return
        else:
            st.warning("⚠️ Please enter 1, 2, or 3.")
            return

    # Для posttest с валидацией
    if st.session_state.current_state == "posttest":
        try:
            scores = list(map(int, user_input.split()))
            if len(scores) == 3 and all(1 <= s <= 5 for s in scores):
                st.session_state.user_data["posttest_scores"] = scores
                st.session_state.current_state = "data_collection"
                st.session_state.chat_history.append(
                    {
                        "role": "assistant",
                        "content": get_current_message(),
                        "state": st.session_state.current_state,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                return
            else:
                st.warning(
                    "⚠️ Please enter three numbers between 1 and 5, separated by spaces."
                )
                return
        except:
            st.warning(
                "⚠️ Please enter three numbers between 1 and 5, separated by spaces."
            )
            return

    # ========== ОБРАБОТКА КОМАНД В ФИДБЕКАХ РОЛЕЙ ==========
    if "roleplay_feedback" in st.session_state.current_state:
        cmd = user_input.lower()
        current_role = st.session_state.user_data.get("current_role", "role_mediator")
        if cmd == "revise":
            st.session_state.current_state = current_role
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": get_current_message(),
                    "state": st.session_state.current_state,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return
        elif cmd == "next":
            st.session_state.current_state = "role_menu"
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": get_current_message(),
                    "state": st.session_state.current_state,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return
        elif cmd == "back":
            st.session_state.current_state = "role_menu"
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": get_current_message(),
                    "state": st.session_state.current_state,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return
        else:
            st.warning("⚠️ Please type 'revise', 'next', or 'back'.")
            return

    # ========== ОБРАБОТКА КОМАНД В АНАЛИЗЕ ==========
    if "analysis_feedback_" in st.session_state.current_state:
        if user_input.lower() == "next":
            if "task_1" in st.session_state.current_state:
                new_state = st.session_state.current_state.replace(
                    "feedback_1", "task_2"
                )
                st.session_state.current_state = new_state
                st.session_state.chat_history.append(
                    {
                        "role": "assistant",
                        "content": get_current_message(),
                        "state": st.session_state.current_state,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                return
            elif "task_2" in st.session_state.current_state:
                st.session_state.current_state = "roleplay_intro"
                st.session_state.chat_history.append(
                    {
                        "role": "assistant",
                        "content": get_current_message(),
                        "state": st.session_state.current_state,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                return
        elif user_input.lower() == "back":
            level = st.session_state.user_data.get("level", "beginner")
            st.session_state.current_state = f"analysis_intro_{level}"
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": get_current_message(),
                    "state": st.session_state.current_state,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return

    # Для выбора Step 1 или Step 2
    if "after_registration_" in st.session_state.current_state:
        if user_input in ["1", "2"]:
            if user_input == "1":
                level = st.session_state.user_data.get("level", "beginner")
                st.session_state.current_state = f"analysis_intro_{level}"
            else:
                st.session_state.current_state = "roleplay_intro"
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": get_current_message(),
                    "state": st.session_state.current_state,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return
        elif user_input.lower() == "back":
            st.session_state.current_state = "level_assessment"
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": get_current_message(),
                    "state": st.session_state.current_state,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return
        else:
            st.warning("⚠️ Please type 1 (ANALYSIS) or 2 (ROLE-PLAY).")
            return

    # Для выбора роли
    if st.session_state.current_state == "role_menu":
        if user_input.lower() == "finish":
            st.session_state.current_state = "reflection"
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": get_current_message(),
                    "state": st.session_state.current_state,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return
        elif user_input.lower() == "back":
            st.session_state.current_state = "roleplay_intro"
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": get_current_message(),
                    "state": st.session_state.current_state,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return
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
            st.session_state.user_data["current_role"] = role_map[user_input]
            st.session_state.current_state = role_map[user_input]
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": get_current_message(),
                    "state": st.session_state.current_state,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return
        else:
            st.warning("⚠️ Please type a number from 1 to 9, or 'finish'.")
            return

    # Для команды continue в roleplay_intro
    if st.session_state.current_state == "roleplay_intro":
        if user_input.lower() == "continue":
            st.session_state.current_state = "role_menu"
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": get_current_message(),
                    "state": st.session_state.current_state,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return
        elif user_input.lower() == "back":
            level = st.session_state.user_data.get("level", "beginner")
            st.session_state.current_state = f"after_registration_{level}"
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": get_current_message(),
                    "state": st.session_state.current_state,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return
        else:
            st.warning("⚠️ Please type 'continue' to proceed or 'back' to return.")
            return

    # Для команды yes в analysis_intro
    if "analysis_intro_" in st.session_state.current_state:
        print(f"DEBUG: analysis_intro state, input='{user_input}'")
        if user_input.lower() == "yes":
            current = st.session_state.current_state
            task_state = current.replace("intro", "task_1")
            print(f"DEBUG: Going from {current} to {task_state}")
            st.session_state.current_state = task_state
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": get_current_message(),
                    "state": st.session_state.current_state,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return
        elif user_input.lower() != "back":  # Don't warn if it's 'back' (handled above)
            st.warning("⚠️ Please type 'yes' to start or 'back' to return.")
            return

    # Для заданий анализа (Task 1, Task 2)
    if "analysis_task_" in st.session_state.current_state:
        feedback_state = st.session_state.current_state.replace("task", "feedback")
        st.session_state.current_state = feedback_state
        st.session_state.chat_history.append(
            {
                "role": "assistant",
                "content": get_current_message(),
                "state": st.session_state.current_state,
                "timestamp": datetime.now().isoformat(),
            }
        )
        return

    # Для команды exit в data_collection
    if st.session_state.current_state == "data_collection":
        if user_input.lower() == "exit":
            st.session_state.current_state = "end"
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": get_current_message(),
                    "state": st.session_state.current_state,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return
        else:
            st.warning("⚠️ Please type 'exit' to close the session.")
            return

    # ========== СТАНДАРТНЫЙ ПЕРЕХОД НА СЛЕДУЮЩЕЕ СОСТОЯНИЕ ==========
    if "next_state" in current_state_obj:
        next_state = current_state_obj["next_state"]
        if isinstance(next_state, dict):
            if user_input in next_state:
                st.session_state.current_state = next_state[user_input]
            elif "default" in next_state:
                st.session_state.current_state = next_state["default"]
            else:
                st.session_state.current_state = "end"
        else:
            st.session_state.current_state = next_state
    elif "options" in current_state_obj and user_input in current_state_obj["options"]:
        st.session_state.current_state = current_state_obj["next_state"][user_input]

    # Добавляем ответ бота в историю
    if st.session_state.current_state != "end":
        st.session_state.chat_history.append(
            {
                "role": "assistant",
                "content": get_current_message(),
                "state": st.session_state.current_state,
                "timestamp": datetime.now().isoformat(),
            }
        )


# ==================== ФУНКЦИЯ ДЛЯ LLM (ОПЦИОНАЛЬНО) ====================
def get_llm_feedback(user_answer, role_name, user_name, level):
    """Получение фидбека от LLM через API (если LLM_API_KEY != None)"""
    if LLM_API_KEY is None:
        return None

    # Здесь нужно подключить API
    # Пример заготовки:
    try:
        import requests

        response = requests.post(
            LLM_URL,
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={
                "prompt": f"{THEORETICAL_BASE}\n\nОцени ответ студента... {user_name} {level} {user_answer}",
                "max_tokens": 500,
            },
        )
        return response.json()["choices"][0]["text"]
    except:
        return None


# ==================== ИНТЕРФЕЙС STREAMLIT ====================
def main():
    st.title("🎓 MetaChat Tutor - Research Edition")

    # Инициализация
    init_session_state()

    # Приветственное сообщение, если история пуста
    if not st.session_state.chat_history:
        st.info("📝 **Type down your name and group (e.g., Aida V. 101 bsufl)**")

    # Боковая панель
    with st.sidebar:
        st.header("📊 Session Info")
        st.write(f"**Session ID:** {st.session_state.session_id}")
        if st.session_state.user_data["user_name"]:
            st.write(f"**Participant:** {st.session_state.user_data['user_name']}")
        if st.session_state.user_data["level"]:
            st.write(f"**Level:** {st.session_state.user_data['level']}")

        st.divider()

        # Кнопка экспорта
        if st.button("📥 Export Chat History"):
            export_data = {
                "session_id": st.session_state.session_id,
                "user_data": st.session_state.user_data,
                "chat_history": st.session_state.chat_history,
                "export_time": datetime.now().isoformat(),
            }
            st.download_button(
                label="Download JSON File",
                data=json.dumps(export_data, indent=2, ensure_ascii=False),
                file_name=f"metachat_session_{st.session_state.session_id}.json",
                mime="application/json",
            )

    # Отображение истории чата
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            st.chat_message("user").write(message["content"])
        else:
            with st.chat_message("assistant"):
                st.markdown(message["content"])

    # Поле ввода
    if st.session_state.current_state != "end":
        user_input = st.chat_input("Type your answer here...")
        if user_input:
            process_input(user_input)
            st.rerun()
    else:
        st.success("🎉 Session completed! Don't forget to export your chat history.")
        st.balloons()


if __name__ == "__main__":
    main()
