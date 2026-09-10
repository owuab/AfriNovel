@echo off
cd /d "C:\Users\LENOVO\TheBookClub"
".\.venv\Scripts\python.exe" manage.py test books > test_results.txt 2>&1
type test_results.txt
pause
