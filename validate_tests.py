import subprocess
from pathlib import Path
root = Path(r'C:/Users/LENOVO/AfriNovels')
res = subprocess.run(['python', 'manage.py', 'test', 'books.tests', '--verbosity', '1'], cwd=root, capture_output=True, text=True, timeout=180)
output = 'STDOUT:\n' + (res.stdout[-20000:] or '') + '\nSTDERR:\n' + (res.stderr[-20000:] or '') + f'\nRETURN_CODE: {res.returncode}\n'
Path(root / 'validation_output.txt').write_text(output, encoding='utf-8')
