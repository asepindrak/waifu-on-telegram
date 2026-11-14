import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from persona_manager import (
    PersonaManager,
    build_custom_persona,
    ARCHETYPE_PRESETS,
    BODY_PRESETS,
    LORE_PRESETS,
    CUSTOM_PERSONA_OUTFIT_PRESETS
)


class TestCustomPersonaBuilder(unittest.TestCase):
    def test_presets_structure(self):
        self.assertIn("tsundere", ARCHETYPE_PRESETS)
        self.assertIn("kuudere", ARCHETYPE_PRESETS)
        self.assertIn("elf", ARCHETYPE_PRESETS)
        self.assertIn("nekomimi", ARCHETYPE_PRESETS)
        self.assertIn("petite_curvy", BODY_PRESETS)
        self.assertIn("hourglass_curvy", BODY_PRESETS)
        self.assertIn("elven_slender", BODY_PRESETS)
        self.assertIn("nekomimi_petite", BODY_PRESETS)
        self.assertIn("roommate", LORE_PRESETS)
        self.assertIn("childhood", LORE_PRESETS)
        self.assertIn("fantasy_elf", LORE_PRESETS)
        self.assertIn("fantasy_nekomimi", LORE_PRESETS)
        self.assertIn("casual", CUSTOM_PERSONA_OUTFIT_PRESETS)
        self.assertIn("streetwear", CUSTOM_PERSONA_OUTFIT_PRESETS)

    def test_nekomimi_persona_negative_prompt_adaptation(self):
        persona = build_custom_persona(
            name="Mimi",
            archetype="nekomimi",
            visual_traits="cute fluffy cat ears, playful tail, chocolate brown hair",
            outfit="casual",
            body_type="nekomimi_petite",
            lore="fantasy_nekomimi",
            age=21
        )
        self.assertEqual(persona["name"], "Mimi")
        self.assertNotIn("cat ears, animal ears, animal tail", persona["negative_prompt"])
        self.assertIn("missing cat ears", persona["negative_prompt"])
        self.assertIn("cat ears", persona["visual_traits"])

    def test_built_in_mimi_persona_loaded(self):
        pm = PersonaManager()
        self.assertIn("mimi", pm.personas)
        mimi = pm.personas["mimi"]
        self.assertEqual(mimi["name"], "Mimi")
        self.assertIn("cat ears", mimi["visual_traits"])
        self.assertIn("Nekomimi", mimi["archetype"])

    def test_build_custom_persona_with_presets(self):
        persona = build_custom_persona(
            name="Elysia",
            archetype="tsundere",
            visual_traits="long lavender hair, violet eyes, white ribbon",
            outfit="casual",
            body_type="petite_curvy",
            lore="roommate",
            age=21
        )
        self.assertEqual(persona["name"], "Elysia")
        self.assertEqual(persona["age"], 21)
        self.assertIn("Elysia", persona["system_instruction"])
        self.assertIn("young adult anime woman", persona["visual_traits"])
        self.assertIn("C-cup medium breasts", persona["visual_traits"])
        self.assertIn("petite curvy adult body", persona["visual_traits"])
        self.assertIn("(child:1.4)", persona["negative_prompt"])
        self.assertIn("(bad breasts:1.3)", persona["negative_prompt"])
        self.assertIsNotNone(persona.get("initial_greeting"))

    def test_build_custom_persona_with_manual_lore_and_body(self):
        persona = build_custom_persona(
            name="Seraphina",
            archetype="Onee-san Pelindung",
            visual_traits="silver hair, crimson eyes",
            outfit="elegant evening gown",
            body_type="tall curvaceous hourglass figure, D-cup large breasts, shapely bust",
            lore="Kakak tingkat yang sering mentraktir kopi dan mendampingi riset lab",
            age=22
        )
        self.assertEqual(persona["name"], "Seraphina")
        self.assertIn("D-cup large breasts", persona["visual_traits"])
        self.assertIn("mentraktir kopi", persona["system_instruction"])

    def test_build_custom_persona_with_mock_llm_enrichment(self):
        mock_llm = MagicMock()
        mock_llm.chat.side_effect = [
            ("long silver hair, glowing crimson eyes, black rose hairpin", None),  # visual Danbooru
            ("Nama kamu Seraphina, mahasiswi tingkat akhir yang anggun dan sangat menyayangi pasanganmu.", None),  # system instruction
            ("Halo sayang! Akhirnya kita bisa ngobrol santai berdua... ✨", None)  # initial greeting
        ]

        persona = build_custom_persona(
            name="Seraphina",
            archetype="oneesan",
            visual_traits="rambut perak panjang, mata merah menyala, jepit mawar hitam",
            outfit="dress",
            body_type="hourglass_curvy",
            lore="campus_junior",
            llm_client=mock_llm
        )
        self.assertEqual(persona["name"], "Seraphina")
        self.assertIn("glowing crimson eyes", persona["visual_traits"])
        self.assertIn("D-cup large breasts", persona["visual_traits"])
        self.assertEqual(persona["initial_greeting"], "Halo sayang! Akhirnya kita bisa ngobrol santai berdua... ✨")

    def test_telegram_wizard_state_progression(self):
        import bot
        user_id = 987654
        chat_id = 123456
        bot.USER_PERSONA_WIZARD[user_id] = {"step": "name", "data": {}}

        # Step 1: Input name
        msg_name = MagicMock()
        msg_name.from_user.id = user_id
        msg_name.chat.id = chat_id
        msg_name.text = "Aoi"
        with patch.object(bot.bot, "reply_to") as mock_reply:
            consumed = bot.handle_persona_wizard_input(msg_name)
            self.assertTrue(consumed)
            self.assertEqual(bot.USER_PERSONA_WIZARD[user_id]["step"], "archetype")
            self.assertEqual(bot.USER_PERSONA_WIZARD[user_id]["data"]["name"], "Aoi")

        # Step 2: Choose archetype via callback
        call_arch = MagicMock()
        call_arch.from_user.id = user_id
        call_arch.message.chat.id = chat_id
        call_arch.message.message_id = 111
        call_arch.data = "wizard_arch:kuudere"
        with patch("bot.is_authorized", return_value=True), \
             patch.object(bot.bot, "answer_callback_query"), \
             patch.object(bot.bot, "edit_message_text"):
            bot.callback_persona_wizard(call_arch)
            self.assertEqual(bot.USER_PERSONA_WIZARD[user_id]["step"], "body")

        # Step 3: Choose body via callback
        call_body = MagicMock()
        call_body.from_user.id = user_id
        call_body.message.chat.id = chat_id
        call_body.message.message_id = 111
        call_body.data = "wizard_body:slender_graceful"
        with patch("bot.is_authorized", return_value=True), \
             patch.object(bot.bot, "answer_callback_query"), \
             patch.object(bot.bot, "edit_message_text"):
            bot.callback_persona_wizard(call_body)
            self.assertEqual(bot.USER_PERSONA_WIZARD[user_id]["step"], "visual")
            self.assertEqual(bot.USER_PERSONA_WIZARD[user_id]["data"]["body"], "slender_graceful")

        # Step 4: Input visual traits
        msg_vis = MagicMock()
        msg_vis.from_user.id = user_id
        msg_vis.chat.id = chat_id
        msg_vis.text = "short dark blue hair, silver glasses, pale skin"
        with patch.object(bot.bot, "reply_to"):
            consumed = bot.handle_persona_wizard_input(msg_vis)
            self.assertTrue(consumed)
            self.assertEqual(bot.USER_PERSONA_WIZARD[user_id]["step"], "lore")

        # Step 5: Choose lore via callback
        call_lore = MagicMock()
        call_lore.from_user.id = user_id
        call_lore.message.chat.id = chat_id
        call_lore.message.message_id = 111
        call_lore.data = "wizard_lore:childhood"
        with patch("bot.is_authorized", return_value=True), \
             patch.object(bot.bot, "answer_callback_query"), \
             patch.object(bot.bot, "edit_message_text"):
            bot.callback_persona_wizard(call_lore)
            self.assertEqual(bot.USER_PERSONA_WIZARD[user_id]["step"], "outfit")
            self.assertEqual(bot.USER_PERSONA_WIZARD[user_id]["data"]["lore"], "childhood")

        # Step 6: Choose outfit via callback
        call_outfit = MagicMock()
        call_outfit.from_user.id = user_id
        call_outfit.message.chat.id = chat_id
        call_outfit.message.message_id = 111
        call_outfit.data = "wizard_outfit:school"
        with patch("bot.is_authorized", return_value=True), \
             patch.object(bot.bot, "answer_callback_query"), \
             patch("bot.show_persona_wizard_preview"):
            bot.callback_persona_wizard(call_outfit)
            self.assertEqual(bot.USER_PERSONA_WIZARD[user_id]["data"]["outfit"], "school")


if __name__ == "__main__":
    unittest.main()
