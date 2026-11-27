@echo off
echo ============================================================
echo   HK-Link Logistics Management System (v4.0 Full-Stack)
echo ============================================================
echo Installing Flask (if needed)...
pip install -r requirements.txt
echo.
echo Starting Flask Backend Server at http://127.0.0.1:5000 ...
echo Keep this black window open while using the website!
echo.
start http://127.0.0.1:5000
python app.py
pause
