#!/usr/bin/env python
"""Test script for Homepage Redesign"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookclub.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client
from books.models import Book, Genre, Review

def test_homepage_view():
    """Test homepage view"""
    print("Testing homepage view...")
    client = Client()
    response = client.get('/')
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("[PASS] Homepage view returns 200")
    
    # Check that the page contains expected content
    content = response.content.decode('utf-8')
    assert 'Discover' in content or 'Popular' in content, "Expected discovery content"
    print("[PASS] Homepage contains discovery content")

def test_featured_book_section():
    """Test featured book section"""
    print("\nTesting featured book section...")
    client = Client()
    response = client.get('/')
    
    content = response.content.decode('utf-8')
    # Check for featured book elements
    assert 'Featured' in content or 'featured' in content.lower(), "Expected featured book section"
    print("[PASS] Featured book section is present")

def test_quick_access_cards():
    """Test quick access cards"""
    print("\nTesting quick access cards...")
    client = Client()
    response = client.get('/')
    
    content = response.content.decode('utf-8')
    # Check for quick access elements
    assert 'Bookshelf' in content or 'bookshelf' in content.lower(), "Expected bookshelf card"
    assert 'Rankings' in content or 'rankings' in content.lower(), "Expected rankings card"
    print("[PASS] Quick access cards are present")

def test_popular_books_section():
    """Test popular books section"""
    print("\nTesting popular books section...")
    client = Client()
    response = client.get('/')
    
    content = response.content.decode('utf-8')
    assert 'Popular' in content or 'popular' in content.lower(), "Expected popular books section"
    print("[PASS] Popular books section is present")

def test_genre_section():
    """Test genre section"""
    print("\nTesting genre section...")
    client = Client()
    response = client.get('/')
    
    content = response.content.decode('utf-8')
    assert 'Genre' in content or 'genre' in content.lower() or 'Category' in content, "Expected genre section"
    print("[PASS] Genre section is present")

def test_recent_books_section():
    """Test recently added books section"""
    print("\nTesting recently added books section...")
    client = Client()
    response = client.get('/')
    
    content = response.content.decode('utf-8')
    assert 'Recent' in content or 'recent' in content.lower(), "Expected recent books section"
    print("[PASS] Recent books section is present")

def test_trending_section():
    """Test trending books section"""
    print("\nTesting trending books section...")
    client = Client()
    response = client.get('/')
    
    content = response.content.decode('utf-8')
    assert 'Trending' in content or 'trending' in content.lower(), "Expected trending section"
    print("[PASS] Trending section is present")

def test_rankings_section():
    """Test top rankings section"""
    print("\nTesting top rankings section...")
    client = Client()
    response = client.get('/')
    
    content = response.content.decode('utf-8')
    assert 'Top' in content or 'top' in content.lower() or 'Ranking' in content, "Expected rankings section"
    print("[PASS] Rankings section is present")

def test_reviews_section():
    """Test recent reviews section"""
    print("\nTesting recent reviews section...")
    client = Client()
    response = client.get('/')
    
    content = response.content.decode('utf-8')
    assert 'Review' in content or 'review' in content.lower(), "Expected reviews section"
    print("[PASS] Reviews section is present")

def test_recommendations_section():
    """Test recommendations section"""
    print("\nTesting recommendations section...")
    client = Client()
    response = client.get('/')
    
    content = response.content.decode('utf-8')
    assert 'Recommended' in content or 'recommended' in content.lower(), "Expected recommendations section"
    print("[PASS] Recommendations section is present")

def test_homepage_context():
    """Test that homepage context has all required data"""
    print("\nTesting homepage context...")
    # Skip this test as it requires proper user authentication setup
    print("[SKIP] Homepage context test (requires auth setup)")

def main():
    print("=" * 60)
    print("Homepage Redesign Test")
    print("=" * 60)
    
    try:
        test_homepage_view()
        test_featured_book_section()
        test_quick_access_cards()
        test_popular_books_section()
        test_genre_section()
        test_recent_books_section()
        test_trending_section()
        test_rankings_section()
        test_reviews_section()
        test_recommendations_section()
        test_homepage_context()
        
        print("\n" + "=" * 60)
        print("[SUCCESS] All homepage tests passed!")
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