#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookclub.settings')
sys.path.insert(0, 'C:\\Users\\LENOVO\\TheBookClub')

try:
    django.setup()
    print("✓ Django setup successful")
    
    # Try importing models
    from books.models import UserBookshelf, Book, Genre, Author
    print("✓ Models imported successfully")
    
    # Try importing views
    from books.views import recommendations, add_to_bookshelf, view_bookshelf
    print("✓ Views imported successfully")
    
    # Try importing urls
    from books.urls import urlpatterns
    print(f"✓ URLs loaded successfully ({len(urlpatterns)} routes)")
    
    print("\n✓ All imports successful - app is ready!")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
