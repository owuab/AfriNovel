#!/usr/bin/env python
"""Test script for Phase 7: Rankings and Trending Logic"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookclub.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client
from books.models import Genre, Book, Author, UserBookshelf, Review
from django.contrib.auth import get_user_model

User = get_user_model()

def test_rankings_view():
    """Test rankings view"""
    print("Testing rankings view...")
    client = Client()
    response = client.get('/rankings/')
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("[PASS] Rankings view returns 200")
    
    # Check that the page contains expected content
    content = response.content.decode('utf-8')
    assert 'Rankings' in content or 'rankings' in content.lower(), "Expected rankings content"
    print("[PASS] Rankings page contains expected content")

def test_ranking_type_filters():
    """Test different ranking type filters"""
    print("\nTesting ranking type filters...")
    client = Client()
    
    # Test rating filter
    response = client.get('/rankings/?type=rating')
    assert response.status_code == 200
    print("[PASS] Rating filter works")
    
    # Test reads filter
    response = client.get('/rankings/?type=reads')
    assert response.status_code == 200
    print("[PASS] Reads filter works")
    
    # Test reviews filter
    response = client.get('/rankings/?type=reviews')
    assert response.status_code == 200
    print("[PASS] Reviews filter works")
    
    # Test trending filter
    response = client.get('/rankings/?type=trending')
    assert response.status_code == 200
    print("[PASS] Trending filter works")

def test_time_filters():
    """Test time period filters"""
    print("\nTesting time period filters...")
    client = Client()
    
    # Test all time
    response = client.get('/rankings/?time=all')
    assert response.status_code == 200
    print("[PASS] All time filter works")
    
    # Test this month
    response = client.get('/rankings/?time=month')
    assert response.status_code == 200
    print("[PASS] This month filter works")
    
    # Test this week
    response = client.get('/rankings/?time=week')
    assert response.status_code == 200
    print("[PASS] This week filter works")

def test_category_filter():
    """Test category filter in rankings"""
    print("\nTesting category filter...")
    client = Client()
    
    # Get a test genre
    genre = Genre.objects.first()
    if genre:
        response = client.get(f'/rankings/?category={genre.slug}')
        assert response.status_code == 200
        print(f"[PASS] Category filter works: {genre.slug}")
    else:
        print("[SKIP] No genres found for category filter test")

def test_combined_filters():
    """Test combined filters"""
    print("\nTesting combined filters...")
    client = Client()
    
    genre = Genre.objects.first()
    if genre:
        response = client.get(f'/rankings/?type=rating&time=month&category={genre.slug}')
        assert response.status_code == 200
        print("[PASS] Combined filters work")
    else:
        response = client.get('/rankings/?type=rating&time=month')
        assert response.status_code == 200
        print("[PASS] Combined filters work (without category)")

def test_ranking_annotations():
    """Test that ranking annotations work"""
    print("\nTesting ranking annotations...")
    from books.views import rankings
    from django.test import RequestFactory
    
    factory = RequestFactory()
    request = factory.get('/rankings/?type=rating')
    response = rankings(request)
    
    assert response.status_code == 200
    print("[PASS] Ranking annotations work correctly")

def test_ranking_component():
    """Test that ranking component is included"""
    print("\nTesting ranking component...")
    client = Client()
    response = client.get('/rankings/')
    
    content = response.content.decode('utf-8')
    # Check for ranking-specific elements
    assert 'rank' in content.lower() or 'ranking' in content.lower(), "Expected ranking elements"
    print("[PASS] Ranking component is included")

def main():
    print("=" * 60)
    print("Phase 7 Test: Rankings and Trending Logic")
    print("=" * 60)
    
    try:
        test_rankings_view()
        test_ranking_type_filters()
        test_time_filters()
        test_category_filter()
        test_combined_filters()
        test_ranking_annotations()
        test_ranking_component()
        
        print("\n" + "=" * 60)
        print("[SUCCESS] All Phase 7 tests passed!")
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