"""Admin dashboard analytics and statistics"""
from decimal import Decimal
from datetime import timedelta

from django.db.models import Count, Q, Avg, Sum
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import (
    Advertisement, AdClick, AdImpression, Chapter, Genre, Author, Book, Review,
    UserBookshelf, ReadingList, MonetizationPayment, PremiumSubscription,
    SubscriptionPlan, WriterEarning, WriterProfile, WriterWithdrawal,
)
from .admin_models import UserSuspension

User = get_user_model()


def get_dashboard_stats():
    """
    Collect all dashboard statistics for admin panel
    Returns a dictionary with comprehensive analytics
    """
    
    try:
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
        
        stats['monetization'] = get_monetization_stats()
        return stats
    except Exception:
        # Return default stats if database queries fail
        return {
            'books': {
                'total': 0, 'published': 0, 'draft': 0, 'archived': 0,
                'featured': 0, 'avg_rating': 0,
                'highest_rated': {'title': 'N/A', 'rating': 0},
                'most_reviewed': {'title': 'N/A', 'count': 0},
            },
            'authors': {
                'total': 0, 'total_followers': 0,
                'most_followed': {'name': 'N/A', 'followers': 0},
            },
            'genres': {
                'total': 0,
                'most_popular': {'name': 'N/A', 'books': 0},
            },
            'users': {
                'total': 0, 'active': 0, 'inactive': 0,
            },
            'reviews': {
                'total': 0, 'avg_per_book': 0,
            },
            'bookshelf': {
                'total_items': 0, 'currently_reading': 0,
                'want_to_read': 0, 'completed': 0,
            },
            'reading_lists': {
                'total': 0, 'public': 0, 'private': 0,
            },
            'monetization': get_monetization_stats(),
        }


def get_monetization_stats():
    """Calculate owner-facing monetary and ad metrics from verified ledgers."""
    now = timezone.now()
    active_subscriptions = PremiumSubscription.objects.filter(
        status=PremiumSubscription.ACTIVE,
        starts_at__lte=now,
        ends_at__gt=now,
    )
    subscription_revenue = MonetizationPayment.objects.filter(
        status=MonetizationPayment.SUCCESS,
        currency='NGN',
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    pending_payments = MonetizationPayment.objects.filter(
        status__in=[MonetizationPayment.PENDING, MonetizationPayment.INITIALIZED],
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    active_ads = Advertisement.objects.filter(is_active=True).filter(
        Q(starts_at__isnull=True) | Q(starts_at__lte=now),
        Q(ends_at__isnull=True) | Q(ends_at__gt=now),
    )
    impressions = AdImpression.objects.count()
    clicks = AdClick.objects.count()
    ad_revenue = sum(
        (ad.estimated_revenue_per_click or Decimal('0')) * ad.click_count
        for ad in Advertisement.objects.annotate(click_count=Count('clicks'))
    )
    paid_payouts = WriterWithdrawal.objects.filter(
        status=WriterWithdrawal.PAID,
        currency='NGN',
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    pending_payouts = WriterWithdrawal.objects.filter(
        status__in=[WriterWithdrawal.PENDING, WriterWithdrawal.PROCESSING],
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    total_earnings = WriterEarning.objects.exclude(
        status=WriterEarning.REVERSED,
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    approved_writers = WriterProfile.objects.filter(status=WriterProfile.APPROVED)
    active_writers = approved_writers.filter(
        user__premium_subscriptions__status=PremiumSubscription.ACTIVE,
        user__premium_subscriptions__starts_at__lte=now,
        user__premium_subscriptions__ends_at__gt=now,
    ).distinct().count()
    platform_revenue = subscription_revenue + ad_revenue - paid_payouts
    return {
        'users': {
            'total': User.objects.count(),
            'subscribers': active_subscriptions.values('user_id').distinct().count(),
            'non_subscribers': max(User.objects.count() - active_subscriptions.values('user_id').distinct().count(), 0),
            'active': User.objects.filter(is_active=True).count(),
            'suspended': UserSuspension.objects.filter(is_active=True).values('user_id').distinct().count(),
        },
        'subscriptions': {
            'active': active_subscriptions.count(),
            'expired': PremiumSubscription.objects.filter(status=PremiumSubscription.EXPIRED).count(),
            'monthly': active_subscriptions.filter(plan__billing_period=SubscriptionPlan.MONTHLY).count(),
            'yearly': active_subscriptions.filter(plan__billing_period=SubscriptionPlan.YEARLY).count(),
            'revenue': subscription_revenue,
            'renewing_30_days': active_subscriptions.filter(ends_at__lte=now + timedelta(days=30), cancel_at_period_end=False).count(),
        },
        'writers': {
            'total': WriterProfile.objects.count(),
            'approved': approved_writers.count(),
            'active': active_writers,
            'published_books': Book.objects.filter(owner__writer_profile__status=WriterProfile.APPROVED, status=Book.PUBLISHED).distinct().count(),
            'chapters': Chapter.objects.filter(book__owner__writer_profile__status=WriterProfile.APPROVED).count(),
            'earnings': total_earnings,
            'withdrawal_requests': WriterWithdrawal.objects.filter(status__in=[WriterWithdrawal.PENDING, WriterWithdrawal.PROCESSING]).count(),
        },
        'advertising': {
            'active_ads': active_ads.count(),
            'impressions': impressions,
            'clicks': clicks,
            'ctr': round(clicks / impressions * 100, 2) if impressions else 0,
            'revenue': ad_revenue,
        },
        'finance': {
            'subscription_revenue': subscription_revenue,
            'advertising_revenue': ad_revenue,
            'writer_payouts': paid_payouts,
            'platform_revenue': platform_revenue,
            'pending_payments': pending_payments + pending_payouts,
            'completed_payments': subscription_revenue + paid_payouts,
        },
    }


def get_recent_activity():
    """Get recent activity for dashboard timeline"""
    
    try:
        recent_books = Book.objects.select_related('author').order_by('-created_at')[:5]
        recent_reviews = Review.objects.select_related('book', 'user').order_by('-created_at')[:5]
        recent_lists = ReadingList.objects.select_related('user').order_by('-created_at')[:5]
        
        activity = {
            'recent_books': recent_books,
            'recent_reviews': recent_reviews,
            'recent_lists': recent_lists,
        }
        
        return activity
    except Exception:
        return {
            'recent_books': [],
            'recent_reviews': [],
            'recent_lists': [],
        }


def get_top_performers():
    """Get top performers data for admin dashboard"""
    
    try:
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
    except Exception:
        return {
            'top_authors': [],
            'top_books': [],
            'top_users': [],
        }


def get_health_metrics():
    """Get system health metrics"""
    
    try:
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
    except Exception:
        return {
            'content_health': {
                'books_with_rating': 0,
                'books_without_rating': 0,
                'published_ratio': 0,
            },
            'user_engagement': {
                'users_with_reviews': 0,
                'users_with_bookshelf': 0,
                'users_with_lists': 0,
            },
            'data_completeness': {
                'authors_with_bio': 0,
                'books_with_summary': 0,
                'books_with_genres': 0,
            }
        }
