"""
Porto DE Weather — Load Module
================================
Creates tables and upserts data into PostgreSQL (raw_weather schema).
Idempotent: safe to re-run without creating duplicates.

Tables:
  - raw_weather.weather_hourly     (city × hour weather data)
  - raw_weather.air_quality_hourly (city × hour air quality data)
"""

import logging
from datetime import datetime

import psycopg2
from psycopg2.extras import execute_values

from pipeline.config import DB_CONFIG, RAW_SCHEMA

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# TABLE DEFINITIONS
# ──────────────────────────────────────────────────────────────

CREATE_WEATHER_TABLE = f"""
CREATE TABLE IF NOT EXISTS {RAW_SCHEMA}.weather_hourly (
    city_name           VARCHAR(100)   NOT NULL,
    timestamp           TIMESTAMPTZ    NOT NULL,
    temperature_2m      NUMERIC(5,2),
    relative_humidity_2m INTEGER,
    apparent_temperature NUMERIC(5,2),
    precipitation       NUMERIC(8,2),
    rain                NUMERIC(8,2),
    weather_code        INTEGER,
    wind_speed_10m      NUMERIC(6,2),
    wind_gusts_10m      NUMERIC(6,2),
    uv_index            NUMERIC(4,2),
    surface_pressure    NUMERIC(7,2),
    cloud_cover         INTEGER,
    ingested_at         TIMESTAMPTZ    NOT NULL DEFAULT NOW(),

    -- Composite primary key: one row per city per hour
    PRIMARY KEY (city_name, timestamp)
);

-- Index for dbt staging model performance
CREATE INDEX IF NOT EXISTS idx_weather_hourly_timestamp
    ON {RAW_SCHEMA}.weather_hourly (timestamp);
"""

CREATE_AQ_TABLE = f"""
CREATE TABLE IF NOT EXISTS {RAW_SCHEMA}.air_quality_hourly (
    city_name               VARCHAR(100)   NOT NULL,
    timestamp               TIMESTAMPTZ    NOT NULL,
    pm10                    NUMERIC(8,2),
    pm2_5                   NUMERIC(8,2),
    carbon_monoxide         NUMERIC(10,2),
    nitrogen_dioxide        NUMERIC(8,2),
    sulphur_dioxide         NUMERIC(8,2),
    ozone                   NUMERIC(8,2),
    european_aqi            INTEGER,
    european_aqi_pm2_5      INTEGER,
    european_aqi_pm10       INTEGER,
    ingested_at             TIMESTAMPTZ    NOT NULL DEFAULT NOW(),

    -- Composite primary key: one row per city per hour
    PRIMARY KEY (city_name, timestamp)
);

-- Index for dbt staging model performance
CREATE INDEX IF NOT EXISTS idx_aq_hourly_timestamp
    ON {RAW_SCHEMA}.air_quality_hourly (timestamp);
"""

# ──────────────────────────────────────────────────────────────
# UPSERT QUERIES
# ──────────────────────────────────────────────────────────────

UPSERT_WEATHER = f"""
INSERT INTO {RAW_SCHEMA}.weather_hourly (
    city_name, timestamp, temperature_2m, relative_humidity_2m,
    apparent_temperature, precipitation, rain, weather_code,
    wind_speed_10m, wind_gusts_10m, uv_index, surface_pressure,
    cloud_cover, ingested_at
) VALUES %s
ON CONFLICT (city_name, timestamp) DO UPDATE SET
    temperature_2m       = EXCLUDED.temperature_2m,
    relative_humidity_2m = EXCLUDED.relative_humidity_2m,
    apparent_temperature = EXCLUDED.apparent_temperature,
    precipitation        = EXCLUDED.precipitation,
    rain                 = EXCLUDED.rain,
    weather_code         = EXCLUDED.weather_code,
    wind_speed_10m       = EXCLUDED.wind_speed_10m,
    wind_gusts_10m       = EXCLUDED.wind_gusts_10m,
    uv_index             = EXCLUDED.uv_index,
    surface_pressure     = EXCLUDED.surface_pressure,
    cloud_cover          = EXCLUDED.cloud_cover,
    ingested_at          = EXCLUDED.ingested_at;
"""

UPSERT_AQ = f"""
INSERT INTO {RAW_SCHEMA}.air_quality_hourly (
    city_name, timestamp, pm10, pm2_5, carbon_monoxide,
    nitrogen_dioxide, sulphur_dioxide, ozone,
    european_aqi, european_aqi_pm2_5, european_aqi_pm10, ingested_at
) VALUES %s
ON CONFLICT (city_name, timestamp) DO UPDATE SET
    pm10                = EXCLUDED.pm10,
    pm2_5               = EXCLUDED.pm2_5,
    carbon_monoxide     = EXCLUDED.carbon_monoxide,
    nitrogen_dioxide    = EXCLUDED.nitrogen_dioxide,
    sulphur_dioxide     = EXCLUDED.sulphur_dioxide,
    ozone               = EXCLUDED.ozone,
    european_aqi        = EXCLUDED.european_aqi,
    european_aqi_pm2_5  = EXCLUDED.european_aqi_pm2_5,
    european_aqi_pm10   = EXCLUDED.european_aqi_pm10,
    ingested_at         = EXCLUDED.ingested_at;
"""


# ──────────────────────────────────────────────────────────────
# DATABASE FUNCTIONS
# ──────────────────────────────────────────────────────────────

def _get_connection():
    """Create a PostgreSQL connection."""
    return psycopg2.connect(**DB_CONFIG)


def create_tables():
    """
    Create raw tables if they don't exist.
    Idempotent — safe to call every pipeline run.
    """
    logger.info("🗄️  Creating tables (if not exist)...")

    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_WEATHER_TABLE)
            cur.execute(CREATE_AQ_TABLE)
        conn.commit()
        logger.info("   ✅ Tables ready")
    finally:
        conn.close()


def load_weather(rows: list[dict]) -> int:
    """
    Upsert weather rows into raw_weather.weather_hourly.

    Args:
        rows: List of dicts from extract.extract_weather()

    Returns:
        Number of rows upserted
    """
    if not rows:
        logger.warning("No weather rows to load")
        return 0

    weather_cols = [
        "city_name", "timestamp", "temperature_2m", "relative_humidity_2m",
        "apparent_temperature", "precipitation", "rain", "weather_code",
        "wind_speed_10m", "wind_gusts_10m", "uv_index", "surface_pressure",
        "cloud_cover", "ingested_at",
    ]

    values = [tuple(row.get(col) for col in weather_cols) for row in rows]

    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            execute_values(cur, UPSERT_WEATHER, values, page_size=500)
        conn.commit()
        logger.info(f"   ✅ Loaded {len(values)} weather rows")
        return len(values)
    finally:
        conn.close()


def load_air_quality(rows: list[dict]) -> int:
    """
    Upsert air quality rows into raw_weather.air_quality_hourly.

    Args:
        rows: List of dicts from extract.extract_air_quality()

    Returns:
        Number of rows upserted
    """
    if not rows:
        logger.warning("No air quality rows to load")
        return 0

    aq_cols = [
        "city_name", "timestamp", "pm10", "pm2_5", "carbon_monoxide",
        "nitrogen_dioxide", "sulphur_dioxide", "ozone",
        "european_aqi", "european_aqi_pm2_5", "european_aqi_pm10", "ingested_at",
    ]

    values = [tuple(row.get(col) for col in aq_cols) for row in rows]

    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            execute_values(cur, UPSERT_AQ, values, page_size=500)
        conn.commit()
        logger.info(f"   ✅ Loaded {len(values)} air quality rows")
        return len(values)
    finally:
        conn.close()


def get_table_counts() -> dict:
    """Get row counts for monitoring."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {RAW_SCHEMA}.weather_hourly")
            weather_count = cur.fetchone()[0]
            cur.execute(f"SELECT COUNT(*) FROM {RAW_SCHEMA}.air_quality_hourly")
            aq_count = cur.fetchone()[0]
        return {"weather_hourly": weather_count, "air_quality_hourly": aq_count}
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────
# MAIN (for standalone testing)
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    create_tables()
    counts = get_table_counts()
    print(f"Current row counts: {counts}")
