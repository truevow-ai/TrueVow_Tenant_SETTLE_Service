@echo off
REM Start TrueVow SETTLE Service
REM Port: 3041 (from Internal Ops .env.local)
echo Starting SETTLE Service on port 3041...
cd /d "%~dp0"
python -m uvicorn app.main:app --host 127.0.0.1 --port 3041 --reload
