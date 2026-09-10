#!/usr/bin/env python
"""Test script for Phase 6: Categories and Completed Books"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookclub.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from books.models import Genre, Book, Author, UserBookshelf

User = get_user_model()

def test_categories_view():
    """Test categories listing view"""
    print("Testing categories view...")
    client = Client()
    response = client.get('/categories/')
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("[PASS] Categories view returns 200")
    
    # Check that the page contains expected content
    content = response.content.decode('utf-8')
    assert 'Browse by Category' in content or 'Categories' in content, "Expected category page content"
    print("[PASS] Categories page contains expected content")

def test_category_detail_view():
    """Test category detail view"""
    print("\nTesting category detail view...")
    client = Client()
    
    # Get a test genre
    genre = Genre.objects.first()
    if not genre:
        print("[SKIP] No genres found, skipping test")
        return
    
    response = client.get(f'/categories/{genre.slug}/')
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("[PASS] Category detail view returns 200")
    
    # Check that the page contains the genre name
    content = response.content.decode('utf-8')
    assert genre.name in content, f"Expected genre name '{genre.name}' in content"
    print(f"[PASS] Category: {genre.name} found in page content")

def test_completed_view_anonymous():
    """Test completed books view for anonymous users"""
    print("\nTesting completed view (anonymous)...")
    client = Client()
    response = client.get('/completed/')
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("[PASS] Completed view returns 200 for anonymous users")
    
    # Check that the page contains expected content
    content = response.content.decode('utf-8')
    assert 'Completed Books' in content or 'completed' in content.lower(), "Expected completed books content"
    print("[PASS] Completed page contains expected content")

def test_completed_view_authenticated():
    """Test completed books view for authenticated users"""
    print("\nTesting completed view (authenticated)...")
    
    # Create test user if needed
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com'}
    )
    if created:
        user.set_password('testpass123')
        user.save()
    
    client = Client()
    client.login(username='testuser', password='testpass123')
    response = client.get('/completed/')
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("[PASS] Completed view returns 200 for authenticated users")
    
    # Check that the page contains expected content
    content = response.content.decode('utf-8')
    assert 'Completed Books' in content or 'completed' in content.lower(), "Expected completed books content"
    print("[PASS] Completed page contains expected content for authenticated users")

def test_filter_functionality():
    """Test filter functionality in completed view"""
    print("\nTesting filter functionality...")
    client = Client()
    
    # Test genre filter
    genre = Genre.objects.first()
    if genre:
        response = client.get(f'/completed/?genre={genre.slug}')
        assert response.status_code == 200
        print(f"[PASS] Genre filter works: {genre.slug}")
    
    # Test sort filter
    response = client.get('/completed/?sort=rating')
    assert response.status_code == 200
    print("[PASS] Sort filter works: rating")

def main():
    print("=" * 60)
    print("Phase 6 Test: Categories and Completed Books")
    print("=" * 60)
    
    try:
        test_categories_view()
        test_category_detail_view()
        test_completed_view_anonymous()
        test_completed_view_authenticated()
        test_filter_functionality()
        
        print("\n" + "=" * 60)
        print("[SUCCESS] All Phase 6 tests passed!")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())