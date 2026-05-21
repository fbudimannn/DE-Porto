"""
Porto DE Weather — Pipeline Configuration
==========================================
Central config for cities, API endpoints, and database connection.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────────────────────
# DATABASE
# ──────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "weather_dw"),
    "user": os.getenv("POSTGRES_USER", "dbt_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "dbt_pass"),
}

DB_URL = (
    f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
)

RAW_SCHEMA = "raw_weather"

# ──────────────────────────────────────────────────────────────
# OPEN-METEO API ENDPOINTS
# ──────────────────────────────────────────────────────────────
WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY_API_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

# Weather variables to fetch (hourly)
WEATHER_HOURLY_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation",
    "rain",
    "weather_code",
    "wind_speed_10m",
    "wind_gusts_10m",
    "uv_index",
    "surface_pressure",
    "cloud_cover",
]

# Air quality variables to fetch (hourly)
AQ_HOURLY_VARS = [
    "pm10",
    "pm2_5",
    "carbon_monoxide",
    "nitrogen_dioxide",
    "sulphur_dioxide",
    "ozone",
    "european_aqi",
    "european_aqi_pm2_5",
    "european_aqi_pm10",
]

# ──────────────────────────────────────────────────────────────
# INDONESIAN CITIES TO TRACK
# ──────────────────────────────────────────────────────────────
from pipeline.config_cities import CITIES

# ──────────────────────────────────────────────────────────────
# PIPELINE SETTINGS
# ──────────────────────────────────────────────────────────────
SCHEDULE_INTERVAL_HOURS = int(os.getenv("PIPELINE_SCHEDULE_HOURS", "1"))
LOG_LEVEL = os.getenv("PIPELINE_LOG_LEVEL", "INFO")
API_DELAY_SECONDS = 0.15  # Respectful delay between API calls
FORECAST_DAYS = 7
PAST_DAYS = 2  # Also grab 2 past days to fill any gaps
TIMEZONE = "Asia/Jakarta"
