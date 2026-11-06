import unittest
import os
from open_design_engine import OpenDesignEngine, get_open_design_engine

class TestOpenDesignEngine(unittest.TestCase):

    def setUp(self):
        self.ode = get_open_design_engine()

    def test_open_design_available(self):
        self.assertTrue(self.ode.is_available(), "Open-Design should be available with bundled design systems.")
        systems = self.ode.list_available_systems()
        self.assertGreater(len(systems), 50, f"Expected >50 design systems, found {len(systems)}")
        self.assertIn("apple", systems)
        self.assertIn("shadcn", systems)
        self.assertIn("cursor", systems)
        self.assertIn("stripe", systems)

    def test_skills_available(self):
        skills = self.ode.list_available_skills()
        self.assertGreater(len(skills), 20, f"Expected >20 skills, found {len(skills)}")

    def test_is_frontend_or_design_request(self):
        self.assertTrue(self.ode.is_frontend_or_design_request("bikin landing page kopi susu"))
        self.assertTrue(self.ode.is_frontend_or_design_request("buatkan web dashboard crypto"))
        self.assertTrue(self.ode.is_frontend_or_design_request("design button dengan tailwind css"))
        self.assertFalse(self.ode.is_frontend_or_design_request("hitung rumus matematika fisika"))
        self.assertFalse(self.ode.is_frontend_or_design_request("git status"))

    def test_detect_design_style(self):
        self.assertEqual(self.ode.detect_design_style("bikinin website portofolio gaya apple minimal"), "apple")
        self.assertEqual(self.ode.detect_design_style("buatkan dashboard admin analitik penjualan"), "dashboard")
        self.assertEqual(self.ode.detect_design_style("bikin web crypto trading"), "binance")
        self.assertEqual(self.ode.detect_design_style("landing page saas pembayaran fintech"), "stripe")
        self.assertEqual(self.ode.detect_design_style("bikin landing page toko online"), "shopify")
        self.assertEqual(self.ode.detect_design_style("bikin aplikasi web biasa"), "shadcn")

    def test_enhance_coding_prompt(self):
        prompt = "buatkan landing page untuk cafe kopi"
        enhanced, style = self.ode.enhance_coding_prompt(prompt)
        self.assertIsNotNone(style)
        self.assertIn("OPEN-DESIGN SYSTEM ACTIVE", enhanced)
        self.assertIn("ANTI-AI-SLOP", enhanced)

        non_frontend = "tulis script python untuk scrape website"
        enhanced_nf, style_nf = self.ode.enhance_coding_prompt(non_frontend)
        self.assertIsNone(style_nf)
        self.assertEqual(enhanced_nf, non_frontend)

if __name__ == "__main__":
    unittest.main()
