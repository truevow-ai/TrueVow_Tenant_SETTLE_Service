@echo off
REM Start TrueVow SETTLE Service
REM Port: 8002 (verified — not 3009 as external docs claimed)
REM Requires: Python venv, .env.local with Supabase + CourtListener keys
echo Starting SETTLE Service on port 8002...
cd /d "%~dp0"
venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --reload
