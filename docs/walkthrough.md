# 🌦️ Indonesia Weather & Air Quality Analytics — Walkthrough

We have successfully completed all phases of the project! Below is a detailed walkthrough of the architectural components, execution results, test coverages, and frontend interface.

---

## 📸 Client-Side Dashboard Portal (Mockup)

Below is the design mockup representing the premium dark-theme client-side analytics portal. It consumes the pipeline JSON feed and dynamically renders meteorological and environmental metrics.

<img src="/C:/Users/Fakhri/.gemini/antigravity-ide/brain/cbb457f6-c1d2-45cf-b8d1-20ac1569cf07/dashboard_mockup_1779340672413.png" alt="IndoWeather Premium Dashboard Mockup" width="100%" />

---

## 🛠️ Verification & Pipeline Execution Results

### 1. Ingestion & Storage (`raw_weather` schema)
When executing `python -m pipeline.run_pipeline --once`, the pipeline pulls hourly parameters for the past 9 days (216 hours per city) across 10 Indonesian cities:
- **Jakarta, Surabaya, Bandung, Medan, Semarang, Makassar, Palembang, Denpasar, Yogyakarta, Balikpapan**
- Ingests **2,160 rows** of raw weather conditions.
- Ingests **2,160 rows** of raw air quality parameters.
- Utilizes idempotent Postgres constraints (`INSERT ... ON CONFLICT DO UPDATE`) to prevent duplicate entry errors during periodic syncs.

### 2. Transformation Layer (`analytics` schema)
The dbt core project normalizes and materializes raw tables into a star schema:
- `dim_cities`: Seeded metadata table containing coordinate boundaries, islands, and provinces.
- `dim_dates`: Dynamically generated day dimension.
- `fact_weather_hourly`: Staged hourly temperature, humidity, rainfall, wind, and UV records.
- `fact_air_quality`: Staged hourly particulate concentrations and AQI classifications.
- `mart_city_daily_summary`: Rolled up daily averages, UV risk factors, and worst hourly air categories.
- `mart_aqi_alerts`: Specific alert events where European AQI exceeded 100.
- `mart_weather_trends`: 24-hour moving rolling averages.

### 3. Data Quality & Test Execution
All **24 tests** successfully passed:
```
05:16:58  20 of 24 PASS source_not_null_raw_weather_air_quality_hourly_timestamp ... [PASS in 0.08s]
05:16:58  21 of 24 PASS source_not_null_raw_weather_weather_hourly_city_name ............. [PASS in 0.09s]
05:16:58  22 of 24 PASS source_not_null_raw_weather_weather_hourly_timestamp ............. [PASS in 0.07s]
05:16:58  23 of 24 PASS unique_dim_cities_city_key ....................................... [PASS in 0.06s]
05:16:58  24 of 24 PASS unique_dim_dates_date_key ........................................ [PASS in 0.04s]
05:16:58  
05:16:58  Finished running 24 data tests in 0 hours 0 minutes and 0.83 seconds (0.83s).
05:16:58  Completed successfully
05:16:58  Done. PASS=24 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=24
```

### 4. Automated Export Feed
The pipeline runner automatically executes `pipeline/export_dashboard.py` at the end of the load-transform sequence. This script queries the PostgreSQL DW using parameterized cursors and outputs to `dashboard/data/dashboard_data.json` while converting database numeric values (`Decimal` type) to serializable floats.

---

## 📂 Project Directory
All code and assets are stored in the standalone workspace:
- Main Project: [c:/Users/Fakhri/Documents/Porto DE/porto-de-weather](file:///c:/Users/Fakhri/Documents/Porto%20DE/porto-de-weather)
- Execution Script: [run_pipeline.py](file:///c:/Users/Fakhri/Documents/Porto%20DE/porto-de-weather/pipeline/run_pipeline.py)
- Transformations: [dbt_weather](file:///c:/Users/Fakhri/Documents/Porto%20DE/porto-de-weather/dbt_weather)
- Client-Side Dashboard: [index.html](file:///c:/Users/Fakhri/Documents/Porto%20DE/porto-de-weather/dashboard/index.html)

---

## 🌪️ Phase 5: Apache Airflow Orchestration & Verification

To match enterprise standards, we successfully implemented and verified production-grade orchestration using **Apache Airflow**.

### 1. Airflow Service Design
- **Single-Container Standalone Instance:** Runs webserver and scheduler concurrently using the lightweight `SequentialExecutor` (SQLite backed), avoiding database overhead.
- **Port Mapping:** Exposes port `8085` to host (`http://localhost:8085`) to guarantee no port conflicts with pre-existing services on port `8080`.
- **Dynamic Connection Mapping:** The dbt `profiles.yml` and Python pipeline variables automatically detect the environment:
  - Connects to `localhost:5433` (Postgres mapping) when triggered from the host CLI.
  - Connects to `postgres:5432` (internal Docker network) when triggered inside Airflow tasks.
- **Dynamic Dependency Loading:** The `_PIP_ADDITIONAL_REQUIREMENTS` container feature automatically handles the installation of `dbt-postgres`, `psycopg2-binary`, etc., on container startup.

### 2. DAG Flow & Task Graph (`weather_elt_dag`)
The pipeline runs hourly using the following task sequence:
```
 [extract_and_load_weather] -----\
                                  +--> [dbt_seed] --> [dbt_run] --> [dbt_test] --> [export_dashboard_data]
 [extract_and_load_air_quality] --/
```

### 3. Execution Verification Log
The DAG has been successfully activated and completed its end-to-end execution:
- **`dbt_seed`:** Successfully created and loaded the `city_metadata` seed.
- **`dbt_run`:** Formed and materialized all 9 star-schema tables and aggregates in PostgreSQL.
- **`dbt_test`:** Successfully passed all 24 schema assertions and custom value ranges.
- **`export_dashboard_data`:** Gathered analytical marts and exported the JSON feed to `dashboard/data/dashboard_data.json` inside the mounted volume.
- **Status:** **SUCCESS** 🟢

```
dag_id          | run_id                               | state   | execution_date            | start_date                       | end_date                        
================+======================================+=========+===========================+==================================+=================================
weather_elt_dag | scheduled__2026-05-21T04:00:00+00:00 | success | 2026-05-21T04:00:00+00:00 | 2026-05-21T05:37:17.242412+00:00 | 2026-05-21T05:43:57.457858+00:00
```
