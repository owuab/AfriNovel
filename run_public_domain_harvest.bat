@echo off
cd /d "%~dp0"
call .venv\Scripts\activate
python manage.py runapscheduler --interval-minutes 60
