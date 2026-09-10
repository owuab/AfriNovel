#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookclub.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from books.models import Book

book = Book.objects.first()
if book:
    book.is_featured = True
    book.save()
    print(f'Set {book.title} as featured book')
else:
    print('No books found')