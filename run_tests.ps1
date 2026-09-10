$env:Path += ";C:\Users\LENOVO\TheBookClub\.venv\Scripts"
Set-Location "C:\Users\LENOVO\TheBookClub"
python.exe manage.py test books -v 2
