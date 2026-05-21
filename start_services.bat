@echo off
title 🌦️ IndoWeather Services Controller
echo =========================================================
echo   🌦️ STARTING INDOWEATHER SERVICES (AIRFLOW & DASHBOARD)
echo =========================================================
echo.

:: Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running! Please start Docker Desktop first.
    echo.
    pause
    exit /b 1
)

echo [1/3] Starting Docker containers (Postgres & Airflow)...
docker compose -f docker-compose-airflow.yml up -d
if %errorlevel% neq 0 (
    echo [ERROR] Failed to start Docker containers.
    echo.
    pause
    exit /b 1
)
echo.

echo [2/3] Checking Dashboard local HTTP server (Port 8000)...
netstat -ano | findstr "LISTENING" | findstr ":8000" >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] A server is already running on port 8000.
) else (
    echo [INFO] Starting Python HTTP server on port 8000 serving 'dashboard' directory...
    start /b python -m http.server 8000 --directory dashboard
)
echo.

echo [3/3] Launching web browser pages...
timeout /t 2 /nobreak >nul
start http://localhost:8000
start http://localhost:8085

echo =========================================================
echo   🎉 ALL SERVICES ARE UP AND RUNNING!
echo =========================================================
echo.
echo   🔗 Local Dashboard:   http://localhost:8000
echo   🔗 Airflow Web UI:     http://localhost:8085 (admin / admin)
echo   🔗 Postgres DW Port:   localhost:5433 (dbt_user / dbt_pass)
echo.
echo =========================================================
echo Press any key to exit this console (services will keep running in the background).
pause >nul
