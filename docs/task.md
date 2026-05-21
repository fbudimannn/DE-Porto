# 🌦️ Porto DE Weather — Task Tracker

## Phase 1: Foundation
- [x] Create project folder structure
- [x] `docker-compose.yml` — PostgreSQL 16 (downgraded to 12.6 image for reliability)
- [x] `requirements.txt`
- [x] `.env.example` + `.env`
- [x] `.gitignore`
- [x] `pipeline/__init__.py`
- [x] `pipeline/config.py` — cities + API endpoints
- [x] Verify: `docker-compose up` → PostgreSQL accessible

## Phase 2: Extract & Load
- [x] `pipeline/extract.py` — fetch from Open-Meteo API
- [x] `pipeline/load.py` — create tables + upsert to PostgreSQL
- [x] `pipeline/run_pipeline.py` — CLI entry point
- [x] `pipeline/scheduler.py` — APScheduler hourly
- [x] Verify: `python -m pipeline.run_pipeline --once` → data in DB

## Phase 3: Transform (dbt)
- [x] `dbt_weather/dbt_project.yml` + `profiles.yml`
- [x] `dbt_weather/seeds/city_metadata.csv`
- [x] Staging models: `stg_weather_hourly`, `stg_air_quality`
- [x] Dimension models: `dim_cities`, `dim_dates`
- [x] Fact models: `fact_weather_hourly`, `fact_air_quality`
- [x] Mart models: `mart_city_daily_summary`, `mart_aqi_alerts`, `mart_weather_trends`
- [x] Macros: `aqi_category.sql`
- [x] Tests: `assert_temperature_range`, `assert_valid_aqi`
- [x] Schema YAML: sources, descriptions, tests
- [x] Verify: `dbt run` + `dbt test` → 0 failures

## Phase 4: Dashboard + Polish
- [x] `pipeline/export_dashboard.py` — mart → JSON
- [x] `dashboard/index.html`
- [x] `dashboard/styles.css`
- [x] `dashboard/app.js`
- [x] `README.md` — portfolio showcase
- [x] Verify: dashboard renders correctly with real data

## Phase 5: Airflow Orchestration
- [x] Create `docker-compose-airflow.yml`
- [x] Create `dags/weather_elt_dag.py`
- [x] Update `README.md` to document Airflow usage
- [x] Verify: Start Airflow and run the DAG successfully
