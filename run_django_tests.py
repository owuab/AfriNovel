#!/usr/bin/env python
import os
import sys
import subprocess

os.chdir("C:\\Users\\LENOVO\\TheBookClub")
sys.path.insert(0, "C:\\Users\\LENOVO\\TheBookClub")

# Run tests
result = subprocess.run([
    ".venv\\Scripts\\python.exe",
    "manage.py",
    "test",
    "books",
    "-v", "2"
], capture_output=True, text=True)

print(result.stdout)
print(result.stderr)
print(f"\nReturn code: {result.returncode}")
