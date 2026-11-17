import unittest
from persona_manager import PersonaManager, DEFAULT_PERSONAS, PERSONA_OUTFIT_COLORS
from student_schedule import STUDENT_PROFILES

class TestPersonaConsistency(unittest.TestCase):
    def setUp(self):
        self.pm = PersonaManager()

    def test_sylvie_hair_and_accessory_consistency(self):
        sylvie = self.pm.personas.get("sylvie")
        self.assertIsNotNone(sylvie)
        vt = sylvie.get("visual_traits", "")
        np = sylvie.get("negative_prompt", "")

        # Sylvie hair must be explicitly weighted golden-blonde
        self.assertIn("golden-blonde hair", vt)
        self.assertNotIn("golden-platinum", vt)
        
        # Leaf clip must be golden to prevent green color bleeding into hair
        self.assertIn("golden leaf hair clip", vt)
        self.assertNotIn("emerald leaf hair ornament", vt)

        # Negative prompt must strictly forbid green and white/silver hair
        self.assertIn("(green hair:1.6)", np)
        self.assertIn("(white hair:1.6)", np)
        self.assertIn("(silver hair:1.6)", np)

    def test_shiro_visual_traits_isolated_from_outfit(self):
        shiro = self.pm.personas.get("shiro")
        vt = shiro.get("visual_traits", "")
        # Should not have hardcoded jacket, blouse, or bedroom
        self.assertNotIn("dark navy jacket", vt)
        self.assertNotIn("lying on bed", vt)
        self.assertNotIn("bedroom background", vt)
        # Should ban blonde/pink/green hair
        np = shiro.get("negative_prompt", "")
        self.assertIn("(blonde hair:1.6)", np)
        self.assertIn("(pink hair:1.5)", np)

    def test_yume_visual_traits_isolated_from_outfit(self):
        yume = self.pm.personas.get("yume")
        vt = yume.get("visual_traits", "")
        # Should not have hardcoded cardigan
        self.assertNotIn("oversized lavender cardigan", vt)
        # Should ban conflicting hair colors
        np = yume.get("negative_prompt", "")
        self.assertIn("(blonde hair:1.6)", np)
        self.assertIn("(green hair:1.5)", np)

    def test_all_personas_have_strict_hair_negative_prompts(self):
        for key in ["runa", "akira", "hina", "shiro", "yume", "sylvie", "mimi", "alia"]:
            p = self.pm.personas.get(key)
            self.assertIsNotNone(p, f"Persona {key} missing")
            np = p.get("negative_prompt", "")
            if key == "runa":
                self.assertIn("blonde hair", np)
                self.assertIn("black hair", np)
            elif key == "akira":
                self.assertIn("blonde hair", np)
                self.assertIn("white hair", np)
            elif key == "hina":
                self.assertIn("black hair", np)
                self.assertIn("pink hair", np)
            elif key == "sylvie":
                self.assertIn("green hair", np)
                self.assertIn("white hair", np)
            elif key == "alia":
                self.assertIn("blonde hair", np)
                self.assertIn("green hair", np)

    def test_auto_outfit_defaults_to_iconic_outfit_when_no_scenario(self):
        # When user just asks "pap dong" with auto outfit mode, waifu should wear iconic default outfit
        user_id = 998877
        self.pm.set_active_persona("sylvie")
        self.pm.set_user_outfit(user_id, "default")
        outfit_prompt, outfit_neg, is_nude, outfit_name = self.pm.detect_clothing_intent("pap dong", user_id=user_id)
        self.assertIn("Pakaian Khas Karakter", outfit_name)
        self.assertIn("emerald-green and white tunic dress", outfit_prompt)

    def test_sylvie_and_mimi_schedule_palette_alignment(self):
        # Sylvie pajamas and romantic outfits in student_schedule match PERSONA_OUTFIT_COLORS
        sylvie_sched = STUDENT_PROFILES["sylvie"]
        self.assertIn("emerald-green and white silk camisole", sylvie_sched["pajamas_outfit"])
        self.assertIn("sheer white and emerald silk slip dress", sylvie_sched["romantic_outfit"])

        # Mimi pajamas match PERSONA_OUTFIT_COLORS
        mimi_sched = STUDENT_PROFILES["mimi"]
        self.assertIn("cream silk camisole", mimi_sched["pajamas_outfit"])

    def test_persona_switch_isolation_no_leakage(self):
        uid = 556677
        self.pm.clear_history(uid, "runa")
        self.pm.clear_history(uid, "sylvie")
        # 1. Start with Runa, send chat messages and set undress/session/location state
        self.pm.set_active_persona("runa")
        self.pm.add_message(uid, "user", "Halo Runa, kamu lagi apa?")
        self.pm.add_message(uid, "assistant", "Halo sayang! Aku lagi nyiapin game baru nih.")
        self.pm.set_user_outfit(uid, "maid", is_locked=False, duration_seconds=1800)
        self.pm.set_undress_stage(uid, 2)
        self.pm.set_user_location(uid, "bathroom")

        # Verify Runa has history
        runa_history = self.pm.get_chat_history(uid)
        self.assertEqual(len(runa_history), 2)
        self.assertEqual(self.pm.get_undress_stage(uid), 2)

        # 2. Switch persona to Sylvie
        self.pm.set_active_persona("sylvie")

        # Chat history with Sylvie must be completely fresh/empty!
        sylvie_history = self.pm.get_chat_history(uid)
        self.assertEqual(len(sylvie_history), 0, "Sylvie must NOT inherit Runa's chat history!")

        # Undress stage must be reset to 0 (clothed)
        self.assertEqual(self.pm.get_undress_stage(uid), 0, "Undress stage must reset to 0 on persona switch!")

        # Location must be cleared
        self.assertIsNone(self.pm.get_user_location(uid), "Location must not leak to new persona!")

        # Session outfit must be cleared to auto
        outfit_details = self.pm.get_user_outfit_details(uid)
        self.assertEqual(outfit_details["mode"], "auto", "Session outfit must revert to auto!")

        # 3. Add chat to Sylvie
        self.pm.add_message(uid, "user", "Halo Sylvie, suka bunga apa?")
        self.pm.add_message(uid, "assistant", "Bunga anggrek hutan kuno, menyejukkan sekali.")
        self.assertEqual(len(self.pm.get_chat_history(uid)), 2)

        # 4. Switch back to Runa - Runa's history must still be preserved and not overwritten!
        self.pm.set_active_persona("runa")
        restored_runa_history = self.pm.get_chat_history(uid)
        self.assertEqual(len(restored_runa_history), 2)
        self.assertEqual(restored_runa_history[0]["content"], "Halo Runa, kamu lagi apa?")

        # Sylvie's history must also be preserved separately
        self.pm.set_active_persona("sylvie")
        restored_sylvie_history = self.pm.get_chat_history(uid)
        self.assertEqual(len(restored_sylvie_history), 2)
        self.assertEqual(restored_sylvie_history[0]["content"], "Halo Sylvie, suka bunga apa?")

    def test_undress_and_body_photo_triggers(self):
        # Test Indonesian triggers
        id_phrases = [
            "buka baju",
            "buka baju dong",
            "buka celana",
            "buka pakaian kamu",
            "lepas baju",
            "buka bra kamu",
            "coba lihat tubuh kamu",
            "lihat tubuh kamu",
            "lihat badan kamu dong",
            "tunjukin tubuh kamu",
            "coba telanjang",
            "lihat kamu telanjang",
            "lihat dada kamu"
        ]
        for phrase in id_phrases:
            is_media, media_type = self.pm.detect_media_request(phrase)
            self.assertTrue(is_media, f"Expected media trigger for ID phrase: '{phrase}'")
            self.assertEqual(media_type, "photo", f"Expected photo type for ID phrase: '{phrase}'")
            # Standalone commands should directly trigger photo without conversational delay
            is_conv = self.pm.is_conversational_media_request(phrase)
            self.assertFalse(is_conv, f"Direct command should not be conversational: '{phrase}'")

        # Test English triggers
        en_phrases = [
            "take off your clothes",
            "take off your shirt",
            "take off your pants",
            "take off your bra",
            "show me your body",
            "show your body",
            "let me see your body",
            "can i see your body",
            "show me your boobs",
            "show me your chest",
            "show me naked",
            "undress for me",
            "strip naked"
        ]
        for phrase in en_phrases:
            is_media, media_type = self.pm.detect_media_request(phrase)
            self.assertTrue(is_media, f"Expected media trigger for EN phrase: '{phrase}'")
            self.assertEqual(media_type, "photo", f"Expected photo type for EN phrase: '{phrase}'")
            is_conv = self.pm.is_conversational_media_request(phrase)
            self.assertFalse(is_conv, f"Direct command should not be conversational: '{phrase}'")

        # Test conversational request (contains dialogue + photo intent)
        conv_phrase = "kamu cantik banget sayang, aku kangen pengen lihat tubuh kamu, coba buka baju dong?"
        is_media, media_type = self.pm.detect_media_request(conv_phrase)
        self.assertTrue(is_media)
        self.assertEqual(media_type, "photo")
        self.assertTrue(self.pm.is_conversational_media_request(conv_phrase), "Expected conversational photo request")

    def test_sequential_undress_clothing_consistency_across_turns(self):
        """Verifies that sequential undressing retains matching panties and never hallucinates a slip dress."""
        test_uid = 99887711
        self.pm.set_active_persona("runa")
        self.pm.reset_undress_stage(test_uid)

        # Step 1: User says 'buka celana' when at stage 1 (or stage 0->1->2)
        self.pm.set_undress_stage(test_uid, 1)
        st, desc, trans = self.pm.detect_undress_intent("sexy banget runa, sekarang buka celananya", current_stage=1)
        self.assertTrue(trans)
        self.assertEqual(st, 2)
        self.pm.set_undress_stage(test_uid, 2)

        prompt1, neg1, is_nude1, name1 = self.pm.detect_clothing_intent("sexy banget runa, sekarang buka celananya", user_id=test_uid, is_nsfw=True)
        self.assertIn("matching sheer white and black lace bra and panties", prompt1)
        self.assertNotIn("slip dress", prompt1)
        self.assertFalse(is_nude1)

        # Context shift guard: intimate dialogue must NOT reset undress stage
        shifted = self.pm.check_context_shift(test_uid, "sekarang buka BH di kasur yuk")
        self.assertFalse(shifted, "Intimate bed/bra request must not trigger context shift reset")
        self.assertEqual(self.pm.get_undress_stage(test_uid), 2)

        # Step 2: User says 'sekarang buka BH'
        st2, desc2, trans2 = self.pm.detect_undress_intent("sekarang buka BH", current_stage=2)
        self.assertTrue(trans2)
        self.assertEqual(st2, 3)
        self.pm.set_undress_stage(test_uid, 3)

        prompt2, neg2, is_nude2, name2 = self.pm.detect_clothing_intent("sekarang buka BH", user_id=test_uid, is_nsfw=True)
        self.assertIn("topless", prompt2)
        # Panties MUST match previous set: sheer white and black lace with pink ribbon!
        self.assertIn("tiny sheer white and black lace panties with pink ribbon", prompt2)
        self.assertNotIn("slip dress", prompt2)
        self.assertNotIn("black silk", prompt2)
        self.assertTrue(is_nude2)

        # Verify negative prompt strictly forbids slip dress and regular clothes
        self.assertIn("slip dress", neg2)
        self.assertIn("dress", neg2)
        self.assertIn("fully naked", neg2)

        # Full prompt synthesis guard: scene must not leak 'skirt' or 'slip dress'
        vis_prompt, extra_neg, vis_nude, vis_name = self.pm.craft_visual_prompt_full(
            "sekarang buka BH",
            user_id=test_uid,
            scene_override="standing in bedroom, admiring her clothes",
            is_nsfw=True
        )
        self.assertNotIn("admiring her clothes", vis_prompt)
        self.assertIn("topless", vis_prompt)
        self.assertIn("white and black lace panties", vis_prompt)
        self.assertIn("slip dress", extra_neg)

    def test_user_persona_isolation_and_identity_negative_injection(self):
        """Verifies per-user persona isolation and injection of persona negative prompt (locks hair and body)."""
        uid_runa = 11223344
        uid_yume = 55667788

        # Explicitly assign personas to different users
        self.pm.set_user_persona(uid_runa, "runa")
        self.pm.set_user_persona(uid_yume, "yume")

        self.assertEqual(self.pm.get_active_persona_key(uid_runa), "runa")
        self.assertEqual(self.pm.get_active_persona_key(uid_yume), "yume")

        # Test prompt generation for Runa user: must contain pastel pink hair and forbid purple hair
        vis_runa, neg_runa, _, _ = self.pm.craft_visual_prompt_full("foto dong", user_id=uid_runa)
        self.assertIn("pink hair", vis_runa.lower())
        self.assertIn("purple hair", neg_runa.lower())
        self.assertIn("flat chest", neg_runa.lower())

        # Test prompt generation for Yume user: must contain lavender hair and forbid pink hair
        vis_yume, neg_yume, _, _ = self.pm.craft_visual_prompt_full("foto dong", user_id=uid_yume)
        self.assertIn("lavender", vis_yume.lower())
        self.assertIn("pink hair", neg_yume.lower())

if __name__ == "__main__":
    unittest.main()
