@echo off
title 🌦️ Stop IndoWeather Services
echo =========================================================
echo   🌦️ STOPPING INDOWEATHER SERVICES (AIRFLOW & DASHBOARD)
echo =========================================================
echo.

echo [1/2] Stopping Docker containers...
docker compose -f docker-compose-airflow.yml down
echo.

echo [2/2] Stopping Python HTTP server on port 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr "LISTENING" ^| findstr ":8000"') do (
    taskkill /F /PID %%a >nul 2>&1
    echo [INFO] Stopped Python HTTP server (PID %%a).
)
echo.

echo =========================================================
echo   🛑 ALL SERVICES STOPPED SUCCESSFULLY!
echo =========================================================
echo.
pause
