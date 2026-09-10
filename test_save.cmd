@echo off
cd /d "C:\Users\LENOVO\TheBookClub"
".\.venv\Scripts\python.exe" manage.py test books > test_output_full.txt 2>&1
type test_output_full.txt
