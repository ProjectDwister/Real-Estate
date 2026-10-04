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
python scripts\igr_metadata_year_scraper.py --years 2026 --village Anik --property 1A/1
python scripts\build_master_transactions.py
git add data/master_transactions.csv data/coverage.csv data/status.json
git diff --cached --quiet
if %errorlevel%==0 (
  echo No public changes detected.
  pause
  exit /b 0
)
git commit -m "Daily IGR real estate update"
git push
pause
