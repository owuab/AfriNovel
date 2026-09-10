#!/usr/bin/env python
"""
BookClub Import System Health Check & Status Script

This script provides diagnostic information about the book import system:
- Configuration validation
- Database connectivity
- Provider status
- Storage usage
- Recent import activity
- System health status
"""

import os
import sys
import django
from pathlib import Path

# Add the project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookclub.settings')
django.setup()

from django.conf import settings
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from books.models import (
    ImportedBook, BookFile, ImportJob, ReadingBookmark, ReadingHighlight,
    ProviderStatus, CatalogBook, BookSource
)
from django.contrib.auth import get_user_model

User = get_user_model()

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'


def print_header(title):
    """Print a formatted header"""
    print(f"\n{BOLD}{BLUE}{'=' * 60}{RESET}")
    print(f"{BOLD}{BLUE}{title:^60}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 60}{RESET}\n")


def print_check(label, status, details=""):
    """Print a status check result"""
    status_icon = f"{GREEN}✓{RESET}" if status else f"{RED}✗{RESET}"
    status_text = f"{GREEN}OK{RESET}" if status else f"{RED}FAILED{RESET}"
    print(f"{status_icon} {label}: {status_text}", end="")
    if details:
        print(f" - {details}", end="")
    print()


def print_info(label, value):
    """Print an info line"""
    print(f"  {BLUE}→{RESET} {label}: {value}")


def check_configuration():
    """Check if import system is properly configured"""
    print_header("Configuration Check")
    
    print_check(
        "Import system enabled",
        settings.BOOK_IMPORT_ENABLED,
        f"BOOK_IMPORT_ENABLED={settings.BOOK_IMPORT_ENABLED}"
    )
    
    max_size_mb = settings.BOOK_IMPORT_MAX_FILE_SIZE / (1024 * 1024)
    print_check(
        "File size limit configured",
        settings.BOOK_IMPORT_MAX_FILE_SIZE > 0,
        f"{max_size_mb:.0f} MB"
    )
    
    has_approved_hosts = len(settings.BOOK_IMPORT_APPROVED_HOSTS) > 0
    print_check(
        "Approved hosts configured",
        has_approved_hosts,
        f"{len(settings.BOOK_IMPORT_APPROVED_HOSTS)} hosts"
    )
    
    if has_approved_hosts:
        for host in list(settings.BOOK_IMPORT_APPROVED_HOSTS)[:3]:
            print_info("Approved host", host)
        if len(settings.BOOK_IMPORT_APPROVED_HOSTS) > 3:
            remaining = len(settings.BOOK_IMPORT_APPROVED_HOSTS) - 3
            print_info("Other hosts", f"+{remaining} more")
    
    # Check media storage
    media_root_exists = os.path.exists(settings.MEDIA_ROOT)
    print_check(
        "Media directory exists",
        media_root_exists,
        settings.MEDIA_ROOT
    )
    
    # Check if directory is writable
    if media_root_exists:
        writable = os.access(settings.MEDIA_ROOT, os.W_OK)
        print_check("Media directory writable", writable)
    
    # Check allowed formats
    print_info("Allowed formats", ", ".join(settings.BOOK_IMPORT_ALLOWED_FORMATS))
    
    # Check cache timeout
    print_info("Search cache timeout", f"{settings.BOOK_SEARCH_CACHE_TIMEOUT}s")


def check_providers():
    """Check provider status"""
    print_header("Provider Status")
    
    total_providers = 0
    enabled_providers = 0
    
    statuses = ProviderStatus.objects.all().order_by('provider')
    
    if not statuses.exists():
        print(f"{YELLOW}⚠{RESET} No provider status records found")
        print("  Creating default providers...")
        
        default_providers = ['gutenberg', 'open_library', 'internet_archive', 'standard_ebooks']
        for provider in default_providers:
            ProviderStatus.objects.get_or_create(
                provider=provider,
                defaults={'is_enabled': True}
            )
        statuses = ProviderStatus.objects.all().order_by('provider')
    
    for status in statuses:
        total_providers += 1
        enabled_providers += 1 if status.is_enabled else 0
        
        icon = f"{GREEN}✓{RESET}" if status.is_enabled else f"{RED}✗{RESET}"
        enabled_text = f"{GREEN}Enabled{RESET}" if status.is_enabled else f"{RED}Disabled{RESET}"
        
        print(f"{icon} {status.provider}: {enabled_text}", end="")
        if status.last_checked:
            print(f" - Checked {status.last_checked.strftime('%Y-%m-%d %H:%M')}", end="")
        print()
    
    print(f"\n  Summary: {enabled_providers}/{total_providers} providers enabled")


def check_database():
    """Check database and models"""
    print_header("Database & Models")
    
    # Try to query models
    try:
        imported_count = ImportedBook.objects.count()
        print_check("ImportedBook model", True, f"{imported_count} records")
    except Exception as e:
        print_check("ImportedBook model", False, str(e))
    
    try:
        job_count = ImportJob.objects.count()
        print_check("ImportJob model", True, f"{job_count} records")
    except Exception as e:
        print_check("ImportJob model", False, str(e))
    
    try:
        bookmark_count = ReadingBookmark.objects.count()
        print_check("ReadingBookmark model", True, f"{bookmark_count} records")
    except Exception as e:
        print_check("ReadingBookmark model", False, str(e))
    
    try:
        highlight_count = ReadingHighlight.objects.count()
        print_check("ReadingHighlight model", True, f"{highlight_count} records")
    except Exception as e:
        print_check("ReadingHighlight model", False, str(e))


def check_storage():
    """Check storage usage"""
    print_header("Storage Usage")
    
    # Calculate total storage
    total_bytes = BookFile.objects.aggregate(
        total=Sum('file_size')
    )['total'] or 0
    
    total_mb = total_bytes / (1024 * 1024)
    total_gb = total_mb / 1024
    
    if total_gb > 1:
        print_info("Total storage used", f"{total_gb:.2f} GB")
    else:
        print_info("Total storage used", f"{total_mb:.2f} MB")
    
    # Count by format
    format_stats = ImportedBook.objects.values('format').annotate(
        count=Count('id'),
        size=Sum('file_size')
    ).order_by('-size')
    
    print("\n  Storage by format:")
    for stat in format_stats:
        size_mb = (stat['size'] or 0) / (1024 * 1024)
        print_info(
            f"{stat['format'].upper()} ({stat['count']} books)",
            f"{size_mb:.2f} MB"
        )
    
    # Largest books
    print("\n  Largest imported books:")
    largest = ImportedBook.objects.filter(
        status='imported'
    ).order_by('-file_size')[:3]
    
    for imported in largest:
        size_mb = imported.file_size / (1024 * 1024)
        print_info(
            f"{imported.catalog_book.title}",
            f"{size_mb:.2f} MB"
        )


def check_imports():
    """Check import activity"""
    print_header("Import Activity")
    
    # Overall statistics
    total_imports = ImportedBook.objects.count()
    successful = ImportedBook.objects.filter(status='imported').count()
    failed = ImportedBook.objects.filter(status='failed').count()
    queued = ImportedBook.objects.filter(status='queued').count()
    processing = ImportedBook.objects.filter(status='downloading', status='processing').count()
    
    print(f"  Total imported books: {total_imports}")
    print(f"    {GREEN}✓ Successful: {successful}{RESET}")
    print(f"    {RED}✗ Failed: {failed}{RESET}")
    print(f"    {YELLOW}⊕ Queued: {queued}{RESET}")
    print(f"    {BLUE}↻ Processing: {processing}{RESET}")
    
    # Recent imports (last 7 days)
    print("\n  Recent imports (last 7 days):")
    week_ago = timezone.now() - timedelta(days=7)
    recent = ImportedBook.objects.filter(
        imported_at__gte=week_ago
    ).count()
    
    print_info("Imported last 7 days", recent)
    
    # Failed imports details
    if failed > 0:
        print("\n  Recent failures:")
        failures = ImportedBook.objects.filter(
            status='failed'
        ).order_by('-updated_at')[:3]
        
        for imported in failures:
            error = imported.import_error[:50] if imported.import_error else "Unknown"
            print_info(
                f"{imported.catalog_book.title}",
                f"{error}..."
            )
    
    # Stalled jobs (processing for > 1 hour)
    print("\n  Stalled imports (processing > 1 hour):")
    one_hour_ago = timezone.now() - timedelta(hours=1)
    stalled = ImportJob.objects.filter(
        status='processing',
        updated_at__lt=one_hour_ago
    ).count()
    
    if stalled > 0:
        print_check("Stalled jobs detected", False, f"{stalled} jobs stuck")
    else:
        print_check("No stalled jobs", True)


def check_users():
    """Check user activity"""
    print_header("User Activity")
    
    # Users with bookmarks/highlights
    bookmark_users = User.objects.filter(
        readingbookmark__isnull=False
    ).distinct().count()
    
    highlight_users = User.objects.filter(
        readinghighlight__isnull=False
    ).distinct().count()
    
    reading_users = User.objects.filter(
        readingbookmark__isnull=False
    ) | User.objects.filter(
        readinghighlight__isnull=False
    )
    reading_users = reading_users.distinct().count()
    
    print_info("Users with bookmarks", bookmark_users)
    print_info("Users with highlights", highlight_users)
    print_info("Total active readers", reading_users)
    
    # Total interactions
    total_bookmarks = ReadingBookmark.objects.count()
    total_highlights = ReadingHighlight.objects.count()
    
    print_info("Total bookmarks created", total_bookmarks)
    print_info("Total highlights created", total_highlights)


def print_summary():
    """Print a summary status"""
    print_header("System Summary")
    
    all_ok = True
    
    # Check enabled
    if not settings.BOOK_IMPORT_ENABLED:
        print(f"{RED}⚠ Import system is DISABLED{RESET}")
        all_ok = False
    else:
        print(f"{GREEN}✓ Import system is ENABLED{RESET}")
    
    # Check storage
    media_ok = os.path.exists(settings.MEDIA_ROOT) and os.access(settings.MEDIA_ROOT, os.W_OK)
    if not media_ok:
        print(f"{RED}⚠ Media directory not accessible{RESET}")
        all_ok = False
    else:
        print(f"{GREEN}✓ Media directory accessible{RESET}")
    
    # Check database
    try:
        ImportedBook.objects.count()
        print(f"{GREEN}✓ Database connected{RESET}")
    except:
        print(f"{RED}⚠ Database connection failed{RESET}")
        all_ok = False
    
    # Check providers
    enabled_providers = ProviderStatus.objects.filter(is_enabled=True).count()
    if enabled_providers > 0:
        print(f"{GREEN}✓ {enabled_providers} provider(s) enabled{RESET}")
    else:
        print(f"{RED}⚠ No providers enabled{RESET}")
        all_ok = False
    
    print()
    if all_ok:
        print(f"{GREEN}{BOLD}✓ System Status: HEALTHY{RESET}")
    else:
        print(f"{YELLOW}{BOLD}⚠ System Status: NEEDS ATTENTION{RESET}")


def main():
    """Run all checks"""
    print(f"\n{BOLD}{BLUE}BookClub Import System - Health Check{RESET}")
    print(f"{BLUE}Django {django.get_version()}{RESET}")
    print(f"{BLUE}Started: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    
    try:
        check_configuration()
        check_providers()
        check_database()
        check_storage()
        check_imports()
        check_users()
        print_summary()
    except Exception as e:
        print(f"\n{RED}Error during checks:{RESET}")
        print(f"{RED}{str(e)}{RESET}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
