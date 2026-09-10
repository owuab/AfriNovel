@echo off
setlocal enabledelayedexpansion
cd /d "C:\Users\LENOVO\TheBookClub"
".\.venv\Scripts\python.exe" manage.py test books 2>&1
echo.
echo ====== TEST COMPLETED ======
