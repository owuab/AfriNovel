from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from pathlib import Path
from uuid import uuid4
from urllib.parse import quote
from django.core.validators import FileExtensionValidator
from datetime import timedelta


class Permission(models.Model):
    """Granular admin permission registry for role-based access control."""
    name = models.CharField(max_length=100, unique=True)
    module = models.CharField(max_length=50)
    action = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, blank=True)
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['module', 'action']
        constraints = [
            models.UniqueConstraint(fields=['module', 'action'], name='unique_permission_module_action'),
        ]
        indexes = [
            models.Index(fields=['module', 'action'], name='perm_module_action_idx'),
            models.Index(fields=['name'], name='perm_name_idx'),
        ]

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    """Tracks which permissions are granted to a role and when they were revoked."""
    role_name = models.CharField(max_length=50, db_index=True, default='moderator')
    permission = models.ForeignKey('Permission', on_delete=models.CASCADE, related_name='role_permissions')
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_permissions',
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='revoked_permissions',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['role_name', 'permission'], name='unique_role_permission'),
        ]
        indexes = [
            models.Index(fields=['role_name'], name='roleperm_role_idx'),
            models.Index(fields=['permission'], name='roleperm_permission_idx'),
            models.Index(fields=['granted_at'], name='roleperm_granted_at_idx'),
        ]

    def __str__(self):
        return f'{self.role_name}: {self.permission.name}'


class Genre(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Author(models.Model):
    name = models.CharField(max_length=150)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Book(models.Model):
    DRAFT = 'draft'
    PUBLISHED = 'published'
    ARCHIVED = 'archived'
    STATUS_CHOICES = [
        (DRAFT, 'Draft'),
        (PUBLISHED, 'Published'),
        (ARCHIVED, 'Archived'),
    ]

    ONGOING = 'ongoing'
    COMPLETED = 'completed'
    HIATUS = 'hiatus'
    NOVEL_STATUS_CHOICES = [
        (ONGOING, 'Ongoing'),
        (COMPLETED, 'Completed'),
        (HIATUS, 'Hiatus'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='books')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='authored_books')
    translator = models.CharField(max_length=200, blank=True, help_text='Translator name')
    licensor = models.CharField(max_length=200, blank=True, help_text='Publisher/licensor name')
    language = models.CharField(max_length=50, default='English', help_text='Original language')
    subtitle = models.CharField(max_length=240, blank=True)
    subgenre = models.CharField(max_length=100, blank=True)
    tags = models.CharField(max_length=500, blank=True, help_text='Comma-separated discovery tags')
    summary = models.TextField()
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    content_rating = models.CharField(max_length=16, choices=[('everyone', 'Everyone'), ('teen', 'Teen'), ('mature', 'Mature')], default='teen')
    cover_url = models.URLField(max_length=1000, blank=True)
    catalog_book = models.ForeignKey('CatalogBook', null=True, blank=True, on_delete=models.SET_NULL, related_name='homepage_books')
    view_count = models.PositiveIntegerField(default=0)
    cover_color = models.CharField(max_length=80, default='linear-gradient(135deg, #dcae7b, #8a563f)')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=DRAFT)
    novel_status = models.CharField(max_length=20, choices=NOVEL_STATUS_CHOICES, default=ONGOING, help_text='Story status (ongoing/completed)')
    published_at = models.DateTimeField(null=True, blank=True)
    rights_confirmed = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    genres = models.ManyToManyField(Genre, related_name='books')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def chapters_total(self):
        return self.chapters.count()

    @property
    def saves_total(self):
        return self.on_shelves.count()

    def get_absolute_url(self):
        return reverse('book_detail', args=[self.slug])
    
    def get_reader_url(self):
        """Return the appropriate reader URL for this book (wuxiaworld-style direct reading)"""
        # Prioritize chapter detail system for books with chapters
        if self.chapters.exists():
            first_chapter = self.chapters.first()
            if first_chapter:
                return reverse('chapter_detail', args=[self.slug, first_chapter.chapter_number])
        # Fall back to other reader systems
        elif self.catalog_book and self.catalog_book.can_read_in_app:
            return reverse('catalogue_reader', args=[self.catalog_book.pk])
        elif self.uploads.filter(kind='manuscript').exists():
            return reverse('uploaded_book_reader', args=[self.slug])
        else:
            return reverse('book_detail', args=[self.slug])

    @property
    def cover_image_url(self):
        if self.cover_url and 'gutenberg.org' not in self.cover_url.casefold():
            return self.cover_url
        cover_upload = self.uploads.filter(kind=BookUpload.COVER).first()
        if cover_upload and cover_upload.file:
            try:
                if cover_upload.file.storage.exists(cover_upload.file.name):
                    return cover_upload.file.url
            except (OSError, ValueError):
                pass
        if self.catalog_book:
            return self.catalog_book.cover_image_url
        return ''

    @property
    def chapter_count(self):
        return self.chapters.count()

    @property
    def review_count(self):
        return self.reviews.count()


class Chapter(models.Model):
    """Individual chapters for web novels"""
    DRAFT = 'draft'
    PUBLISHED = 'published'
    COMPLETED = 'completed'
    STATUS_CHOICES = [
        (DRAFT, 'Draft'),
        (PUBLISHED, 'Published'),
        (COMPLETED, 'Completed'),
    ]

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='chapters')
    chapter_number = models.PositiveIntegerField()
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300)
    content = models.TextField(blank=True, help_text='Chapter content')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=PUBLISHED, db_index=True)
    published_date = models.DateTimeField(null=True, blank=True)
    is_free = models.BooleanField(default=True, help_text='Free to read without subscription')
    is_locked = models.BooleanField(default=False, help_text='Locked for premium users')
    word_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['chapter_number']
        unique_together = ['book', 'chapter_number']
        indexes = [
            models.Index(fields=['book', 'chapter_number']),
            models.Index(fields=['book', 'status', 'chapter_number'], name='books_chapt_book_id_50e026_idx'),
            models.Index(fields=['book', 'is_free']),
        ]

    def __str__(self):
        return f"Chapter {self.chapter_number}: {self.title}"

    def get_absolute_url(self):
        return reverse('chapter_detail', args=[self.book.slug, self.chapter_number])


def book_upload_path(instance, filename):
    safe_name = slugify(Path(filename).stem) or 'book-file'
    suffix = Path(filename).suffix.lower()
    return f'book-uploads/{instance.uploaded_by_id}/{instance.book_id}/{uuid4().hex}-{safe_name}{suffix}'


class BookUpload(models.Model):
    MANUSCRIPT = 'manuscript'
    COVER = 'cover'
    ASSET = 'asset'
    KIND_CHOICES = [(MANUSCRIPT, 'Manuscript'), (COVER, 'Cover'), (ASSET, 'Supporting asset')]
    PENDING = 'pending'
    PROCESSING = 'processing'
    READY = 'ready'
    FAILED = 'failed'
    STATUS_CHOICES = [(PENDING, 'Pending'), (PROCESSING, 'Processing'), (READY, 'Ready'), (FAILED, 'Failed')]

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='uploads')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='book_uploads')
    file = models.FileField(upload_to=book_upload_path)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveBigIntegerField(default=0)
    content_type = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.book.title}: {self.original_filename}'


class Review(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], default=5)
    content = models.TextField()
    helpful_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['book', 'user']

    def __str__(self):
        return f'{self.user.username} on {self.book.title} ({self.rating}★)'


class ReviewComment(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='review_comments')
    content = models.TextField()
    helpful_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.user.username} on {self.review.book.title}'


class UserFreeChapterAllowance(models.Model):
    """Track free chapter allowance for users"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='free_chapter_allowance')
    free_chapters_remaining = models.PositiveIntegerField(default=2)
    last_reset_time = models.DateTimeField(auto_now=True)
    reset_interval_hours = models.PositiveIntegerField(default=23, help_text='Hours between free chapter resets')
    total_free_chapters_per_reset = models.PositiveIntegerField(default=2)

    def reset_if_needed(self):
        """Reset free chapters if the interval has passed"""
        time_since_reset = timezone.now() - self.last_reset_time
        if time_since_reset >= timedelta(hours=self.reset_interval_hours):
            self.free_chapters_remaining = self.total_free_chapters_per_reset
            self.last_reset_time = timezone.now()
            self.save()
            return True
        return False

    def get_time_until_reset(self):
        """Get time remaining until next reset"""
        time_since_reset = timezone.now() - self.last_reset_time
        time_until_reset = timedelta(hours=self.reset_interval_hours) - time_since_reset
        return max(time_until_reset, timedelta())

    class Meta:
        verbose_name = "User Free Chapter Allowance"
        verbose_name_plural = "User Free Chapter Allowances"

    def __str__(self):
        return f'{self.user.username}: {self.free_chapters_remaining} free chapters'


class AuthorFollow(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='following_authors')
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'author')

    def __str__(self):
        return f'{self.follower.username} follows {self.author.name}'


class UserBookshelf(models.Model):
    WANT_TO_READ = 'want_to_read'
    CURRENTLY_READING = 'currently_reading'
    READ = 'read'
    STATUS_CHOICES = [
        (WANT_TO_READ, 'Want to Read'),
        (CURRENTLY_READING, 'Currently Reading'),
        (READ, 'Read'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookshelf')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='on_shelves')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=WANT_TO_READ)
    progress_percent = models.IntegerField(default=0)
    rating = models.IntegerField(null=True, blank=True)  # 1-5 stars
    notes = models.TextField(blank=True)
    added_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_read_chapter = models.ForeignKey('Chapter', null=True, blank=True, on_delete=models.SET_NULL, related_name='read_by_users')
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'book')
        ordering = ['-added_at']

    def __str__(self):
        return f'{self.user.username} - {self.book.title} ({self.status})'


class ReadingList(models.Model):
    """Curated collections of books created by users"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reading_lists')
    title = models.CharField(max_length=150)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    books = models.ManyToManyField(Book, related_name='in_lists')
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'slug')
        ordering = ['-updated_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.user.username} - {self.title}'

    def get_absolute_url(self):
        return reverse('reading_list_detail', args=[self.user.username, self.slug])


class CatalogBook(models.Model):
    """A normalized record returned by a legal external catalogue provider."""

    FREE_FULL_TEXT = 'free_full_text'
    PUBLIC_DOMAIN = 'public_domain'
    OPEN_ACCESS = 'open_access'
    FREE_READ_EXTERNAL = 'free_read_external'
    BORROW = 'borrow'
    PURCHASE_REQUIRED = 'purchase_required'
    UNAVAILABLE = 'unavailable'
    ACCESS_TYPES = [
        (FREE_FULL_TEXT, 'Free full text'),
        (PUBLIC_DOMAIN, 'Public domain'),
        (OPEN_ACCESS, 'Open access'),
        (FREE_READ_EXTERNAL, 'Free to read at source'),
        (BORROW, 'Borrow'),
        (PURCHASE_REQUIRED, 'Purchase required'),
        (UNAVAILABLE, 'Unavailable'),
    ]

    PUBLIC_DOMAIN_STATUS = 'public_domain'
    OPEN_LICENSE = 'open_license'
    AUTHORIZED = 'authorized'
    UNKNOWN = 'unknown'
    COPYRIGHTED = 'copyrighted'
    COPYRIGHT_STATUSES = [
        (PUBLIC_DOMAIN_STATUS, 'Public domain'),
        (OPEN_LICENSE, 'Open license'),
        (AUTHORIZED, 'Authorized'),
        (UNKNOWN, 'Unknown'),
        (COPYRIGHTED, 'Copyrighted'),
    ]

    source = models.CharField(max_length=80)
    external_id = models.CharField(max_length=160)
    title = models.CharField(max_length=500)
    subtitle = models.CharField(max_length=500, blank=True)
    authors = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True)
    subjects = models.JSONField(default=list, blank=True)
    languages = models.JSONField(default=list, blank=True)
    publication_year = models.PositiveIntegerField(null=True, blank=True)
    publisher = models.CharField(max_length=300, blank=True)
    isbn10 = models.CharField(max_length=16, blank=True)
    isbn13 = models.CharField(max_length=20, blank=True)
    cover_url = models.URLField(max_length=1000, blank=True)
    source_url = models.URLField(max_length=1000)
    reading_url = models.URLField(max_length=1000, blank=True)
    access_type = models.CharField(max_length=32, choices=ACCESS_TYPES, default=UNAVAILABLE)
    copyright_status = models.CharField(max_length=32, choices=COPYRIGHT_STATUSES, default=UNKNOWN)
    license = models.CharField(max_length=300, blank=True)
    license_url = models.URLField(max_length=1000, blank=True)
    license_verified_at = models.DateTimeField(null=True, blank=True)
    original_language = models.CharField(max_length=16, blank=True)
    translated_language = models.CharField(max_length=16, blank=True)
    transliterated_title = models.CharField(max_length=500, blank=True)
    script = models.CharField(max_length=32, blank=True)
    full_text_available = models.BooleanField(default=False)
    borrowable = models.BooleanField(default=False)
    page_count = models.PositiveIntegerField(null=True, blank=True)
    disabled = models.BooleanField(default=False)
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['source', 'external_id'], name='unique_catalogue_source_record'),
        ]
        ordering = ['title']

    def __str__(self):
        return f'{self.title} ({self.source})'

    @property
    def cover_image_url(self):
        if self.cover_url and 'gutenberg.org' not in self.cover_url.casefold():
            return self.cover_url
        if self.source == 'internet_archive':
            return f'https://archive.org/services/img/{self.external_id}'
        if self.source == 'gutenberg' and self.title:
            return f'https://covers.openlibrary.org/b/title/{quote(self.title, safe="")}-L.jpg'
        return ''

    @property
    def can_read_in_app(self):
        return (
            not self.disabled
            and self.full_text_available
            and self.copyright_status in {self.PUBLIC_DOMAIN_STATUS, self.OPEN_LICENSE, self.AUTHORIZED}
            and bool(self.reading_url)
        )


class CatalogCategory(models.Model):
    """Controlled taxonomy assigned to legally available catalogue records."""

    ASIAN = 'asian'
    CATEGORY_CHOICES = [(ASIAN, 'Asian')]
    SUBCATEGORY_CHOICES = [
        ('chinese', 'Chinese'),
        ('korean', 'Korean'),
        ('japanese', 'Japanese'),
        ('south_asian', 'South Asian'),
        ('southeast_asian', 'Southeast Asian'),
    ]

    book = models.ForeignKey(CatalogBook, on_delete=models.CASCADE, related_name='categories')
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES)
    subcategory = models.CharField(max_length=40, choices=SUBCATEGORY_CHOICES)
    confidence = models.DecimalField(max_digits=4, decimal_places=3, default=1)
    rule_version = models.CharField(max_length=24, default='asian-v1')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['book', 'category', 'subcategory'], name='unique_catalog_category'),
        ]
        indexes = [models.Index(fields=['category', 'subcategory'])]

    def __str__(self):
        return f'{self.book.title}: {self.get_subcategory_display()}'


class BookSource(models.Model):
    """Every known authorized edition/source for a normalized catalogue record."""

    book = models.ForeignKey(CatalogBook, on_delete=models.CASCADE, related_name='sources')
    provider = models.CharField(max_length=80)
    external_id = models.CharField(max_length=160)
    source_url = models.URLField(max_length=1000)
    reading_url = models.URLField(max_length=1000, blank=True)
    access_type = models.CharField(max_length=32, choices=CatalogBook.ACCESS_TYPES)
    copyright_status = models.CharField(max_length=32, choices=CatalogBook.COPYRIGHT_STATUSES)
    license = models.CharField(max_length=300, blank=True)
    internal_reading_allowed = models.BooleanField(default=False)
    is_primary = models.BooleanField(default=False)
    last_checked_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['provider', 'external_id'], name='unique_book_provider_edition'),
        ]

    def __str__(self):
        return f'{self.provider}: {self.book.title}'


class ReadingProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='catalogue_progress')
    book = models.ForeignKey(CatalogBook, on_delete=models.CASCADE, related_name='reading_progress')
    chapter = models.CharField(max_length=250, blank=True)
    paragraph = models.PositiveIntegerField(default=0)
    character_offset = models.PositiveIntegerField(default=0)
    percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    last_read_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'book'], name='unique_catalogue_reading_progress')]


class CatalogLibraryEntry(models.Model):
    SAVED = 'saved'
    CURRENTLY_READING = 'currently_reading'
    FINISHED = 'finished'
    STATES = [(SAVED, 'Saved'), (CURRENTLY_READING, 'Currently reading'), (FINISHED, 'Finished')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='catalogue_library')
    book = models.ForeignKey(CatalogBook, on_delete=models.CASCADE, related_name='library_entries')
    state = models.CharField(max_length=24, choices=STATES, default=SAVED)
    saved_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'book'], name='unique_catalogue_library_entry')]
        ordering = ['-saved_at']


class Bookmark(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='catalogue_bookmarks')
    book = models.ForeignKey(CatalogBook, on_delete=models.CASCADE, related_name='bookmarks')
    chapter = models.CharField(max_length=250, blank=True)
    paragraph = models.PositiveIntegerField(default=0)
    excerpt = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class Highlight(models.Model):
    YELLOW = 'yellow'
    GREEN = 'green'
    BLUE = 'blue'
    PINK = 'pink'
    COLORS = [(YELLOW, 'Yellow'), (GREEN, 'Green'), (BLUE, 'Blue'), (PINK, 'Pink')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='catalogue_highlights')
    book = models.ForeignKey(CatalogBook, on_delete=models.CASCADE, related_name='highlights')
    chapter = models.CharField(max_length=250, blank=True)
    paragraph = models.PositiveIntegerField(default=0)
    selected_text = models.TextField()
    color = models.CharField(max_length=12, choices=COLORS, default=YELLOW)
    created_at = models.DateTimeField(auto_now_add=True)


class ReadingNote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='catalogue_notes')
    book = models.ForeignKey(CatalogBook, on_delete=models.CASCADE, related_name='notes')
    chapter = models.CharField(max_length=250, blank=True)
    paragraph = models.PositiveIntegerField(default=0)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class SearchHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='catalogue_searches', null=True, blank=True)
    query = models.CharField(max_length=300)
    result_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class ProviderStatus(models.Model):
    provider = models.CharField(max_length=80, unique=True)
    is_enabled = models.BooleanField(default=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    failure_count = models.PositiveIntegerField(default=0)


class AuthenticationEvent(models.Model):
    PASSWORD_LOGIN = 'password_login'
    SOCIAL_LOGIN = 'social_login'
    ACCOUNT_LINKED = 'account_linked'
    ACCOUNT_UNLINKED = 'account_unlinked'
    EVENTS = [
        (PASSWORD_LOGIN, 'Password login'),
        (SOCIAL_LOGIN, 'Social login'),
        (ACCOUNT_LINKED, 'Account linked'),
        (ACCOUNT_UNLINKED, 'Account unlinked'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='authentication_events')
    event_type = models.CharField(max_length=32, choices=EVENTS)
    provider = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} - {self.get_event_type_display()}'


class UserProfile(models.Model):
    EVERYONE = 'everyone'
    FOLLOWERS = 'followers'
    ONLY_ME = 'only_me'
    VISIBILITY_CHOICES = [(EVERYONE, 'Everyone'), (FOLLOWERS, 'Followers'), (ONLY_ME, 'Only me')]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='social_profile')
    display_name = models.CharField(max_length=100, blank=True)
    bio = models.CharField(max_length=280, blank=True)
    location = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    avatar = models.ImageField(
        upload_to='profile_avatars/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif', 'webp'])]
    )
    avatar_url = models.URLField(blank=True)
    banner_url = models.URLField(blank=True)
    allow_followers = models.CharField(max_length=16, choices=VISIBILITY_CHOICES, default=EVERYONE)
    comment_visibility = models.CharField(max_length=16, choices=VISIBILITY_CHOICES, default=EVERYONE)
    reading_visibility = models.CharField(max_length=16, choices=VISIBILITY_CHOICES, default=EVERYONE)
    books_visibility = models.CharField(max_length=16, choices=VISIBILITY_CHOICES, default=EVERYONE)
    recommendation_visibility = models.CharField(max_length=16, choices=VISIBILITY_CHOICES, default=EVERYONE)
    profile_views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name or self.user.username

    def get_avatar_url(self):
        """Return avatar URL, preferring uploaded avatar over URL"""
        if self.avatar:
            return self.avatar.url
        elif self.avatar_url:
            return self.avatar_url
        else:
            # Default avatar based on username
            return f"https://ui-avatars.com/api/?name={self.user.username}&background=random"


class UserFollow(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='following_users')
    followed = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='follower_users')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['follower', 'followed'], name='unique_user_follow'),
            models.CheckConstraint(condition=~models.Q(follower=models.F('followed')), name='prevent_self_follow'),
        ]
        indexes = [models.Index(fields=['followed', '-created_at'])]


class SocialPost(models.Model):
    MAX_LENGTH = 280
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='social_posts')
    content = models.CharField(max_length=MAX_LENGTH, blank=True)
    book = models.ForeignKey(Book, on_delete=models.SET_NULL, null=True, blank=True, related_name='social_posts')
    catalog_book = models.ForeignKey(CatalogBook, on_delete=models.SET_NULL, null=True, blank=True, related_name='social_posts')
    image_url = models.URLField(blank=True)
    quoted_post = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='quote_posts')
    hidden = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['author', '-created_at']), models.Index(fields=['-created_at'])]

    def __str__(self):
        return f'{self.author.username}: {self.content[:40]}'


class PostLike(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='liked_posts')
    post = models.ForeignKey(SocialPost, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'post'], name='unique_post_like')]


class PostComment(models.Model):
    post = models.ForeignKey(SocialPost, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='post_comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    content = models.CharField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    hidden = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']
        indexes = [models.Index(fields=['post', 'created_at'])]


class PostRepost(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reposts')
    post = models.ForeignKey(SocialPost, on_delete=models.CASCADE, related_name='reposts')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'post'], name='unique_post_repost')]


class SavedPost(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_social_posts')
    post = models.ForeignKey(SocialPost, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'post'], name='unique_saved_post')]


class Notification(models.Model):
    FOLLOW = 'follow'
    LIKE = 'like'
    COMMENT = 'comment'
    REPOST = 'repost'
    RECOMMENDATION = 'recommendation'
    MENTION = 'mention'
    BOOK_PUBLISHED = 'book_published'
    CHAPTER_PUBLISHED = 'chapter_published'
    SUBSCRIPTION = 'subscription'
    PAYMENT_FAILED = 'payment_failed'
    SUBSCRIPTION_EXPIRED = 'subscription_expired'
    EARNING_CREATED = 'earning_created'
    WITHDRAWAL_REQUESTED = 'withdrawal_requested'
    WITHDRAWAL_APPROVED = 'withdrawal_approved'
    WITHDRAWAL_REJECTED = 'withdrawal_rejected'
    PAYMENT_RECEIVED = 'payment_received'
    WRITER_APPROVED = 'writer_approved'
    WRITER_REJECTED = 'writer_rejected'
    TYPES = [
        (FOLLOW, 'Follow'),
        (LIKE, 'Like'),
        (COMMENT, 'Comment'),
        (REPOST, 'Repost'),
        (RECOMMENDATION, 'Recommendation'),
        (MENTION, 'Mention'),
        (BOOK_PUBLISHED, 'Book published'),
        (CHAPTER_PUBLISHED, 'Chapter published'),
        (SUBSCRIPTION, 'Subscription updated'),
        (PAYMENT_FAILED, 'Payment failed'),
        (SUBSCRIPTION_EXPIRED, 'Subscription expired'),
        (EARNING_CREATED, 'Writer earning created'),
        (WITHDRAWAL_REQUESTED, 'Withdrawal requested'),
        (WITHDRAWAL_APPROVED, 'Withdrawal approved'),
        (WITHDRAWAL_REJECTED, 'Withdrawal rejected'),
        (PAYMENT_RECEIVED, 'Payment received'),
        (WRITER_APPROVED, 'Writer application approved'),
        (WRITER_REJECTED, 'Writer application rejected'),
    ]

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_notifications')
    notification_type = models.CharField(max_length=24, choices=TYPES)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    post = models.ForeignKey(SocialPost, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    message = models.CharField(max_length=280, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['recipient', 'is_read', '-created_at'])]


class BookRecommendation(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_recommendations')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_recommendations')
    book = models.ForeignKey(Book, on_delete=models.SET_NULL, null=True, blank=True, related_name='recommendations')
    catalog_book = models.ForeignKey(CatalogBook, on_delete=models.SET_NULL, null=True, blank=True, related_name='recommendations')
    message = models.CharField(max_length=280, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class UserBlock(models.Model):
    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blocks_created')
    blocked = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blocked_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['blocker', 'blocked'], name='unique_user_block')]


class UserMute(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mutes_created')
    muted = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='muted_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'muted'], name='unique_user_mute')]


class ContentReport(models.Model):
    SPAM = 'spam'
    HARASSMENT = 'harassment'
    COPYRIGHT = 'copyright'
    MISINFORMATION = 'misinformation'
    INAPPROPRIATE = 'inappropriate'
    OTHER = 'other'
    REASONS = [(SPAM, 'Spam'), (HARASSMENT, 'Harassment'), (COPYRIGHT, 'Copyright violation'), (MISINFORMATION, 'Misinformation'), (INAPPROPRIATE, 'Inappropriate content'), (OTHER, 'Other')]

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports_created')
    post = models.ForeignKey(SocialPost, on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
    book = models.ForeignKey('Book', on_delete=models.SET_NULL, null=True, blank=True, related_name='content_reports')
    chapter = models.ForeignKey('Chapter', on_delete=models.SET_NULL, null=True, blank=True, related_name='content_reports')
    reported_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='reports_received')
    reason = models.CharField(max_length=24, choices=REASONS)
    details = models.TextField(blank=True)
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class Promotion(models.Model):
    DRAFT = 'draft'
    SCHEDULED = 'scheduled'
    PUBLISHED = 'published'
    EXPIRED = 'expired'
    ARCHIVED = 'archived'
    STATUS_CHOICES = [(DRAFT, 'Draft'), (SCHEDULED, 'Scheduled'), (PUBLISHED, 'Published'), (EXPIRED, 'Expired'), (ARCHIVED, 'Archived')]
    WRITING = 'writing'
    COMPETITION = 'competition'
    AWARDS = 'awards'
    PLATFORM = 'platform'
    CATEGORY_CHOICES = [(WRITING, 'Writing'), (COMPETITION, 'Competition'), (AWARDS, 'Awards'), (PLATFORM, 'Platform news')]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    banner = models.ImageField(upload_to='promotions/', blank=True)
    category = models.CharField(max_length=24, choices=CATEGORY_CHOICES, default=PLATFORM)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=DRAFT, db_index=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    rules = models.TextField(blank=True)
    eligibility = models.TextField(blank=True)
    call_to_action = models.CharField(max_length=80, blank=True)
    destination_url = models.URLField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='promotions_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-starts_at', '-created_at']
        indexes = [models.Index(fields=['status', '-starts_at'])]

    def __str__(self):
        return self.title


class Competition(models.Model):
    DRAFT = 'draft'
    OPEN = 'open'
    CLOSED = 'closed'
    JUDGING = 'judging'
    COMPLETED = 'completed'
    STATUS_CHOICES = [(DRAFT, 'Draft'), (OPEN, 'Open'), (CLOSED, 'Closed'), (JUDGING, 'Judging'), (COMPLETED, 'Completed')]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    banner = models.ImageField(upload_to='competitions/', blank=True)
    rules = models.TextField()
    eligibility = models.TextField(blank=True)
    submission_requirements = models.TextField(blank=True)
    prizes = models.TextField(blank=True)
    opens_at = models.DateTimeField()
    closes_at = models.DateTimeField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=DRAFT, db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='competitions_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-opens_at']

    def __str__(self):
        return self.title


class CompetitionEntry(models.Model):
    SUBMITTED = 'submitted'
    SHORTLISTED = 'shortlisted'
    WINNER = 'winner'
    REJECTED = 'rejected'
    STATUS_CHOICES = [(SUBMITTED, 'Submitted'), (SHORTLISTED, 'Shortlisted'), (WINNER, 'Winner'), (REJECTED, 'Rejected')]

    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name='entries')
    writer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='competition_entries')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='competition_entries')
    statement = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=SUBMITTED)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['competition', 'writer', 'book'], name='unique_competition_book_entry')]
        ordering = ['-submitted_at']


class Award(models.Model):
    title = models.CharField(max_length=200)
    year = models.PositiveIntegerField()
    description = models.TextField(blank=True)
    announcement = models.TextField(blank=True)
    is_published = models.BooleanField(default=False, db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='awards_created')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-year', 'title']
        constraints = [models.UniqueConstraint(fields=['title', 'year'], name='unique_award_title_year')]

    def __str__(self):
        return f'{self.title} ({self.year})'


class AwardCategory(models.Model):
    award = models.ForeignKey(Award, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['award', 'name'], name='unique_award_category')]
        ordering = ['name']

    def __str__(self):
        return f'{self.award}: {self.name}'


class AwardNominee(models.Model):
    category = models.ForeignKey(AwardCategory, on_delete=models.CASCADE, related_name='nominees')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, null=True, blank=True, related_name='award_nominations')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='award_nominations')
    is_winner = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['category', 'book', 'author'], name='unique_award_nominee')]


class CriticProfile(models.Model):
    PENDING = 'pending'
    APPROVED = 'approved'
    SUSPENDED = 'suspended'
    STATUS_CHOICES = [(PENDING, 'Pending'), (APPROVED, 'Approved'), (SUSPENDED, 'Suspended')]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='critic_profile')
    bio = models.TextField(blank=True)
    genres = models.ManyToManyField('Genre', blank=True, related_name='critics')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=PENDING, db_index=True)
    reputation = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.get_username()


class CriticApplication(models.Model):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    STATUS_CHOICES = [(PENDING, 'Pending'), (APPROVED, 'Approved'), (REJECTED, 'Rejected')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='critic_applications')
    experience = models.TextField()
    genres_of_interest = models.CharField(max_length=500)
    writing_sample = models.TextField()
    preferred_categories = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=PENDING, db_index=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='critic_applications_reviewed')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class ReviewAssignment(models.Model):
    REQUESTED = 'requested'
    ACCEPTED = 'accepted'
    SUBMITTED = 'submitted'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    STATUS_CHOICES = [(REQUESTED, 'Requested'), (ACCEPTED, 'Accepted'), (SUBMITTED, 'Submitted'), (APPROVED, 'Approved'), (REJECTED, 'Rejected')]

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='critic_assignments')
    critic = models.ForeignKey(CriticProfile, on_delete=models.PROTECT, related_name='assignments')
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='review_assignments_created')
    payout_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    due_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=REQUESTED, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['book', 'critic'], name='unique_book_critic_assignment')]


class CriticReview(models.Model):
    assignment = models.OneToOneField(ReviewAssignment, on_delete=models.CASCADE, related_name='review')
    overall = models.TextField()
    story_quality = models.PositiveSmallIntegerField(default=3)
    characters = models.PositiveSmallIntegerField(default=3)
    world_building = models.PositiveSmallIntegerField(default=3)
    writing_style = models.PositiveSmallIntegerField(default=3)
    plot = models.PositiveSmallIntegerField(default=3)
    originality = models.PositiveSmallIntegerField(default=3)
    strengths = models.TextField(blank=True)
    improvements = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-submitted_at']


class CriticEarning(models.Model):
    PENDING = 'pending'
    APPROVED = 'approved'
    PAID = 'paid'
    STATUS_CHOICES = [(PENDING, 'Pending'), (APPROVED, 'Approved'), (PAID, 'Paid')]

    critic = models.ForeignKey(CriticProfile, on_delete=models.PROTECT, related_name='earnings')
    assignment = models.OneToOneField(ReviewAssignment, on_delete=models.PROTECT, related_name='earning')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']


class ImportedBook(models.Model):
    """
    Tracks a book that has been imported and stored locally.
    
    Links a CatalogBook (discovered book) to its local storage
    and provides metadata about the import process.
    """
    
    EPUB_FORMAT = 'epub'
    PDF_FORMAT = 'pdf'
    TXT_FORMAT = 'txt'
    FORMAT_CHOICES = [
        (EPUB_FORMAT, 'EPUB'),
        (PDF_FORMAT, 'PDF'),
        (TXT_FORMAT, 'Plain Text'),
    ]
    
    DISCOVERED = 'discovered'
    QUEUED = 'queued'
    DOWNLOADING = 'downloading'
    PROCESSING = 'processing'
    IMPORTED = 'imported'
    FAILED = 'failed'
    REJECTED = 'rejected'
    STATUS_CHOICES = [
        (DISCOVERED, 'Discovered'),
        (QUEUED, 'Queued for Import'),
        (DOWNLOADING, 'Downloading'),
        (PROCESSING, 'Processing'),
        (IMPORTED, 'Imported'),
        (FAILED, 'Failed'),
        (REJECTED, 'Rejected'),
    ]
    
    catalog_book = models.OneToOneField(CatalogBook, on_delete=models.CASCADE, related_name='imported_copy')
    book_source = models.ForeignKey(BookSource, on_delete=models.PROTECT, related_name='imported_books')
    
    # Storage info
    format = models.CharField(max_length=16, choices=FORMAT_CHOICES, default=EPUB_FORMAT)
    file_size = models.BigIntegerField(default=0, help_text="File size in bytes")
    checksum = models.CharField(max_length=64, blank=True, help_text="SHA256 checksum of file")
    
    # Import status
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=DISCOVERED)
    import_error = models.TextField(blank=True, help_text="Error message if import failed")
    
    # Tracking
    imported_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Links to extended book info
    linked_book = models.ForeignKey(Book, on_delete=models.SET_NULL, null=True, blank=True, related_name='imported_from_catalog', help_text="Link to a Book model if also published internally")
    
    class Meta:
        ordering = ['-imported_at', '-created_at']
        indexes = [
            models.Index(fields=['status', '-imported_at']),
            models.Index(fields=['catalog_book']),
        ]
    
    def __str__(self):
        return f'{self.catalog_book.title} (Imported {self.get_format_display()})'
    
    @property
    def is_available_to_read(self):
        return self.status == self.IMPORTED and self.file_exists
    
    @property
    def file_exists(self):
        if hasattr(self, 'file') and self.file:
            return self.file.file_exists
        return False


class Subscription(models.Model):
    MONTHLY = 'monthly'
    PLAN_CHOICES = [(MONTHLY, 'Monthly reading access')]
    NGN = 'NGN'
    USDT = 'USDT'
    BTC = 'BTC'
    ETH = 'ETH'
    CURRENCY_CHOICES = [(NGN, 'Naira'), (USDT, 'USDT'), (BTC, 'Bitcoin'), (ETH, 'Ethereum')]
    ACTIVE = 'active'
    EXPIRED = 'expired'
    CANCELLED = 'cancelled'
    STATUS_CHOICES = [(ACTIVE, 'Active'), (EXPIRED, 'Expired'), (CANCELLED, 'Cancelled')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.CharField(max_length=24, choices=PLAN_CHOICES, default=MONTHLY)
    currency = models.CharField(max_length=8, choices=CURRENCY_CHOICES, default=NGN)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=ACTIVE)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-ends_at']
        indexes = [models.Index(fields=['user', 'status', '-ends_at'])]

    @property
    def is_current(self):
        return self.status == self.ACTIVE and self.starts_at <= timezone.now() < self.ends_at


class PaymentTransaction(models.Model):
    PENDING = 'pending'
    VERIFIED = 'verified'
    FAILED = 'failed'
    STATUS_CHOICES = [(PENDING, 'Pending'), (VERIFIED, 'Verified'), (FAILED, 'Failed')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payment_transactions')
    currency = models.CharField(max_length=8, choices=Subscription.CURRENCY_CHOICES)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    reference = models.CharField(max_length=120, unique=True)
    provider = models.CharField(max_length=60, default='manual_verification')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=PENDING)
    proof_url = models.URLField(blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class SubscriptionPlan(models.Model):
    MONTHLY = 'monthly'
    YEARLY = 'yearly'
    BILLING_PERIODS = [(MONTHLY, 'Monthly'), (YEARLY, 'Yearly')]

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    billing_period = models.CharField(max_length=16, choices=BILLING_PERIODS)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, choices=Subscription.CURRENCY_CHOICES, default=Subscription.NGN)
    benefits = models.JSONField(default=list, blank=True)
    provider_plan_code = models.CharField(max_length=100, blank=True, help_text='Optional Paystack plan code for automatic renewals.')
    is_active = models.BooleanField(default=True, db_index=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'price']

    def __str__(self):
        return f'{self.name} ({self.get_billing_period_display()})'


class PremiumSubscription(models.Model):
    PENDING = 'pending'
    ACTIVE = 'active'
    CANCELLED = 'cancelled'
    EXPIRED = 'expired'
    STATUSES = [(PENDING, 'Pending'), (ACTIVE, 'Active'), (CANCELLED, 'Cancelled'), (EXPIRED, 'Expired')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='premium_subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='subscriptions')
    status = models.CharField(max_length=16, choices=STATUSES, default=PENDING, db_index=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    provider_subscription_code = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'status', '-ends_at'])]
        constraints = [
            models.UniqueConstraint(
                fields=['user'], condition=models.Q(status='active'), name='unique_active_premium_subscription',
            ),
        ]

    @property
    def is_current(self):
        now = timezone.now()
        return self.status == self.ACTIVE and self.starts_at and self.starts_at <= now and self.ends_at and now < self.ends_at


class MonetizationPayment(models.Model):
    SUBSCRIPTION = 'subscription'
    PURPOSES = [(SUBSCRIPTION, 'Subscription')]
    INITIALIZED = 'initialized'
    PENDING = 'pending'
    SUCCESS = 'success'
    FAILED = 'failed'
    REFUNDED = 'refunded'
    STATUSES = [(INITIALIZED, 'Initialized'), (PENDING, 'Pending'), (SUCCESS, 'Success'), (FAILED, 'Failed'), (REFUNDED, 'Refunded')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='monetization_payments')
    plan = models.ForeignKey(SubscriptionPlan, null=True, blank=True, on_delete=models.PROTECT, related_name='payments')
    subscription = models.ForeignKey(PremiumSubscription, null=True, blank=True, on_delete=models.SET_NULL, related_name='payments')
    purpose = models.CharField(max_length=24, choices=PURPOSES, default=SUBSCRIPTION)
    provider = models.CharField(max_length=32, default='paystack')
    reference = models.CharField(max_length=120, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default=Subscription.NGN)
    status = models.CharField(max_length=16, choices=STATUSES, default=INITIALIZED, db_index=True)
    checkout_url = models.URLField(max_length=1000, blank=True)
    provider_reference = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'status', '-created_at'])]


class WriterProfile(models.Model):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    SUSPENDED = 'suspended'
    STATUSES = [(PENDING, 'Pending'), (APPROVED, 'Approved'), (REJECTED, 'Rejected'), (SUSPENDED, 'Suspended')]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='writer_profile')
    pen_name = models.CharField(max_length=120)
    bio = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=STATUSES, default=PENDING, db_index=True)
    payout_recipient_code = models.CharField(max_length=120, blank=True, help_text='Tokenized payout recipient stored by the configured provider.')
    payout_account_name = models.CharField(max_length=120, blank=True)
    payout_account_last4 = models.CharField(max_length=4, blank=True)
    payout_bank_code = models.CharField(max_length=32, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='writer_profiles_reviewed')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.pen_name


class MonetizationConfig(models.Model):
    PER_READ = 'per_read'
    ENGAGEMENT = 'read_engagement'
    EARNING_FORMULAS = [(PER_READ, 'Per qualifying read'), (ENGAGEMENT, 'Read plus engagement bonus')]

    earning_formula = models.CharField(max_length=24, choices=EARNING_FORMULAS, default=PER_READ)
    earning_per_read = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    engagement_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    minimum_read_seconds = models.PositiveSmallIntegerField(default=30)
    minimum_withdrawal = models.DecimalField(max_digits=12, decimal_places=2, default=5000)
    ad_frequency_cap = models.PositiveSmallIntegerField(default=3)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return 'Monetization settings'


class ReaderSession(models.Model):
    token = models.UUIDField(default=uuid4, unique=True, editable=False)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reader_sessions')
    chapter = models.ForeignKey(Chapter, null=True, blank=True, on_delete=models.CASCADE, related_name='reader_sessions')
    reader = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='verified_reader_sessions')
    identity_hash = models.CharField(max_length=64)
    read_date = models.DateField(default=timezone.localdate)
    started_at = models.DateTimeField(auto_now_add=True)
    qualified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['chapter', 'identity_hash', 'read_date'], name='unique_daily_chapter_reader_session')]
        indexes = [models.Index(fields=['book', 'qualified_at'])]


class WriterEarning(models.Model):
    PENDING = 'pending'
    AVAILABLE = 'available'
    WITHDRAWN = 'withdrawn'
    REVERSED = 'reversed'
    STATUSES = [(PENDING, 'Pending'), (AVAILABLE, 'Available'), (WITHDRAWN, 'Withdrawn'), (REVERSED, 'Reversed')]
    QUALIFYING_READ = 'qualifying_read'
    ENGAGEMENT = 'engagement'
    ACTIVITY_TYPES = [(QUALIFYING_READ, 'Qualifying read'), (ENGAGEMENT, 'Engagement bonus')]

    writer = models.ForeignKey(WriterProfile, on_delete=models.PROTECT, related_name='earnings')
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name='writer_earnings')
    chapter = models.ForeignKey(Chapter, null=True, blank=True, on_delete=models.PROTECT, related_name='writer_earnings')
    reader_session = models.OneToOneField(ReaderSession, null=True, blank=True, on_delete=models.PROTECT, related_name='earning')
    activity_type = models.CharField(max_length=24, choices=ACTIVITY_TYPES, default=QUALIFYING_READ)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default=Subscription.NGN)
    status = models.CharField(max_length=16, choices=STATUSES, default=PENDING, db_index=True)
    reference = models.UUIDField(default=uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    available_at = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['writer', 'status', '-created_at'])]


class WriterWithdrawal(models.Model):
    PENDING = 'pending'
    PROCESSING = 'processing'
    PAID = 'paid'
    REJECTED = 'rejected'
    FAILED = 'failed'
    STATUSES = [(PENDING, 'Pending'), (PROCESSING, 'Processing'), (PAID, 'Paid'), (REJECTED, 'Rejected'), (FAILED, 'Failed')]

    writer = models.ForeignKey(WriterProfile, on_delete=models.PROTECT, related_name='withdrawals')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default=Subscription.NGN)
    status = models.CharField(max_length=16, choices=STATUSES, default=PENDING, db_index=True)
    reference = models.UUIDField(default=uuid4, unique=True, editable=False)
    provider_reference = models.CharField(max_length=120, blank=True)
    failure_reason = models.TextField(blank=True)
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='writer_withdrawals_processed')
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-requested_at']
        indexes = [models.Index(fields=['status', '-requested_at'])]


class WithdrawalAllocation(models.Model):
    withdrawal = models.ForeignKey(WriterWithdrawal, on_delete=models.PROTECT, related_name='allocations')
    earning = models.ForeignKey(WriterEarning, on_delete=models.PROTECT, related_name='withdrawal_allocations')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['withdrawal', 'earning'], name='unique_withdrawal_earning_allocation')]


class Advertisement(models.Model):
    BANNER = 'banner'
    IN_APP = 'in_app'
    INTERSTITIAL = 'interstitial'
    SPONSORED = 'sponsored'
    AD_TYPES = [(BANNER, 'Banner'), (IN_APP, 'In-app'), (INTERSTITIAL, 'Interstitial'), (SPONSORED, 'Sponsored content')]
    SITE_BANNER = 'site_banner'
    READER_INLINE = 'reader_inline'
    HOME_FEATURED = 'home_featured'
    PLACEMENTS = [(SITE_BANNER, 'Site banner'), (READER_INLINE, 'Reader inline'), (HOME_FEATURED, 'Home feature')]

    title = models.CharField(max_length=180)
    image = models.ImageField(upload_to='advertisements/', blank=True)
    destination_url = models.URLField(max_length=1000)
    ad_type = models.CharField(max_length=16, choices=AD_TYPES, default=BANNER)
    placement = models.CharField(max_length=24, choices=PLACEMENTS, default=SITE_BANNER, db_index=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False, db_index=True)
    estimated_revenue_per_click = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class AdImpression(models.Model):
    ad = models.ForeignKey(Advertisement, on_delete=models.CASCADE, related_name='impressions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='ad_impressions')
    session_hash = models.CharField(max_length=64)
    path = models.CharField(max_length=500)
    impression_key = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['ad', '-created_at'])]


class AdClick(models.Model):
    ad = models.ForeignKey(Advertisement, on_delete=models.CASCADE, related_name='clicks')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='ad_clicks')
    session_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['ad', '-created_at'])]


class ReadingChallenge(models.Model):
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    target_books = models.PositiveIntegerField(default=1)
    prize_pool = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    prize_currency = models.CharField(max_length=8, choices=Subscription.CURRENCY_CHOICES, default=Subscription.NGN)
    referral_prize = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-starts_at']


class ChallengeEntry(models.Model):
    challenge = models.ForeignKey(ReadingChallenge, on_delete=models.CASCADE, related_name='entries')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='challenge_entries')
    books_completed = models.PositiveIntegerField(default=0)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['challenge', 'user'], name='unique_challenge_entry')]


class ChallengeReferral(models.Model):
    challenge = models.ForeignKey(ReadingChallenge, on_delete=models.CASCADE, related_name='referrals')
    referrer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='challenge_referrals')
    referred_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='challenge_referrals_received')
    qualified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['challenge', 'referred_user'], name='unique_challenge_referral')]


class PrizeAward(models.Model):
    WINNER = 'winner'
    REFERRAL = 'referral'
    AWARD_TYPES = [(WINNER, 'Challenge winner'), (REFERRAL, 'Challenge referral')]
    PENDING = 'pending'
    PAID = 'paid'
    STATUS_CHOICES = [(PENDING, 'Pending'), (PAID, 'Paid')]

    challenge = models.ForeignKey(ReadingChallenge, on_delete=models.CASCADE, related_name='prize_awards')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='prize_awards')
    award_type = models.CharField(max_length=16, choices=AWARD_TYPES)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=8, choices=Subscription.CURRENCY_CHOICES)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=PENDING)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class BookFile(models.Model):
    """
    Stores the path and metadata of an actual imported book file.
    """
    
    imported_book = models.OneToOneField(ImportedBook, on_delete=models.CASCADE, related_name='file')
    
    # File storage
    file_path = models.CharField(max_length=500, help_text="Relative path in media storage")
    file_size = models.BigIntegerField(default=0)
    checksum = models.CharField(max_length=64, blank=True)
    
    # Metadata (populated after processing)
    page_count = models.PositiveIntegerField(null=True, blank=True, help_text="For PDF, approximate page count")
    chapters_count = models.PositiveIntegerField(null=True, blank=True, help_text="For EPUB, number of chapters extracted")
    
    # Processing
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f'File: {self.file_path}'
    
    @property
    def file_exists(self):
        from django.core.files.storage import default_storage
        return default_storage.exists(self.file_path)


class ImportJob(models.Model):
    """
    Tracks the lifecycle of a book import operation.
    Supports async/background job execution.
    """
    
    PENDING = 'pending'
    PROCESSING = 'processing'
    SUCCESS = 'success'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (PROCESSING, 'Processing'),
        (SUCCESS, 'Success'),
        (FAILED, 'Failed'),
        (CANCELLED, 'Cancelled'),
    ]
    
    imported_book = models.ForeignKey(ImportedBook, on_delete=models.CASCADE, related_name='import_jobs')
    
    # Job tracking
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=PENDING)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Progress
    progress_percent = models.IntegerField(default=0)
    current_step = models.CharField(max_length=100, blank=True, help_text="Current step in import process")
    
    # Error tracking
    error_message = models.TextField(blank=True)
    error_traceback = models.TextField(blank=True)
    
    # Retry info
    retry_count = models.PositiveIntegerField(default=0)
    last_retry_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='import_jobs_initiated')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['imported_book', '-created_at']),
        ]
    
    def __str__(self):
        return f'Job for {self.imported_book.catalog_book.title} - {self.status}'


class ReadingBookmark(models.Model):
    """
    Allows users to bookmark positions in imported books.
    """
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reading_bookmarks')
    imported_book = models.ForeignKey(ImportedBook, on_delete=models.CASCADE, related_name='bookmarks')
    
    # Position in book
    chapter_identifier = models.CharField(max_length=250, blank=True, help_text="For EPUB: spine item; for PDF: page number")
    position_info = models.JSONField(default=dict, help_text="Format-specific position data")
    
    # Metadata
    label = models.CharField(max_length=250, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['chapter_identifier', '-created_at']
        indexes = [
            models.Index(fields=['user', 'imported_book']),
        ]
    
    def __str__(self):
        return f'{self.user.username}: {self.imported_book.catalog_book.title} - Bookmark'


class ReadingHighlight(models.Model):
    """
    Allows users to highlight and annotate text in imported books.
    """
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reading_highlights')
    imported_book = models.ForeignKey(ImportedBook, on_delete=models.CASCADE, related_name='highlights')
    
    # Highlighted content
    text_excerpt = models.TextField(help_text="The actual highlighted text")
    chapter_identifier = models.CharField(max_length=250, blank=True, help_text="Which chapter/section")
    location_info = models.JSONField(default=dict, help_text="Format-specific location data")
    
    # Annotation
    note = models.TextField(blank=True, help_text="User's note on the highlight")
    color = models.CharField(max_length=16, default='yellow', help_text="Highlight color (yellow, green, blue, pink, etc.)")
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['chapter_identifier', '-created_at']
        indexes = [
            models.Index(fields=['user', 'imported_book']),
        ]
    
    def __str__(self):
        return f'{self.user.username}: Highlight in {self.imported_book.catalog_book.title}'
