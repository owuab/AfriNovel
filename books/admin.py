from django.contrib import admin
from django.contrib.admin.actions import delete_selected
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count, Q
from django.urls import path, reverse
from django.template.response import TemplateResponse
from django.utils.safestring import mark_safe
from allauth.socialaccount.models import SocialAccount
from .models import (
    Genre, Author, Book, Chapter, Review, ReviewComment, AuthorFollow, UserBookshelf, ReadingList,
    Bookmark, BookSource, CatalogBook, CatalogLibraryEntry, Highlight, ProviderStatus,
    ReadingNote, ReadingProgress, SearchHistory, AuthenticationEvent,
    ImportedBook, BookFile, ImportJob, ReadingBookmark, ReadingHighlight, BookUpload,
    Promotion, Competition, CompetitionEntry, Award, AwardCategory, AwardNominee,
    CriticProfile, CriticApplication, ReviewAssignment, CriticReview, CriticEarning,
    Notification,
    SubscriptionPlan, PremiumSubscription, MonetizationPayment, WriterProfile,
    MonetizationConfig, ReaderSession, WriterEarning, WriterWithdrawal,
    WithdrawalAllocation, Advertisement, AdImpression, AdClick,
)
from .admin_dashboard import get_dashboard_stats
from .monetization import finalize_withdrawal, notify_user, submit_withdrawal

User = get_user_model()


class BookClubAdminSite(admin.AdminSite):
    """Custom admin site with modern styling and dashboard"""
    
    site_header = "AfriNovel Admin Dashboard"
    site_title = "AfriNovel Admin"
    index_title = "Welcome to AfriNovel Administration"

    def login(self, request, extra_context=None):
        """Add database-backed operational metrics to the admin sign-in page."""
        from django.db.models import Avg

        context = extra_context or {}
        
        try:
            published_books = Book.objects.filter(status=Book.PUBLISHED)
            active_readers = User.objects.filter(
                Q(catalogue_progress__isnull=False) | Q(bookshelf__isnull=False)
            ).distinct().count()
            average_rating = published_books.filter(
                catalog_book__isnull=True,
                rating__gt=0,
            ).aggregate(avg=Avg('rating'))['avg'] or 0
            context['login_metrics'] = {
                'published_books': published_books.count(),
                'active_readers': active_readers,
                'average_rating': round(float(average_rating), 1),
                'catalogue_books': CatalogBook.objects.filter(disabled=False).count(),
            }
        except Exception:
            # If database queries fail, provide default metrics
            context['login_metrics'] = {
                'published_books': 0,
                'active_readers': 0,
                'average_rating': 0.0,
                'catalogue_books': 0,
            }
        
        return super().login(request, extra_context=context)
    
    def get_urls(self):
        """Add custom dashboard URL"""
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_site_dashboard, name='admin_dashboard'),
        ]
        return custom_urls + urls
    
    def admin_site_dashboard(self, request):
        """Render custom dashboard"""
        if not request.user.is_staff:
            return self.login_view(request)
        
        stats = get_dashboard_stats()
        context = {
            'title': 'Admin Dashboard',
            'stats': stats,
            'site_header': self.site_header,
            'site_title': self.site_title,
        }
        return TemplateResponse(request, 'admin/dashboard.html', context)
    
    def index(self, request, extra_context=None):
        """Override default admin index to show dashboard"""
        if extra_context is None:
            extra_context = {}
        
        try:
            # Add dashboard stats to context
            extra_context['dashboard_stats'] = get_dashboard_stats()
        except Exception:
            # If dashboard stats fail, provide empty stats
            extra_context['dashboard_stats'] = {}
        
        return super().index(request, extra_context)


class WriterProfileAdmin(admin.ModelAdmin):
    list_display = ('pen_name', 'user', 'status', 'payout_account_last4', 'created_at', 'reviewed_at')
    list_filter = ('status', 'created_at')
    search_fields = ('pen_name', 'user__username', 'user__email')
    readonly_fields = ('payout_recipient_code', 'payout_account_last4', 'created_at', 'updated_at', 'reviewed_at')
    actions = ('approve_writers', 'reject_writers', 'suspend_writers')

    @admin.action(description='Approve selected writer applications')
    def approve_writers(self, request, queryset):
        for profile in queryset:
            profile.status = WriterProfile.APPROVED
            profile.reviewed_by = request.user
            profile.reviewed_at = timezone.now()
            profile.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'updated_at'])
            notify_user(profile.user, Notification.WRITER_APPROVED, 'Your writer programme application was approved.', request.user)
        self.message_user(request, 'Selected writer applications approved.')

    @admin.action(description='Reject selected writer applications')
    def reject_writers(self, request, queryset):
        for profile in queryset:
            profile.status = WriterProfile.REJECTED
            profile.reviewed_by = request.user
            profile.reviewed_at = timezone.now()
            profile.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'updated_at'])
            notify_user(profile.user, Notification.WRITER_REJECTED, 'Your writer programme application was not approved.', request.user)
        self.message_user(request, 'Selected writer applications rejected.')

    @admin.action(description='Suspend selected writer profiles')
    def suspend_writers(self, request, queryset):
        queryset.update(status=WriterProfile.SUSPENDED, reviewed_by=request.user, reviewed_at=timezone.now())
        self.message_user(request, 'Selected writer profiles suspended.')


class WriterWithdrawalAdmin(admin.ModelAdmin):
    list_display = ('reference', 'writer', 'amount', 'currency', 'status', 'requested_at', 'processed_at')
    list_filter = ('status', 'currency', 'requested_at')
    search_fields = ('reference', 'writer__pen_name', 'writer__user__username', 'provider_reference')
    readonly_fields = ('writer', 'amount', 'currency', 'status', 'reference', 'provider_reference', 'requested_at', 'processed_at')
    actions = ('initiate_paystack_transfers', 'mark_settled', 'reject_requests')

    @admin.action(description='Initiate Paystack transfers')
    def initiate_paystack_transfers(self, request, queryset):
        processed = 0
        for withdrawal in queryset:
            try:
                submit_withdrawal(withdrawal.pk, request.user)
            except Exception as error:
                self.message_user(request, f'{withdrawal.reference}: {error}', level='ERROR')
            else:
                processed += 1
        if processed:
            self.message_user(request, f'{processed} transfer(s) submitted to Paystack.')

    @admin.action(description='Mark as paid after confirmed external settlement')
    def mark_settled(self, request, queryset):
        for withdrawal in queryset:
            finalize_withdrawal(str(withdrawal.reference), True)
        self.message_user(request, 'Selected withdrawals marked paid and earnings reconciled.')

    @admin.action(description='Reject selected withdrawal requests')
    def reject_requests(self, request, queryset):
        for withdrawal in queryset.filter(status__in=[WriterWithdrawal.PENDING, WriterWithdrawal.PROCESSING]):
            withdrawal.status = WriterWithdrawal.REJECTED
            withdrawal.failure_reason = 'Rejected by platform administrator.'
            withdrawal.processed_by = request.user
            withdrawal.processed_at = timezone.now()
            withdrawal.save(update_fields=['status', 'failure_reason', 'processed_by', 'processed_at'])
            notify_user(withdrawal.writer.user, Notification.WITHDRAWAL_REJECTED, 'Your withdrawal request was rejected.', request.user)
        self.message_user(request, 'Selected withdrawal requests rejected.')


class MonetizationConfigAdmin(admin.ModelAdmin):
    list_display = ('earning_formula', 'earning_per_read', 'engagement_bonus', 'minimum_read_seconds', 'minimum_withdrawal', 'ad_frequency_cap', 'updated_at')
    readonly_fields = ('updated_at',)

    def has_add_permission(self, request):
        return not MonetizationConfig.objects.exists()


class MonetizationPaymentAdmin(admin.ModelAdmin):
    list_display = ('reference', 'user', 'plan', 'amount', 'currency', 'status', 'provider', 'verified_at', 'created_at')
    list_filter = ('status', 'provider', 'currency', 'created_at')
    search_fields = ('reference', 'provider_reference', 'user__username', 'user__email')
    readonly_fields = ('user', 'plan', 'subscription', 'purpose', 'provider', 'reference', 'amount', 'currency', 'status', 'checkout_url', 'provider_reference', 'metadata', 'verified_at', 'created_at')
    actions = None


class PremiumSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'starts_at', 'ends_at', 'cancel_at_period_end')
    list_filter = ('status', 'plan__billing_period', 'cancel_at_period_end')
    search_fields = ('user__username', 'user__email', 'provider_subscription_code')
    readonly_fields = tuple(field.name for field in PremiumSubscription._meta.fields)
    actions = None


class ReaderSessionAdmin(admin.ModelAdmin):
    list_display = ('book', 'chapter', 'reader', 'read_date', 'started_at', 'qualified_at')
    list_filter = ('read_date', 'qualified_at')
    readonly_fields = tuple(field.name for field in ReaderSession._meta.fields)
    actions = None


class WithdrawalAllocationAdmin(admin.ModelAdmin):
    list_display = ('withdrawal', 'earning', 'amount', 'created_at')
    readonly_fields = tuple(field.name for field in WithdrawalAllocation._meta.fields)
    actions = None


class WriterEarningAdmin(admin.ModelAdmin):
    list_display = ('reference', 'writer', 'book', 'chapter', 'activity_type', 'amount', 'currency', 'status', 'created_at')
    list_filter = ('status', 'activity_type', 'currency', 'created_at')
    search_fields = ('reference', 'writer__pen_name', 'book__title')
    readonly_fields = tuple(field.name for field in WriterEarning._meta.fields)
    actions = None


class AdImpressionAdmin(admin.ModelAdmin):
    list_display = ('ad', 'user', 'path', 'created_at')
    list_filter = ('created_at',)
    readonly_fields = tuple(field.name for field in AdImpression._meta.fields)
    actions = None


class AdClickAdmin(admin.ModelAdmin):
    list_display = ('ad', 'user', 'created_at')
    list_filter = ('created_at',)
    readonly_fields = tuple(field.name for field in AdClick._meta.fields)
    actions = None


# Create custom admin site instance
admin_site = BookClubAdminSite(name='bookclub_admin')


# ==================== GENRE ADMIN ====================
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name', 'book_count', 'slug')
    list_filter = ('created_at',) if hasattr(Genre, 'created_at') else ()
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    
    def book_count(self, obj):
        count = obj.books.count()
        return format_html(
            '<span style="background-color: #e3f2fd; padding: 3px 8px; border-radius: 3px;">{} books</span>',
            count
        )
    book_count.short_description = 'Books'


# ==================== AUTHOR ADMIN ====================
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('name', 'book_count', 'follower_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'bio')
    readonly_fields = ('created_at', 'follower_count_display', 'books_display')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'bio')
        }),
        ('Statistics', {
            'fields': ('created_at', 'follower_count_display', 'books_display'),
            'classes': ('collapse',)
        }),
    )
    
    def book_count(self, obj):
        count = obj.books.count()
        return format_html(
            '<span style="background-color: #f3e5f5; padding: 3px 8px; border-radius: 3px;">{} books</span>',
            count
        )
    book_count.short_description = 'Books'
    
    def follower_count(self, obj):
        count = obj.followers.count()
        return format_html(
            '<span style="background-color: #fce4ec; padding: 3px 8px; border-radius: 3px;">{} followers</span>',
            count
        )
    follower_count.short_description = 'Followers'
    
    def follower_count_display(self, obj):
        return obj.followers.count()
    follower_count_display.short_description = 'Total Followers'
    
    def books_display(self, obj):
        books = obj.books.all()
        if not books:
            return "No books published"
        book_items = format_html_join('', '<li>{}</li>', ((book.title,) for book in books))
        return format_html(
            '<ul style="margin: 0; padding-left: 20px;">{}</ul>',
            book_items
        )
    books_display.short_description = 'Published Books'


# ==================== BOOK ADMIN ====================
class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 0
    fields = ('chapter_number', 'title', 'status', 'word_count', 'view_count', 'published_date')
    readonly_fields = ('word_count', 'view_count')


class ChapterAdmin(admin.ModelAdmin):
    list_display = ('book', 'chapter_number', 'title', 'status', 'word_count', 'view_count', 'updated_at')
    list_filter = ('status', 'updated_at')
    search_fields = ('book__title', 'book__author__name', 'title', 'content')
    readonly_fields = ('word_count', 'view_count', 'created_at', 'updated_at')


class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'owner', 'status_badge', 'rating_display', 'featured_badge', 'review_count')
    list_filter = ('status', 'is_featured', 'created_at', 'genres')
    search_fields = ('title', 'author__name', 'owner__username', 'summary')
    filter_horizontal = ('genres',)
    prepopulated_fields = {'slug': ('title',)}
    inlines = (ChapterInline,)
    readonly_fields = ('created_at', 'updated_at', 'cover_preview', 'review_count_display')
    actions = ('approve_selected_books', 'return_selected_books_to_draft', 'archive_selected_books', delete_selected)
    
    fieldsets = (
        ('Book Information', {
            'fields': ('title', 'slug', 'author', 'summary')
        }),
        ('Metadata', {
            'fields': ('status', 'rating', 'genres', 'is_featured', 'cover_color')
        }),
        ('Appearance', {
            'fields': ('cover_preview',),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('review_count_display', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @admin.action(description='Approve selected books for publication')
    def approve_selected_books(self, request, queryset):
        queryset.update(status=Book.PUBLISHED)

    @admin.action(description='Return selected books to draft')
    def return_selected_books_to_draft(self, request, queryset):
        queryset.update(status=Book.DRAFT)

    @admin.action(description='Archive selected books')
    def archive_selected_books(self, request, queryset):
        queryset.update(status=Book.ARCHIVED)
    
    def status_badge(self, obj):
        colors = {
            'published': '#4caf50',
            'draft': '#ff9800',
            'archived': '#f44336',
        }
        color = colors.get(obj.status, '#9e9e9e')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def featured_badge(self, obj):
        if obj.is_featured:
            return mark_safe(
                '<span style="background-color: #2196f3; color: white; padding: 3px 8px; border-radius: 3px;">⭐ Featured</span>'
            )
        return '—'
    featured_badge.short_description = 'Featured'
    
    def rating_display(self, obj):
        if obj.rating > 0:
            return format_html(
                '<span style="color: #ffc107; font-weight: bold;">★ {}</span>',
                obj.rating
            )
        return '—'
    rating_display.short_description = 'Rating'
    
    def review_count(self, obj):
        count = obj.reviews.count()
        return format_html(
            '<span style="background-color: #e0e0e0; padding: 3px 8px; border-radius: 3px;">{} reviews</span>',
            count
        )
    review_count.short_description = 'Reviews'
    
    def cover_preview(self, obj):
        cover_url = obj.cover_url
        if not cover_url and obj.pk:
            cover_upload = obj.uploads.filter(kind=BookUpload.COVER).first()
            if cover_upload and cover_upload.file:
                cover_url = cover_upload.file.url
        if cover_url:
            return format_html(
                '<img class="admin-cover-preview" src="{}" alt="Cover of {}">',
                cover_url,
                obj.title,
            )
        return format_html(
            '<div class="admin-cover-placeholder" style="background: {};"><span>Cover preview</span></div>',
            obj.cover_color
        )
    cover_preview.short_description = 'Cover Preview'
    
    def review_count_display(self, obj):
        return obj.reviews.count()
    review_count_display.short_description = 'Total Reviews'


# ==================== REVIEW ADMIN ====================
class ReviewCommentInline(admin.TabularInline):
    model = ReviewComment
    extra = 1
    fields = ('user', 'content', 'created_at')
    readonly_fields = ('created_at',)


class ReviewAdmin(admin.ModelAdmin):
    list_display = ('book', 'user', 'created_at', 'comment_count')
    list_filter = ('created_at', 'book__author')
    search_fields = ('content', 'user__username', 'book__title')
    readonly_fields = ('created_at', 'comment_count_display')
    inlines = [ReviewCommentInline]
    
    fieldsets = (
        ('Review Information', {
            'fields': ('book', 'user', 'content')
        }),
        ('Statistics', {
            'fields': ('created_at', 'comment_count_display'),
            'classes': ('collapse',)
        }),
    )
    
    def comment_count(self, obj):
        count = obj.comments.count()
        return format_html(
            '<span style="background-color: #c8e6c9; padding: 3px 8px; border-radius: 3px;">{} comments</span>',
            count
        )
    comment_count.short_description = 'Comments'
    
    def comment_count_display(self, obj):
        return obj.comments.count()
    comment_count_display.short_description = 'Total Comments'


# ==================== REVIEW COMMENT ADMIN ====================
class ReviewCommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'review_book', 'created_at')
    list_filter = ('created_at', 'review__book')
    search_fields = ('content', 'user__username', 'review__book__title')
    readonly_fields = ('created_at',)
    
    def review_book(self, obj):
        return obj.review.book.title
    review_book.short_description = 'Book'


# ==================== AUTHOR FOLLOW ADMIN ====================
class AuthorFollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'author', 'created_at')
    list_filter = ('created_at', 'author')
    search_fields = ('follower__username', 'author__name')
    readonly_fields = ('created_at',)


# ==================== USER BOOKSHELF ADMIN ====================
class UserBookshelfAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'status_badge', 'progress_display', 'rating_stars', 'added_at')
    list_filter = ('status', 'added_at', 'book__author')
    search_fields = ('user__username', 'book__title')
    readonly_fields = ('added_at', 'completed_at')
    
    fieldsets = (
        ('Bookshelf Entry', {
            'fields': ('user', 'book', 'status')
        }),
        ('Reading Progress', {
            'fields': ('progress_percent', 'rating', 'notes')
        }),
        ('Timestamps', {
            'fields': ('added_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'want_to_read': '#2196f3',
            'currently_reading': '#ff9800',
            'read': '#4caf50',
        }
        color = colors.get(obj.status, '#9e9e9e')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def progress_display(self, obj):
        return format_html(
            '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px; overflow: hidden; display: inline-block;">'
            '<div style="background-color: #4caf50; height: 20px; width: {}%; text-align: center; color: white; font-size: 12px; line-height: 20px;">'
            '{}</div></div>',
            obj.progress_percent,
            f'{obj.progress_percent}%' if obj.progress_percent > 5 else ''
        )
    progress_display.short_description = 'Progress'
    
    def rating_stars(self, obj):
        if obj.rating:
            stars = '★' * obj.rating + '☆' * (5 - obj.rating)
            return format_html(
                '<span style="color: #ffc107; font-weight: bold;">{}</span>',
                stars
            )
        return '—'
    rating_stars.short_description = 'Rating'


# ==================== READING LIST ADMIN ====================
class ReadingListAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'public_badge', 'book_count', 'created_at')
    list_filter = ('is_public', 'created_at')
    search_fields = ('title', 'user__username', 'description')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('books',)
    readonly_fields = ('slug', 'created_at', 'updated_at', 'book_count_display')
    
    fieldsets = (
        ('List Information', {
            'fields': ('user', 'title', 'slug', 'description', 'is_public')
        }),
        ('Books', {
            'fields': ('books', 'book_count_display')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def public_badge(self, obj):
        if obj.is_public:
            return format_html(
                '<span style="background-color: #4caf50; color: white; padding: 3px 8px; border-radius: 3px;">🌍 Public</span>'
            )
        return format_html(
            '<span style="background-color: #f44336; color: white; padding: 3px 8px; border-radius: 3px;">🔒 Private</span>'
        )
    public_badge.short_description = 'Visibility'
    
    def book_count(self, obj):
        count = obj.books.count()
        return format_html(
            '<span style="background-color: #e3f2fd; padding: 3px 8px; border-radius: 3px;">{} books</span>',
            count
        )
    book_count.short_description = 'Books'
    
    def book_count_display(self, obj):
        return obj.books.count()
    book_count_display.short_description = 'Total Books'


class CatalogBookAdmin(admin.ModelAdmin):
    list_display = ('title', 'source', 'access_type', 'copyright_status', 'full_text_available', 'disabled', 'updated_at')
    list_filter = ('source', 'access_type', 'copyright_status', 'full_text_available', 'borrowable', 'disabled')
    search_fields = ('title', 'authors', 'isbn10', 'isbn13', 'external_id')
    readonly_fields = ('created_at', 'updated_at')
    actions = ('disable_selected_books', 'enable_selected_books')

    @admin.action(description='Disable selected catalogue books')
    def disable_selected_books(self, request, queryset):
        queryset.update(disabled=True)

    @admin.action(description='Enable selected catalogue books')
    def enable_selected_books(self, request, queryset):
        queryset.update(disabled=False)


class BookSourceAdmin(admin.ModelAdmin):
    list_display = ('book', 'provider', 'access_type', 'copyright_status', 'internal_reading_allowed', 'last_checked_at')
    list_filter = ('provider', 'access_type', 'copyright_status', 'internal_reading_allowed')
    search_fields = ('book__title', 'external_id')


class ProviderStatusAdmin(admin.ModelAdmin):
    list_display = ('provider', 'is_enabled', 'last_success_at', 'failure_count')
    list_editable = ('is_enabled',)
    readonly_fields = ('last_success_at', 'last_error', 'failure_count')


class ReadingProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'chapter', 'percent', 'last_read_at')
    list_filter = ('last_read_at',)
    search_fields = ('user__username', 'book__title')
    readonly_fields = ('last_read_at',)


class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ('query', 'user', 'result_count', 'created_at')
    search_fields = ('query', 'user__username')
    readonly_fields = ('created_at',)


class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'provider', 'uid', 'date_joined', 'last_login')
    list_filter = ('provider', 'date_joined', 'last_login')
    search_fields = ('user__username', 'user__email', 'uid')
    readonly_fields = ('user', 'provider', 'uid', 'date_joined', 'last_login', 'extra_data')


class AuthenticationEventAdmin(admin.ModelAdmin):
    list_display = ('user', 'event_type', 'provider', 'created_at')
    list_filter = ('event_type', 'provider', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('user', 'event_type', 'provider', 'created_at')


class UserRestrictionAdmin(DefaultUserAdmin):
    list_display = ('username', 'email', 'is_active', 'is_staff', 'is_superuser', 'last_login')
    list_filter = ('is_active', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    actions = ('restrict_selected_users', 'restore_selected_users')

    @admin.action(description='Restrict selected user accounts')
    def restrict_selected_users(self, request, queryset):
        queryset.exclude(pk=request.user.pk).filter(is_superuser=False).update(is_active=False)

    @admin.action(description='Restore selected user accounts')
    def restore_selected_users(self, request, queryset):
        queryset.filter(is_superuser=False).update(is_active=True)


# ==================== IMPORTED BOOK ADMIN ====================
class BookFileInline(admin.TabularInline):
    model = BookFile
    readonly_fields = ('file_path', 'file_size', 'checksum', 'chapters_count', 'processed_at')
    can_delete = False
    extra = 0


class ImportJobInline(admin.TabularInline):
    model = ImportJob
    readonly_fields = ('status', 'progress_percent', 'current_step', 'error_message', 'created_at', 'completed_at')
    can_delete = False
    extra = 0


class ImportedBookAdmin(admin.ModelAdmin):
    list_display = ('catalog_book_title', 'format_display', 'status_badge', 'file_size_display', 'imported_date')
    list_filter = ('status', 'format', 'imported_at', 'created_at')
    search_fields = ('catalog_book__title', 'catalog_book__authors')
    readonly_fields = ('file_size', 'checksum', 'imported_at', 'created_at', 'updated_at')
    inlines = [BookFileInline, ImportJobInline]
    actions = ('retry_failed_imports', 'delete_imported_book')
    
    fieldsets = (
        ('Book Information', {
            'fields': ('catalog_book', 'book_source')
        }),
        ('Import Details', {
            'fields': ('format', 'status', 'file_size', 'checksum', 'import_error')
        }),
        ('Timeline', {
            'fields': ('imported_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def catalog_book_title(self, obj):
        return obj.catalog_book.title
    catalog_book_title.short_description = 'Book'
    
    def format_display(self, obj):
        colors = {
            'epub': '#007bff',
            'pdf': '#dc3545',
            'txt': '#28a745',
        }
        color = colors.get(obj.format, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_format_display()
        )
    format_display.short_description = 'Format'
    
    def status_badge(self, obj):
        status_colors = {
            'imported': '#28a745',
            'failed': '#dc3545',
            'processing': '#ffc107',
            'downloading': '#17a2b8',
            'queued': '#6c757d',
            'discovered': '#e83e8c',
            'rejected': '#6f42c1',
        }
        color = status_colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def file_size_display(self, obj):
        if obj.file_size:
            return f"{obj.file_size / (1024*1024):.2f} MB"
        return "-"
    file_size_display.short_description = 'Size'
    
    def imported_date(self, obj):
        if obj.imported_at:
            return obj.imported_at.strftime('%Y-%m-%d %H:%M')
        return "-"
    imported_date.short_description = 'Imported'
    
    @admin.action(description='Retry failed imports')
    def retry_failed_imports(self, request, queryset):
        failed = queryset.filter(status=ImportedBook.FAILED)
        failed.update(status=ImportedBook.QUEUED)
        self.message_user(request, f'{failed.count()} imports queued for retry')
    
    @admin.action(description='Delete selected imports (keep file)')
    def delete_imported_book(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'{count} imports deleted')


class ImportJobAdmin(admin.ModelAdmin):
    list_display = ('imported_book_title', 'status_badge', 'progress_display', 'created_date')
    list_filter = ('status', 'created_at', 'completed_at')
    search_fields = ('imported_book__catalog_book__title',)
    readonly_fields = ('progress_display_detail', 'error_traceback', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Job Information', {
            'fields': ('imported_book', 'initiated_by', 'status', 'progress_display_detail')
        }),
        ('Progress', {
            'fields': ('current_step', 'started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
        ('Error Details', {
            'fields': ('error_message', 'error_traceback'),
            'classes': ('collapse',)
        }),
        ('Retry Information', {
            'fields': ('retry_count', 'last_retry_at'),
            'classes': ('collapse',)
        }),
    )
    
    def imported_book_title(self, obj):
        return obj.imported_book.catalog_book.title
    imported_book_title.short_description = 'Book'
    
    def status_badge(self, obj):
        status_colors = {
            'success': '#28a745',
            'failed': '#dc3545',
            'processing': '#ffc107',
            'pending': '#17a2b8',
            'cancelled': '#6c757d',
        }
        color = status_colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def progress_display(self, obj):
        return f"{obj.progress_percent}%"
    progress_display.short_description = 'Progress'
    
    def progress_display_detail(self, obj):
        return format_html(
            '<div style="width: 300px; height: 20px; background: #e9ecef; border-radius: 3px; overflow: hidden;">'
            '<div style="width: {}%; height: 100%; background: #28a745;"></div>'
            '</div><p style="margin-top: 5px;">{} - {}</p>',
            obj.progress_percent,
            obj.progress_percent,
            obj.current_step
        )
    progress_display_detail.short_description = 'Progress'
    
    def created_date(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_date.short_description = 'Created'


class ReadingBookmarkAdmin(admin.ModelAdmin):
    list_display = ('user_name', 'book_title', 'chapter_identifier', 'created_date')
    list_filter = ('created_at', 'user')
    search_fields = ('user__username', 'imported_book__catalog_book__title', 'chapter_identifier')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Bookmark Info', {
            'fields': ('user', 'imported_book', 'chapter_identifier', 'label')
        }),
        ('Position Data', {
            'fields': ('position_info',),
            'classes': ('collapse',)
        }),
        ('Timeline', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_name(self, obj):
        return obj.user.username
    user_name.short_description = 'User'
    
    def book_title(self, obj):
        return obj.imported_book.catalog_book.title
    book_title.short_description = 'Book'
    
    def created_date(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_date.short_description = 'Created'


class ReadingHighlightAdmin(admin.ModelAdmin):
    list_display = ('user_name', 'book_title', 'text_preview', 'color_display', 'created_date')
    list_filter = ('color', 'created_at', 'user')
    search_fields = ('user__username', 'imported_book__catalog_book__title', 'text_excerpt', 'note')
    readonly_fields = ('created_at', 'updated_at', 'text_display')
    
    fieldsets = (
        ('Highlight Info', {
            'fields': ('user', 'imported_book', 'chapter_identifier', 'color')
        }),
        ('Content', {
            'fields': ('text_display', 'note'),
        }),
        ('Position Data', {
            'fields': ('location_info',),
            'classes': ('collapse',)
        }),
        ('Timeline', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_name(self, obj):
        return obj.user.username
    user_name.short_description = 'User'
    
    def book_title(self, obj):
        return obj.imported_book.catalog_book.title
    book_title.short_description = 'Book'
    
    def text_preview(self, obj):
        preview = obj.text_excerpt[:50] + '...' if len(obj.text_excerpt) > 50 else obj.text_excerpt
        return preview
    text_preview.short_description = 'Text'
    
    def text_display(self, obj):
        return format_html(
            '<blockquote style="padding: 10px; background: #f8f9fa; border-left: 4px solid {};">{}</blockquote>',
            obj.color,
            obj.text_excerpt
        )
    text_display.short_description = 'Highlighted Text'
    
    def color_display(self, obj):
        return format_html(
            '<span style="display: inline-block; width: 20px; height: 20px; background: {}; border-radius: 3px;"></span> {}',
            obj.color,
            obj.color
        )
    color_display.short_description = 'Color'
    
    def created_date(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_date.short_description = 'Created'


# ==================== REGISTER ALL MODELS ====================
admin_site.register(Genre, GenreAdmin)
admin_site.register(Author, AuthorAdmin)
admin_site.register(Book, BookAdmin)
admin_site.register(Chapter, ChapterAdmin)
admin_site.register(Review, ReviewAdmin)
admin_site.register(ReviewComment, ReviewCommentAdmin)
admin_site.register(AuthorFollow, AuthorFollowAdmin)
admin_site.register(UserBookshelf, UserBookshelfAdmin)
admin_site.register(ReadingList, ReadingListAdmin)
admin_site.register(CatalogBook, CatalogBookAdmin)
admin_site.register(BookSource, BookSourceAdmin)
admin_site.register(ProviderStatus, ProviderStatusAdmin)
admin_site.register(ReadingProgress, ReadingProgressAdmin)
admin_site.register(Bookmark)
admin_site.register(Highlight)
admin_site.register(ReadingNote)
admin_site.register(CatalogLibraryEntry)
admin_site.register(SearchHistory, SearchHistoryAdmin)
admin_site.register(SocialAccount, SocialAccountAdmin)
admin_site.register(AuthenticationEvent, AuthenticationEventAdmin)
admin_site.register(User, UserRestrictionAdmin)

# ===== Imported Books & Reading =====
admin_site.register(ImportedBook, ImportedBookAdmin)
admin_site.register(ImportJob, ImportJobAdmin)
admin_site.register(ReadingBookmark, ReadingBookmarkAdmin)
admin_site.register(ReadingHighlight, ReadingHighlightAdmin)
admin_site.register(BookUpload)
admin_site.register(Promotion)
admin_site.register(Competition)
admin_site.register(CompetitionEntry)
admin_site.register(Award)
admin_site.register(AwardCategory)
admin_site.register(AwardNominee)
admin_site.register(CriticProfile)
admin_site.register(CriticApplication)
admin_site.register(ReviewAssignment)
admin_site.register(CriticReview)
admin_site.register(CriticEarning)
admin_site.register(SubscriptionPlan)
admin_site.register(PremiumSubscription, PremiumSubscriptionAdmin)
admin_site.register(MonetizationPayment, MonetizationPaymentAdmin)
admin_site.register(WriterProfile, WriterProfileAdmin)
admin_site.register(MonetizationConfig, MonetizationConfigAdmin)
admin_site.register(ReaderSession, ReaderSessionAdmin)
admin_site.register(WriterEarning, WriterEarningAdmin)
admin_site.register(WriterWithdrawal, WriterWithdrawalAdmin)
admin_site.register(WithdrawalAllocation, WithdrawalAllocationAdmin)
admin_site.register(Advertisement)
admin_site.register(AdImpression, AdImpressionAdmin)
admin_site.register(AdClick, AdClickAdmin)

