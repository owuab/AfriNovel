import subprocess
import sys
import os

os.chdir("C:\\Users\\LENOVO\\TheBookClub")

# Run migrations
print("Running migrations...")
subprocess.run([".venv\\Scripts\\python.exe", "manage.py", "makemigrations", "books"])
subprocess.run([".venv\\Scripts\\python.exe", "manage.py", "migrate"])

# Run tests
print("\nRunning tests...")
result = subprocess.run([".venv\\Scripts\\python.exe", "manage.py", "test", "books"], 
                       capture_output=False, text=True)
sys.exit(result.returncode)
