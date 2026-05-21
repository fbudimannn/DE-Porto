# 🌦️ Indonesia Weather & Air Quality Analytics Portal

A high-performance, automated **ELT (Extract-Load-Transform) Data Engineering Portfolio Project** designed to capture, process, and analyze meteorological and environmental (AQI) trends across 10 major Indonesian cities. 

This project demonstrates professional-grade data architecture patterns, including API ingestion, idempotent database upserts, a structured star-schema warehouse built with **dbt (data build tool)**, data quality testing, and a modern frontend dashboard.

---

## 🏗️ Architecture & Data Flow

```
                      +---------------------------------------+
                      |         Open-Meteo Public API         |
                      +-------------------+-------------------+
                                          | Ingestion
                                          v
                      +-------------------+-------------------+
                      |      Python extract.py & load.py      |
                      +-------------------+-------------------+
                                          | Idempotent Upserts
                                          v
                      +-------------------+-------------------+
                      |  PostgreSQL Database (Raw Schemas)    |
                      +-------------------+-------------------+
                                          | ELT Transformations
                                          v
                      +-------------------+-------------------+
                      |     dbt Core (Analytics Schemas)      |
                      |  [Staging -> Dimensions/Facts -> Marts]|
                      +-------------------+-------------------+
                                          | Automated Export
                                          v
                      +-------------------+-------------------+
                      |     dashboard_data.json Feed          |
                      +-------------------+-------------------+
                                          | Client Render
                                          v
                      +-------------------+-------------------+
                      |  HTML5/CSS3 Dashboard (Chart.js/UI)  |
                      +-------------------+-------------------+
```

1. **Extract & Load (Python/PostgreSQL)**: Hourly cron scheduler requests meteorological (temperature, humidity, rain, wind, UV) and air quality (PM2.5, PM10, CO, European AQI) indices. Data is loaded into PostgreSQL with transactional integrity and constraint-based idempotency.
2. **Transform (dbt Core)**: Normalizes raw schemas into a optimized **Star Schema Dimensional Model** under the `analytics` namespace.
3. **Data Quality Test**: Includes unit-level schema validation and custom SQL range assertions (e.g. valid temperature boundaries and active alert checks).
4. **Serve & Visualize**: The runner automatically queries dbt marts and exports a fast JSON feed consumed by a premium dark-themed web dashboard.

---

## 🛠️ Technology Stack

- **Data Ingestion:** Python 3.13, `requests`, `psycopg2-binary`, `APScheduler`
- **Warehouse & Modeling:** PostgreSQL 12.6, **dbt Core v1.11** (dbt-postgres)
- **Containerization:** Docker Desktop
- **Frontend Visualization:** HTML5, Vanilla CSS3 (Custom Dark/Glassmorphism Theme), JS, **Chart.js** (Dynamic Trends), **Lucide Icons**

---

## 📈 Database Schema & Dimensional Modeling

Transformations are modeled as follows in dbt:
- **Staging Layer (`staging` schema):** Normalizes JSON/Text response columns, sanitizes types, and casts timestamps.
- **Dimensions (`analytics` schema):**
  - `dim_cities`: Seeded metadata details (lat/long, island, province).
  - `dim_dates`: Generated calendar dimension for time-series intelligence.
- **Facts (`analytics` schema):**
  - `fact_weather_hourly`: Hourly fact measurements.
  - `fact_air_quality`: Hourly air quality measurements.
- **Marts (`analytics` schema):**
  - `mart_city_daily_summary`: Daily aggregations (averages, min/max, UV risks, rainfall, worst AQI category).
  - `mart_aqi_alerts`: Filtered alerts where AQI exceeds critical thresholds (>100).
  - `mart_weather_trends`: 24-hour moving rolling averages for weather and AQI indices.

---

## 🚀 How to Run the Project

You can run this project in two different modes: **Option A (Lightweight Mode)** or **Option B (Production Orchestration Mode)**.

---

### 💻 Option A: Lightweight Mode (Python Scheduler)
*Recommended for quick testing and review without setup overhead.*

#### 1. Start the Database Container
Make sure Docker Desktop is running, then start the PostgreSQL container:
```bash
docker-compose up -d
```
*Note: This starts PostgreSQL 12.6, exposing port `5433` to bypass any default local installations.*

#### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

#### 3. Setup dbt Profile
The pipeline utilizes a profile configured to connect to `localhost:5433`. Run a connection test to ensure dbt can reach the DW:
```bash
cd dbt_weather
dbt debug --profiles-dir .
cd ..
```

#### 4. Execute the Pipeline
You can run a single complete ELT cycle (Extract → Load → dbt Run → dbt Test → JSON Export):
```bash
python -m pipeline.run_pipeline --once
```
Or start the continuous scheduling agent (runs immediately, then every hour):
```bash
python -m pipeline.run_pipeline --scheduler
```

---

### 🌪️ Option B: Production Mode (Apache Airflow DAG)
*Recommended for demonstrating real-world data engineering orchestration.*

This mode spins up PostgreSQL alongside a single-container Apache Airflow service that schedules the entire pipeline via an Airflow DAG.

#### 1. Start Airflow & PostgreSQL Stack
Run the dedicated compose file:
```bash
docker-compose -f docker-compose-airflow.yml up -d
```
*Note: The container automatically installs Python dependencies (`dbt-postgres`, `requests`, etc.) at startup, which might take 1–2 minutes on the first run.*

#### 2. Access the Airflow Web UI
1. Open your browser and go to: **`http://localhost:8085`**
2. Log in with the default credentials:
   * **Username:** `admin`
   * **Password:** `admin`

#### 3. Trigger the DAG
1. Find the DAG named **`weather_elt_dag`** in the list.
2. Unpause/toggle the DAG to **Active** (switch to `ON`).
3. Click the **Trigger DAG** button (play icon) on the top right to start the execution immediately.
4. Verify that the task flows run successfully:
   `[extract_and_load_weather, extract_and_load_air_quality] >> dbt_seed >> dbt_run >> dbt_test >> export_dashboard_data`

---

### 📊 5. Launch the Dashboard Portal
Once the data is ingested and processed (by either Option A or Option B), simply open the client-side portal directly in your browser:
* Double-click **`dashboard/index.html`** or serve via any local extension (e.g., VS Code Live Server).

---

## 🧪 Data Testing & Quality Assurance

Quality assurance is integrated directly into the build sequence:
- **Generic Tests:** Unique and Not Null checks on dimensional keys (`city_key`, `date_key`, etc.), as well as Referential Integrity (Relationship) assertions linking Facts to Dimensions.
- **Custom Singular Tests:**
  - `assert_temperature_range`: Catches anomalous temperature spikes outside expected boundaries (-10°C to 55°C).
  - `assert_valid_aqi`: Validates that AQI index ranges match the mathematical bounds (0 to 500).

Run the tests manually:
```bash
cd dbt_weather
dbt test --profiles-dir .
```

---

## 📂 Repository Structure

```
├── .env.example
├── docker-compose.yml
├── requirements.txt
├── README.md
├── pipeline/
│   ├── __init__.py
│   ├── config.py             # Database & API coordinates
│   ├── extract.py            # API request handlers
│   ├── load.py               # SQL ingestion & table creation
│   ├── export_dashboard.py   # Mart exporter (Decimal-JSON converter)
│   └── run_pipeline.py       # Orchestrator
├── dbt_weather/
│   ├── dbt_project.yml
│   ├── profiles.yml          # Connection profile
│   ├── seeds/
│   │   └── city_metadata.csv # 10 cities seed metadata
│   ├── models/
│   │   ├── staging/          # stg_weather_hourly, stg_air_quality
│   │   ├── dimensions/       # dim_cities, dim_dates
│   │   ├── facts/            # fact_weather_hourly, fact_air_quality
│   │   └── marts/            # summaries, alerts, rolling trends
│   ├── macros/
│   │   └── aqi_category.sql  # Custom categorizer
│   └── tests/
│       ├── assert_temperature_range.sql
│       └── assert_valid_aqi.sql
└── dashboard/
    ├── index.html            # Premium Layout
    ├── styles.css            # Dark Theme styling
    ├── app.js                # Dynamic rendering, search, & Chart.js
    └── data/
        └── dashboard_data.json # Automatically generated JSON feed
```
