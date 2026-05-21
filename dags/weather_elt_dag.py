from datetime import datetime, timedelta
import os
import sys
import logging

# Ensure /opt/airflow is in Python path for loading pipeline module
sys.path.append("/opt/airflow")

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

# Set up logging
logger = logging.getLogger("airflow.task")

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

def extract_and_load_weather_data():
    from pipeline.extract import extract_weather
    from pipeline.load import create_tables, load_weather
    
    logger.info("Starting Weather Extraction & Load...")
    # Ensure tables exist
    create_tables()
    
    # Extract
    weather_rows = extract_weather()
    # Load
    loaded = load_weather(weather_rows)
    logger.info(f"Successfully loaded {loaded} weather rows.")

def extract_and_load_air_quality_data():
    from pipeline.extract import extract_air_quality
    from pipeline.load import create_tables, load_air_quality
    
    logger.info("Starting Air Quality Extraction & Load...")
    # Ensure tables exist
    create_tables()
    
    # Extract
    aq_rows = extract_air_quality()
    # Load
    loaded = load_air_quality(aq_rows)
    logger.info(f"Successfully loaded {loaded} air quality rows.")

def export_dashboard():
    from pipeline.export_dashboard import export_dashboard_data
    logger.info("Exporting dbt mart tables to dashboard JSON feed...")
    success = export_dashboard_data()
    if not success:
        raise Exception("Dashboard export failed!")
    logger.info("Dashboard export completed successfully.")

with DAG(
    "weather_elt_dag",
    default_args=default_args,
    description="Automated Weather and Air Quality ELT pipeline with dbt and Dashboard Feed",
    schedule_interval=timedelta(hours=1),
    start_date=datetime(2026, 1, 1),
    catchup=False,
) as dag:

    # Task 1 & 2: Extract and Load
    el_weather = PythonOperator(
        task_id="extract_and_load_weather",
        python_callable=extract_and_load_weather_data,
    )

    el_air_quality = PythonOperator(
        task_id="extract_and_load_air_quality",
        python_callable=extract_and_load_air_quality_data,
    )

    # Task 3: dbt seed
    dbt_seed = BashOperator(
        task_id="dbt_seed",
        bash_command="dbt seed --profiles-dir .",
        cwd="/opt/airflow/dbt_weather",
    )

    # Task 4: dbt run
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command="dbt run --profiles-dir .",
        cwd="/opt/airflow/dbt_weather",
    )

    # Task 5: dbt test
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command="dbt test --profiles-dir .",
        cwd="/opt/airflow/dbt_weather",
    )

    # Task 6: Export for Dashboard
    export_data = PythonOperator(
        task_id="export_dashboard_data",
        python_callable=export_dashboard,
    )

    # Flow definition
    [el_weather, el_air_quality] >> dbt_seed >> dbt_run >> dbt_test >> export_data
