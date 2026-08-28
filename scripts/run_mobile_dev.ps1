@echo off
setlocal
cd /d "%~dp0.."

echo Starting FastAPI on http://127.0.0.1:8000
start "Garmin API" cmd /k "uvicorn api.main:app --reload --host 127.0.0.1 --port 8000"

echo Starting Vite on http://127.0.0.1:5173
cd frontend
npm run dev
