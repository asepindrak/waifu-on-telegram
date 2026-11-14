import unittest
import time
from persona_manager import PersonaManager, LOCATION_PRESETS, INTIMATE_SEX_POSITIONS


class TestNsfwPositionsAndLocationLock(unittest.TestCase):
    def setUp(self):
        self.mgr = PersonaManager()
        self.test_user_id = 998877
        self.mgr.clear_user_location(self.test_user_id)
        if hasattr(self.mgr, "user_recent_angles"):
            self.mgr.user_recent_angles[self.test_user_id] = []

    def tearDown(self):
        self.mgr.clear_user_location(self.test_user_id)

    def test_intimate_positions_detection(self):
        """Test that intimate positions are detected with correct prompts and negative prompts."""
        # 1. Doggy style / Nungging
        pos, neg = self.mgr.detect_intimate_position("coba pap posisi doggy style dong")
        self.assertIsNotNone(pos)
        self.assertIn("doggy style", pos)
        self.assertIn("on all fours", pos)
        self.assertIn("rear view", pos)
        self.assertIn("standing", neg)

        pos_nungging, _ = self.mgr.detect_intimate_position("pap lagi nungging dari belakang")
        self.assertIsNotNone(pos_nungging)
        self.assertIn("doggy style", pos_nungging)

        # 2. Missionary / Misionaris
        pos_m, neg_m = self.mgr.detect_intimate_position("foto posisi missionary ya")
        self.assertIsNotNone(pos_m)
        self.assertIn("missionary", pos_m)
        self.assertIn("view from above", pos_m)
        self.assertIn("rear view", neg_m)

        pos_ngangkang, _ = self.mgr.detect_intimate_position("posisi telentang kaki terbuka lebar")
        self.assertIsNotNone(pos_ngangkang)
        self.assertIn("missionary", pos_ngangkang)

        # 3. Cowgirl / Di atas
        pos_cg, neg_cg = self.mgr.detect_intimate_position("aku mau kamu posisi cowgirl di atas")
        self.assertIsNotNone(pos_cg)
        self.assertIn("cowgirl", pos_cg)
        self.assertIn("straddling", pos_cg)
        self.assertIn("lying flat", neg_cg)

        # 4. Mating press
        pos_mp, _ = self.mgr.detect_intimate_position("pap posisi mating press kaki ditekuk ke dada")
        self.assertIsNotNone(pos_mp)
        self.assertIn("mating press", pos_mp)
        self.assertIn("legs folded up", pos_mp)

        # 5. Prone bone
        pos_pb, _ = self.mgr.detect_intimate_position("posisi prone bone tengkurap pasrah")
        self.assertIsNotNone(pos_pb)
        self.assertIn("prone bone", pos_pb)
        self.assertIn("lying flat on stomach", pos_pb)

        # 6. Standing against wall
        pos_stand, _ = self.mgr.detect_intimate_position("posisi berdiri nempel tembok")
        self.assertIsNotNone(pos_stand)
        self.assertIn("standing against wall", pos_stand)

    def test_visual_prompt_locks_camera_and_bypasses_random_angle(self):
        """Test that requesting an intimate position locks the camera angle in craft_visual_prompt_full."""
        prompt, extra_neg, _, _ = self.mgr.craft_visual_prompt_full(
            "pap posisi doggy style",
            user_id=self.test_user_id,
            is_nsfw=True
        )
        self.assertIn("doggy style", prompt)
        self.assertIn("rear view from behind", prompt)
        self.assertIn("standing", extra_neg)

        prompt_m, extra_neg_m, _, _ = self.mgr.craft_visual_prompt_full(
            "pap posisi missionary",
            user_id=self.test_user_id,
            is_nsfw=True
        )
        self.assertIn("missionary", prompt_m)
        self.assertIn("view from above looking down", prompt_m)
        self.assertIn("rear view", extra_neg_m)

    def test_location_locking_and_transitions(self):
        """Test that active location is locked and persists across chats until transitioned."""
        # 1. User mentions cooking in kitchen
        scene1 = self.mgr.extract_contextual_scene(
            "Yuk kita masak di dapur bareng",
            user_id=self.test_user_id
        )
        self.assertIn("kitchen", scene1.lower())

        # Verify active location is locked in state
        loc = self.mgr.get_user_location(self.test_user_id)
        self.assertIsNotNone(loc)
        self.assertEqual(loc["key"], "kitchen")

        # 2. Subsequent chat has NO location mention (e.g. asking for photo of smile)
        scene2 = self.mgr.extract_contextual_scene(
            "Wanginya enak banget, pap dong senyum kamu",
            user_id=self.test_user_id
        )
        # MUST still be in kitchen!
        self.assertIn("kitchen", scene2.lower())

        # 3. User explicitly moves to living room / TV
        scene3 = self.mgr.extract_contextual_scene(
            "Udah kenyang nih, yuk pindah ke ruang tv santai di sofa",
            user_id=self.test_user_id
        )
        self.assertIn("sofa", scene3.lower())
        loc3 = self.mgr.get_user_location(self.test_user_id)
        self.assertEqual(loc3["key"], "living_room")

        # 4. Subsequent chat in living room still locks to sofa / living room
        scene4 = self.mgr.extract_contextual_scene(
            "Pap dong lagi nonton",
            user_id=self.test_user_id
        )
        self.assertIn("sofa", scene4.lower())

        # 5. User moves to cafe
        scene5 = self.mgr.extract_contextual_scene(
            "Yuk nongkrong ngopi di kafe",
            user_id=self.test_user_id
        )
        self.assertIn("cafe", scene5.lower())
        self.assertEqual(self.mgr.get_user_location(self.test_user_id)["key"], "cafe")

        # 6. Subsequent chat in cafe still stays in cafe
        scene6 = self.mgr.extract_contextual_scene(
            "Kopinya enak ya, pap wajah manis kamu",
            user_id=self.test_user_id
        )
        self.assertIn("cafe", scene6.lower())

        # 7. User moves to campus
        scene7 = self.mgr.extract_contextual_scene(
            "Sekarang kita ke kampus kuliah ya",
            user_id=self.test_user_id
        )
        self.assertIn("campus", scene7.lower())
        self.assertEqual(self.mgr.get_user_location(self.test_user_id)["key"], "campus")

    def test_nsfw_location_adaptation_and_public_safety(self):
        """Test that private locked locations adapt for NSFW, and public locations fall back to bedroom."""
        # 1. Private location: Kitchen
        self.mgr.set_user_location(self.test_user_id, "kitchen")
        nsfw_scene_kitchen = self.mgr.extract_contextual_scene(
            "pap tanpa busana",
            user_id=self.test_user_id,
            is_nsfw=True
        )
        self.assertIn("kitchen counter", nsfw_scene_kitchen.lower())

        # Combined kitchen + doggy style
        prompt, _, _, _ = self.mgr.craft_visual_prompt_full(
            "pap posisi doggy style",
            user_id=self.test_user_id,
            is_nsfw=True
        )
        self.assertIn("kitchen counter", prompt.lower())
        self.assertIn("doggy style", prompt.lower())

        # 2. Private location: Living room couch
        self.mgr.set_user_location(self.test_user_id, "living_room")
        nsfw_scene_lr = self.mgr.extract_contextual_scene(
            "pap telanjang",
            user_id=self.test_user_id,
            is_nsfw=True
        )
        self.assertIn("couch", nsfw_scene_lr.lower())

        # 3. Public location: Cafe (Must NOT allow public nudity -> falls back to private bedroom)
        self.mgr.set_user_location(self.test_user_id, "cafe")
        nsfw_scene_cafe = self.mgr.extract_contextual_scene(
            "pap telanjang bulat",
            user_id=self.test_user_id,
            is_nsfw=True
        )
        self.assertIn("bedroom", nsfw_scene_cafe.lower())
        self.assertNotIn("cafe", nsfw_scene_cafe.lower())

        # 4. Public location: Campus (Must fall back to private bedroom for NSFW)
        self.mgr.set_user_location(self.test_user_id, "campus")
        nsfw_scene_campus = self.mgr.extract_contextual_scene(
            "pap nude",
            user_id=self.test_user_id,
            is_nsfw=True
        )
        self.assertIn("bedroom", nsfw_scene_campus.lower())
        self.assertNotIn("lecture hall", nsfw_scene_campus.lower())


if __name__ == "__main__":
    unittest.main()

