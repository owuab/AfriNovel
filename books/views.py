from django.contrib import messages
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from datetime import timedelta
from django.utils import timezone
import json
import zipfile
from pathlib import Path
from .forms import ProfileEditForm

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Count, F, Q
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods, require_POST

from .models import (
    Author, AuthorFollow, Bookmark, Book, CatalogBook, CatalogCategory, CatalogLibraryEntry, Genre,
    Highlight, ReadingList, ReadingNote, ReadingProgress, Review, ReviewComment,
    SearchHistory, UserBookshelf, AuthenticationEvent,
    Notification, PostComment, PostLike, BookUpload,
    PostRepost, SavedPost, SocialPost, UserBlock, UserFollow, UserMute, UserProfile,
)
from .admin_models import BookApprovalStatus
from .admin_utilities import AdminNotificationManager
from .social_auth import BookClubRegistrationForm, EmailOrUsernameAuthenticationForm
from .services import CatalogService, OpenLibraryProvider, ProviderUnavailable, fetch_reader_text, fetch_uploaded_book_sections, fetch_uploaded_book_text, split_reader_sections


def landing_page(request):
    """Public landing page with book discovery focus"""
    _seed_homepage_books_from_catalog()
    asian_books = CatalogBook.objects.filter(
        categories__category=CatalogCategory.ASIAN,
        disabled=False,
        full_text_available=True,
        copyright_status__in={CatalogBook.PUBLIC_DOMAIN_STATUS, CatalogBook.OPEN_LICENSE, CatalogBook.AUTHORIZED},
    ).distinct().order_by('-publication_year', 'title')[:8]
    asian_subcategories = CatalogCategory.SUBCATEGORY_CHOICES
    # Get featured book for hero section
    featured_book = Book.objects.filter(
        is_featured=True, 
        status=Book.PUBLISHED
    ).select_related('author').prefetch_related('genres').first()
    
    # Popular books (highest rated)
    popular_books = Book.objects.filter(
        status=Book.PUBLISHED
    ).select_related('author').prefetch_related('genres').order_by('-rating', '-created_at')[:8]
    
    # Browse by genre
    genres = Genre.objects.all().annotate(
        book_count=Count('books')
    ).order_by('name')[:12]
    
    # Recently added books
    recent_books = Book.objects.filter(
        status=Book.PUBLISHED
    ).select_related('author').prefetch_related('genres').order_by('-created_at')[:8]
    
    # Trending books (recent with high engagement)
    trending_books = Book.objects.filter(
        status=Book.PUBLISHED,
        created_at__gte=timezone.now() - timedelta(days=30)
    ).select_related('author').prefetch_related('genres').order_by('-rating', '-created_at')[:8]
    
    # Top rankings (top 5 books)
    top_ranked_books = Book.objects.filter(
        status=Book.PUBLISHED
    ).select_related('author').prefetch_related('genres').order_by('-rating', '-created_at')[:5]
    
    # Recent reviews
    recent_reviews = Review.objects.select_related(
        'user', 'book', 'book__author'
    ).order_by('-created_at')[:5]
    
    # Recommendations (for authenticated users, otherwise popular books)
    is_authenticated = request.user.is_authenticated if hasattr(request, 'user') else False
    if is_authenticated:
        # Simple recommendation: books from genres user has read
        user_genres = Genre.objects.filter(
            books__on_shelves__user=request.user,
            books__on_shelves__status=UserBookshelf.READ
        ).distinct()
        
        if user_genres.exists():
            recommended_books = Book.objects.filter(
                status=Book.PUBLISHED,
                genres__in=user_genres
            ).exclude(
                on_shelves__user=request.user
            ).select_related('author').prefetch_related('genres').distinct()[:8]
        else:
            recommended_books = popular_books[:8]
    else:
        recommended_books = popular_books[:8]
    
    context = {
        'featured_book': featured_book,
        'popular_books': popular_books,
        'genres': genres,
        'recent_books': recent_books,
        'trending_books': trending_books,
        'top_ranked_books': top_ranked_books,
        'recent_reviews': recent_reviews,
        'recommended_books': recommended_books,
        'asian_books': asian_books,
        'asian_subcategories': asian_subcategories,
        'is_authenticated': is_authenticated,
    }
    return render(request, 'books/landing.html', context)


def _public_free_catalog_books(limit=8):
    """Return approved public-domain and open-license catalogue records for anonymous reading."""
    return CatalogBook.objects.filter(
        disabled=False,
        full_text_available=True,
        copyright_status__in={
            CatalogBook.PUBLIC_DOMAIN_STATUS,
            CatalogBook.OPEN_LICENSE,
            CatalogBook.AUTHORIZED,
        },
        access_type__in={
            CatalogBook.PUBLIC_DOMAIN,
            CatalogBook.OPEN_ACCESS,
            CatalogBook.FREE_FULL_TEXT,
        },
    ).order_by('-publication_year', '-updated_at')[:limit]


def _seed_homepage_books_from_catalog():
    """Populate the regular Book model from the legal catalog so homepage cards render even when authored books already exist."""
    for catalog_book in _public_free_catalog_books(limit=24):
        existing_book = Book.objects.filter(title=catalog_book.title).first()
        if existing_book:
            changed_fields = []
            if existing_book.catalog_book_id != catalog_book.pk:
                existing_book.catalog_book = catalog_book
                changed_fields.append('catalog_book')
            if existing_book.rating:
                existing_book.rating = 0
                changed_fields.append('rating')
            if not existing_book.cover_url and catalog_book.cover_image_url:
                existing_book.cover_url = catalog_book.cover_image_url
                changed_fields.append('cover_url')
            if changed_fields:
                existing_book.save(update_fields=changed_fields)
            continue

        author_name = (catalog_book.authors or ['Unknown Author'])[0] if catalog_book.authors else 'Unknown Author'
        author, _ = Author.objects.get_or_create(name=author_name)
        base_slug = slugify(catalog_book.title) or 'public-domain-book'
        slug = base_slug
        counter = 1
        while Book.objects.filter(slug=slug).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1

        summary = catalog_book.description.strip() or 'A legal, public-domain reading pick from AfriNovel.'
        book = Book.objects.create(
            title=catalog_book.title,
            slug=slug,
            author=author,
            summary=summary,
            catalog_book=catalog_book,
            rating=0,
            cover_url=catalog_book.cover_image_url,
            cover_color='linear-gradient(135deg, #d6c29a, #7c5d45)',
            status=Book.PUBLISHED,
            is_featured=True,
        )
        for subject in (catalog_book.subjects or [])[:5]:
            genre, _ = Genre.objects.get_or_create(name=subject, defaults={'slug': slugify(subject)})
            book.genres.add(genre)


def home(request):
    """Discovery-focused homepage for all users"""
    _seed_homepage_books_from_catalog()
    asian_books = CatalogBook.objects.filter(
        categories__category=CatalogCategory.ASIAN,
        disabled=False,
        full_text_available=True,
        copyright_status__in={CatalogBook.PUBLIC_DOMAIN_STATUS, CatalogBook.OPEN_LICENSE, CatalogBook.AUTHORIZED},
    ).distinct().order_by('-publication_year', 'title')[:8]
    asian_subcategories = CatalogCategory.SUBCATEGORY_CHOICES
    # Featured book (hero section)
    featured_book = Book.objects.filter(is_featured=True, status=Book.PUBLISHED).select_related('author').prefetch_related('genres').first()
    
    # Popular books (by rating)
    popular_books = Book.objects.filter(status=Book.PUBLISHED).select_related('author', 'catalog_book').prefetch_related('genres').order_by('-view_count', '-rating')[:8]
    
    # Recently added books
    recent_books = Book.objects.filter(status=Book.PUBLISHED).select_related('author', 'catalog_book').prefetch_related('genres').order_by('-created_at')[:8]
    
    # Public catalogue picks: legal free books available without account creation.
    free_catalog_books = _public_free_catalog_books(8)
    
    # Genres for browsing
    genres = Genre.objects.all().annotate(book_count=Count('books')).order_by('name')[:12]
    
    # Top ranked books
    top_ranked = Book.objects.filter(status=Book.PUBLISHED).select_related('author').prefetch_related('genres').order_by('-rating')[:5]
    
    # Recent reviews
    recent_reviews = Review.objects.select_related('user', 'book').order_by('-created_at')[:5]
    
    # Recommendations for authenticated users
    recommended_books = []
    if request.user.is_authenticated:
        user_books = request.user.bookshelf.filter(
            status__in=[UserBookshelf.READ, UserBookshelf.CURRENTLY_READING]
        ).select_related('book')
        
        user_genres = set()
        for shelf_item in user_books:
            user_genres.update(shelf_item.book.genres.values_list('id', flat=True))
        
        if user_genres:
            recommended_books = Book.objects.filter(
                status=Book.PUBLISHED,
                genres__id__in=user_genres
            ).exclude(
                on_shelves__user=request.user
            ).distinct().order_by('-rating')[:8]
    
    context = {
        'featured_book': featured_book,
        'popular_books': popular_books,
        'recent_books': recent_books,
        'free_catalog_books': free_catalog_books,
        'asian_books': asian_books,
        'asian_subcategories': asian_subcategories,
        'genres': genres,
        'top_ranked': top_ranked,
        'recent_reviews': recent_reviews,
        'recommended_books': recommended_books,
        'user': request.user,
    }
    return render(request, 'books/home.html', context)


def book_detail(request, slug):
    book = get_object_or_404(Book, slug=slug, status=Book.PUBLISHED)
    catalog_book = book.catalog_book
    if not catalog_book:
        catalog_book = CatalogBook.objects.filter(
            title=book.title,
            disabled=False,
            full_text_available=True,
            copyright_status__in={CatalogBook.PUBLIC_DOMAIN_STATUS, CatalogBook.OPEN_LICENSE, CatalogBook.AUTHORIZED},
        ).first()
        if catalog_book:
            Book.objects.filter(pk=book.pk).update(catalog_book=catalog_book)
    if catalog_book and catalog_book.can_read_in_app:
        return redirect('catalogue_reader', book_id=catalog_book.pk)
    Book.objects.filter(pk=book.pk).update(view_count=F('view_count') + 1)
    book.refresh_from_db(fields=['view_count'])
    context = {
        'book': book,
        'reviews': book.reviews.select_related('user')[:10],
        'has_uploaded_reader': (
            book.uploads.filter(kind=BookUpload.MANUSCRIPT).exists()
            and hasattr(book, 'approval_status')
            and book.approval_status.status == BookApprovalStatus.APPROVED
        ),
    }
    return render(request, 'books/book_detail.html', context)


@login_required
def uploaded_book_reader(request, slug):
    book = get_object_or_404(
        Book.objects.select_related('author'),
        slug=slug,
        status=Book.PUBLISHED,
        approval_status__status=BookApprovalStatus.APPROVED,
    )
    manuscript = book.uploads.filter(kind=BookUpload.MANUSCRIPT).order_by('-created_at').first()
    if not manuscript:
        return render(request, 'books/reader.html', {
            'book': book,
            'sections': [],
            'progress': None,
            'bookmarks': [],
            'reader_error': 'This book does not have a readable manuscript.',
        }, status=404)
    try:
        sections = fetch_uploaded_book_sections(manuscript)
        reader_error = ''
    except (ProviderUnavailable, ValueError, zipfile.BadZipFile) as error:
        sections = []
        reader_error = str(error)
    return render(request, 'books/reader.html', {
        'book': book,
        'sections': sections,
        'progress': None,
        'bookmarks': [],
        'reader_error': reader_error,
        'chapter_number': 1,  # Default to chapter 1 for uploaded books
    })


def reader_dashboard(request):
    if request.user.is_authenticated:
        currently_reading = request.user.bookshelf.filter(status=UserBookshelf.CURRENTLY_READING).select_related('book')
        want_to_read = request.user.bookshelf.filter(status=UserBookshelf.WANT_TO_READ).select_related('book')[:4]
        read_books = request.user.bookshelf.filter(status=UserBookshelf.READ).select_related('book')[:4]
        reading_stats = {
            'read': request.user.bookshelf.filter(status=UserBookshelf.READ).count(),
            'currently_reading': request.user.bookshelf.filter(status=UserBookshelf.CURRENTLY_READING).count(),
            'total': request.user.bookshelf.count(),
        }
        context = {
            'section_title': 'My Library',
            'currently_reading': currently_reading,
            'want_to_read': want_to_read,
            'read_books': read_books,
            'bookshelf_count': request.user.bookshelf.count(),
            'reading_stats': reading_stats,
            'user': request.user,
        }
    else:
        context = {
            'section_title': 'My Library',
            'currently_reading': [],
            'want_to_read': [],
            'read_books': [],
            'bookshelf_count': 0,
            'reading_stats': {'read': 0, 'currently_reading': 0, 'total': 0},
            'user': request.user,
        }
    return render(request, 'books/reader_dashboard.html', context)


def _profile_for(user):
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={'display_name': user.get_full_name() or user.username},
    )
    return profile


def _blocked_users(user):
    if not user.is_authenticated:
        return []
    return list(UserBlock.objects.filter(blocker=user).values_list('blocked_id', flat=True)) + list(UserBlock.objects.filter(blocked=user).values_list('blocker_id', flat=True))


def _feed_queryset(user, tab):
    posts = SocialPost.objects.filter(hidden=False).select_related('author', 'book', 'catalog_book', 'quoted_post__author').annotate(
        like_count=Count('likes', distinct=True), comment_count=Count('comments', distinct=True), repost_count=Count('reposts', distinct=True),
    )
    if user.is_authenticated:
        posts = posts.exclude(author_id__in=_blocked_users(user))
        if tab == 'following':
            posts = posts.filter(author__in=UserFollow.objects.filter(follower=user).values('followed'))
    elif tab == 'following':
        return posts.none()
    return posts


@login_required
def social_feed(request, tab='home'):
    if tab not in {'home', 'following', 'discover'}:
        return HttpResponseBadRequest('Unknown feed.')
    posts = _feed_queryset(request.user, tab)
    if tab == 'discover':
        posts = posts.order_by('-like_count', '-created_at')
    page = Paginator(posts, 20).get_page(request.GET.get('page'))
    liked_post_ids = set(PostLike.objects.filter(user=request.user, post__in=page.object_list).values_list('post_id', flat=True))
    saved_post_ids = set(SavedPost.objects.filter(user=request.user, post__in=page.object_list).values_list('post_id', flat=True))
    return render(request, 'books/social_feed.html', {'posts': page, 'tab': tab, 'liked_post_ids': liked_post_ids, 'saved_post_ids': saved_post_ids})


@login_required
@require_POST
def create_post(request):
    content = request.POST.get('content', '').strip()
    book_id = request.POST.get('book_id')
    catalog_book_id = request.POST.get('catalog_book_id')
    if not content and not book_id and not catalog_book_id:
        messages.error(request, 'Write something or attach a book before posting.')
        return redirect('social_feed')
    if len(content) > SocialPost.MAX_LENGTH:
        messages.error(request, f'Posts are limited to {SocialPost.MAX_LENGTH} characters.')
        return redirect('social_feed')
    post = SocialPost.objects.create(
        author=request.user, content=content, image_url=request.POST.get('image_url', '').strip(),
        book=Book.objects.filter(pk=book_id, status=Book.PUBLISHED).first() if book_id else None,
        catalog_book=CatalogBook.objects.filter(pk=catalog_book_id, disabled=False).first() if catalog_book_id else None,
    )
    _notify_mentions(post)
    messages.success(request, 'Your post is live.')
    return redirect('post_detail', post_id=post.pk)


def _notify(recipient, actor, notification_type, post=None, message=''):
    if recipient != actor:
        Notification.objects.create(recipient=recipient, actor=actor, notification_type=notification_type, post=post, message=message)


def _notify_mentions(post):
    import re
    usernames = set(re.findall(r'(?<!\w)@([\w.@+-]+)', post.content))
    for username in usernames:
        recipient = get_user_model().objects.filter(username__iexact=username).first()
        if recipient:
            _notify(recipient, post.author, Notification.MENTION, post, f'{post.author.username} mentioned you')


@login_required
@require_POST
def toggle_post_like(request, post_id):
    post = get_object_or_404(SocialPost, pk=post_id, hidden=False)
    like, created = PostLike.objects.get_or_create(user=request.user, post=post)
    if created:
        _notify(post.author, request.user, Notification.LIKE, post, f'{request.user.username} liked your post')
    else:
        like.delete()
    return redirect(request.POST.get('next') or 'post_detail', post_id=post.pk)


@login_required
@require_POST
def toggle_saved_post(request, post_id):
    post = get_object_or_404(SocialPost, pk=post_id, hidden=False)
    saved, created = SavedPost.objects.get_or_create(user=request.user, post=post)
    if not created:
        saved.delete()
    return redirect(request.POST.get('next') or 'post_detail', post_id=post.pk)


@login_required
@require_POST
def repost_post(request, post_id):
    post = get_object_or_404(SocialPost, pk=post_id, hidden=False)
    quote = request.POST.get('quote', '').strip()
    if quote:
        if len(quote) > SocialPost.MAX_LENGTH:
            return HttpResponseBadRequest('Quote is too long.')
        SocialPost.objects.create(author=request.user, content=quote, quoted_post=post)
    else:
        _, created = PostRepost.objects.get_or_create(user=request.user, post=post)
        if not created:
            messages.info(request, 'You already reposted this.')
            return redirect('post_detail', post_id=post.pk)
    _notify(post.author, request.user, Notification.REPOST, post, f'{request.user.username} reposted your post')
    return redirect('post_detail', post_id=post.pk)


@login_required
@require_POST
def create_post_comment(request, post_id):
    post = get_object_or_404(SocialPost, pk=post_id, hidden=False)
    content = request.POST.get('content', '').strip()
    if not content or len(content) > 1000:
        return HttpResponseBadRequest('A comment must contain up to 1,000 characters.')
    parent_id = request.POST.get('parent_id')
    parent = PostComment.objects.filter(pk=parent_id, post=post).first() if parent_id else None
    if parent and parent.parent_id:
        parent = parent.parent
    comment = PostComment.objects.create(post=post, author=request.user, parent=parent, content=content)
    _notify(parent.author if parent else post.author, request.user, Notification.COMMENT, post, f'{request.user.username} replied to your post')
    return redirect('post_detail', post_id=post.pk)


def post_detail(request, post_id):
    post = get_object_or_404(SocialPost.objects.select_related('author', 'book', 'catalog_book').annotate(like_count=Count('likes'), repost_count=Count('reposts')), pk=post_id, hidden=False)
    comments = post.comments.filter(parent__isnull=True, hidden=False).select_related('author').prefetch_related('replies__author')
    liked = request.user.is_authenticated and PostLike.objects.filter(user=request.user, post=post).exists()
    saved = request.user.is_authenticated and SavedPost.objects.filter(user=request.user, post=post).exists()
    return render(request, 'books/post_detail.html', {'post': post, 'comments': comments, 'liked': liked, 'saved': saved})


@login_required
@require_POST
def toggle_user_follow(request, username):
    followed = get_object_or_404(get_user_model(), username=username)
    if followed == request.user:
        return HttpResponseBadRequest('You cannot follow yourself.')
    if UserBlock.objects.filter(Q(blocker=request.user, blocked=followed) | Q(blocker=followed, blocked=request.user)).exists():
        return HttpResponseBadRequest('This account cannot be followed.')
    follow, created = UserFollow.objects.get_or_create(follower=request.user, followed=followed)
    if created:
        _notify(followed, request.user, Notification.FOLLOW, message=f'{request.user.username} started following you')
    else:
        follow.delete()
    return redirect(request.POST.get('next') or 'social_profile', username=followed.username)


def social_profile(request, username, tab='posts'):
    profile_user = get_object_or_404(get_user_model(), username=username)
    profile = _profile_for(profile_user)
    own_profile = request.user.is_authenticated and request.user == profile_user
    if not own_profile:
        UserProfile.objects.filter(pk=profile.pk).update(profile_views=F('profile_views') + 1)
        profile.refresh_from_db()
    following = request.user.is_authenticated and UserFollow.objects.filter(follower=request.user, followed=profile_user).exists()
    posts = SocialPost.objects.filter(author=profile_user, hidden=False).select_related('book', 'catalog_book').annotate(like_count=Count('likes'), comment_count=Count('comments'))
    context = {'profile_user': profile_user, 'profile': profile, 'tab': tab, 'is_own_profile': own_profile, 'following': following,
               'followers_count': profile_user.follower_users.count(), 'following_count': profile_user.following_users.count(),
               'books_read_count': profile_user.bookshelf.filter(status=UserBookshelf.READ).count(), 'posts': posts[:30],
               'reviews': Review.objects.filter(user=profile_user).select_related('book')[:30],
               'books': profile_user.bookshelf.select_related('book').filter(status__in=[UserBookshelf.READ, UserBookshelf.CURRENTLY_READING])[:30]}
    return render(request, 'books/social_profile.html', context)


def followers_page(request, username, relationship='followers'):
    profile_user = get_object_or_404(get_user_model(), username=username)
    if relationship not in {'followers', 'following'}:
        return HttpResponseBadRequest('Unknown relationship.')
    query = request.GET.get('q', '').strip()
    users = (profile_user.follower_users.select_related('follower') if relationship == 'followers' else profile_user.following_users.select_related('followed'))
    people = [row.follower if relationship == 'followers' else row.followed for row in users]
    if query:
        people = [person for person in people if query.casefold() in person.username.casefold() or query.casefold() in person.get_full_name().casefold()]
    page = Paginator(people, 20).get_page(request.GET.get('page'))
    followed_ids = set(UserFollow.objects.filter(follower=request.user, followed__in=page.object_list).values_list('followed_id', flat=True)) if request.user.is_authenticated else set()
    return render(request, 'books/followers.html', {'profile_user': profile_user, 'people': page, 'relationship': relationship, 'followed_ids': followed_ids, 'query': query})


@login_required
def notifications_page(request):
    notification_filter = request.GET.get('type', '')
    notifications = request.user.notifications.select_related('actor', 'post').all()
    if notification_filter in {choice[0] for choice in Notification.TYPES}:
        notifications = notifications.filter(notification_type=notification_filter)
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'books/notifications.html', {'notifications': notifications[:100], 'active_type': notification_filter})


@login_required
def reading_now(request):
    local = request.user.bookshelf.filter(status=UserBookshelf.CURRENTLY_READING).select_related('book')
    catalogue = ReadingProgress.objects.filter(user=request.user).select_related('book').order_by('-last_read_at')
    return render(request, 'books/reading_now.html', {'local_books': local, 'catalogue_books': catalogue})


@login_required
def social_reviews(request):
    reviews = Review.objects.select_related('book', 'user').annotate(comment_count=Count('comments')).order_by('-created_at')
    return render(request, 'books/social_reviews.html', {'reviews': reviews[:50]})


@login_required
def book_recommendations(request):
    recommended = Book.objects.filter(status=Book.PUBLISHED).exclude(on_shelves__user=request.user).order_by('-rating', '-created_at')[:24]
    return render(request, 'books/social_recommendations.html', {'recommended_books': recommended})


@login_required
@require_POST
def recommend_book(request, slug):
    book = get_object_or_404(Book, slug=slug, status=Book.PUBLISHED)
    recipient = get_object_or_404(get_user_model(), username=request.POST.get('username', '').strip())
    if recipient == request.user:
        return HttpResponseBadRequest('Choose another reader.')
    recommendation = BookRecommendation.objects.create(sender=request.user, recipient=recipient, book=book, message=request.POST.get('message', '').strip()[:280])
    _notify(recipient, request.user, Notification.RECOMMENDATION, message=f'{request.user.username} recommended {book.title}')
    messages.success(request, f'Recommendation sent to {recipient.username}.')
    return redirect('book_detail', slug=book.slug)


@login_required
def saved_content(request):
    return render(request, 'books/saved_content.html', {'posts': SavedPost.objects.filter(user=request.user).select_related('post__author', 'post__book')})


def writer_dashboard(request):
    context = {
        'drafts': [
            {'title': 'The Last Orchard', 'status': 'Draft'},
            {'title': 'Midnight Essays', 'status': 'Editing'},
        ],
        'published': [
            {'title': 'The Quiet Horizon', 'reads': 1240},
            {'title': 'Letters of a New Dawn', 'reads': 980},
        ],
    }
    return render(request, 'books/writer_dashboard.html', context)


@login_required
def review_create(request, slug):
    book = get_object_or_404(Book, slug=slug, status=Book.PUBLISHED)
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            Review.objects.create(book=book, user=request.user, content=content)
            return redirect('book_detail', slug=book.slug)
    return render(request, 'books/review_create.html', {'book': book})


@login_required
def publish_book(request):
    allowed_files = {
        'manuscript': {'epub', 'pdf', 'docx', 'mobi'},
        'cover': {'jpg', 'jpeg', 'png', 'webp'},
        'asset': {'zip', 'jpg', 'jpeg', 'png', 'webp', 'pdf'},
    }
    max_upload_size = 50 * 1024 * 1024
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        slug = request.POST.get('slug', '').strip()
        summary = request.POST.get('summary', '').strip()
        cover_color = request.POST.get('cover_color', 'linear-gradient(135deg, #dcae7b, #8a563f)')
        # Every community submission is reviewed in the custom admin before readers can see it.
        status = Book.DRAFT

        upload_items = []
        for kind, uploaded_file in [('manuscript', request.FILES.get('manuscript')), ('cover', request.FILES.get('cover'))]:
            if uploaded_file:
                upload_items.append((kind, uploaded_file))
        upload_items.extend(('asset', uploaded_file) for uploaded_file in request.FILES.getlist('assets'))

        errors = []
        if not title or not slug or not summary:
            errors.append('Please complete all required fields.')
        if not request.FILES.get('manuscript'):
            errors.append('Add a manuscript file before submitting.')
        for kind, uploaded_file in upload_items:
            extension = Path(uploaded_file.name).suffix.lower().lstrip('.')
            if extension not in allowed_files[kind]:
                errors.append(f'{uploaded_file.name}: unsupported {kind} format.')
            if uploaded_file.size > max_upload_size:
                errors.append(f'{uploaded_file.name}: files must be 50 MB or smaller.')
        if errors:
            return render(request, 'books/publish_book.html', {'errors': errors, 'max_upload_size': max_upload_size})

        author, _ = Author.objects.get_or_create(name=request.user.username)
        book = Book.objects.create(
            title=title,
            slug=slug,
            author=author,
            summary=summary,
            cover_color=cover_color,
            status=status,
            is_featured=False,
            rating=0.00,
        )
        for kind, uploaded_file in upload_items:
            BookUpload.objects.create(
                book=book,
                uploaded_by=request.user,
                file=uploaded_file,
                kind=kind,
                original_filename=Path(uploaded_file.name).name[:255],
                file_size=uploaded_file.size,
                content_type=uploaded_file.content_type or '',
            )
        BookApprovalStatus.objects.create(book=book)
        AdminNotificationManager.notify_pending_approval()
        messages.success(request, f'"{book.title}" was submitted for administrator review.')
        return redirect('writer_dashboard')

    return render(request, 'books/publish_book.html')


def login_view(request):
    if request.method == 'POST':
        form = EmailOrUsernameAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            AuthenticationEvent.objects.create(user=user, event_type=AuthenticationEvent.PASSWORD_LOGIN)
            next_url = request.POST.get('next', '')
            if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}, request.is_secure()):
                return redirect(next_url)
            if user.is_staff:
                return redirect('admin_panel:dashboard')
            return redirect('home')
    else:
        form = EmailOrUsernameAuthenticationForm(request)
    return render(request, 'books/login.html', {
        'form': form,
        'next': request.GET.get('next', ''),
        'social_providers': configured_social_providers(),
    })


@login_required
@require_http_methods(["GET", "POST"])
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been signed out.')
    return redirect('landing_page')


def signup_view(request):
    if request.method == 'POST':
        form = BookClubRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Welcome to AfriNovel!')
            return redirect('home')
    else:
        form = BookClubRegistrationForm()
    return render(request, 'books/signup.html', {'form': form, 'social_providers': configured_social_providers()})


def configured_social_providers():
    """Only render live OAuth actions when the server has provider credentials."""
    configured = settings.SOCIALACCOUNT_PROVIDERS
    return {
        'google': bool(configured.get('google', {}).get('APP', {}).get('client_id')),
        'apple': bool(configured.get('apple', {}).get('APP', {}).get('client_id')),
        'microsoft': bool(configured.get('microsoft', {}).get('APP', {}).get('client_id')),
    }


@login_required
def connected_accounts(request):
    from allauth.socialaccount.models import SocialAccount

    accounts = {account.provider: account for account in SocialAccount.objects.filter(user=request.user)}
    return render(request, 'books/connected_accounts.html', {
        'accounts': accounts,
        'social_providers': configured_social_providers(),
        'has_password': request.user.has_usable_password(),
    })


@login_required
@require_POST
def disconnect_social_account(request, provider):
    from allauth.socialaccount.models import SocialAccount

    if provider not in {'google', 'apple', 'microsoft'}:
        return HttpResponseBadRequest('Unknown provider.')
    account = get_object_or_404(SocialAccount, user=request.user, provider=provider)
    social_count = SocialAccount.objects.filter(user=request.user).count()
    if not request.user.has_usable_password() and social_count <= 1:
        messages.error(request, 'Add a password or connect another provider before disconnecting your only sign-in method.')
        return redirect('connected_accounts')
    account.delete()
    AuthenticationEvent.objects.create(user=request.user, event_type=AuthenticationEvent.ACCOUNT_UNLINKED, provider=provider)
    messages.success(request, f'{provider.title()} has been disconnected.')
    return redirect('connected_accounts')


@login_required
def profile_view(request):
    user = request.user
    profile = _profile_for(user)
    authored_books = Book.objects.filter(author__name=user.username)[:4]
    context = {
        'user': user,
        'profile': profile,
        'authored_books': authored_books,
        'reviews': Review.objects.filter(user=user)[:5],
        'books_read_count': user.bookshelf.filter(status=UserBookshelf.READ).count(),
        'followers_count': user.follower_users.count(),
        'profile_view_count': profile.profile_views,
    }
    return render(request, 'books/profile.html', context)


@login_required
def profile_edit(request):
    """Edit user profile including avatar upload"""
    profile = _profile_for(request.user)
    
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
        else:
            # Form is invalid, show errors
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProfileEditForm(instance=profile)
    
    context = {
        'form': form,
        'profile': profile,
    }
    return render(request, 'books/profile_edit.html', context)


def author_profile(request, author_name):
    author = get_object_or_404(Author, name__iexact=author_name.replace('-', ' '))
    books = author.books.filter(status=Book.PUBLISHED)[:6]
    context = {
        'author': author,
        'books': books,
        'reviews': Review.objects.filter(book__author=author)[:5],
        'followers_count': author.followers.count(),
    }
    return render(request, 'books/author_profile.html', context)


@login_required
def review_comments(request, slug, review_id):
    book = get_object_or_404(Book, slug=slug, status=Book.PUBLISHED)
    review = get_object_or_404(Review, id=review_id, book=book)
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            ReviewComment.objects.create(review=review, user=request.user, content=content)
            return redirect('review_comments', slug=book.slug, review_id=review.id)
    comments = review.comments.select_related('user')
    return render(request, 'books/review_comments.html', {'book': book, 'review': review, 'comments': comments})


@login_required
def follow_author(request, author_id):
    author = get_object_or_404(Author, id=author_id)
    AuthorFollow.objects.get_or_create(follower=request.user, author=author)
    return redirect('author_profile', author_name=author.name.replace(' ', '-'))


def genre_page(request, slug):
    genre = get_object_or_404(Genre, slug=slug)
    books = genre.books.filter(
        status=Book.PUBLISHED
    ).select_related('author').prefetch_related('genres').order_by('-created_at')
    
    # Pagination
    paginator = Paginator(books, 20)
    page = paginator.get_page(request.GET.get('page'))
    
    context = {
        'genre': genre,
        'books': page,
    }
    return render(request, 'books/genre_page.html', context)


def search_books(request):
    """Enhanced search with filters and pagination"""
    query = request.GET.get('q', '').strip()
    genre_filter = request.GET.get('genre', '')
    author_filter = request.GET.get('author', '')
    rating_filter = request.GET.get('rating', '')
    sort_by = request.GET.get('sort', 'relevance')
    
    # Base queryset
    books = Book.objects.filter(status=Book.PUBLISHED).select_related('author').prefetch_related('genres')
    
    # Apply search query
    if query:
        books = books.filter(
            Q(title__icontains=query) | 
            Q(summary__icontains=query) |
            Q(author__name__icontains=query)
        )
    
    # Apply filters
    if genre_filter:
        books = books.filter(genres__slug=genre_filter)
    
    if author_filter:
        books = books.filter(author__name__icontains=author_filter)
    
    if rating_filter:
        try:
            min_rating = float(rating_filter)
            books = books.filter(rating__gte=min_rating)
        except ValueError:
            pass
    
    # Apply sorting
    if sort_by == 'rating':
        books = books.order_by('-rating', '-created_at')
    elif sort_by == 'newest':
        books = books.order_by('-created_at')
    elif sort_by == 'oldest':
        books = books.order_by('created_at')
    else:  # relevance
        books = books.order_by('-rating', '-created_at')
    
    # Pagination
    paginator = Paginator(books, 20)
    page = paginator.get_page(request.GET.get('page'))
    
    # Get all genres for filter dropdown
    genres = Genre.objects.all()
    
    context = {
        'query': query,
        'books': page,
        'genres': genres,
        'genre_filter': genre_filter,
        'author_filter': author_filter,
        'rating_filter': rating_filter,
        'sort_by': sort_by,
    }
    return render(request, 'books/search_results.html', context)


def discover(request):
    """Discover and filter novels from the Book model."""
    query = request.GET.get('q', '').strip()
    
    # Get filter parameters
    genre_filter = request.GET.get('genre', '')
    status_filter = request.GET.get('status', '')
    sort_filter = request.GET.get('sort', 'trending')
    min_rating = request.GET.get('min_rating', '')
    
    # Start with base queryset
    books = Book.objects.filter(status=Book.PUBLISHED).select_related('author').prefetch_related('genres')
    
    # Apply search filter
    if query:
        books = books.filter(
            Q(title__icontains=query) |
            Q(author__name__icontains=query) |
            Q(summary__icontains=query)
        )
    
    # Apply genre filter
    if genre_filter:
        books = books.filter(genres__slug=genre_filter)
    
    # Apply status filter
    if status_filter:
        books = books.filter(novel_status=status_filter)
    
    # Apply rating filter
    if min_rating:
        try:
            books = books.filter(rating__gte=float(min_rating))
        except ValueError:
            pass
    
    # Apply sorting
    if sort_filter == 'popular':
        books = books.order_by('-view_count', '-rating')
    elif sort_filter == 'newest':
        books = books.order_by('-created_at')
    elif sort_filter == 'rating':
        books = books.order_by('-rating', '-view_count')
    elif sort_filter == 'chapters':
        books = books.annotate(chapter_count=Count('chapters')).order_by('-chapter_count')
    else:  # trending (default)
        books = books.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).order_by('-rating', '-view_count', '-created_at')
    
    # Get all genres for filter dropdown
    genres = Genre.objects.all().annotate(book_count=Count('books')).order_by('name')
    
    # Pagination
    paginator = Paginator(books, 24)
    page_number = request.GET.get('page', 1)
    try:
        page = paginator.page(page_number)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)
    
    # Create filters dict for template
    filters = {
        'genre': genre_filter,
        'status': status_filter,
        'sort': sort_filter,
        'min_rating': min_rating,
    }
    
    return render(request, 'books/discover.html', {
        'query': query,
        'books': page,
        'genres': genres,
        'filters': filters,
    })


def catalogue_detail(request, book_id):
    book = get_object_or_404(CatalogBook, pk=book_id, disabled=False)
    CatalogBook.objects.filter(pk=book.pk).update(view_count=F('view_count') + 1)
    book.view_count += 1
    provider_error = ''
    if not book.description and book.source == OpenLibraryProvider.name:
        try:
            details = OpenLibraryProvider().get_book(book.external_id)
            if details:
                book.description = details.description
                if details.subjects:
                    book.subjects = details.subjects
                book.save(update_fields=['description', 'subjects', 'updated_at'])
        except ProviderUnavailable:
            provider_error = 'Some catalogue information is temporarily unavailable. The source link remains available.'
    library_entry = None
    progress = None
    if request.user.is_authenticated:
        library_entry = CatalogLibraryEntry.objects.filter(user=request.user, book=book).first()
        progress = ReadingProgress.objects.filter(user=request.user, book=book).first()
    return render(request, 'books/catalogue_detail.html', {
        'book': book, 'sources': book.sources.order_by('-is_primary', 'provider'),
        'library_entry': library_entry, 'progress': progress, 'provider_error': provider_error,
    })


@login_required
@require_POST
def catalogue_library_action(request, book_id):
    book = get_object_or_404(CatalogBook, pk=book_id, disabled=False)
    action = request.POST.get('action', 'save')
    if action == 'remove':
        CatalogLibraryEntry.objects.filter(user=request.user, book=book).delete()
        messages.success(request, f'Removed "{book.title}" from your library.')
    else:
        state = request.POST.get('state', CatalogLibraryEntry.SAVED)
        if state not in dict(CatalogLibraryEntry.STATES):
            return HttpResponseBadRequest('Invalid library state.')
        entry, _ = CatalogLibraryEntry.objects.update_or_create(user=request.user, book=book, defaults={'state': state})
        if state == CatalogLibraryEntry.FINISHED:
            entry.finished_at = timezone.now()
            entry.save(update_fields=['finished_at'])
        messages.success(request, f'Added "{book.title}" to your library.')
    return redirect('catalogue_detail', book_id=book.pk)


def catalogue_reader(request, book_id):
    book = get_object_or_404(CatalogBook, pk=book_id, disabled=False)
    if not book.can_read_in_app:
        return redirect('catalogue_detail', book_id=book.pk)
    CatalogBook.objects.filter(pk=book.pk).update(view_count=F('view_count') + 1)
    entry = None
    progress = None
    if request.user.is_authenticated:
        entry, _ = CatalogLibraryEntry.objects.get_or_create(user=request.user, book=book, defaults={'state': CatalogLibraryEntry.CURRENTLY_READING})
        if entry.state == CatalogLibraryEntry.SAVED:
            entry.state = CatalogLibraryEntry.CURRENTLY_READING
            entry.save(update_fields=['state'])
        progress, _ = ReadingProgress.objects.get_or_create(user=request.user, book=book)
    reader_error = ''
    sections = []
    try:
        sections = split_reader_sections(fetch_reader_text(book))
    except (PermissionError, ProviderUnavailable) as error:
        reader_error = str(error)
    return render(request, 'books/reader.html', {
        'book': book, 'sections': sections, 'progress': progress,
        'bookmarks': Bookmark.objects.filter(user=request.user, book=book) if request.user.is_authenticated else [], 'reader_error': reader_error,
    })


@login_required
def catalogue_library(request):
    entries = CatalogLibraryEntry.objects.filter(user=request.user).select_related('book')
    return render(request, 'books/catalogue_library.html', {
        'currently_reading': entries.filter(state=CatalogLibraryEntry.CURRENTLY_READING),
        'saved_books': entries.filter(state=CatalogLibraryEntry.SAVED),
        'finished_books': entries.filter(state=CatalogLibraryEntry.FINISHED),
    })


def _json_payload(request):
    try:
        return json.loads(request.body or '{}') if request.content_type == 'application/json' else request.POST
    except json.JSONDecodeError:
        raise ValueError('Invalid JSON body.')


def _book_json(book):
    return {
        'id': book.pk, 'title': book.title, 'authors': book.authors, 'source': book.source,
        'source_url': book.source_url, 'cover_url': book.cover_image_url, 'access_type': book.access_type,
        'copyright_status': book.copyright_status, 'full_text_available': book.full_text_available,
        'read_url': reverse('catalogue_reader', args=[book.pk]) if book.can_read_in_app else '',
    }


@require_http_methods(['GET'])
def api_book_search(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': [], 'total': 0})
    try:
        page = max(int(request.GET.get('page', 1) or 1), 1)
    except ValueError:
        page = 1
    normalized, total, errors = CatalogService.search(query, request.GET, page)
    books = [CatalogService.persist(result) for result in normalized]
    return JsonResponse({'results': [_book_json(book) for book in books], 'total': total, 'provider_errors': errors})


@require_http_methods(['GET'])
def api_book_availability(request, book_id):
    book = get_object_or_404(CatalogBook, pk=book_id, disabled=False)
    return JsonResponse({
        'access_type': book.access_type, 'copyright_status': book.copyright_status,
        'can_read_in_app': book.can_read_in_app, 'borrowable': book.borrowable,
        'source_url': book.source_url, 'reading_url': book.reading_url,
    })


def _authorized_sections(book):
    if not book.can_read_in_app:
        return None, JsonResponse({'error': 'This book is not authorized for in-app reading.'}, status=403)
    try:
        return split_reader_sections(fetch_reader_text(book)), None
    except ProviderUnavailable:
        return None, JsonResponse({'error': 'Reading source temporarily unavailable.'}, status=503)


@login_required
@require_http_methods(['GET'])
def api_reader_chapters(request, book_id):
    book = get_object_or_404(CatalogBook, pk=book_id, disabled=False)
    sections, error_response = _authorized_sections(book)
    if error_response:
        return error_response
    return JsonResponse({'chapters': [{'index': index, 'title': section['title']} for index, section in enumerate(sections)]})


@login_required
@require_http_methods(['GET'])
def api_reader_section(request, book_id):
    book = get_object_or_404(CatalogBook, pk=book_id, disabled=False)
    sections, error_response = _authorized_sections(book)
    if error_response:
        return error_response
    try:
        index = int(request.GET.get('chapter', 0))
        section = sections[index]
    except (ValueError, IndexError):
        return JsonResponse({'error': 'Chapter not found.'}, status=404)
    return JsonResponse({'index': index, 'title': section['title'], 'paragraphs': section['paragraphs']})


@login_required
@require_http_methods(['GET'])
def api_search_in_book(request, book_id):
    book = get_object_or_404(CatalogBook, pk=book_id, disabled=False)
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})
    sections, error_response = _authorized_sections(book)
    if error_response:
        return error_response
    needle = query.casefold()
    matches = []
    for chapter_index, section in enumerate(sections):
        for paragraph_index, paragraph in enumerate(section['paragraphs']):
            if needle in paragraph.casefold():
                start = max(0, paragraph.casefold().find(needle) - 80)
                excerpt = paragraph[start:start + 250]
                matches.append({'chapter': chapter_index, 'title': section['title'], 'paragraph': paragraph_index, 'excerpt': excerpt})
                if len(matches) == 30:
                    return JsonResponse({'results': matches})
    return JsonResponse({'results': matches})


@login_required
@require_http_methods(['POST'])
def api_reading_progress(request, book_id):
    book = get_object_or_404(CatalogBook, pk=book_id, disabled=False)
    try:
        data = _json_payload(request)
        percent = max(0, min(float(data.get('percent', 0)), 100))
        paragraph = max(0, int(data.get('paragraph', 0)))
        character_offset = max(0, int(data.get('character_offset', 0)))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid reading position.'}, status=400)
    progress, _ = ReadingProgress.objects.update_or_create(
        user=request.user, book=book,
        defaults={'chapter': str(data.get('chapter', ''))[:250], 'paragraph': paragraph, 'character_offset': character_offset, 'percent': percent},
    )
    CatalogLibraryEntry.objects.update_or_create(user=request.user, book=book, defaults={'state': CatalogLibraryEntry.CURRENTLY_READING})
    return JsonResponse({'percent': float(progress.percent), 'last_read_at': progress.last_read_at.isoformat()})


@login_required
@require_http_methods(['GET', 'POST', 'DELETE'])
def api_bookmarks(request, book_id):
    book = get_object_or_404(CatalogBook, pk=book_id, disabled=False)
    if request.method == 'GET':
        return JsonResponse({'bookmarks': list(Bookmark.objects.filter(user=request.user, book=book).values('id', 'chapter', 'paragraph', 'excerpt', 'created_at'))})
    try:
        data = _json_payload(request)
    except ValueError as error:
        return JsonResponse({'error': str(error)}, status=400)
    if request.method == 'DELETE':
        Bookmark.objects.filter(user=request.user, book=book, pk=data.get('id')).delete()
        return JsonResponse({}, status=204)
    bookmark = Bookmark.objects.create(user=request.user, book=book, chapter=str(data.get('chapter', ''))[:250], paragraph=max(0, int(data.get('paragraph', 0))), excerpt=str(data.get('excerpt', ''))[:500])
    return JsonResponse({'id': bookmark.pk}, status=201)


@login_required
@require_POST
def api_highlight(request, book_id):
    book = get_object_or_404(CatalogBook, pk=book_id, disabled=False)
    if not book.can_read_in_app:
        return JsonResponse({'error': 'Highlights are available only for authorized in-app text.'}, status=403)
    try:
        data = _json_payload(request)
        text = str(data.get('selected_text', '')).strip()
        color = data.get('color', Highlight.YELLOW)
        if not text or color not in dict(Highlight.COLORS):
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Select text and a valid highlight color.'}, status=400)
    highlight = Highlight.objects.create(user=request.user, book=book, chapter=str(data.get('chapter', ''))[:250], paragraph=max(0, int(data.get('paragraph', 0))), selected_text=text, color=color)
    return JsonResponse({'id': highlight.pk}, status=201)


@login_required
@require_POST
def api_reading_note(request, book_id):
    book = get_object_or_404(CatalogBook, pk=book_id, disabled=False)
    try:
        data = _json_payload(request)
        content = str(data.get('content', '')).strip()
        if not content:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'error': 'A note cannot be empty.'}, status=400)
    note = ReadingNote.objects.create(user=request.user, book=book, chapter=str(data.get('chapter', ''))[:250], paragraph=max(0, int(data.get('paragraph', 0))), content=content)
    return JsonResponse({'id': note.pk}, status=201)


@login_required
@require_http_methods(['GET'])
def api_personal_library(request):
    entries = CatalogLibraryEntry.objects.filter(user=request.user).select_related('book')
    return JsonResponse({'entries': [{**_book_json(entry.book), 'state': entry.state} for entry in entries]})


@login_required
@require_http_methods(['GET'])
def api_continue_reading(request):
    progresses = ReadingProgress.objects.filter(user=request.user).select_related('book').order_by('-last_read_at')[:12]
    return JsonResponse({'entries': [{**_book_json(item.book), 'percent': float(item.percent), 'chapter': item.chapter, 'last_read_at': item.last_read_at.isoformat()} for item in progresses]})


@login_required
def add_to_bookshelf(request, slug):
    book = get_object_or_404(Book, slug=slug, status=Book.PUBLISHED)
    status = request.POST.get('status', UserBookshelf.WANT_TO_READ)
    bookshelf_item, created = UserBookshelf.objects.get_or_create(
        user=request.user,
        book=book,
        defaults={'status': status}
    )
    if not created:
        bookshelf_item.status = status
        bookshelf_item.save()
    messages.success(request, f'Added "{book.title}" to your bookshelf!')
    return redirect('book_detail', slug=book.slug)


@login_required
def update_bookshelf(request, shelf_id):
    shelf_item = get_object_or_404(UserBookshelf, id=shelf_id, user=request.user)
    if request.method == 'POST':
        status = request.POST.get('status', shelf_item.status)
        progress = request.POST.get('progress_percent', shelf_item.progress_percent)
        rating = request.POST.get('rating', shelf_item.rating)
        notes = request.POST.get('notes', shelf_item.notes)
        
        shelf_item.status = status
        shelf_item.progress_percent = int(progress) if progress else 0
        shelf_item.rating = int(rating) if rating else None
        shelf_item.notes = notes
        
        if status == UserBookshelf.READ and not shelf_item.completed_at:
            from django.utils import timezone
            shelf_item.completed_at = timezone.now()
        
        shelf_item.save()
        messages.success(request, 'Bookshelf updated!')
        return redirect('view_bookshelf')
    
    context = {'shelf_item': shelf_item}
    return render(request, 'books/edit_bookshelf.html', context)


@login_required
def remove_from_bookshelf(request, shelf_id):
    shelf_item = get_object_or_404(UserBookshelf, id=shelf_id, user=request.user)
    book_title = shelf_item.book.title
    shelf_item.delete()
    messages.success(request, f'Removed "{book_title}" from your bookshelf.')
    return redirect('view_bookshelf')


@login_required
def view_bookshelf(request):
    status_filter = request.GET.get('status', '')
    bookshelf = request.user.bookshelf.select_related('book').order_by('-added_at')
    
    if status_filter:
        bookshelf = bookshelf.filter(status=status_filter)
    
    reading_stats = {
        'total': request.user.bookshelf.count(),
        'currently_reading': request.user.bookshelf.filter(status=UserBookshelf.CURRENTLY_READING).count(),
        'want_to_read': request.user.bookshelf.filter(status=UserBookshelf.WANT_TO_READ).count(),
        'read': request.user.bookshelf.filter(status=UserBookshelf.READ).count(),
    }
    
    context = {
        'bookshelf': bookshelf,
        'reading_stats': reading_stats,
        'status_filter': status_filter,
        'status_choices': UserBookshelf.STATUS_CHOICES,
    }
    return render(request, 'books/view_bookshelf.html', context)


@login_required
def recommendations(request):
    """Personalized recommendations based on reading history and genres"""
    # Get books the user has read or is reading
    user_books = request.user.bookshelf.filter(
        status__in=[UserBookshelf.READ, UserBookshelf.CURRENTLY_READING]
    ).select_related('book')
    
    # Get genres from user's books
    user_genres = set()
    for shelf_item in user_books:
        user_genres.update(shelf_item.book.genres.values_list('id', flat=True))
    
    # Get books in similar genres that user hasn't added to bookshelf
    if user_genres:
        recommended = Book.objects.filter(
            status=Book.PUBLISHED,
            genres__id__in=user_genres
        ).exclude(
            on_shelves__user=request.user
        ).distinct().order_by('-rating', '-created_at')[:12]
    else:
        # If no reading history, recommend featured books
        recommended = Book.objects.filter(
            is_featured=True,
            status=Book.PUBLISHED
        ).exclude(
            on_shelves__user=request.user
        )[:12]
    
    context = {
        'recommended_books': recommended,
        'has_reading_history': bool(user_books),
    }
    return render(request, 'books/recommendations.html', context)


@login_required
def create_reading_list(request):
    """Create a new reading list"""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        is_public = request.POST.get('is_public') == 'on'
        
        if not title:
            return render(request, 'books/create_reading_list.html', {'error': 'List title is required.'})
        
        reading_list = ReadingList.objects.create(
            user=request.user,
            title=title,
            description=description,
            is_public=is_public,
        )
        return redirect('reading_list_detail', username=request.user.username, slug=reading_list.slug)
    
    return render(request, 'books/create_reading_list.html')


@login_required
def reading_list_detail(request, username, slug):
    """View a reading list"""
    from django.db.models import Q
    
    # Get the reading list
    reading_list = get_object_or_404(
        ReadingList.objects.select_related('user').prefetch_related('books'),
        user__username=username,
        slug=slug
    )
    
    # Check permissions - allow viewing own lists or public lists
    is_owner = request.user == reading_list.user
    if not is_owner and not reading_list.is_public:
        return redirect('home')
    
    books = reading_list.books.all()
    
    context = {
        'reading_list': reading_list,
        'books': books,
        'is_owner': is_owner,
        'book_count': books.count(),
    }
    return render(request, 'books/reading_list_detail.html', context)


@login_required
def edit_reading_list(request, slug):
    """Edit a reading list"""
    reading_list = get_object_or_404(ReadingList, user=request.user, slug=slug)
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        is_public = request.POST.get('is_public') == 'on'
        
        if not title:
            return render(request, 'books/edit_reading_list.html', 
                         {'reading_list': reading_list, 'error': 'List title is required.'})
        
        reading_list.title = title
        reading_list.description = description
        reading_list.is_public = is_public
        reading_list.save()
        
        return redirect('reading_list_detail', username=request.user.username, slug=reading_list.slug)
    
    context = {'reading_list': reading_list}
    return render(request, 'books/edit_reading_list.html', context)


@login_required
def delete_reading_list(request, slug):
    """Delete a reading list"""
    reading_list = get_object_or_404(ReadingList, user=request.user, slug=slug)
    
    if request.method == 'POST':
        reading_list.delete()
        return redirect('my_reading_lists')
    
    context = {'reading_list': reading_list}
    return render(request, 'books/delete_reading_list.html', context)


@login_required
def my_reading_lists(request):
    """View all reading lists for the logged-in user"""
    reading_lists = request.user.reading_lists.all()
    
    context = {
        'reading_lists': reading_lists,
        'list_count': reading_lists.count(),
    }
    return render(request, 'books/my_reading_lists.html', context)


@login_required
def add_to_reading_list(request, slug, book_id):
    """Add a book to a reading list"""
    reading_list = get_object_or_404(ReadingList, user=request.user, slug=slug)
    book = get_object_or_404(Book, id=book_id)
    
    reading_list.books.add(book)
    messages.success(request, f'Added "{book.title}" to "{reading_list.title}"')
    
    return redirect('reading_list_detail', username=request.user.username, slug=reading_list.slug)


@login_required
def remove_from_reading_list(request, slug, book_id):
    """Remove a book from a reading list"""
    reading_list = get_object_or_404(ReadingList, user=request.user, slug=slug)
    book = get_object_or_404(Book, id=book_id)
    
    reading_list.books.remove(book)
    messages.success(request, f'Removed "{book.title}" from "{reading_list.title}"')
    
    return redirect('reading_list_detail', username=request.user.username, slug=reading_list.slug)


def rankings(request):
    """Rankings page with various ranking filters"""
    time_filter = request.GET.get('time', 'all')
    category_filter = request.GET.get('category', '')
    ranking_type = request.GET.get('type', 'rating')  # rating, reads, reviews, trending
    
    # Base queryset with annotations for ranking calculations
    books = Book.objects.filter(status=Book.PUBLISHED).select_related('author', 'catalog_book').prefetch_related('genres')
    
    # Annotate with review count for rankings
    books = books.annotate(
        review_count=Count('reviews', distinct=True),
        bookshelf_count=Count('on_shelves', distinct=True)
    )
    
    # Apply time filter
    if time_filter == 'week':
        books = books.filter(created_at__gte=timezone.now() - timedelta(days=7))
    elif time_filter == 'month':
        books = books.filter(created_at__gte=timezone.now() - timedelta(days=30))
    
    # Apply category filter
    if category_filter:
        books = books.filter(genres__slug=category_filter)
    
    # Apply ranking type ordering
    if ranking_type == 'rating':
        books = books.order_by('-rating', '-created_at')
    elif ranking_type == 'reads':
        books = books.order_by('-bookshelf_count', '-rating')
    elif ranking_type == 'reviews':
        books = books.order_by('-review_count', '-rating')
    elif ranking_type == 'trending':
        # Trending reflects real recent views, saves, and reviews.
        books = books.filter(
            Q(created_at__gte=timezone.now() - timedelta(days=30)) | Q(view_count__gt=0)
        ).order_by('-view_count', '-bookshelf_count', '-review_count', '-created_at')
    else:
        books = books.order_by('-rating', '-created_at')
    
    # Pagination
    paginator = Paginator(books, 20)
    page = paginator.get_page(request.GET.get('page'))
    
    # Get all genres for filter
    genres = Genre.objects.all()
    
    # Calculate rank numbers for display
    start_rank = (page.number - 1) * 20 + 1
    
    context = {
        'books': page,
        'genres': genres,
        'time_filter': time_filter,
        'category_filter': category_filter,
        'ranking_type': ranking_type,
        'start_rank': start_rank,
    }
    return render(request, 'books/rankings.html', context)


def categories(request):
    """Categories listing page"""
    genres = Genre.objects.all().annotate(
        book_count=Count('books')
    ).order_by('name')
    
    context = {
        'genres': genres,
    }
    return render(request, 'books/categories.html', context)


def category_detail(request, slug):
    """Category detail page with books"""
    genre = get_object_or_404(Genre, slug=slug)
    
    # Get books in this genre
    books = Book.objects.filter(
        genres=genre,
        status=Book.PUBLISHED
    ).select_related('author').prefetch_related('genres')
    
    # Apply sorting
    sort = request.GET.get('sort', 'popular')
    if sort == 'new':
        books = books.order_by('-created_at')
    elif sort == 'trending':
        # For now, use rating as a proxy for trending
        books = books.order_by('-rating', '-created_at')
    else:  # popular
        books = books.order_by('-rating', '-created_at')
    
    # Pagination
    paginator = Paginator(books, 20)
    page = paginator.get_page(request.GET.get('page'))
    
    context = {
        'genre': genre,
        'books': page,
        'sort': sort,
    }
    return render(request, 'books/category_detail.html', context)


def completed(request):
    """Completed books page showing only the current user's completed books."""
    # Initialize filter variables
    genre_filter = request.GET.get('genre', '')
    author_filter = request.GET.get('author', '')
    rating_filter = request.GET.get('rating', '')
    sort = request.GET.get('sort', 'recent')
    
    if request.user.is_authenticated:
        # Show authenticated user's completed books from their bookshelf
        bookshelf_entries = UserBookshelf.objects.filter(
            user=request.user,
            status=UserBookshelf.READ
        ).select_related('book__author').prefetch_related('book__genres')
        
        # Filter by genre if specified
        if genre_filter:
            bookshelf_entries = bookshelf_entries.filter(book__genres__slug=genre_filter)
        
        # Filter by author if specified
        if author_filter:
            bookshelf_entries = bookshelf_entries.filter(book__author__name__icontains=author_filter)
        
        # Filter by rating if specified
        if rating_filter:
            bookshelf_entries = bookshelf_entries.filter(rating=rating_filter)
        
        # Sort options
        if sort == 'rating':
            bookshelf_entries = bookshelf_entries.order_by('-rating', '-completed_at')
        elif sort == 'title':
            bookshelf_entries = bookshelf_entries.order_by('book__title')
        else:  # recent
            bookshelf_entries = bookshelf_entries.order_by('-completed_at')
        
        # Pagination
        paginator = Paginator(bookshelf_entries, 20)
        page = paginator.get_page(request.GET.get('page'))
        
        is_authenticated = True
    else:
        # Completion is personal data; never label a book completed without a user record.
        page = Paginator(Book.objects.none(), 20).get_page(request.GET.get('page'))
        
        is_authenticated = False
    
    # Get all genres for filter
    genres = Genre.objects.all()
    
    # Get all authors for filter
    authors = Author.objects.all()
    
    context = {
        'books': page,
        'genres': genres,
        'authors': authors,
        'genre_filter': genre_filter,
        'author_filter': author_filter,
        'rating_filter': rating_filter,
        'sort': sort,
        'is_authenticated': is_authenticated,
    }
    return render(request, 'books/completed.html', context)


@login_required
def reading_history(request):
    """Reading history page for authenticated users"""
    # Get user's reading progress from catalog
    history = ReadingProgress.objects.filter(
        user=request.user
    ).select_related('book').order_by('-last_read_at')
    
    # Pagination
    paginator = Paginator(history, 20)
    page = paginator.get_page(request.GET.get('page'))
    
    context = {
        'history': page,
    }
    return render(request, 'books/reading_history.html', context)
