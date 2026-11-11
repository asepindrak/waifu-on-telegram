import unittest
from persona_manager import PersonaManager


class TestPhotoIntentAndCameraAngle(unittest.TestCase):
    def setUp(self):
        self.mgr = PersonaManager(active_key="runa")

    def test_detect_media_request_natural_phrasing(self):
        """Natural Indonesian photo requests without /pap must be recognized reliably."""
        queries = [
            "coba foto dong",
            "fotoin dong",
            "foto lagi rebahan",
            "foto dari atas lagi telentang",
            "mau lihat foto kamu",
            "mana fotonya",
            "spill foto kamu",
            "foto dari samping",
            "foto lagi berdiri",
            "fotonya dong",
            "pap dong",
            "minta pap kamu dong",
            "kirimin fotonya ya",
            "coba pap"
        ]
        for q in queries:
            is_media, media_type = self.mgr.detect_media_request(q)
            self.assertTrue(is_media, f"Failed to detect photo intent for: '{q}'")
            self.assertEqual(media_type, "photo", f"Expected 'photo' for: '{q}', got '{media_type}'")

    def test_detect_camera_angles(self):
        """Recognizes camera perspectives (from above, from below, side, etc.)."""
        # 1. From above / top down
        angle, _ = self.mgr.detect_camera_angle_and_pose("foto dari atas ya")
        self.assertIsNotNone(angle)
        self.assertIn("from above", angle)

        # 2. From below / low angle
        angle_below, _ = self.mgr.detect_camera_angle_and_pose("coba foto dari bawah")
        self.assertIsNotNone(angle_below)
        self.assertIn("from below", angle_below)

        # 3. From side / profile
        angle_side, _ = self.mgr.detect_camera_angle_and_pose("foto dari samping dong")
        self.assertIsNotNone(angle_side)
        self.assertIn("from side", angle_side)

        # 4. From behind
        angle_back, _ = self.mgr.detect_camera_angle_and_pose("foto dari belakang")
        self.assertIsNotNone(angle_back)
        self.assertIn("from behind", angle_back)

    def test_detect_body_poses(self):
        """Recognizes body poses (lying down, lying on back / telentang, standing, sitting)."""
        # 1. Telentang / supine
        _, pose_supine = self.mgr.detect_camera_angle_and_pose("foto lagi telentang di kasur")
        self.assertIsNotNone(pose_supine)
        self.assertIn("lying on back", pose_supine)

        # 2. Rebahan / lying down
        _, pose_recline = self.mgr.detect_camera_angle_and_pose("coba pap lagi rebahan santai")
        self.assertIsNotNone(pose_recline)
        self.assertIn("lying down", pose_recline)

        # 3. Berdiri / standing
        _, pose_stand = self.mgr.detect_camera_angle_and_pose("foto kamu lagi berdiri full body")
        self.assertIsNotNone(pose_stand)
        self.assertIn("standing pose", pose_stand)

        # 4. Duduk / sitting
        _, pose_sit = self.mgr.detect_camera_angle_and_pose("foto lagi duduk manis")
        self.assertIsNotNone(pose_sit)
        self.assertIn("sitting pose", pose_sit)

    def test_combined_angle_and_pose_in_visual_prompt(self):
        """Visual prompt includes both requested camera angle and pose."""
        user_req = "kirim foto dari atas pas kamu lagi telentang di kasur"
        prompt, _, _, _ = self.mgr.craft_visual_prompt_full(user_req)

        self.assertIn("from above", prompt)
        self.assertIn("lying on back", prompt)
        self.assertIn("pillow", prompt)


if __name__ == "__main__":
    unittest.main()

