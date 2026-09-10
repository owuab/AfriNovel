"""Admin dashboard analytics and statistics"""
from django.db.models import Count, Q, Avg
from django.contrib.auth import get_user_model
from .models import Genre, Author, Book, Review, UserBookshelf, ReadingList

User = get_user_model()


def get_dashboard_stats():
    """
    Collect all dashboard statistics for admin panel
    Returns a dictionary with comprehensive analytics
    """
    
    # Count statistics
    total_books = Book.objects.count()
    published_books = Book.objects.filter(status='published').count()
    draft_books = Book.objects.filter(status='draft').count()
    archived_books = Book.objects.filter(status='archived').count()
    
    total_authors = Author.objects.count()
    total_genres = Genre.objects.count()
    total_users = User.objects.count()
    active_users = User.objects.filter(bookshelf__isnull=False).distinct().count()
    
    total_reviews = Review.objects.count()
    total_reading_lists = ReadingList.objects.count()
    public_lists = ReadingList.objects.filter(is_public=True).count()
    private_lists = ReadingList.objects.filter(is_public=False).count()
    
    # Book statistics
    featured_books = Book.objects.filter(is_featured=True).count()
    avg_rating = Book.objects.filter(rating__gt=0).aggregate(Avg('rating'))['rating__avg'] or 0
    highest_rated_book = Book.objects.filter(rating__gt=0).order_by('-rating').first()
    
    # User statistics
    total_bookshelf_items = UserBookshelf.objects.count()
    currently_reading = UserBookshelf.objects.filter(status='currently_reading').count()
    want_to_read = UserBookshelf.objects.filter(status='want_to_read').count()
    completed_reading = UserBookshelf.objects.filter(status='read').count()
    
    # Engagement statistics
    total_followers = sum(author.followers.count() for author in Author.objects.all())
    most_followed_author = Author.objects.annotate(
        follower_count=Count('followers')
    ).order_by('-follower_count').first()
    
    most_reviewed_book = Book.objects.annotate(
        review_count=Count('reviews')
    ).order_by('-review_count').first()
    
    # Genre statistics
    most_popular_genre = Genre.objects.annotate(
        book_count=Count('books')
    ).order_by('-book_count').first()
    
    # Format statistics for display
    stats = {
        # Books Section
        'books': {
            'total': total_books,
            'published': published_books,
            'draft': draft_books,
            'archived': archived_books,
            'featured': featured_books,
            'avg_rating': round(avg_rating, 2) if avg_rating else 0,
            'highest_rated': {
                'title': highest_rated_book.title if highest_rated_book else 'N/A',
                'rating': float(highest_rated_book.rating) if highest_rated_book else 0,
            },
            'most_reviewed': {
                'title': most_reviewed_book.title if most_reviewed_book else 'N/A',
                'count': most_reviewed_book.reviews.count() if most_reviewed_book else 0,
            },
        },
        
        # Authors Section
        'authors': {
            'total': total_authors,
            'total_followers': total_followers,
            'most_followed': {
                'name': most_followed_author.name if most_followed_author else 'N/A',
                'followers': most_followed_author.followers.count() if most_followed_author else 0,
            },
        },
        
        # Genres Section
        'genres': {
            'total': total_genres,
            'most_popular': {
                'name': most_popular_genre.name if most_popular_genre else 'N/A',
                'books': most_popular_genre.books.count() if most_popular_genre else 0,
            },
        },
        
        # Users Section
        'users': {
            'total': total_users,
            'active': active_users,
            'inactive': total_users - active_users,
        },
        
        # Reviews Section
        'reviews': {
            'total': total_reviews,
            'avg_per_book': round(total_reviews / total_books, 2) if total_books > 0 else 0,
        },
        
        # Bookshelf Section
        'bookshelf': {
            'total_items': total_bookshelf_items,
            'currently_reading': currently_reading,
            'want_to_read': want_to_read,
            'completed': completed_reading,
        },
        
        # Reading Lists Section
        'reading_lists': {
            'total': total_reading_lists,
            'public': public_lists,
            'private': private_lists,
        },
    }
    
    return stats


def get_recent_activity():
    """Get recent activity for dashboard timeline"""
    
    recent_books = Book.objects.select_related('author').order_by('-created_at')[:5]
    recent_reviews = Review.objects.select_related('book', 'user').order_by('-created_at')[:5]
    recent_lists = ReadingList.objects.select_related('user').order_by('-created_at')[:5]
    
    activity = {
        'recent_books': recent_books,
        'recent_reviews': recent_reviews,
        'recent_lists': recent_lists,
    }
    
    return activity


def get_top_performers():
    """Get top performers data for admin dashboard"""
    
    top_authors = Author.objects.annotate(
        book_count=Count('books'),
        follower_count=Count('followers')
    ).order_by('-follower_count')[:5]
    
    top_books = Book.objects.annotate(
        review_count=Count('reviews')
    ).filter(status='published').order_by('-review_count')[:5]
    
    top_users = User.objects.annotate(
        review_count=Count('reviews'),
        bookshelf_count=Count('bookshelf')
    ).order_by('-review_count')[:5]
    
    return {
        'top_authors': top_authors,
        'top_books': top_books,
        'top_users': top_users,
    }


def get_health_metrics():
    """Get system health metrics"""
    
    metrics = {
        'content_health': {
            'books_with_rating': Book.objects.filter(rating__gt=0).count(),
            'books_without_rating': Book.objects.filter(rating=0).count(),
            'published_ratio': round(
                (Book.objects.filter(status='published').count() / max(Book.objects.count(), 1)) * 100, 1
            ),
        },
        'user_engagement': {
            'users_with_reviews': User.objects.filter(reviews__isnull=False).distinct().count(),
            'users_with_bookshelf': User.objects.filter(bookshelf__isnull=False).distinct().count(),
            'users_with_lists': User.objects.filter(reading_lists__isnull=False).distinct().count(),
        },
        'data_completeness': {
            'authors_with_bio': Author.objects.exclude(bio='').count(),
            'books_with_summary': Book.objects.exclude(summary='').count(),
            'books_with_genres': Book.objects.filter(genres__isnull=False).distinct().count(),
        }
    }
    
    return metrics
