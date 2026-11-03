import os
import unittest
from unittest.mock import MagicMock, patch
from routing_engine import detect_nsfw_intent, HybridLLMClient, PROVIDER_PRESETS
from lu_llm_client import LocallyUncensoredClient
from media_engine import MediaEngine


class TestRoutingEngine(unittest.TestCase):
    def test_nsfw_intent_detection(self):
        """Tests accurate detection of SFW vs NSFW conversation turns."""
        # SFW cases
        self.assertFalse(detect_nsfw_intent("Halo apa kabar?"))
        self.assertFalse(detect_nsfw_intent("Hari ini ada tugas kuliah apa aja?"))
        self.assertFalse(detect_nsfw_intent("Nanti mau makan siang bareng anak kantor jam 1"))
        self.assertFalse(detect_nsfw_intent("Coba bantuin bikin kodingan Python dong"))
        self.assertFalse(detect_nsfw_intent("Lagi dengerin musik apa sekarang?"))

        # NSFW cases - Nudity & Stripping
        self.assertTrue(detect_nsfw_intent("Kirim foto tanpa busana dong"))
        self.assertTrue(detect_nsfw_intent("Coba lepas baju kamu sekarang"))
        self.assertTrue(detect_nsfw_intent("Mau liat kamu telanjang di kasur"))
        self.assertTrue(detect_nsfw_intent("Foto nude dong"))
        self.assertTrue(detect_nsfw_intent("Gak pake pakaian ya"))

        # NSFW cases - Erotic / Intimate / Adult
        self.assertTrue(detect_nsfw_intent("Aku lagi sange banget nih"))
        self.assertTrue(detect_nsfw_intent("Mau bercinta sama kamu malam ini"))
        self.assertTrue(detect_nsfw_intent("Pengen denger kamu mendesah"))
        self.assertTrue(detect_nsfw_intent("*meraba paha dan payudara kamu*"))
        self.assertTrue(detect_nsfw_intent("Pakai lingerie seksi transparan dong"))

    def test_hybrid_client_unified_mode(self):
        """Unified mode uses single client for all requests."""
        mock_client = MagicMock(spec=LocallyUncensoredClient)
        mock_client.chat.return_value = ("Balasan santai", "")
        mock_client.base_url = "http://127.0.0.1:5001/v1"
        mock_client.model = "default"
        mock_client.check_health.return_value = {"online": True, "backend": "KoboldCPP"}

        hybrid = HybridLLMClient(mode="unified", sfw_client=mock_client, nsfw_client=mock_client)
        self.assertFalse(hybrid.is_split_mode())

        reply, _ = hybrid.chat([{"role": "user", "content": "Halo apa kabar"}])
        self.assertEqual(reply, "Balasan santai")
        mock_client.chat.assert_called_once()

    def test_hybrid_client_split_dispatch(self):
        """Split mode dispatches SFW to SFW provider and NSFW to NSFW provider."""
        mock_sfw = MagicMock(spec=LocallyUncensoredClient)
        mock_sfw.chat.return_value = ("Jawaban ramah dari OpenAI", "")
        mock_sfw.base_url = "https://api.openai.com/v1"
        mock_sfw.model = "gpt-4o-mini"
        mock_sfw.check_health.return_value = {"online": True, "backend": "OpenAI"}

        mock_nsfw = MagicMock(spec=LocallyUncensoredClient)
        mock_nsfw.chat.return_value = ("Balasan mesra & uncensored dari KoboldCPP", "")
        mock_nsfw.base_url = "http://127.0.0.1:5001/v1"
        mock_nsfw.model = "Huihui-Qwythos-9B"
        mock_nsfw.check_health.return_value = {"online": True, "backend": "KoboldCPP"}

        hybrid = HybridLLMClient(mode="split", sfw_client=mock_sfw, nsfw_client=mock_nsfw)
        self.assertTrue(hybrid.is_split_mode())
        self.assertTrue(hybrid.is_sfw_cloud())
        self.assertTrue(hybrid.is_nsfw_local())

        # 1. Send SFW message
        reply_sfw, _ = hybrid.chat([{"role": "user", "content": "Hari ini belajar apa?"}])
        self.assertEqual(reply_sfw, "Jawaban ramah dari OpenAI")
        mock_sfw.chat.assert_called_once()
        mock_nsfw.chat.assert_not_called()

        # 2. Send NSFW message
        reply_nsfw, _ = hybrid.chat([{"role": "user", "content": "Kirim foto tanpa busana dong sayang"}])
        self.assertEqual(reply_nsfw, "Balasan mesra & uncensored dari KoboldCPP")
        mock_nsfw.chat.assert_called_once()

    def test_hybrid_client_safety_fallback(self):
        """If SFW provider triggers content policy rejection, auto-failover to uncensored engine."""
        mock_sfw = MagicMock(spec=LocallyUncensoredClient)
        mock_sfw.base_url = "https://api.openai.com/v1"
        mock_sfw.model = "gpt-4o-mini"
        mock_sfw.chat.side_effect = RuntimeError("400 Client Error: content_policy_violation - Request rejected by safety filters")

        mock_nsfw = MagicMock(spec=LocallyUncensoredClient)
        mock_nsfw.base_url = "http://127.0.0.1:5001/v1"
        mock_nsfw.model = "default"
        mock_nsfw.chat.return_value = ("Balasan aman dari local uncensored model", "")

        hybrid = HybridLLMClient(mode="split", sfw_client=mock_sfw, nsfw_client=mock_nsfw)
        # Even if tagged as is_nsfw=False initially, failure triggers auto-fallback to NSFW uncensored
        reply, _ = hybrid.chat([{"role": "user", "content": "Pertanyaan agak nakal"}], is_nsfw=False)
        self.assertEqual(reply, "Balasan aman dari local uncensored model")
        mock_nsfw.chat.assert_called_once()

    def test_media_engine_checkpoint_routing(self):
        """MediaEngine resolves separate checkpoints for SFW and NSFW."""
        engine = MediaEngine(comfyui_url="http://127.0.0.1:8188")
        engine.get_available_checkpoints = MagicMock(return_value=[
            "AnythingXL_xl.safetensors",
            "AOM3A1B_orangemixs.safetensors",
            "meinamix_v12Final.safetensors"
        ])

        with patch.dict(os.environ, {
            "SFW_COMFYUI_CHECKPOINT": "AnythingXL_xl.safetensors",
            "NSFW_COMFYUI_CHECKPOINT": "AOM3A1B_orangemixs.safetensors"
        }):
            sfw_ckpt = engine.get_active_checkpoint(is_nude=False)
            self.assertEqual(sfw_ckpt, "AnythingXL_xl.safetensors")

            nsfw_ckpt = engine.get_active_checkpoint(is_nude=True)
            self.assertEqual(nsfw_ckpt, "AOM3A1B_orangemixs.safetensors")


if __name__ == "__main__":
    unittest.main()
