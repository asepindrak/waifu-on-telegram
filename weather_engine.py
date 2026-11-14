"""
waifu-on-telegram: Live Realtime Weather Engine
Fetches live realtime weather from Open-Meteo (100% Free, No API Key Required).
Seamlessly syncs real-world weather with AI photo lighting, backgrounds, and conversational awareness.
"""

import os
import re
import time
import json
import logging
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("WeatherEngine")

# WMO Weather Interpretation Codes (WW)
# Code -> (name_id, name_en, is_rain, is_thunderstorm, is_clear, pos_prompt_outdoor, pos_prompt_indoor, neg_prompt)
WMO_WEATHER_MAP: Dict[int, Tuple[str, str, bool, bool, bool, str, str, str]] = {
    0: (
        "Cerah", "Clear sky", False, False, True,
        "clear blue sky, natural bright sunlight, beautiful outdoor weather",
        "clear bright natural daylight streaming through window",
        "(rain:1.5), (overcast:1.4), (storm:1.5), cloudy sky, puddles"
    ),
    1: (
        "Cerah Berawan", "Mainly clear", False, False, True,
        "mostly clear sky with few light clouds, pleasant bright daylight",
        "soft pleasant natural sunlight through window",
        "(heavy rain:1.5), (thunderstorm:1.5), dark stormy sky"
    ),
    2: (
        "Berawan Sebagian", "Partly cloudy", False, False, False,
        "partly cloudy sky, soft natural daylight, gentle breeze",
        "pleasant natural room lighting, soft daylight outside window",
        "(heavy rain:1.5), (thunderstorm:1.5)"
    ),
    3: (
        "Mendung / Berawan Tebal", "Overcast", False, False, False,
        "overcast cloudy sky, soft diffused natural daylight, gentle breeze, cool atmospheric lighting",
        "diffused soft ambient daylight, overcast sky visible outside window, cool indoor mood",
        "(harsh direct sunlight:1.5), (bright sunny sky:1.4), (harsh sunbeams:1.4)"
    ),
    45: (
        "Berkabut", "Foggy", False, False, False,
        "atmospheric light fog, soft misty mood, cinematic depth of field",
        "cozy soft morning indoor lighting, misty window glass",
        "(harsh midday sun:1.5)"
    ),
    48: (
        "Kabut Tebal", "Depositing rime fog", False, False, False,
        "thick atmospheric fog, misty air, cinematic soft bokeh",
        "soft dim ambient room lighting, foggy background outside",
        "(bright direct sunlight:1.5)"
    ),
    51: (
        "Gerimis Ringan", "Light drizzle", True, False, False,
        "gentle light drizzle, delicate raindrops, wet reflections on ground, cozy romantic rainy day atmosphere",
        "cozy warm room lamp lighting, soft rain drops and moisture on window pane, cozy rainy mood",
        "(bright sunny day:1.5), (harsh midday sun:1.5), (clear sky:1.5)"
    ),
    53: (
        "Gerimis", "Moderate drizzle", True, False, False,
        "light drizzle, soft falling raindrops, wet pavement reflections, romantic cozy rainy atmosphere",
        "cozy warm room lamp, gentle raindrops on window glass, intimate rainy day atmosphere",
        "(bright sunny day:1.5), (clear blue sky:1.5)"
    ),
    55: (
        "Gerimis Lebat", "Dense drizzle", True, False, False,
        "continuous drizzle, misty rain atmosphere, wet reflections, overcast rainy sky",
        "dim cozy room lighting, rain droplets streaming on window glass, comforting rainy day mood",
        "(bright sunny day:1.5), (clear blue sky:1.5)"
    ),
    61: (
        "Hujan Ringan", "Slight rain", True, False, False,
        "rainy weather, falling raindrops, wet reflections on surfaces, atmospheric street lighting, cozy rain ambience",
        "warm cozy indoor lighting, raindrops visible on window glass, rainy day room ambiance",
        "(bright sunny day:1.5), (clear sky:1.5), (sunny:1.5)"
    ),
    63: (
        "Hujan Sedang", "Moderate rain", True, False, False,
        "moderate rain, visible falling rain droplets, wet pavement reflections, dynamic rainy weather, cinematic rain",
        "dim warm cozy room lamp lighting, rain sliding down window pane, intimate indoor rainy mood",
        "(bright sunny day:1.5), (harsh sun:1.5), (clear blue sky:1.5)"
    ),
    65: (
        "Hujan Lebat", "Heavy rain", True, False, False,
        "heavy rain, dark overcast rainy sky, intense falling rain, dramatic wet reflections, cinematic rainy atmosphere",
        "soft cozy indoor room lighting, heavy rain pouring outside window, warm comforting indoor refuge",
        "(bright sunny day:1.5), (clear sky:1.5), (sunshine:1.5)"
    ),
    71: (
        "Salju Ringan", "Slight snow", False, False, False,
        "gentle falling snowflakes, light snow on ground, winter chill, soft winter daylight",
        "warm indoor heater lighting, falling snowflakes visible outside window, cozy winter mood",
        "summer beach, scorching sun"
    ),
    73: (
        "Salju Sedang", "Moderate snow", False, False, False,
        "falling snow, snowy winter landscape, picturesque snow aesthetic",
        "cozy warm room, snowy window view, soft winter ambient",
        "summer beach, bright sun"
    ),
    75: (
        "Salju Lebat", "Heavy snow", False, False, False,
        "heavy snowfall, winter wonderland, thick snow aesthetic",
        "warm room, snow piled on window sill, winter chill mood",
        "summer beach, bright sun"
    ),
    80: (
        "Hujan Deras Sesaat", "Slight rain showers", True, False, False,
        "passing rain showers, glistening wet surfaces, dynamic overcast sky, atmospheric reflections",
        "cozy room, rain shower outside window, soft moody ambient",
        "(bright sunny day:1.5)"
    ),
    81: (
        "Hujan Deras", "Moderate rain showers", True, False, False,
        "heavy rain showers, dark rainy clouds, rain streaks, wet reflections on ground",
        "cozy room with warm lamp, rain pelting window pane, relaxed indoor retreat",
        "(bright sunny day:1.5), (clear sky:1.5)"
    ),
    82: (
        "Hujan Sangat Deras", "Violent rain showers", True, False, False,
        "torrential downpour rain, intense dark clouds, heavy falling water, dramatic wet environment",
        "warm cozy indoor refuge, heavy torrential downpour against window glass",
        "(bright sunny day:1.5), (clear sky:1.5)"
    ),
    95: (
        "Badai Petir", "Thunderstorm", True, True, False,
        "stormy thunderstorm weather, dramatic dark storm clouds, heavy rain, dramatic lightning illumination in sky",
        "warm dim indoor room lighting, dramatic dark storm clouds and rain flashes visible outside window",
        "(bright sunny day:1.5), (clear blue sky:1.5)"
    ),
    96: (
        "Badai Petir & Hujan Es", "Thunderstorm with slight hail", True, True, False,
        "dramatic thunderstorm with hail, dark stormy sky, heavy rain, atmospheric dramatic weather",
        "safe cozy indoor room lamp, thunderstorm visible outside",
        "(bright sunny day:1.5)"
    ),
    99: (
        "Badai Petir Hebat", "Thunderstorm with heavy hail", True, True, False,
        "severe thunderstorm, violent dark storm clouds, intense rain and hail, dramatic tempest atmosphere",
        "safe warm room, stormy gale and rain on window",
        "(bright sunny day:1.5)"
    ),
}

DEFAULT_WEATHER = (
    "Cerah Berawan", "Partly cloudy", False, False, False,
    "pleasant natural daylight, soft clouds, gentle breeze",
    "comfortable natural room lighting",
    "(heavy rain:1.5)"
)


class WeatherEngine:
    """
    Manages live realtime weather detection and synchronizes weather conditions
    with photo generation visual prompts and conversational knowledge.
    Uses Open-Meteo REST API (Free, zero API key).
    """

    def __init__(self):
        self._geo_cache: Dict[str, Tuple[float, float, str]] = {}
        self._weather_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl_seconds = 900  # 15 minutes TTL for weather data
        self._auto_ip_coords: Optional[Tuple[float, float, str]] = None
        self._auto_ip_last_check = 0.0

    def get_auto_ip_location(self) -> Optional[Tuple[float, float, str]]:
        """
        Attempts to detect current host/bot public IP location as default coordinates.
        Cached for 24 hours. Returns: (lat, lon, city_name) or None.
        """
        now = time.time()
        if self._auto_ip_coords and (now - self._auto_ip_last_check < 86400):
            return self._auto_ip_coords

        try:
            req = urllib.request.Request(
                "http://ip-api.com/json/",
                headers={"User-Agent": "WaifuOnTelegram/2.4"}
            )
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("status") == "success":
                    lat = float(data.get("lat", -6.2))
                    lon = float(data.get("lon", 106.8))
                    city = data.get("city", "Jakarta")
                    self._auto_ip_coords = (lat, lon, city)
                    self._auto_ip_last_check = now
                    logger.info(f"Auto-detected IP coordinates: {city} ({lat}, {lon})")
                    return self._auto_ip_coords
        except Exception as e:
            logger.debug(f"IP location auto-detect skipped: {e}")

        # Fallback to Jakarta default coordinates
        return (-6.2088, 106.8456, "Jakarta")

    def geocode_city(self, city_name: str) -> Optional[Tuple[float, float, str]]:
        """
        Resolves city name to latitude and longitude using Open-Meteo Geocoding API.
        Caches resolved coordinates forever in memory.
        """
        clean_name = city_name.strip()
        if not clean_name:
            return None

        clean_lower = clean_name.lower()
        if clean_lower in self._geo_cache:
            return self._geo_cache[clean_lower]

        # Common Indonesian major cities quick lookup (instant 0ms)
        CITY_SHORTCUTS = {
            "jakarta": (-6.2088, 106.8456, "Jakarta"),
            "bandung": (-6.9175, 107.6191, "Bandung"),
            "surabaya": (-7.2575, 112.7521, "Surabaya"),
            "yogyakarta": (-7.7956, 110.3695, "Yogyakarta"),
            "jogja": (-7.7956, 110.3695, "Yogyakarta"),
            "semarang": (-6.9667, 110.4167, "Semarang"),
            "malang": (-7.9797, 112.6304, "Malang"),
            "bali": (-8.4095, 115.1889, "Denpasar"),
            "denpasar": (-8.6705, 115.2126, "Denpasar"),
            "medan": (3.5952, 98.6722, "Medan"),
            "palembang": (-2.9909, 104.7565, "Palembang"),
            "makassar": (-5.1477, 119.4327, "Makassar"),
            "bogor": (-6.5971, 106.8060, "Bogor"),
            "depok": (-6.4025, 106.7942, "Depok"),
            "tangerang": (-6.1783, 106.6319, "Tangerang"),
            "bekasi": (-6.2383, 106.9756, "Bekasi"),
            "tasikmalaya": (-7.3274, 108.2207, "Tasikmalaya"),
            "cirebon": (-6.7320, 108.5523, "Cirebon"),
            "surakarta": (-7.5755, 110.8243, "Surakarta"),
            "solo": (-7.5755, 110.8243, "Surakarta"),
            "tokyo": (35.6762, 139.6503, "Tokyo"),
            "seoul": (37.5665, 126.9780, "Seoul"),
            "singapore": (1.3521, 103.8198, "Singapore"),
        }

        if clean_lower in CITY_SHORTCUTS:
            res = CITY_SHORTCUTS[clean_lower]
            self._geo_cache[clean_lower] = res
            return res

        # Online geocoding query
        try:
            encoded = urllib.parse.quote(clean_name)
            url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded}&count=1&language=id&format=json"
            req = urllib.request.Request(url, headers={"User-Agent": "WaifuOnTelegram/2.4"})
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                results = data.get("results")
                if results and len(results) > 0:
                    first = results[0]
                    lat = float(first.get("latitude"))
                    lon = float(first.get("longitude"))
                    resolved_name = first.get("name", clean_name)
                    coords = (lat, lon, resolved_name)
                    self._geo_cache[clean_lower] = coords
                    logger.info(f"Geocoded '{clean_name}' -> {resolved_name} ({lat}, {lon})")
                    return coords
        except Exception as e:
            logger.debug(f"Open-Meteo geocoding error for '{clean_name}': {e}")

        return None

    def fetch_live_weather(
        self,
        lat: float,
        lon: float,
        city_display_name: str = "Kota Kamu"
    ) -> Dict[str, Any]:
        """
        Queries Open-Meteo forecast API for current weather parameters.
        Returns detailed parsed weather dictionary.
        """
        cache_key = f"{round(lat, 2)},{round(lon, 2)}"
        now = time.time()

        cached = self._weather_cache.get(cache_key)
        if cached and (now - cached.get("_cached_at", 0) < self._cache_ttl_seconds):
            return cached

        try:
            url = (
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={lat}&longitude={lon}"
                f"&current=temperature_2m,relative_humidity_2m,is_day,precipitation,rain,weather_code,cloud_cover"
                f"&timezone=auto"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "WaifuOnTelegram/2.4"})
            with urllib.request.urlopen(req, timeout=4.5) as resp:
                raw_data = json.loads(resp.read().decode("utf-8"))
                current = raw_data.get("current", {})

                code = int(current.get("weather_code", 2))
                temp = float(current.get("temperature_2m", 28.0))
                humidity = int(current.get("relative_humidity_2m", 70))
                cloud_cover = int(current.get("cloud_cover", 40))
                is_day = bool(current.get("is_day", 1))
                rain_val = float(current.get("rain", current.get("precipitation", 0.0)))

                wmo_info = WMO_WEATHER_MAP.get(code, DEFAULT_WEATHER)
                name_id, name_en, is_rain, is_thunder, is_clear, pos_out, pos_in, neg_p = wmo_info

                # If rain gauge reports rain > 0.1mm, treat as raining regardless of code
                if rain_val > 0.1 and not is_rain:
                    is_rain = True
                    name_id = "Hujan"
                    pos_out = "rainy weather, falling raindrops, wet reflections on surfaces, cozy rain ambience"
                    pos_in = "warm cozy indoor lighting, raindrops on window glass, rainy day room ambiance"
                    neg_p = "(bright sunny day:1.5), (clear sky:1.5)"

                weather_data = {
                    "city": city_display_name,
                    "lat": lat,
                    "lon": lon,
                    "temperature": temp,
                    "humidity": humidity,
                    "cloud_cover": cloud_cover,
                    "is_day": is_day,
                    "rain_mm": rain_val,
                    "weather_code": code,
                    "condition_id": name_id,
                    "condition_en": name_en,
                    "is_rain": is_rain,
                    "is_thunderstorm": is_thunder,
                    "is_cloudy": (cloud_cover >= 65 or code in (2, 3)),
                    "is_clear": is_clear and (cloud_cover < 40),
                    "pos_prompt_outdoor": pos_out,
                    "pos_prompt_indoor": pos_in,
                    "neg_prompt": neg_p,
                    "summary_text": f"{name_id} ({temp:.1f}°C, kelembapan {humidity}%)",
                    "_cached_at": now
                }
                self._weather_cache[cache_key] = weather_data
                logger.info(f"Live Weather fetched for {city_display_name}: {weather_data['summary_text']}")
                return weather_data
        except Exception as e:
            logger.debug(f"Live Weather API error for ({lat}, {lon}): {e}")

        # Return default pleasant weather fallback on network error
        return {
            "city": city_display_name,
            "lat": lat,
            "lon": lon,
            "temperature": 28.5,
            "humidity": 70,
            "cloud_cover": 50,
            "is_day": True,
            "rain_mm": 0.0,
            "weather_code": 2,
            "condition_id": "Cerah Berawan",
            "condition_en": "Partly cloudy",
            "is_rain": False,
            "is_thunderstorm": False,
            "is_cloudy": False,
            "is_clear": True,
            "pos_prompt_outdoor": DEFAULT_WEATHER[5],
            "pos_prompt_indoor": DEFAULT_WEATHER[6],
            "neg_prompt": DEFAULT_WEATHER[7],
            "summary_text": "Cerah Berawan (28.5°C)",
            "_cached_at": now
        }

    def get_weather_for_user(
        self,
        user_id: Optional[int] = None,
        user_city: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main public interface: Retrieves live weather for given user or specified city.
        Checks user city in user profile or auto-detects from host IP.
        """
        city_candidate = user_city

        if not city_candidate and user_id:
            try:
                from memory_engine import memory_engine
                prof = memory_engine.get_profile(user_id)
                if prof and prof.get("location"):
                    city_candidate = prof.get("location")
            except Exception:
                pass

        if not city_candidate:
            city_candidate = os.environ.get("DEFAULT_WEATHER_CITY", "").strip()

        # If a city was found, resolve coordinates
        if city_candidate:
            coords = self.geocode_city(city_candidate)
            if coords:
                lat, lon, display_name = coords
                return self.fetch_live_weather(lat, lon, city_display_name=display_name)

        # Auto-detect from public IP
        ip_coords = self.get_auto_ip_location()
        if ip_coords:
            lat, lon, display_name = ip_coords
            return self.fetch_live_weather(lat, lon, city_display_name=display_name)

        # Fallback Jakarta
        return self.fetch_live_weather(-6.2088, 106.8456, city_display_name="Jakarta")

    def get_photo_weather_atmosphere(
        self,
        user_text: str = "",
        user_id: Optional[int] = None,
        is_indoor: bool = True
    ) -> Tuple[str, str]:
        """
        Builds visual prompt clauses for photo generation aligned with live weather.
        Explicit user weather requests (e.g. user asking for rain/snow/sunny) take precedence.
        Returns: (positive_weather_prompt, negative_weather_prompt)
        """
        low = (user_text or "").lower()

        # If user explicitly requested weather in their chat message, let user prompt lead!
        has_explicit_rain = bool(re.search(r"\b(hujan|rain|gerimis|drizzle|kehujanan|basah\s+karena\s+hujan|payung)\b", low))
        has_explicit_clear = bool(re.search(r"\b(cerah|terik|panas|sunny|clear\s+sky)\b", low))
        has_explicit_snow = bool(re.search(r"\b(salju|snow|winter)\b", low))

        if has_explicit_rain:
            pos = "rainy weather, falling raindrops, wet reflections on pavement, cozy romantic rain ambience" if not is_indoor else "cozy room lighting, soft rain drops on window pane, intimate rainy atmosphere"
            neg = "(bright sunny day:1.5), (clear sky:1.5)"
            return pos, neg
        elif has_explicit_snow:
            return "falling snow, snowy atmosphere, soft winter glow", "summer, beach, scorching sun"
        elif has_explicit_clear:
            return "clear sky, natural bright daylight", "(rain:1.5), (storm:1.5)"

        # Fetch live realtime weather for user
        w = self.get_weather_for_user(user_id=user_id)
        if w.get("is_rain") or w.get("is_thunderstorm"):
            pos = w.get("pos_prompt_indoor") if is_indoor else w.get("pos_prompt_outdoor")
            neg = w.get("neg_prompt", "")
            return pos, neg
        elif w.get("is_cloudy"):
            pos = w.get("pos_prompt_indoor") if is_indoor else w.get("pos_prompt_outdoor")
            neg = w.get("neg_prompt", "")
            return pos, neg

        return "", ""

    def get_conversation_context(self, user_id: Optional[int] = None) -> str:
        """
        Returns a concise 1-sentence prompt injection for the LLM system instruction
        so waifu is naturally aware of the real-world weather outside.
        """
        w = self.get_weather_for_user(user_id=user_id)
        city = w.get("city", "kota kamu")
        cond = w.get("condition_id", "Cerah Berawan")
        temp = w.get("temperature", 28.0)

        return (
            f"[KONDISI CUACA REALTIME: {city} - {cond}, {temp:.1f}°C]\n"
            f"Di luar saat ini sedang {cond.lower()} ({temp:.1f}°C). Kamu secara alami menyadari cuaca ini dan boleh "
            f"menyinggung suasana atau hawa sejuk/hangatnya secara wajar dan manis jika relevan dengan obrolan.\n"
        )


# Global singleton instance
weather_engine = WeatherEngine()
