# Book Import & Reading System - Architecture Guide

## Overview

The BookClub book import and reading system enables users to discover, import, and read public-domain and open-license books from approved sources without leaving the platform. The system verifies intellectual property rights before importing, downloads books securely, processes EPUB files into chapters, and provides an in-app web-based reader with bookmarks and highlights.

## System Architecture

### High-Level Workflow

```
1. USER SEARCHES FOR BOOK
   ↓
2. PLATFORM SEARCHES LOCAL LIBRARY & EXTERNAL SOURCES
   ↓
3. RESULTS DISPLAYED WITH AVAILABILITY STATUS
   ↓
4. USER SELECTS "IMPORT" OR "READ"
   ↓
5. LICENSE/REDISTRIBUTION ELIGIBILITY VERIFIED
   ↓
6. BOOK DOWNLOADED FROM APPROVED SOURCE
   ↓
7. BOOK IMPORTED TO LOCAL STORAGE
   ↓
8. BOOK OPENED IN PLATFORM READER
   ↓
9. USER READS WITHOUT LEAVING PLATFORM
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Templates)                     │
│  ├─ reader_home.html (Imported books list)                  │
│  ├─ reader.html (EPUB reader with themes & settings)        │
│  └─ reader_error.html (Error handling)                      │
└──────────────────┬────────────────────────────────────────┘
                   │
┌──────────────────┴────────────────────────────────────────┐
│              Views/APIs (import_views.py)                 │
│  ├─ api_book_search() - Search local & external           │
│  ├─ api_import_book() - Initiate import                   │
│  ├─ api_import_status() - Check import progress           │
│  ├─ api_reader_chapter() - Get chapter content            │
│  ├─ api_reading_progress() - Save user progress           │
│  ├─ api_bookmark() - Manage bookmarks                     │
│  └─ api_highlight() - Manage highlights                   │
└──────────────────┬────────────────────────────────────────┘
                   │
┌──────────────────┴────────────────────────────────────────┐
│           Service Layer (services.py)                     │
│  ├─ RightsChecker - Verify copyright status               │
│  ├─ FileValidator - Validate files and checksums          │
│  ├─ BookFileDownloader - Download from approved hosts     │
│  ├─ EPUBProcessor - Parse EPUB files                      │
│  ├─ BookImportService - Orchestrate full import           │
│  └─ BookProvider interface (OpenLibrary, etc.)            │
└──────────────────┬────────────────────────────────────────┘
                   │
┌──────────────────┴────────────────────────────────────────┐
│          Database Models (models.py)                      │
│  ├─ ImportedBook - Imported book metadata                 │
│  ├─ BookFile - File storage information                   │
│  ├─ ImportJob - Import operation tracking                 │
│  ├─ ReadingBookmark - User bookmarks                      │
│  └─ ReadingHighlight - User highlights                    │
└──────────────────┬────────────────────────────────────────┘
                   │
┌──────────────────┴────────────────────────────────────────┐
│            File Storage (Media Directory)                 │
│  └─ books/imported/{provider}/{book_id}/                  │
│     └─ book.{epub|pdf|txt}                                │
└──────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Models

#### ImportedBook
Represents a book that has been imported to local storage.

```python
class ImportedBook(models.Model):
    catalog_book = ForeignKey(CatalogBook)          # Original book metadata
    book_source = ForeignKey(BookSource)            # Source provider info
    status = CharField(choices=[                    # Import workflow status
        ('discovered', 'Discovered'),
        ('queued', 'Queued'),
        ('downloading', 'Downloading'),
        ('processing', 'Processing'),
        ('imported', 'Imported'),
        ('failed', 'Failed'),
        ('rejected', 'Rejected'),
    ])
    format = CharField(choices=['epub', 'pdf', 'txt'])
    file_size = BigIntegerField()                   # Bytes
    checksum = CharField()                          # SHA256 hex
    import_error = TextField()                      # Error details if failed
    imported_at = DateTimeField()
```

#### BookFile
Physical file storage information with content metadata.

```python
class BookFile(models.Model):
    imported_book = OneToOneField(ImportedBook)
    file_path = CharField()                         # Relative to MEDIA_ROOT
    checksum = CharField()                          # SHA256 for integrity
    chapters_count = IntegerField()                 # For EPUB files
    processed_at = DateTimeField()                  # When EPUB was parsed
```

#### ImportJob
Tracks lifecycle of individual import operations.

```python
class ImportJob(models.Model):
    imported_book = ForeignKey(ImportedBook)
    initiated_by = ForeignKey(User)
    status = CharField(choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ])
    progress_percent = IntegerField()               # 0-100
    current_step = CharField()                      # Which phase
    error_message = TextField()
    error_traceback = TextField()
    retry_count = IntegerField()
```

#### ReadingBookmark
User-specific bookmarks within imported books.

```python
class ReadingBookmark(models.Model):
    user = ForeignKey(User)
    imported_book = ForeignKey(ImportedBook)
    chapter_identifier = CharField()                # Chapter title/num
    label = CharField()                             # Bookmark label
    position_info = JSONField()                     # Chapter position data
```

#### ReadingHighlight
User-specific text highlights with optional notes.

```python
class ReadingHighlight(models.Model):
    user = ForeignKey(User)
    imported_book = ForeignKey(ImportedBook)
    chapter_identifier = CharField()
    text_excerpt = TextField()                      # Highlighted text
    note = TextField()                              # Optional user note
    color = CharField()                             # Highlight color
    location_info = JSONField()                     # Position in chapter
```

### 2. Service Layer

#### RightsChecker
Verifies intellectual property rights before import.

```python
class RightsChecker:
    ALLOWED_COPYRIGHT_STATUSES = [
        CatalogBook.PUBLIC_DOMAIN_STATUS,           # Public domain
        CatalogBook.OPEN_LICENSE,                   # CC-BY, CC-0, etc.
        CatalogBook.AUTHORIZED,                     # Rights-holder approved
    ]
    
    @staticmethod
    def can_import_book(catalog_book, book_source):
        """Returns (bool, reason_string)"""
        # Verify copyright status
        # Verify full text is available
        # Verify redistribution rights
        # Verify no DRM/restrictions
    
    @staticmethod
    def verify_source_eligibility(provider_name):
        """Check if provider is enabled in ProviderStatus"""
```

#### FileValidator
Validates files for security and integrity before import.

```python
class FileValidator:
    MAX_FILE_SIZE = 524288000  # 500 MB
    ALLOWED_FORMATS = ['epub', 'pdf', 'txt']
    
    @staticmethod
    def validate_file_format(file_path):
        """Detect format from content, not extension"""
        # EPUB: Check ZIP structure with mimetype
        # PDF: Check %PDF header
        # TXT: Verify UTF-8 encoding
    
    @staticmethod
    def calculate_checksum(file_path):
        """SHA256 for integrity verification"""
```

#### BookFileDownloader
Safely downloads books from approved sources.

```python
class BookFileDownloader:
    APPROVED_HOSTS = {
        'gutenberg.org',
        'standardebooks.org',
        'archive.org',
        # Expandable via BOOK_IMPORT_APPROVED_HOSTS setting
    }
    
    def download_file(self, url, provider, book_id):
        """
        - Validates URL against approved hosts
        - Chunked download with size limit
        - Returns (temp_file_path, detected_format)
        - Raises FileDownloadError
        """
```

#### EPUBProcessor
Extracts and processes EPUB content.

```python
class EPUBProcessor:
    @staticmethod
    def validate_epub(file_path):
        """Check file is valid EPUB"""
    
    @staticmethod
    def extract_metadata(file_path):
        """Get title, authors, language from EPUB"""
    
    @staticmethod
    def extract_chapters(file_path):
        """
        - Parse EPUB structure
        - Sanitize HTML with bleach
        - Remove scripts, iframes, etc.
        - Return list of chapters with content
        """
```

#### BookImportService
Orchestrates complete import workflow.

```python
class BookImportService:
    @staticmethod
    def import_book(user, catalog_book, book_source, force=False):
        """
        1. Verify rights (RightsChecker)
        2. Download file (BookFileDownloader)
        3. Validate file (FileValidator)
        4. Calculate checksum
        5. Store permanently
        6. Extract chapters (EPUBProcessor)
        7. Create ImportJob with status
        
        Returns ImportedBook instance
        Raises RightsCheckError, FileDownloadError
        """
```

### 3. API Endpoints

#### POST /api/import/search/
Search books in local catalog and external providers.

**Request:**
```json
{
    "q": "search query",
    "offset": 0,
    "limit": 20
}
```

**Response:**
```json
{
    "query": "search query",
    "local_results": [...],
    "external_results": {...providers...},
    "total": 100
}
```

#### POST /api/import/
Initiate book import.

**Request:**
```json
{
    "catalog_book_id": 123,
    "book_source_id": 456
}
```

**Response:**
```json
{
    "success": true,
    "imported_book_id": 789,
    "status": "queued",
    "message": "Import queued"
}
```

#### GET /api/import/{id}/status/
Check import progress.

**Response:**
```json
{
    "status": "processing",
    "progress": 45,
    "current_step": "Downloading...",
    "error": null
}
```

#### GET /api/imported/{id}/chapter/{index}/
Get chapter content for reader.

**Response:**
```json
{
    "title": "Chapter 1",
    "content": "<h1>Chapter 1</h1><p>...</p>",
    "prev_available": false,
    "next_available": true
}
```

#### POST /api/imported/{id}/progress/
Save reading position.

**Request:**
```json
{
    "chapter": "1",
    "progress": 50
}
```

#### POST /api/imported/{id}/bookmark/
Create bookmark.

**Request:**
```json
{
    "chapter": "1",
    "label": "Important passage"
}
```

#### POST /api/imported/{id}/highlight/
Create highlight.

**Request:**
```json
{
    "chapter": "1",
    "text": "highlighted text",
    "note": "optional note",
    "color": "#ffff00"
}
```

### 4. Configuration

All settings in `bookclub/settings.py`:

```python
# Enable/disable book import system
BOOK_IMPORT_ENABLED = os.getenv('BOOK_IMPORT_ENABLED', 'True') == 'True'

# Maximum file size in bytes
BOOK_IMPORT_MAX_FILE_SIZE = int(os.getenv(
    'BOOK_IMPORT_MAX_FILE_SIZE',
    524288000  # 500 MB
))

# Allowed file formats
BOOK_IMPORT_ALLOWED_FORMATS = ['epub', 'txt', 'pdf']

# Approved hosts for downloads
BOOK_IMPORT_APPROVED_HOSTS = set(
    os.getenv('BOOK_IMPORT_APPROVED_HOSTS', '').split(',')
    if os.getenv('BOOK_IMPORT_APPROVED_HOSTS')
    else ['gutenberg.org', 'standardebooks.org', 'archive.org']
)

# Provider enable/disable flags
BOOK_PROVIDERS_ENABLED = {
    'open_library': os.getenv('PROVIDER_OPEN_LIBRARY_ENABLED', 'True') == 'True',
    'internet_archive': os.getenv('PROVIDER_ARCHIVE_ENABLED', 'True') == 'True',
    'gutenberg': os.getenv('PROVIDER_GUTENBERG_ENABLED', 'True') == 'True',
    'standard_ebooks': os.getenv('PROVIDER_STANDARD_EBOOKS_ENABLED', 'True') == 'True',
}

# Cache search results
BOOK_SEARCH_CACHE_TIMEOUT = 3600  # 1 hour
```

## Security Considerations

### 1. Host Whitelist
Only downloads from approved domains:
- `gutenberg.org` - Project Gutenberg (public domain)
- `standardebooks.org` - Standard Ebooks (carefully curated)
- `archive.org` - Internet Archive (various licenses)

**Configuration via environment:**
```bash
BOOK_IMPORT_APPROVED_HOSTS="gutenberg.org,standardebooks.org,archive.org,example.com"
```

### 2. Rights Verification
Only imports books with eligible copyright status:
- **PUBLIC_DOMAIN_STATUS**: Published before copyright period
- **OPEN_LICENSE**: CC-0, CC-BY, similar
- **AUTHORIZED**: Rights holder approval

Unknown, restricted, or copyrighted books are automatically rejected.

### 3. File Validation
- **Format detection** from content, not extension
- **Size limits** enforce 500 MB default maximum
- **Checksum verification** ensures integrity (SHA256)
- **Type-specific validation** (EPUB ZIP structure, PDF headers, UTF-8 text)

### 4. HTML Sanitization
EPUB content is sanitized using bleach to prevent:
- JavaScript injection
- Iframe embedding
- Event handlers
- Dangerous attributes

Whitelist includes:
- Block elements: `p, div, section, article, h1-h6, blockquote, ul, ol, li, dl, dt, dd`
- Inline elements: `span, em, strong, a, br, img, code, pre`
- Attributes: `href, src, alt, class, id, title`

### 5. SSRF/Path Traversal Prevention
- URL validation against whitelist
- File paths normalized and verified to stay within media directory
- No access to system files or parent directories

## Provider Integration

### Adding a New Provider

1. **Extend BookProvider interface** in existing providers:

```python
class MyCustomProvider(BookProvider):
    PROVIDER_NAME = 'my_provider'
    PROVIDER_DISPLAY_NAME = 'My Book Provider'
    
    def search_books(self, query, offset=0, limit=20):
        """Return (results, total_count)"""
        # Make API calls to provider
        # Return list of DiscoveredBook instances
        pass
    
    def get_reading_url(self, book):
        """Return direct download URL for book"""
        pass
    
    def get_copyright_status(self, book):
        """Return copyright status"""
        pass
```

2. **Register in CatalogService** (books/services.py):

```python
class CatalogService:
    PROVIDERS = [
        OpenLibraryProvider(),
        InternetArchiveProvider(),
        GutenbergProvider(),
        StandardEbooksProvider(),
        MyCustomProvider(),  # Add here
    ]
```

3. **Update settings** if custom approval/configuration needed:

```python
BOOK_IMPORT_APPROVED_HOSTS.add('my-provider.com')
```

### Example: Integration for new provider

See [PROVIDERS.md](./PROVIDERS.md) for detailed walkthrough.

## Testing

Tests located in `books/test_import.py` covering:

- **File validation**: Size limits, format detection, checksums
- **Rights verification**: Copyright status, eligibility checks
- **Download security**: Host whitelist, file size limits, URL validation
- **Import workflow**: Success, duplicates, error handling
- **Reader API**: Chapter loading, progress saving, bookmarks/highlights
- **EPUB processing**: Valid/invalid EPUB handling
- **Provider integration**: Search, download, metadata extraction

### Running Tests

```bash
python manage.py test books.test_import
```

### Test Coverage

- Provider search and retrieval
- Rights eligibility verification
- File validation and security
- Complete import workflow
- Reader functionality
- User progress tracking
- Error handling and recovery

## Admin Interface

Administrative controls for:
- Viewing imported books with status indicators
- Managing import jobs and retrying failed imports
- Viewing import errors with detailed tracebacks
- Provider status management
- Storage statistics
- User reading activity

Access via `/admin/books/importedbook/` after staff login.

## Troubleshooting

### Import Fails with "Rights Not Eligible"
- Verify copyright status of book in CatalogBook model
- Check that book has `full_text_available = True`
- Ensure source provider is enabled in ProviderStatus

### Download Fails with "Unapproved Host"
- Verify domain is in BOOK_IMPORT_APPROVED_HOSTS
- Add domain to environment: `BOOK_IMPORT_APPROVED_HOSTS="existing.com,new.com"`
- Check that provider implements correct download URL

### File Too Large
- Check BOOK_IMPORT_MAX_FILE_SIZE setting (default 500 MB)
- Consider splitting book or finding different format
- Increase limit via environment: `BOOK_IMPORT_MAX_FILE_SIZE=1048576000`

### EPUB Processing Fails
- Verify EPUB file structure with `EPUBProcessor.validate_epub()`
- Check for corrupt or non-standard EPUB structure
- Ensure lxml and ebooklib are installed correctly

### Reader Shows Blank Chapters
- Verify ImportedBook.status is 'imported'
- Check BookFile.processed_at is set
- Ensure chapters were successfully extracted by EPUBProcessor
- Check browser console for JavaScript errors

## Performance Considerations

### Caching
- Book search results cached 1 hour (configurable)
- Provider API responses cached per query

### Database Indexes
- `ImportedBook`: status, imported_at, catalog_book
- `ImportJob`: status, created_at, imported_book
- `ReadingBookmark`: user, imported_book
- `ReadingHighlight`: user, imported_book

### File Storage
- Books stored in MEDIA_ROOT/books/imported/{provider}/{book_id}/
- Organize by provider and book ID for efficient lookup
- Consider using CloudFront or CDN for file delivery

## Future Enhancements

1. **PDF text extraction** for PDF books
2. **Audiobook support** with playback interface
3. **Social reading features** (shared highlights, book clubs)
4. **Offline reading** with sync on reconnect
5. **Reading recommendations** based on user library
6. **Author/publisher verification** for rights checks
7. **Multiple language support** in EPUB processing
8. **OCR for scanned books** with text extraction
9. **Book series management** with reading order
10. **Reading statistics** (words read, time spent, pace)
