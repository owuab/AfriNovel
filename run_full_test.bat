@echo off
cd /d "C:\Users\LENOVO\TheBookClub"
.\.venv\Scripts\python.exe manage.py makemigrations books
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py test books
echo.
echo Test completed.
