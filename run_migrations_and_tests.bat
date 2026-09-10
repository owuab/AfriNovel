@echo off
cd /d "C:\Users\LENOVO\TheBookClub"
echo Running migrations...
".\.venv\Scripts\python.exe" manage.py makemigrations books
".\.venv\Scripts\python.exe" manage.py migrate
echo.
echo Running tests...
".\.venv\Scripts\python.exe" manage.py test books
echo.
echo Done.
