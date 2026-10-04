@echo off
setlocal
cd /d "%~dp0"
call run_build.bat
git add data/master_transactions.csv data/coverage.csv data/status.json
git diff --cached --quiet
if %errorlevel%==0 (
  echo No public dataset changes to publish.
  pause
  exit /b 0
)
git commit -m "Update Mumbai real estate data"
git push
pause
