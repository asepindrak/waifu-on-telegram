import unittest
from unittest.mock import patch, MagicMock
from weather_engine import WeatherEngine, WMO_WEATHER_MAP
from persona_manager import PersonaManager


class TestLiveWeatherEngine(unittest.TestCase):
    def setUp(self):
        self.engine = WeatherEngine()
        self.persona_mgr = PersonaManager()

    def test_city_shortcuts_and_geocoding(self):
        """Test that major Indonesian cities resolve instantly via shortcut dictionary."""
        jkt = self.engine.geocode_city("Jakarta")
        self.assertIsNotNone(jkt)
        self.assertEqual(jkt[2], "Jakarta")
        self.assertAlmostEqual(jkt[0], -6.2088, places=2)

        bdg = self.engine.geocode_city("Bandung")
        self.assertIsNotNone(bdg)
        self.assertEqual(bdg[2], "Bandung")

        sub = self.engine.geocode_city("Surabaya")
        self.assertIsNotNone(sub)
        self.assertEqual(sub[2], "Surabaya")

    def test_wmo_weather_code_interpretation(self):
        """Test that WMO codes correctly map to weather conditions, rain flags, and prompt cues."""
        # 0: Clear
        self.assertIn(0, WMO_WEATHER_MAP)
        name_id, _, is_rain, _, is_clear, pos_out, pos_in, neg_p = WMO_WEATHER_MAP[0]
        self.assertEqual(name_id, "Cerah")
        self.assertFalse(is_rain)
        self.assertTrue(is_clear)

        # 3: Overcast
        self.assertIn(3, WMO_WEATHER_MAP)
        name_id3, _, is_rain3, _, _, pos_out3, _, _ = WMO_WEATHER_MAP[3]
        self.assertIn("Mendung", name_id3)
        self.assertFalse(is_rain3)
        self.assertIn("overcast", pos_out3)

        # 61: Rain
        self.assertIn(61, WMO_WEATHER_MAP)
        name_id61, _, is_rain61, _, _, _, pos_in61, neg61 = WMO_WEATHER_MAP[61]
        self.assertEqual(name_id61, "Hujan Ringan")
        self.assertTrue(is_rain61)
        self.assertIn("raindrops", pos_in61)
        self.assertIn("sunny", neg61)

    def test_get_photo_weather_atmosphere_explicit_user_override(self):
        """Test that explicit user weather words in chat take precedence over live weather."""
        pos, neg = self.engine.get_photo_weather_atmosphere(
            user_text="pap pas lagi hujan deras ya",
            is_indoor=False
        )
        self.assertIn("rain", pos)
        self.assertIn("sunny", neg)

        pos_clear, neg_clear = self.engine.get_photo_weather_atmosphere(
            user_text="lagi cerah banget hari ini, pap dong",
            is_indoor=False
        )
        self.assertIn("clear sky", pos_clear)
        self.assertIn("rain", neg_clear)

    def test_get_photo_weather_atmosphere_live_sync(self):
        """Test that live weather data injects proper visual cues when user hasn't explicitly specified."""
        mock_weather = {
            "city": "Jakarta",
            "temperature": 25.0,
            "condition_id": "Hujan Sedang",
            "condition_en": "Moderate rain",
            "is_rain": True,
            "is_thunderstorm": False,
            "is_cloudy": True,
            "is_clear": False,
            "pos_prompt_indoor": "cozy room lighting, raindrops on window pane, intimate rainy atmosphere",
            "pos_prompt_outdoor": "rainy weather, falling raindrops, wet pavement reflections",
            "neg_prompt": "(bright sunny day:1.5), (clear sky:1.5)",
            "summary_text": "Hujan Sedang (25.0°C)"
        }
        with patch.object(self.engine, "get_weather_for_user", return_value=mock_weather):
            pos_in, neg_in = self.engine.get_photo_weather_atmosphere(user_text="pap senyum kamu", is_indoor=True)
            self.assertIn("raindrops on window pane", pos_in)
            self.assertIn("sunny", neg_in)

            pos_out, neg_out = self.engine.get_photo_weather_atmosphere(user_text="pap senyum kamu", is_indoor=False)
            self.assertIn("falling raindrops", pos_out)

    def test_conversation_context_injection(self):
        """Test that weather engine creates a natural Indonesian conversation hint for waifu."""
        mock_weather = {
            "city": "Bandung",
            "temperature": 22.4,
            "condition_id": "Gerimis",
            "condition_en": "Drizzle"
        }
        with patch.object(self.engine, "get_weather_for_user", return_value=mock_weather):
            ctx = self.engine.get_conversation_context(user_id=123)
            self.assertIn("Bandung", ctx)
            self.assertIn("Gerimis", ctx)
            self.assertIn("22.4°C", ctx)

    def test_persona_manager_lighting_and_weather_integration(self):
        """Test that PersonaManager's get_realtime_lighting_and_atmosphere integrates weather prompts."""
        mock_weather = {
            "city": "Jakarta",
            "temperature": 26.0,
            "condition_id": "Hujan",
            "is_rain": True,
            "is_thunderstorm": False,
            "is_cloudy": True,
            "is_clear": False,
            "pos_prompt_indoor": "raindrops on window pane, cozy rainy mood",
            "pos_prompt_outdoor": "rainy weather, falling raindrops",
            "neg_prompt": "(bright sunny day:1.5)"
        }
        with patch("weather_engine.weather_engine.get_weather_for_user", return_value=mock_weather):
            pos, neg = self.persona_mgr.get_realtime_lighting_and_atmosphere(
                user_text="pap dong lagi santai",
                scene_desc="bedroom",
                user_id=123
            )
            self.assertIn("raindrops on window pane", pos)
            self.assertIn("sunny", neg)


if __name__ == "__main__":
    unittest.main()
