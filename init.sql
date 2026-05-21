-- =============================================================
-- INIT SQL: Create schemas for the weather data warehouse
-- Runs automatically on first docker-compose up
-- =============================================================

-- Raw schema: landing zone for API data (Extract & Load)
CREATE SCHEMA IF NOT EXISTS raw_weather;

-- Analytics schema: dbt transforms write here
CREATE SCHEMA IF NOT EXISTS analytics;

-- Grant permissions
GRANT ALL ON SCHEMA raw_weather TO dbt_user;
GRANT ALL ON SCHEMA analytics TO dbt_user;
