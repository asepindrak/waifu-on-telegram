"""
Unit tests for Visual Novel Scene Detection, Dynamic Image CG Insertion, and Anatomy Guardrails (v2.4.25).
Verifies:
1. detect_visual_scene_moment triggers proactive CG generation for evocative scene moments
   (lap sitting, cuddling, outfit appreciation/teasing, study buddy).
2. craft_visual_prompt_full injects comprehensive negative tokens against leg/limb mutations
   (bad legs, extra legs, folded legs, elongated limbs).
3. get_dimensions returns safe height <= 768 for SD 1.5 9:16 aspect ratio (448x768).
4. Automatic language mirroring directive supports dynamic conversation mirroring.
"""

import unittest
from persona_manager import PersonaManager
from media_engine import MediaEngine


class TestVisualNovelSceneAndAnatomy(unittest.TestCase):
    def setUp(self):
        self.persona_mgr = PersonaManager()

    def test_lap_sitting_scene_moment(self):
        user_msg = "ayo kita istirahat dulu, kamu bisa duduk di paha aku"
        reply_msg = "*excitedly moves to sit on your lap* Ooh, comfy! This is so much better..."
        is_scene, scene_prompt = self.persona_mgr.detect_visual_scene_moment(user_msg, reply_msg)
        self.assertTrue(is_scene, "Lap sitting interaction should trigger visual novel scene CG!")
        self.assertIsNotNone(scene_prompt)
        self.assertIn("sitting on viewer lap", scene_prompt)

    def test_outfit_compliment_scene_moment(self):
        user_msg = "ya, baju kamu sangat cantik dan seksi, tubuh kamu juga harum"
        reply_msg = "Ooh, thank you! I'm glad you think so! *tugs at her skirt playfully* I love wearing cute things..."
        is_scene, scene_prompt = self.persona_mgr.detect_visual_scene_moment(user_msg, reply_msg)
        self.assertTrue(is_scene, "Outfit compliment and teasing should trigger photo!")
        self.assertIsNotNone(scene_prompt)
        self.assertIn("showing cute outfit", scene_prompt)

    def test_cuddling_scene_moment(self):
        user_msg = "sini mendekat sambil kita mengerjakan PR, biar hangat boleh sambil peluk kamu?"
        reply_msg = "*moves closer, her eyes widening with excitement* Oh, that sounds wonderful! *places her hand on your arm*"
        is_scene, scene_prompt = self.persona_mgr.detect_visual_scene_moment(user_msg, reply_msg)
        self.assertTrue(is_scene, "Intimate cuddling should trigger scene photo!")
        self.assertIsNotNone(scene_prompt)
        self.assertIn("cuddle", scene_prompt)

    def test_action_tag_triggers_scene(self):
        user_msg = "kamu lagi ngapain sekarang?"
        reply_msg = "Lagi santai nugas nih, gimana harimu? 💕 [ACTION: SEND_PAP]"
        is_scene, _ = self.persona_mgr.detect_visual_scene_moment(user_msg, reply_msg)
        self.assertTrue(is_scene, "[ACTION: SEND_PAP] should trigger photo!")

    def test_anatomy_guardrails_in_negative_prompt(self):
        prompt, neg, is_nude, outfit_name = self.persona_mgr.craft_visual_prompt_full(
            user_text="kamu bisa duduk di paha aku",
            user_id=12345
        )
        self.assertIn("bad legs", neg)
        self.assertIn("extra legs", neg)
        self.assertIn("folded legs", neg)
        self.assertIn("elongated limbs", neg)
        self.assertIn("multiple legs", neg)

    def test_sd15_aspect_ratio_safety(self):
        # SD 1.5 9:16 should not exceed 768px in height to prevent duplicated legs/torsos
        w, h = MediaEngine.get_dimensions("9:16", is_sdxl=False)
        self.assertEqual(w, 448)
        self.assertEqual(h, 768)
        self.assertLessEqual(h, 768)

    def test_language_mirroring_directive(self):
        directive = PersonaManager.get_language_directive("auto")
        self.assertIn("match the language", directive)

    def test_bus_stop_setting_transition(self):
        # 1. Fair weather bus stop
        user_msg = "kamu lagi di mana? aku udah nyampe di halte bis nih"
        reply_msg = "*duduk di bangku halte sambil melambaikan tangan* Aku udah nungguin kamu dari tadi tau! Sini duduk bareng~"
        is_scene, scene_prompt = self.persona_mgr.detect_visual_scene_moment(user_msg, reply_msg)
        self.assertTrue(is_scene, "Waiting at bus stop should trigger scene photo!")
        self.assertIsNotNone(scene_prompt)
        self.assertIn("bus stop", scene_prompt)

        # 2. Rainy bus stop with umbrella
        user_rain = "hujan lebat banget, aku lagi neduh di halte bis kehujanan"
        reply_rain = "*merapatkan jaket dan memegang payung* Dingin banget yaa, untung ada halte buat berteduh bareng kamu~"
        is_scene_rain, scene_rain_prompt = self.persona_mgr.detect_visual_scene_moment(user_rain, reply_rain)
        self.assertTrue(is_scene_rain)
        self.assertIn("rainy bus stop", scene_rain_prompt)

    def test_campus_lobby_setting_transition(self):
        user_msg = "kelas udah selesai belum? aku nunggu di lobby kampus ya"
        reply_msg = "*berjalan ke arah lobby kampus sambil tersenyum manis* Udah selesai kok! Aku liat kamu di dekat atrium~"
        is_scene, scene_prompt = self.persona_mgr.detect_visual_scene_moment(user_msg, reply_msg)
        self.assertTrue(is_scene, "Campus lobby location should trigger visual scene!")
        self.assertIsNotNone(scene_prompt)
        self.assertIn("university campus lobby", scene_prompt)

    def test_rooftop_and_convenience_store_setting(self):
        # Rooftop sunset
        user_roof = "pemandangannya indah banget ya dari atas rooftop ini pas sunset"
        reply_roof = "*berdiri di tepi balkon rooftop menikmati angin senja* Indah banget ya, apalagi liatnya bareng kamu..."
        is_scene, scene_roof = self.persona_mgr.detect_visual_scene_moment(user_roof, reply_roof)
        self.assertTrue(is_scene)
        self.assertIn("rooftop", scene_roof)

        # Convenience store
        user_mart = "ayo mampir ke minimarket beli es krim dulu"
        reply_mart = "*melihat rak es krim di minimarket* Mau yang rasa cokelat atau matcha nih? Hehe"
        is_scene_mart, scene_mart = self.persona_mgr.detect_visual_scene_moment(user_mart, reply_mart)
        self.assertTrue(is_scene_mart)
        self.assertIn("convenience store", scene_mart)

    def test_extract_contextual_scene_dynamic_accuracy(self):
        # Check that extract_contextual_scene accurately translates story settings into Danbooru tags
        scene_bus = self.persona_mgr.extract_contextual_scene("lagi nunggu di halte bis")
        self.assertIn("bus stop", scene_bus)

        scene_lobby = self.persona_mgr.extract_contextual_scene("ketemuan di lobby kampus")
        self.assertIn("campus lobby", scene_lobby)

        scene_rain = self.persona_mgr.extract_contextual_scene("lagi kehujanan neduh pake payung")
        self.assertIn("sheltering from rain", scene_rain)

    def test_dynamic_llm_assisted_scene_fallback(self):
        class MockLLMClient:
            def chat(self, messages, max_tokens=35, **kwargs):
                return "standing on lakeside wooden pier at twilight, gentle water ripples, lantern glow", None

        mock_llm = MockLLMClient()
        user_msg = "lagi nunggu di dermaga tepi danau sore-sore"
        reply_msg = "*duduk di pinggir dermaga memandangi air danau* Tenang banget ya suasananya..."
        is_scene, scene_prompt = self.persona_mgr.detect_visual_scene_moment(user_msg, reply_msg, llm_client=mock_llm)
        self.assertTrue(is_scene)
        self.assertIn("lakeside wooden pier", scene_prompt)


if __name__ == "__main__":
    unittest.main()

