"""
Porto DE Weather — Dashboard Export Module
===========================================
Queries the materialized dbt mart tables and exports them
to dashboard/data/dashboard_data.json.

This JSON feed is consumed directly by the web UI.
"""

import os
import json
import logging
from datetime import datetime, timezone
import psycopg2
from psycopg2.extras import RealDictCursor

from pipeline.config import DB_CONFIG

logger = logging.getLogger("pipeline.export")

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "dashboard",
    "data"
)
LATEST_PATH = os.path.join(DATA_DIR, "latest_conditions.json")
SUMMARIES_PATH = os.path.join(DATA_DIR, "daily_summaries.json")
TRENDS_DIR = os.path.join(DATA_DIR, "trends")

# SQL queries to fetch aggregated metrics from analytics marts
QUERY_DAILY_SUMMARY = """
SELECT 
    city_name, province, island, observed_date::text as observed_date,
    avg_temperature_c, min_temperature_c, max_temperature_c,
    avg_humidity_pct, total_precipitation_mm, avg_wind_speed_kmh,
    max_wind_speed_kmh, max_uv_index, avg_pm2_5_ugm3, avg_pm10_ugm3,
    avg_aqi_value, max_aqi_value, is_rainy_day, uv_risk_level, worst_aqi_category
FROM public_analytics.mart_city_daily_summary
WHERE observed_date <= CURRENT_DATE
ORDER BY observed_date DESC, city_name;
"""

QUERY_ACTIVE_ALERTS = """
SELECT 
    city_name, province, observed_at::text as observed_at,
    aqi_value, aqi_category, alert_level
FROM public_analytics.mart_aqi_alerts
ORDER BY observed_at DESC, aqi_value DESC
LIMIT 15;
"""

QUERY_ROLLING_TRENDS = """
SELECT 
    city_name, observed_at::text as observed_at,
    temperature_c, humidity_pct, aqi_value, precipitation_mm,
    rolling_avg_temp_24h, rolling_avg_aqi_24h, temp_change_24h
FROM public_analytics.mart_weather_trends
WHERE observed_at >= NOW() - INTERVAL '1 hour'
ORDER BY city_name, observed_at;
"""

QUERY_LATEST_METRICS = """
WITH latest_per_city AS (
    SELECT 
        city_key, observed_at, temperature_c, humidity_pct,
        precipitation_mm, wind_speed_kmh, uv_index,
        ROW_NUMBER() OVER (PARTITION BY city_key ORDER BY observed_at DESC) as rn
    FROM public_analytics.fact_weather_hourly
    WHERE observed_at <= NOW()
),
latest_aq_per_city AS (
    SELECT 
        city_key, observed_at, pm2_5_ugm3, pm10_ugm3, aqi_value, aqi_category,
        ROW_NUMBER() OVER (PARTITION BY city_key ORDER BY observed_at DESC) as rn
    FROM public_analytics.fact_air_quality
    WHERE observed_at <= NOW()
)
SELECT 
    c.city_name, 
    c.province,
    c.island,
    c.lat,
    c.lon,
    w.observed_at::text as observed_at, 
    w.temperature_c, 
    w.humidity_pct, 
    w.precipitation_mm, 
    w.wind_speed_kmh, 
    w.uv_index,
    a.pm2_5_ugm3, 
    a.pm10_ugm3, 
    a.aqi_value, 
    a.aqi_category
FROM latest_per_city w
JOIN latest_aq_per_city a ON w.city_key = a.city_key AND w.observed_at = a.observed_at
JOIN public_analytics.dim_cities c ON w.city_key = c.city_key
WHERE w.rn = 1 AND a.rn = 1
ORDER BY c.city_name;
"""

def get_city_filename(city_name: str) -> str:
    """Sanitize city name to a file-safe name."""
    return city_name.lower().replace(" ", "_").replace("'", "").replace("-", "_")

def export_dashboard_data():
    """Query analytics marts and write results to sharded JSON files."""
    logger.info("📊 Gathering database metrics for dashboard...")
    
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(TRENDS_DIR, exist_ok=True)
    
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Fetch current status of all cities
            cur.execute(QUERY_LATEST_METRICS)
            latest = cur.fetchall()
            
            # 2. Fetch daily summaries
            cur.execute(QUERY_DAILY_SUMMARY)
            summaries = cur.fetchall()
            
            # 3. Fetch active air quality alerts
            cur.execute(QUERY_ACTIVE_ALERTS)
            alerts = cur.fetchall()
            
            # 4. Fetch 24h rolling trends
            cur.execute(QUERY_ROLLING_TRENDS)
            trends = cur.fetchall()
            
        import decimal
        class DecimalEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, decimal.Decimal):
                    return float(obj)
                return super(DecimalEncoder, self).default(obj)
        
        # Group daily summaries by city
        from collections import defaultdict
        daily_by_city = defaultdict(list)
        for s in summaries:
            daily_by_city[s['city_name']].append(s)
            
        # Group rolling trends by city
        trends_by_city = defaultdict(list)
        for t in trends:
            trends_by_city[t['city_name']].append(t)
            
        # Create lookup of latest metrics by city
        latest_by_city = {city['city_name']: city for city in latest}
        
        # 1. Write latest conditions (metadata + latest_conditions + active_alerts)
        latest_data = {
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "status": "Healthy",
                "cities_count": len(latest),
                "total_rows_processed": len(summaries) + len(trends)
            },
            "latest_conditions": latest,
            "active_alerts": alerts
        }
        with open(LATEST_PATH, 'w') as f:
            json.dump(latest_data, f, indent=2, cls=DecimalEncoder)
        logger.info(f"   ✅ Latest conditions written to: {LATEST_PATH}")
        
        # 2. Write daily summaries
        with open(SUMMARIES_PATH, 'w') as f:
            json.dump(summaries, f, indent=2, cls=DecimalEncoder)
        logger.info(f"   ✅ Daily summaries written to: {SUMMARIES_PATH}")
        
        # 3. Write individual city trends
        written_count = 0
        for city_name, latest_cond in latest_by_city.items():
            filename = get_city_filename(city_name) + ".json"
            city_file_path = os.path.join(TRENDS_DIR, filename)
            
            city_trend_data = {
                "city_name": city_name,
                "latest_condition": latest_cond,
                "daily_summaries": daily_by_city.get(city_name, [])[:14],  # last 14 days
                "hourly_trends": trends_by_city.get(city_name, [])[:24]   # next 24 hours of forecast
            }
            
            with open(city_file_path, 'w') as f:
                json.dump(city_trend_data, f, indent=2, cls=DecimalEncoder)
            written_count += 1
            
        logger.info(f"   ✅ Sharded trends written for {written_count} cities to: {TRENDS_DIR}")
        return True
    except Exception as e:
        logger.error(f"Failed to export dashboard data: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    export_dashboard_data()
