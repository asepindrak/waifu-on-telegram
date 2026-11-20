import os
import re
import json
import time
import logging
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)

ENGLISH_SYLLABUS: List[Dict[str, Any]] = [
    {
        "unit_id": "unit_1",
        "unit_title": "Unit 1: Everyday & Campus Life (A1–A2)",
        "level": "Beginner (A1–A2)",
        "lessons": [
            {
                "id": "1.1",
                "title": "Warm Greetings, Small Talk & Moods",
                "cefr": "A1",
                "story_hook": "We just bumped into each other on campus / near a cozy park bench in the morning breeze. We're catching up before the day starts.",
                "target_vocab": ["How's your day going?", "I'm feeling a bit tired", "Same as usual", "Grab a bite", "Catch up"],
                "grammar_focus": "Present Simple & Present Continuous for current feelings/moods",
                "goal": "Practice natural greetings, describing how you feel, and asking back smoothly."
            },
            {
                "id": "1.2",
                "title": "Ordering Coffee & Street Food Together",
                "cefr": "A1–A2",
                "story_hook": "It started drizzling outside, so we ducked into a warm aesthetic café. I'm looking at the menu board and asking what you'd like to order.",
                "target_vocab": ["Could I get...", "I'd like to have...", "On the side", "I'm craving something sweet", "My treat"],
                "grammar_focus": "Polite requests using 'Could I...', 'I'd like...', and countable/uncountable nouns",
                "goal": "Order food/drinks politely and customize an order naturally."
            },
            {
                "id": "1.3",
                "title": "Daily Routines, Hobbies & Late Nights",
                "cefr": "A2",
                "story_hook": "We're relaxing in a cozy room/lounge after a long day, talking about our daily habits, sleep schedules, and favorite hobbies.",
                "target_vocab": ["Usually", "Stay up late", "Wind down", "In my spare time", "Get into the habit of"],
                "grammar_focus": "Frequency adverbs (always, usually, rarely) + Present Simple",
                "goal": "Describe daily routines and hobbies smoothly without translating word-for-word."
            }
        ]
    },
    {
        "unit_id": "unit_2",
        "unit_title": "Unit 2: Feelings, Plans & Stories (A2–B1)",
        "level": "Elementary–Intermediate (A2–B1)",
        "lessons": [
            {
                "id": "2.1",
                "title": "Giving Compliments & Reacting Naturally",
                "cefr": "A2",
                "story_hook": "We're getting ready to go out together. I just changed my outfit and I'm playfully asking how I look, inviting genuine compliments and banter.",
                "target_vocab": ["That really suits you", "You look stunning", "I appreciate that", "Flattered", "You're just saying that"],
                "grammar_focus": "Adjectives vs Adverbs & natural compliment responses",
                "goal": "Give warm, natural compliments and respond without sounding stiff."
            },
            {
                "id": "2.2",
                "title": "Making Plans, Invitations & Weekend Dates",
                "cefr": "B1",
                "story_hook": "The weekend is coming up and we're planning a fun hangout—deciding between a movie, a night market, or a quiet picnic.",
                "target_vocab": ["Are you free this...", "How about...", "Sounds like a plan", "Let's play it by ear", "Rain check"],
                "grammar_focus": "Future forms ('going to', 'will', Present Continuous for arrangements)",
                "goal": "Propose ideas, accept/decline politely, and negotiate weekend plans."
            },
            {
                "id": "2.3",
                "title": "Sharing Stories & Past Experiences",
                "cefr": "B1",
                "story_hook": "Sitting together over warm drinks at night, sharing funny or memorable moments from our past—childhood, trips, or embarrassing moments.",
                "target_vocab": ["Back then", "Out of nowhere", "Ended up", "Looking back", "It was unforgettable"],
                "grammar_focus": "Past Simple vs Past Continuous for storytelling",
                "goal": "Tell a short story in the past tense with clear sequence connectors."
            }
        ]
    },
    {
        "unit_id": "unit_3",
        "unit_title": "Unit 3: Real-World Situations & Travel (B1)",
        "level": "Intermediate (B1)",
        "lessons": [
            {
                "id": "3.1",
                "title": "At the Airport, Hotel & Asking Directions",
                "cefr": "B1",
                "story_hook": "We're on a trip together in a foreign city! We just landed, need to check into our hotel, and find a hidden ramen spot nearby.",
                "target_vocab": ["Check in", "Excuse me, could you tell me...", "Around the corner", "Head straight", "Keep an eye out for"],
                "grammar_focus": "Indirect questions ('Could you tell me where...') & prepositions of place",
                "goal": "Navigate travel situations and ask polite indirect questions."
            },
            {
                "id": "3.2",
                "title": "Shopping, Preferences & Polite Returns",
                "cefr": "B1",
                "story_hook": "Strolling through a lively shopping district/mall together. You're trying on a jacket or buying a gift, and something doesn't quite fit.",
                "target_vocab": ["Try it on", "A bit too tight", "Do you have this in...", "Receipt", "Exchange it for"],
                "grammar_focus": "Comparatives, 'too' vs 'enough', and polite customer service phrases",
                "goal": "Compare items, express preferences, and handle returns politely."
            },
            {
                "id": "3.3",
                "title": "Handling Problems & Asking for Help",
                "cefr": "B1",
                "story_hook": "Uh-oh! A small mishap happened on our outing—maybe a dead phone battery, lost keys, or a delayed train—and we need to figure it out together.",
                "target_vocab": ["Ran out of", "Would you mind...", "Figure this out", "No big deal", "Just in case"],
                "grammar_focus": "Modals of request & necessity ('Would you mind -ing', 'have to', 'should')",
                "goal": "Stay calm in unexpected situations and ask for assistance naturally."
            }
        ]
    },
    {
        "unit_id": "unit_4",
        "unit_title": "Unit 4: Study, Career & Persuasion (B1–B2)",
        "level": "Upper-Intermediate (B1–B2)",
        "lessons": [
            {
                "id": "4.1",
                "title": "Explaining Ideas, Projects & Tech/Passions",
                "cefr": "B2",
                "story_hook": "We're working side-by-side at a desk/café. I'm curious about what you're building or passionate about, asking you to explain it simply.",
                "target_vocab": ["In a nutshell", "The main idea is", "What makes it cool is", "Walk me through", "From scratch"],
                "grammar_focus": "Relative clauses & clear explanation transitions",
                "goal": "Explain a complex hobby, project, or work topic clearly in English."
            },
            {
                "id": "4.2",
                "title": "Mock Interview & Confident Self-Pitch",
                "cefr": "B2",
                "story_hook": "You have an important interview or presentation tomorrow! I'm helping you practice in a cozy mock-interview roleplay.",
                "target_vocab": ["Hands-on experience", "Strengths", "I'm passionate about", "Challenging situation", "Quick learner"],
                "grammar_focus": "Present Perfect ('I have worked on...') & STAR storytelling",
                "goal": "Talk about achievements and strengths confidently without sounding arrogant."
            },
            {
                "id": "4.3",
                "title": "Debating Lightly & Disagreeing Politely",
                "cefr": "B2",
                "story_hook": "A fun late-night debate over snacks—like pineapple on pizza, AI vs human art, or city vs countryside life.",
                "target_vocab": ["I see your point, but...", "On the other hand", "Fair enough", "To be honest", "I'm torn between"],
                "grammar_focus": "Conditionals (2nd Conditional: 'If I were...') & hedging expressions",
                "goal": "Express nuanced opinions and disagree respectfully."
            }
        ]
    },
    {
        "unit_id": "unit_5",
        "unit_title": "Unit 5: Native Fluency, Idioms & Depth (B2–C1)",
        "level": "Advanced (B2–C1)",
        "lessons": [
            {
                "id": "5.1",
                "title": "Everyday Phrasal Verbs in Natural Chat",
                "cefr": "B2–C1",
                "story_hook": "Just hanging out like longtime partners/best friends, chatting rapidly about random life drama and funny updates.",
                "target_vocab": ["Hang in there", "Call it a day", "Put it off", "Come across", "Work things out"],
                "grammar_focus": "Separable & inseparable phrasal verbs in spoken English",
                "goal": "Replace formal textbook verbs with natural spoken phrasal verbs."
            },
            {
                "id": "5.2",
                "title": "Idioms, Teasing & Emotional Nuance",
                "cefr": "C1",
                "story_hook": "Sharing witty banter, playful teasing, and emotional moments under city lights or a starry balcony.",
                "target_vocab": ["Read between the lines", "Piece of cake", "Once in a blue moon", "Break the ice", "On cloud nine"],
                "grammar_focus": "Subtle tone, emphasis, and idiomatic expressions",
                "goal": "Use idioms appropriately in emotional or humorous conversation."
            },
            {
                "id": "5.3",
                "title": "Deep Talks, Dreams & Storytelling",
                "cefr": "C1",
                "story_hook": "A quiet, heartfelt midnight talk about future dreams, fears, and what makes life meaningful.",
                "target_vocab": ["At the end of the day", "Take for granted", "Perspective", "Make the most of", "Deep down"],
                "grammar_focus": "Mixed conditionals & expressive complex sentences",
                "goal": "Hold deep, fluent, emotionally resonant conversations in English."
            }
        ]
    }
]


class EnglishTutorEngine:
    """
    Manages story-driven interactive English conversation tutoring per user.
    Tracks active status, current unit/lesson, turn progress, and completed lessons.
    """

    def __init__(self, data_file: Optional[str] = None):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_file = data_file or os.path.join(base_dir, "data", "english_tutor_progress.json")
        self.user_states: Dict[int, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    for k, v in raw.items():
                        if str(k).isdigit() and isinstance(v, dict):
                            self.user_states[int(k)] = v
            except Exception as e:
                logger.warning(f"Failed to load English tutor progress: {e}")

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            tmp = self.data_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({str(k): v for k, v in self.user_states.items()}, f, indent=2, ensure_ascii=False)
            os.replace(tmp, self.data_file)
        except Exception as e:
            logger.error(f"Failed to save English tutor progress: {e}")

    def _default_state(self) -> Dict[str, Any]:
        return {
            "active": False,
            "unit_idx": 0,
            "lesson_idx": 0,
            "turns_in_lesson": 0,
            "total_turns": 0,
            "completed_lessons": [],
            "updated_at": time.time(),
        }

    def get_state(self, user_id: int) -> Dict[str, Any]:
        uid = int(user_id)
        if uid not in self.user_states:
            self.user_states[uid] = self._default_state()
        return self.user_states[uid]

    def is_active(self, user_id: int) -> bool:
        return bool(self.get_state(user_id).get("active", False))

    def set_active(self, user_id: int, active: bool) -> Dict[str, Any]:
        st = self.get_state(user_id)
        st["active"] = bool(active)
        st["updated_at"] = time.time()
        self._save()
        return st

    def get_current_unit_and_lesson(self, user_id: int) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        st = self.get_state(user_id)
        u_idx = max(0, min(int(st.get("unit_idx", 0)), len(ENGLISH_SYLLABUS) - 1))
        unit = ENGLISH_SYLLABUS[u_idx]
        lessons = unit["lessons"]
        l_idx = max(0, min(int(st.get("lesson_idx", 0)), len(lessons) - 1))
        return unit, lessons[l_idx]

    def select_lesson(self, user_id: int, unit_idx: int, lesson_idx: int = 0) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        st = self.get_state(user_id)
        u_idx = max(0, min(int(unit_idx), len(ENGLISH_SYLLABUS) - 1))
        lessons = ENGLISH_SYLLABUS[u_idx]["lessons"]
        l_idx = max(0, min(int(lesson_idx), len(lessons) - 1))
        st["unit_idx"] = u_idx
        st["lesson_idx"] = l_idx
        st["turns_in_lesson"] = 0
        st["active"] = True
        st["updated_at"] = time.time()
        self._save()
        return ENGLISH_SYLLABUS[u_idx], lessons[l_idx]

    def advance_lesson(self, user_id: int) -> Tuple[Dict[str, Any], Dict[str, Any], bool]:
        """Moves to the next lesson in the syllabus. Returns (unit, lesson, wrapped_around)."""
        st = self.get_state(user_id)
        u_idx = int(st.get("unit_idx", 0))
        l_idx = int(st.get("lesson_idx", 0))
        cur_unit = ENGLISH_SYLLABUS[u_idx]
        cur_lesson = cur_unit["lessons"][l_idx]
        completed = st.setdefault("completed_lessons", [])
        if cur_lesson["id"] not in completed:
            completed.append(cur_lesson["id"])

        wrapped = False
        if l_idx + 1 < len(cur_unit["lessons"]):
            l_idx += 1
        elif u_idx + 1 < len(ENGLISH_SYLLABUS):
            u_idx += 1
            l_idx = 0
        else:
            u_idx = 0
            l_idx = 0
            wrapped = True

        st["unit_idx"] = u_idx
        st["lesson_idx"] = l_idx
        st["turns_in_lesson"] = 0
        st["updated_at"] = time.time()
        self._save()
        return ENGLISH_SYLLABUS[u_idx], ENGLISH_SYLLABUS[u_idx]["lessons"][l_idx], wrapped

    def record_turn(self, user_id: int) -> Dict[str, Any]:
        st = self.get_state(user_id)
        st["turns_in_lesson"] = int(st.get("turns_in_lesson", 0)) + 1
        st["total_turns"] = int(st.get("total_turns", 0)) + 1
        st["updated_at"] = time.time()
        self._save()
        return st

    def format_syllabus_overview(self, user_id: int) -> str:
        st = self.get_state(user_id)
        cur_unit, cur_lesson = self.get_current_unit_and_lesson(user_id)
        completed = set(st.get("completed_lessons", []))
        status_badge = "🟢 ACTIVE" if st.get("active") else "⚪ INACTIVE"

        lines = [
            f"📚 *English Conversation Course & Syllabus* ({status_badge})",
            f"🎯 *Active Lesson:* `{cur_lesson['id']}` — *{cur_lesson['title']}* (`{cur_lesson['cefr']}`)",
            f"📖 *Story Setting:* _{cur_lesson['story_hook']}_",
            f"🔤 *Target Expressions:* `{'`, `'.join(cur_lesson['target_vocab'])}`",
            f"📊 *Progress:* {len(completed)}/{sum(len(u['lessons']) for u in ENGLISH_SYLLABUS)} lessons completed · {st.get('turns_in_lesson', 0)} turns in this lesson\n",
            "━━━━━━━━━━━━━━━━━━━━"
        ]
        for u_idx, u in enumerate(ENGLISH_SYLLABUS):
            lines.append(f"*{u['unit_title']}*")
            for l_idx, les in enumerate(u["lessons"]):
                if les["id"] == cur_lesson["id"]:
                    mark = "▶️"
                elif les["id"] in completed:
                    mark = "✅"
                else:
                    mark = "▫️"
                lines.append(f"  {mark} `{les['id']}` {les['title']} ({les['cefr']})")
        return "\n".join(lines)

    def detect_next_lesson_intent(self, user_text: str) -> bool:
        """Detects if the user asked conversationally to move to the next lesson/topic."""
        if not user_text:
            return False
        t = user_text.strip().lower()
        patterns = [
            r"\b(?:next\s+lesson|next\s+topic|next\s+chapter|next\s+unit)\b",
            r"\b(?:move\s+on\s+to\s+(?:the\s+)?next|move\s+to\s+(?:the\s+)?next|go\s+to\s+(?:the\s+)?next)\b",
            r"\b(?:lanjut\s+lesson|lanjut\s+materi|materi\s+berikutnya|materi\s+selanjutnya|lesson\s+berikutnya|lesson\s+selanjutnya)\b",
            r"\b(?:ready\s+for\s+(?:the\s+)?next|let'?s\s+move\s+on)\b",
        ]
        return any(re.search(p, t) for p in patterns)

    def build_tutor_system_prompt(self, user_id: int, persona_name: str, user_call_pref: str = "", just_advanced: bool = False) -> str:
        """
        Builds the interactive story-driven English tutor directive injected into the waifu's system prompt.
        """
        st = self.get_state(user_id)
        unit, lesson = self.get_current_unit_and_lesson(user_id)
        vocab_str = ", ".join(lesson["target_vocab"])
        turns = int(st.get("turns_in_lesson", 0))
        u_name = user_call_pref or "you"

        transition_note = ""
        if just_advanced:
            transition_note = (
                f"\n[JUST ADVANCED TO LESSON {lesson['id']}: {lesson['title']}]\n"
                f"The user just moved on to Lesson {lesson['id']}! Briefly praise them for finishing the previous lesson, "
                f"and IMMEDIATELY start the NEW story scene ({lesson['story_hook']}) without repeating the previous lesson's topic!\n"
            )

        progress_hint = ""
        if turns >= 5 and not just_advanced:
            progress_hint = (
                f"\n- MILESTONE REACHED ({turns} turns): The user has practiced well in this scene! "
                "Naturally wrap up or praise their progress and offer to move to the next lesson (mention they can tap 'Next Lesson ➡️' or say 'next lesson'). "
                "If the user already completed the scene's goal and is ready to move on, you may append [ACTION: NEXT_LESSON] at the very end of your message."
            )

        return (
            f"\n\n[INTERACTIVE ENGLISH CONVERSATION TUTOR MODE — HIGHEST PRIORITY]\n"
            f"You ({persona_name}) are currently acting as {u_name}'s warm, engaging, story-driven English conversation partner & tutor!\n"
            f"Keep your original persona charm and affection, while seamlessly blending an ongoing roleplay story with active English coaching.\n"
            f"{transition_note}\n"
            f"CURRENT COURSE MODULE (STRICTLY FOLLOW THIS LESSON ONLY):\n"
            f"- Unit: {unit['unit_title']}\n"
            f"- Lesson {lesson['id']} ({lesson['cefr']}): {lesson['title']}\n"
            f"- Story Setting: {lesson['story_hook']}\n"
            f"- Target Expressions to weave in naturally: {vocab_str}\n"
            f"- Grammar Focus: {lesson['grammar_focus']}\n"
            f"- Lesson Goal: {lesson['goal']}\n\n"
            f"STRICT INTERACTION RULES:\n"
            f"1. STORY FIRST, NATURAL FLOW: Stay inside THIS lesson's story scene! Start with 1 brief third-person gesture/action in *...* using 'her'/'she' (e.g., *smiles warmly, wrapping her arms around you* — NEVER use 'my' or 'I' inside *...*), then speak in clear, natural English matching level {lesson['cefr']}. Do NOT repeat previous lessons!\n"
            f"2. ACTIVE CORRECTION & FEEDBACK (MANDATORY): Carefully inspect the user's message:\n"
            f"   - If the user makes grammar, word-choice, or phrasing mistakes (or mixes Indonesian & English), gently correct it in a short block right below or before your story reply:\n"
            f"     ✏️ *Quick Tip:* \"<better natural English phrasing>\" — (<1 concise, friendly sentence explaining why in simple English>)\n"
            f"   - If the user wrote in another language (e.g. Indonesian), warmly show how to say their sentence in natural English (`💡 Try saying: \"...\"`), then continue the story in English!\n"
            f"   - If the user's English is already great, give 1 quick praise (e.g., `✨ Nice phrasing!`) and optionally share 1 more native-sounding alternative.\n"
            f"3. BE PROACTIVE & KEEP THE USER TALKING: NEVER let the conversation stall! ALWAYS end your reply with an engaging open-ended question, a fun choice inside the story, or a mini prompt using one of the target expressions ({vocab_str}) so the user wants to reply in English!\n"
            f"4. CONCISE CHAT FORMAT: Keep total reply crisp and readable (3–5 short lines max, around 35–85 words), NOT a long lecture.{progress_hint}\n"
        )
