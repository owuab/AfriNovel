# Book Import System Configuration

This document describes all configuration options for the book import system.

## Environment Variables

### Core Import Settings

#### BOOK_IMPORT_ENABLED
**Default:** `True`  
**Type:** Boolean  
**Description:** Enable or disable the entire book import system

```bash
export BOOK_IMPORT_ENABLED=False
```

#### BOOK_IMPORT_MAX_FILE_SIZE
**Default:** `524288000` (500 MB)  
**Type:** Integer (bytes)  
**Description:** Maximum file size allowed for imports

```bash
# Allow 1 GB files
export BOOK_IMPORT_MAX_FILE_SIZE=1073741824

# Allow only 100 MB files
export BOOK_IMPORT_MAX_FILE_SIZE=104857600
```

#### BOOK_IMPORT_APPROVED_HOSTS
**Default:** `gutenberg.org,standardebooks.org,archive.org`  
**Type:** Comma-separated list  
**Description:** Hosts from which books can be downloaded

```bash
# Add custom provider
export BOOK_IMPORT_APPROVED_HOSTS="gutenberg.org,standardebooks.org,archive.org,mylib.example.com"
```

**Important:** Only these exact domains (and subdomains with DNS wildcards) will be allowed for downloads.

### Provider Configuration

Each provider can be independently enabled or disabled:

#### PROVIDER_OPEN_LIBRARY_ENABLED
**Default:** `True`  
**Description:** Enable Open Library provider

```bash
export PROVIDER_OPEN_LIBRARY_ENABLED=False
```

#### PROVIDER_ARCHIVE_ENABLED
**Default:** `True`  
**Description:** Enable Internet Archive provider

```bash
export PROVIDER_ARCHIVE_ENABLED=False
```

#### PROVIDER_GUTENBERG_ENABLED
**Default:** `True`  
**Description:** Enable Project Gutenberg provider

```bash
export PROVIDER_GUTENBERG_ENABLED=False
```

#### PROVIDER_STANDARD_EBOOKS_ENABLED
**Default:** `True`  
**Description:** Enable Standard Ebooks provider

```bash
export PROVIDER_STANDARD_EBOOKS_ENABLED=False
```

### File Storage

#### MEDIA_ROOT
**Type:** File system path  
**Description:** Where imported books are stored

```bash
export MEDIA_ROOT=/var/bookclub/media
```

**Default structure:**
```
MEDIA_ROOT/
├── books/
│   ├── imported/
│   │   ├── gutenberg/
│   │   │   ├── 1342/
│   │   │   │   └── book.epub
│   │   │   └── 2600/
│   │   │       └── book.txt
│   │   ├── open_library/
│   │   │   └── OL1M/
│   │   │       └── book.pdf
│   │   └── archive/
│   │       └── some-book-id/
│   │           └── book.epub
```

#### MEDIA_URL
**Type:** URL path  
**Default:** `/media/`  
**Description:** Web URL for accessing media files

```bash
export MEDIA_URL=/media/
```

### Database Configuration

#### DATABASE_NAME
**Type:** String or path  
**Default:** `db.sqlite3`  
**Description:** Database filename or connection string

```bash
# PostgreSQL
export DATABASE_NAME="bookclub_prod"
export DATABASE_USER="bookclub_user"
export DATABASE_PASSWORD="secure_password"
export DATABASE_HOST="db.example.com"
export DATABASE_PORT="5432"
```

## Django Settings (bookclub/settings.py)

### File Format Settings

```python
# Allowed file formats for import
BOOK_IMPORT_ALLOWED_FORMATS = ['epub', 'txt', 'pdf']
```

### Caching

```python
# How long to cache search results (seconds)
BOOK_SEARCH_CACHE_TIMEOUT = 3600  # 1 hour

# Cache backend configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'bookclub-cache',
    }
}
```

For production with Redis:

```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

### Session Configuration

```python
# Where to store user reading progress and settings
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 1209600  # 2 weeks

# Or use cache for faster access
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

## Runtime Configuration

### Creating Import Jobs

Import jobs are created automatically when users request imports, but can be manually managed:

```python
from books.models import ImportJob, ImportedBook
from django.contrib.auth import get_user_model

User = get_user_model()

# Retry a failed import
job = ImportJob.objects.get(pk=123)
job.status = 'pending'
job.retry_count += 1
job.save()

# Check import status
imported = ImportedBook.objects.get(pk=456)
if imported.status == 'imported':
    print("Ready to read!")
elif imported.status == 'failed':
    print(f"Error: {imported.import_error}")
```

### Managing Providers

Enable or disable providers at runtime:

```python
from books.models import ProviderStatus

# Disable a provider
status = ProviderStatus.objects.get(provider='open_library')
status.is_enabled = False
status.save()

# Re-enable
status.is_enabled = True
status.save()

# Check status
if status.is_enabled:
    print(f"{status.provider} is available")
```

### Storage Cleanup

Monitor and manage storage:

```python
from books.models import ImportedBook, BookFile
from django.db.models import Sum

# Get total storage used
total_bytes = BookFile.objects.aggregate(
    total=Sum('file_size')
)['total'] or 0

print(f"Total storage: {total_bytes / (1024*1024):.2f} MB")

# Find largest imported books
large_books = ImportedBook.objects.filter(
    status='imported'
).order_by('-file_size')[:10]

for book in large_books:
    size_mb = book.file_size / (1024*1024)
    print(f"{book.catalog_book.title}: {size_mb:.2f} MB")

# Delete old imports (older than 1 year)
from datetime import timedelta
from django.utils import timezone

threshold = timezone.now() - timedelta(days=365)
old_imports = ImportedBook.objects.filter(
    imported_at__lt=threshold,
    status='imported'
)

# WARNING: This deletes files!
# for imported in old_imports:
#     imported.delete_files()
#     imported.delete()
```

## Deployment Configuration

### Development

```python
# settings.py
DEBUG = True
BOOK_IMPORT_ENABLED = True
BOOK_IMPORT_MAX_FILE_SIZE = 104857600  # 100 MB
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'
```

### Production

```python
# settings.py or environment
DEBUG = False
BOOK_IMPORT_ENABLED = True
BOOK_IMPORT_MAX_FILE_SIZE = 524288000  # 500 MB

# Use absolute path
MEDIA_ROOT = '/var/www/bookclub/media'
MEDIA_URL = 'https://cdn.example.com/media/'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DATABASE_NAME'),
        'USER': os.getenv('DATABASE_USER'),
        'PASSWORD': os.getenv('DATABASE_PASSWORD'),
        'HOST': os.getenv('DATABASE_HOST'),
        'PORT': os.getenv('DATABASE_PORT', '5432'),
    }
}

# Caching
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://localhost:6379/1'),
    }
}

# File storage with S3
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_STORAGE_BUCKET_NAME = 'bookclub-imports'
AWS_S3_REGION_NAME = 'us-east-1'
```

### Docker Compose

```yaml
version: '3.8'

services:
  web:
    build: .
    environment:
      DEBUG: 'False'
      BOOK_IMPORT_ENABLED: 'True'
      BOOK_IMPORT_MAX_FILE_SIZE: '524288000'
      BOOK_IMPORT_APPROVED_HOSTS: 'gutenberg.org,standardebooks.org,archive.org'
      PROVIDER_OPEN_LIBRARY_ENABLED: 'True'
      PROVIDER_ARCHIVE_ENABLED: 'True'
      PROVIDER_GUTENBERG_ENABLED: 'True'
      PROVIDER_STANDARD_EBOOKS_ENABLED: 'True'
      DATABASE_ENGINE: 'django.db.backends.postgresql'
      DATABASE_NAME: 'bookclub'
      DATABASE_USER: 'bookclub'
      DATABASE_PASSWORD: 'bookclub_pass'
      DATABASE_HOST: 'db'
      DATABASE_PORT: '5432'
      REDIS_URL: 'redis://redis:6379/1'
      MEDIA_ROOT: '/app/media'
      MEDIA_URL: '/media/'
    volumes:
      - ./media:/app/media
    depends_on:
      - db
      - redis
    ports:
      - "8000:8000"

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: 'bookclub'
      POSTGRES_USER: 'bookclub'
      POSTGRES_PASSWORD: 'bookclub_pass'
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

## Nginx Configuration

For serving media files with proper caching:

```nginx
upstream django {
    server localhost:8000;
}

server {
    listen 80;
    server_name bookclub.example.com;

    # Import media with long cache
    location /media/books/imported/ {
        alias /var/www/bookclub/media/books/imported/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # API and HTML
    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Security Configuration

### CORS for Reader

```python
# settings.py
CORS_ALLOWED_ORIGINS = [
    "https://bookclub.example.com",
]

CORS_ALLOW_CREDENTIALS = True
```

### HTTPS

```python
# settings.py
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

### Rate Limiting

```python
# Install django-ratelimit
# pip install django-ratelimit

from django_ratelimit.decorators import ratelimit

@ratelimit(key='user', rate='100/h', method='POST')
def api_import_book(request):
    # Maximum 100 imports per hour per user
    pass

@ratelimit(key='ip', rate='1000/h', method='GET')
def api_book_search(request):
    # Maximum 1000 searches per hour per IP
    pass
```

## Logging Configuration

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/bookclub/import.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 10,
        },
    },
    'loggers': {
        'books.services': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## Performance Tuning

### Database Optimization

```python
# Add indexes for common queries
# In migration:
class Migration(migrations.Migration):
    operations = [
        migrations.RunSQL(
            "CREATE INDEX books_importedboo_status_idx ON books_importedbook(status, imported_at DESC)",
        ),
        migrations.RunSQL(
            "CREATE INDEX books_importjob_idx ON books_importjob(status, created_at DESC)",
        ),
    ]
```

### Connection Pooling

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'CONN_MAX_AGE': 600,  # Reuse connections for 10 minutes
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}
```

### Read Replicas

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'bookclub_primary',
        'HOST': 'primary.db.example.com',
    },
    'read_replica': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'bookclub_replica',
        'HOST': 'replica.db.example.com',
    }
}

# Use replica for searches
books = BookImportedBook.objects.using('read_replica').filter(status='imported')
```

## Monitoring & Alerting

### Health Check Endpoint

```python
# urls.py
from django.http import JsonResponse

def health_check(request):
    """Check import system health"""
    from books.models import ImportJob, ProviderStatus
    
    # Check for stalled imports
    stalled = ImportJob.objects.filter(
        status='processing',
        updated_at__lt=timezone.now() - timedelta(hours=1)
    ).count()
    
    # Check provider status
    providers = ProviderStatus.objects.values('provider', 'is_enabled')
    
    return JsonResponse({
        'status': 'ok' if stalled == 0 else 'warning',
        'stalled_imports': stalled,
        'providers': list(providers),
    })
```

### Metrics to Monitor

- Number of active imports
- Failed import rate
- Average import time
- Storage usage
- API response times
- Provider availability
- User reading activity
