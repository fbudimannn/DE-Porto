"""
Porto DE Weather — Pipeline Runner
====================================
CLI entry point for running the ELT pipeline.

Usage:
    python -m pipeline.run_pipeline --once       # Single run
    python -m pipeline.run_pipeline --scheduler  # Continuous (every hour)
"""

import argparse
import logging
import sys
import signal
import time as _time
from datetime import datetime

from pipeline.config import LOG_LEVEL, SCHEDULE_INTERVAL_HOURS
from pipeline.extract import extract_weather, extract_air_quality
from pipeline.load import create_tables, load_weather, load_air_quality, get_table_counts

logger = logging.getLogger("pipeline")


def setup_logging():
    """Configure structured logging."""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s | %(levelname)-5s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


import subprocess
import os
from pipeline.export_dashboard import export_dashboard_data

def _find_dbt_executable() -> str:
    """Locate dbt executable in common python script folders or fallback to PATH."""
    paths_to_check = [
        # Windows Store Python package path
        os.path.expandvars(r"%LOCALAPPDATA%\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\Scripts\dbt.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Packages\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\LocalCache\local-packages\Python312\Scripts\dbt.exe"),
        # Standard Python path
        os.path.expandvars(r"%APPDATA%\Python\Python313\Scripts\dbt.exe"),
        os.path.expandvars(r"%APPDATA%\Python\Python312\Scripts\dbt.exe"),
    ]
    for p in paths_to_check:
        if os.path.exists(p):
            return p
    return "dbt"  # Fallback to system PATH

def _run_dbt(args: list[str]) -> bool:
    """Execute dbt commands using subprocess."""
    dbt_exe = _find_dbt_executable()
    dbt_project_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "dbt_weather"
    )
    
    cmd = [dbt_exe] + args + ["--profiles-dir", "."]
    logger.info(f"🔄 Running dbt: {' '.join(cmd)}")
    
    try:
        res = subprocess.run(
            cmd,
            cwd=dbt_project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True
        )
        logger.info(res.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ dbt command failed:\n{e.stdout}")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to run dbt: {e}")
        return False

def run_once() -> dict:
    """
    Execute a single end-to-end pipeline run: 
    Extract → Load → Transform (dbt) → Serve (Export)
    """
    start = datetime.now()
    logger.info("=" * 60)
    logger.info("🚀 PIPELINE RUN STARTED (ELT & EXPORT)")
    logger.info("=" * 60)

    # Step 1: Ensure raw tables exist
    create_tables()

    # Step 2: Extract from API
    logger.info("\n📥 EXTRACT PHASE")
    logger.info("-" * 40)
    weather_rows = extract_weather()
    aq_rows = extract_air_quality()

    # Step 3: Load to PostgreSQL
    logger.info("\n📤 LOAD PHASE")
    logger.info("-" * 40)
    weather_loaded = load_weather(weather_rows)
    aq_loaded = load_air_quality(aq_rows)

    # Step 4: Transform via dbt (run & test)
    logger.info("\n🔄 TRANSFORM PHASE (dbt)")
    logger.info("-" * 40)
    dbt_seed_success = _run_dbt(["seed"])
    dbt_run_success = _run_dbt(["run"]) if dbt_seed_success else False
    dbt_test_success = _run_dbt(["test"]) if dbt_run_success else False

    # Step 5: Export for Dashboard
    logger.info("\n📊 SERVE PHASE (Dashboard Export)")
    logger.info("-" * 40)
    export_success = False
    if dbt_run_success:
        try:
            export_success = export_dashboard_data()
        except Exception as e:
            logger.error(f"❌ Dashboard export failed: {e}")
    else:
        logger.warning("⚠️ Skipping dashboard export since dbt run failed.")

    # Report
    duration = (datetime.now() - start).total_seconds()
    counts = get_table_counts()

    logger.info("\n" + "=" * 60)
    logger.info("✅ PIPELINE RUN COMPLETED")
    logger.info(f"   Duration:          {duration:.1f}s")
    logger.info(f"   Weather loaded:    {weather_loaded} rows")
    logger.info(f"   Air quality loaded: {aq_loaded} rows")
    logger.info(f"   Total in DB:       {counts}")
    logger.info(f"   dbt Run Status:    {'SUCCESS' if dbt_run_success else 'FAILED'}")
    logger.info(f"   dbt Test Status:   {'SUCCESS' if dbt_test_success else 'FAILED'}")
    logger.info(f"   Export Status:     {'SUCCESS' if export_success else 'FAILED'}")
    logger.info("=" * 60)

    return {
        "started_at": start.isoformat(),
        "duration_seconds": round(duration, 1),
        "weather_rows": weather_loaded,
        "aq_rows": aq_loaded,
        "dbt_run_success": dbt_run_success,
        "dbt_test_success": dbt_test_success,
        "export_success": export_success,
        "db_counts": counts,
    }


def run_scheduler():
    """
    Run the pipeline on a recurring schedule using APScheduler.
    The pipeline executes immediately on start, then every N hours.
    """
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    scheduler = BlockingScheduler()

    # Graceful shutdown
    def shutdown(signum, frame):
        logger.info("🛑 Shutdown signal received. Stopping scheduler...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Run immediately on start
    logger.info(f"⏰ Scheduler started. Pipeline runs every {SCHEDULE_INTERVAL_HOURS} hour(s)")
    run_once()

    # Schedule recurring runs
    scheduler.add_job(
        run_once,
        trigger=IntervalTrigger(hours=SCHEDULE_INTERVAL_HOURS),
        id="weather_pipeline",
        name="Weather ELT Pipeline",
        max_instances=1,
        coalesce=True,
    )

    next_run = scheduler.get_job("weather_pipeline").next_run_time
    logger.info(f"⏰ Next pipeline run at: {next_run}")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Scheduler stopped.")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Porto DE Weather — ELT Pipeline Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m pipeline.run_pipeline --once        # Single run
  python -m pipeline.run_pipeline --scheduler   # Continuous
        """,
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run the pipeline once and exit",
    )
    parser.add_argument(
        "--scheduler",
        action="store_true",
        help="Run the pipeline on a recurring schedule",
    )

    args = parser.parse_args()
    setup_logging()

    if args.scheduler:
        run_scheduler()
    elif args.once:
        result = run_once()
        print(f"\n[Result] Run result: {result}")
    else:
        parser.print_help()
        print("\n⚠️  Please specify --once or --scheduler")
        sys.exit(1)


if __name__ == "__main__":
    main()
