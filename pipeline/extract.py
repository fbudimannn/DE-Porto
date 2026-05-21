"""
Porto DE Weather — Extract Module
==================================
Fetches weather forecast and air quality data from Open-Meteo API
for 10 Indonesian cities. No API key required.

Endpoints:
  - Weather:     https://api.open-meteo.com/v1/forecast
  - Air Quality: https://air-quality-api.open-meteo.com/v1/air-quality
"""

import time
import logging
from datetime import datetime, timezone
from typing import Any

import requests

from pipeline.config import (
    CITIES,
    WEATHER_API_URL,
    AIR_QUALITY_API_URL,
    WEATHER_HOURLY_VARS,
    AQ_HOURLY_VARS,
    API_DELAY_SECONDS,
    FORECAST_DAYS,
    PAST_DAYS,
    TIMEZONE,
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────

def _fetch_with_retry(url: str, params: dict, max_retries: int = 3) -> dict:
    """
    HTTP GET with exponential backoff retry.
    Open-Meteo is generous with rate limits (10k/day free),
    but we're respectful with delays between calls.
    """
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 429:  # Rate limited
                wait = 2 ** attempt
                logger.warning(f"Rate limited. Retrying in {wait}s (attempt {attempt}/{max_retries})")
                time.sleep(wait)
            else:
                logger.error(f"HTTP error {resp.status_code}: {e}")
                raise
        except requests.exceptions.RequestException as e:
            wait = 2 ** attempt
            logger.warning(f"Request failed: {e}. Retrying in {wait}s (attempt {attempt}/{max_retries})")
            time.sleep(wait)

    raise RuntimeError(f"Failed after {max_retries} retries: {url}")


def _flatten_hourly(city_name: str, api_response: dict, variable_keys: list[str]) -> list[dict]:
    """
    Flatten Open-Meteo hourly JSON into a list of row dicts.

    API returns:
        {"hourly": {"time": [...], "temperature_2m": [...], ...}}

    We transform to:
        [{"city_name": "Jakarta", "timestamp": "2025-01-01T00:00", "temperature_2m": 28.5, ...}, ...]
    """
    hourly = api_response.get("hourly", {})
    timestamps = hourly.get("time", [])

    if not timestamps:
        logger.warning(f"No hourly data returned for {city_name}")
        return []

    now_utc = datetime.now(timezone.utc).isoformat()
    rows = []

    for i, ts in enumerate(timestamps):
        row = {
            "city_name": city_name,
            "timestamp": ts,
            "ingested_at": now_utc,
        }
        for var in variable_keys:
            values = hourly.get(var, [])
            row[var] = values[i] if i < len(values) else None
        rows.append(row)

    return rows


# ──────────────────────────────────────────────────────────────
# PUBLIC EXTRACT FUNCTIONS
# ──────────────────────────────────────────────────────────────

def extract_weather(cities: list[dict] | None = None) -> list[dict]:
    """
    Fetch hourly weather forecast for all configured cities in batches of 100.

    Returns a flat list of dicts, each representing one city × one hour.
    Typically returns ~216 rows per city (9 days × 24 hours).
    """
    cities = cities or CITIES
    all_rows: list[dict] = []
    chunk_size = 100

    for idx in range(0, len(cities), chunk_size):
        chunk = cities[idx:idx + chunk_size]
        logger.info(f"🌤️  Fetching weather batch {idx // chunk_size + 1} ({len(chunk)} cities)...")

        lats = [str(c["lat"]) for c in chunk]
        lons = [str(c["lon"]) for c in chunk]

        params = {
            "latitude": ",".join(lats),
            "longitude": ",".join(lons),
            "hourly": ",".join(WEATHER_HOURLY_VARS),
            "timezone": TIMEZONE,
            "forecast_days": FORECAST_DAYS,
            "past_days": PAST_DAYS,
        }

        data = _fetch_with_retry(WEATHER_API_URL, params)
        if isinstance(data, dict):
            data = [data]

        for city, city_data in zip(chunk, data):
            rows = _flatten_hourly(city["name"], city_data, WEATHER_HOURLY_VARS)
            all_rows.extend(rows)

        logger.info(f"   ✅ Batch {idx // chunk_size + 1} processed. Total weather rows: {len(all_rows)}")
        time.sleep(API_DELAY_SECONDS)

    logger.info(f"📊 Weather extract complete: {len(all_rows)} total rows from {len(cities)} cities")
    return all_rows


def extract_air_quality(cities: list[dict] | None = None) -> list[dict]:
    """
    Fetch hourly air quality data for all configured cities in batches of 100.

    Returns a flat list of dicts, each representing one city × one hour.
    """
    cities = cities or CITIES
    all_rows: list[dict] = []
    chunk_size = 100

    for idx in range(0, len(cities), chunk_size):
        chunk = cities[idx:idx + chunk_size]
        logger.info(f"🌫️  Fetching air quality batch {idx // chunk_size + 1} ({len(chunk)} cities)...")

        lats = [str(c["lat"]) for c in chunk]
        lons = [str(c["lon"]) for c in chunk]

        params = {
            "latitude": ",".join(lats),
            "longitude": ",".join(lons),
            "hourly": ",".join(AQ_HOURLY_VARS),
            "timezone": TIMEZONE,
            "forecast_days": FORECAST_DAYS,
            "past_days": PAST_DAYS,
        }

        data = _fetch_with_retry(AIR_QUALITY_API_URL, params)
        if isinstance(data, dict):
            data = [data]

        for city, city_data in zip(chunk, data):
            rows = _flatten_hourly(city["name"], city_data, AQ_HOURLY_VARS)
            all_rows.extend(rows)

        logger.info(f"   ✅ Batch {idx // chunk_size + 1} processed. Total AQ rows: {len(all_rows)}")
        time.sleep(API_DELAY_SECONDS)

    logger.info(f"📊 Air quality extract complete: {len(all_rows)} total rows from {len(cities)} cities")
    return all_rows


# ──────────────────────────────────────────────────────────────
# MAIN (for standalone testing)
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

    weather_rows = extract_weather()
    aq_rows = extract_air_quality()

    print(f"\n{'='*50}")
    print(f"Weather rows:     {len(weather_rows)}")
    print(f"Air quality rows: {len(aq_rows)}")
    print(f"{'='*50}")

    if weather_rows:
        print(f"\nSample weather row: {weather_rows[0]}")
    if aq_rows:
        print(f"\nSample AQ row:     {aq_rows[0]}")
