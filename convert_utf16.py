from pathlib import Path
src = Path(r'C:\Users\LENOVO\AfriNovels\test_output.txt')
dst = Path(r'C:\Users\LENOVO\AfriNovels\test_output_utf8.txt')
dst.write_text(src.read_text(encoding='utf-16'), encoding='utf-8')
