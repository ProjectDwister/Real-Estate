@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -m venv .venv
  call .venv\Scripts\activate
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  python -m playwright install chromium
) else (
  call .venv\Scripts\activate
)
python scripts\igr_metadata_year_scraper.py --years 2024-2014 --village Anik --property 1A/1
echo.
echo Historical metadata collection finished. Building sanitized public dataset...
python scripts\build_master_transactions.py
pause
