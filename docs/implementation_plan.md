# 🌦️ Porto DE: Indonesia Weather & Air Quality Analytics Pipeline

## Phase 5: Apache Airflow Orchestration

This phase introduces production-grade orchestration using **Apache Airflow** to schedule and monitor the end-to-end ELT pipeline. 

We will introduce a lightweight, single-container Airflow setup to run alongside our existing PostgreSQL database, allowing local execution and easy presentation to recruiters.

---

## User Review Required

> [!IMPORTANT]
> **Docker Desktop memory allocation**: Running Airflow alongside PostgreSQL might require around 2GB-3GB of RAM. Make sure your Docker Desktop has sufficient memory allocated (typically the default 4GB on Windows is enough).
>
> **Port Conflicts**: Airflow's webserver runs on port `8085` by default. Please ensure port `8085` is not being used by any other applications on your system.

---

## Open Questions

* Tidak ada pertanyaan terbuka saat ini. Jika Anda menyetujui rencana di bawah ini, silakan ketik "Approve" atau "Setuju" untuk mulai eksekusi.

---

## Proposed Changes

### Component: Orchestration (Airflow)

#### [NEW] [docker-compose-airflow.yml](file:///c:/Users/Fakhri/Documents/Porto%20DE/porto-de-weather/docker-compose-airflow.yml)
* Setup a single-container Airflow instance using the official `apache/airflow:2.8.1-python3.11` image.
* Configure `SequentialExecutor` using SQLite inside the container for a zero-setup metadata DB.
* Connect to our existing host PostgreSQL database (on port `5433`).
* Inject environment variable `_PIP_ADDITIONAL_REQUIREMENTS` to auto-install: `dbt-postgres`, `requests`, `python-dotenv`, and `psycopg2-binary` at container startup.
* Mount local folders:
  * `./dags` to `/opt/airflow/dags`
  * `./pipeline` to `/opt/airflow/pipeline`
  * `./dbt_weather` to `/opt/airflow/dbt_weather`
  * `./.env` to `/opt/airflow/.env`

#### [NEW] [weather_elt_dag.py](file:///c:/Users/Fakhri/Documents/Porto%20DE/porto-de-weather/dags/weather_elt_dag.py)
* Define the Directed Acyclic Graph (DAG) scheduled to run hourly.
* Implement tasks using `PythonOperator` and `BashOperator`:
  1. `extract_and_load_weather`: Calls `pipeline.extract.extract_weather` and `pipeline.load.load_weather`.
  2. `extract_and_load_air_quality`: Calls `pipeline.extract.extract_air_quality` and `pipeline.load.load_air_quality`.
  3. `dbt_seed`: Runs `dbt seed` to populate city metadata.
  4. `dbt_run`: Runs `dbt run` to build facts and marts.
  5. `dbt_test`: Runs `dbt test` to assert data quality.
  6. `export_dashboard`: Runs `pipeline.export_dashboard.export_dashboard_data` to refresh the frontend JSON feed.
* Set upstream/downstream task flow:
  `[extract_and_load_weather, extract_and_load_air_quality] >> dbt_seed >> dbt_run >> dbt_test >> export_dashboard`

#### [MODIFY] [README.md](file:///c:/Users/Fakhri/Documents/Porto%20DE/porto-de-weather/README.md)
* Add instructions on how to start Airflow: `docker-compose -f docker-compose-airflow.yml up -d`.
* Explain how to access the UI at `http://localhost:8085` (credentials: `admin`/`admin`).
* Describe the DAG structure and how it orchestrates the pipeline.

---

## Verification Plan

### Automated/Manual Verification
1. Start Airflow container:
   ```bash
   docker-compose -f docker-compose-airflow.yml up -d
   ```
2. Wait for initialization (takes 1-2 minutes for downloading/loading dependencies).
3. Access Airflow UI at `http://localhost:8085` using `admin`/`admin`.
4. Trigger the DAG manually `weather_elt_dag`.
5. Verify that all tasks (Extract/Load -> dbt seed/run/test -> Export) execute in order and turn green.
6. Verify that `dashboard/data/dashboard_data.json` is successfully updated.
