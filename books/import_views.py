"""
Import and reading endpoints for imported books.

Provides API endpoints for:
- Searching and importing books
- Managing import jobs  
- Reading imported books
- Tracking reading progress
"""

import json
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse, Http404, FileResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods, require_POST
from django.utils.decorators import method_decorator
from django.views import View

from .models import (
    CatalogBook, ImportedBook, BookSource, ImportJob, ReadingProgress,
    ReadingBookmark, ReadingHighlight, ProviderStatus,
)
from .services import (
    CatalogService, BookImportService, RightsChecker, RightsCheckError,
    FileDownloadError, EPUBProcessor,
)


# ============================================================================
# BOOK SEARCH & DISCOVERY
# ============================================================================

@require_http_methods(["GET", "POST"])
def api_book_search(request):
    """
    Search for books from local library and approved external sources.
    
    Returns: JSON with local results and external results grouped separately
    """
    if not settings.BOOK_IMPORT_ENABLED:
        return JsonResponse({'error': 'Book import is not enabled'}, status=403)
    
    query = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))
    search_external = request.GET.get('external', 'true').lower() == 'true'
    
    if not query or len(query) < 2:
        return JsonResponse({'error': 'Query must be at least 2 characters'}, status=400)
    
    response_data = {
        'query': query,
        'local_results': [],
        'external_results': [],
        'external_errors': [],
        'total_local': 0,
        'total_external': 0,
    }
    
    # Search local library
    local_books = CatalogBook.objects.filter(
        Q(title__icontains=query) | Q(authors__contains=query)
    ).select_related().distinct()[:50]
    
    response_data['total_local'] = local_books.count()
    
    for book in local_books:
        imported = ImportedBook.objects.filter(catalog_book=book).first()
        response_data['local_results'].append({
            'id': book.id,
            'title': book.title,
            'authors': book.authors,
            'description': book.description[:200],
            'source': book.source,
            'cover_url': book.cover_image_url,
            'copyright_status': book.copyright_status,
            'access_type': book.access_type,
            'license': book.license,
            'imported': imported is not None,
            'imported_id': imported.id if imported else None,
            'imported_status': imported.status if imported else None,
        })
    
    # Search external sources if requested
    if search_external:
        try:
            external_books, total, errors = CatalogService.search(query, page=page)
            response_data['total_external'] = total
            response_data['external_errors'] = errors
            
            for book in external_books:
                # Check if already imported locally
                local = CatalogBook.objects.filter(
                    source=book.source,
                    external_id=book.external_id
                ).first()
                
                if local:
                    imported = ImportedBook.objects.filter(catalog_book=local).first()
                else:
                    imported = None
                
                response_data['external_results'].append({
                    'source': book.source,
                    'external_id': book.external_id,
                    'title': book.title,
                    'authors': book.authors,
                    'description': book.description[:200],
                    'cover_url': book.cover_image_url,
                    'language': book.languages[0] if book.languages else 'en',
                    'publication_year': book.publication_year,
                    'copyright_status': book.copyright_status,
                    'access_type': book.access_type,
                    'license': book.license,
                    'isbn13': book.isbn13,
                    'can_import': RightsChecker.can_import_book(
                        CatalogBook.objects.filter(
                            source=book.source,
                            external_id=book.external_id
                        ).first() or
                        CatalogBook(
                            source=book.source,
                            external_id=book.external_id,
                            full_text_available=book.full_text_available,
                            copyright_status=book.copyright_status,
                        ),
                        BookSource(
                            provider=book.source,
                            reading_url=book.reading_url,
                            internal_reading_allowed=book.full_text_available and book.copyright_status in {
                                CatalogBook.PUBLIC_DOMAIN_STATUS,
                                CatalogBook.OPEN_LICENSE,
                                CatalogBook.AUTHORIZED,
                            }
                        )
                    )[0],
                    'imported': imported is not None,
                    'imported_id': imported.id if imported else None,
                    'imported_status': imported.status if imported else None,
                })
        except Exception as e:
            response_data['external_errors'].append(str(e))
    
    return JsonResponse(response_data)


# ============================================================================
# BOOK IMPORT
# ============================================================================

@login_required
@require_POST
def api_import_book(request):
    """
    Import a book from an external source or create record for local import.
    
    POST data:
    - source: Provider name (e.g., 'open_library', 'gutenberg')
    - external_id: External book ID
    """
    if not settings.BOOK_IMPORT_ENABLED:
        return JsonResponse({'error': 'Book import is not enabled'}, status=403)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    source = data.get('source', '').strip()
    external_id = data.get('external_id', '').strip()
    
    if not source or not external_id:
        return JsonResponse({'error': 'Missing source or external_id'}, status=400)
    
    # Check if provider is enabled
    if not RightsChecker.verify_source_eligibility(source):
        return JsonResponse({
            'error': 'This source is not enabled for imports'
        }, status=403)
    
    try:
        # Get or create CatalogBook record
        catalog_book, created = CatalogBook.objects.get_or_create(
            source=source,
            external_id=external_id,
            defaults={
                'title': 'Loading...',
                'source_url': f'{source}/{external_id}',
                'access_type': CatalogBook.PUBLIC_DOMAIN,
                'copyright_status': CatalogBook.PUBLIC_DOMAIN_STATUS,
            }
        )
        
        # Check if already imported
        try:
            imported = ImportedBook.objects.get(catalog_book=catalog_book)
            if imported.status == ImportedBook.IMPORTED:
                return JsonResponse({
                    'status': 'already_imported',
                    'imported_id': imported.id,
                })
            else:
                return JsonResponse({
                    'status': 'import_pending',
                    'imported_id': imported.id,
                    'import_status': imported.status,
                })
        except ImportedBook.DoesNotExist:
            pass
        
        # Get primary BookSource for this book
        book_source = BookSource.objects.filter(
            book=catalog_book,
            provider=source,
            external_id=external_id,
            internal_reading_allowed=True,
        ).first()
        
        if not book_source:
            return JsonResponse({
                'error': 'No eligible source found for import'
            }, status=400)
        
        # Initiate import
        try:
            imported_book = BookImportService.import_book(
                user=request.user,
                catalog_book=catalog_book,
                book_source=book_source,
            )
            
            return JsonResponse({
                'status': 'import_started',
                'imported_id': imported_book.id,
                'import_status': imported_book.status,
            })
        
        except RightsCheckError as e:
            return JsonResponse({
                'error': f'Cannot import: {str(e)}'
            }, status=403)
        except FileDownloadError as e:
            return JsonResponse({
                'error': f'Download failed: {str(e)}'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': f'Import failed: {str(e)}'
            }, status=500)
    
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@login_required
def api_import_status(request, imported_book_id):
    """Get status of an import job."""
    imported_book = get_object_or_404(ImportedBook, id=imported_book_id)
    
    # Only user who initiated can view their own imports
    job = imported_book.import_jobs.latest('created_at')
    can_view = request.user.is_staff or job.initiated_by_id == request.user.id
    
    if not can_view:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    return JsonResponse({
        'id': imported_book.id,
        'status': imported_book.status,
        'format': imported_book.format,
        'file_size': imported_book.file_size,
        'checksum': imported_book.checksum,
        'import_error': imported_book.import_error,
        'imported_at': imported_book.imported_at.isoformat() if imported_book.imported_at else None,
        'job_status': job.status,
        'job_progress': job.progress_percent,
        'job_error': job.error_message,
    })


# ============================================================================
# READER
# ============================================================================

def reader_home(request):
    """Reader homepage - list of imported books."""
    if not settings.BOOK_IMPORT_ENABLED:
        return render(request, '404.html', status=404)
    
    imported_books = ImportedBook.objects.filter(
        status=ImportedBook.IMPORTED
    ).select_related('catalog_book').order_by('-imported_at')
    
    # Pagination
    paginator = Paginator(imported_books, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_books': paginator.count,
    }
    return render(request, 'books/reader_home.html', context)


def book_reader(request, imported_book_id, chapter_id=None):
    """Main EPUB/book reader view."""
    imported_book = get_object_or_404(
        ImportedBook.objects.select_related('catalog_book', 'file'),
        id=imported_book_id,
        status=ImportedBook.IMPORTED
    )
    
    # Check file exists
    if not imported_book.file_exists:
        return render(request, 'books/reader_error.html', {
            'error': 'Book file not found',
        })
    
    # Get reading progress
    reading_progress = None
    if request.user.is_authenticated:
        reading_progress = ReadingProgress.objects.filter(
            user=request.user,
            book=imported_book.catalog_book,
        ).first()
    
    # Get chapter list if EPUB
    chapters = []
    if imported_book.format == 'epub':
        # Load chapters from cache or extract
        try:
            from django.core.cache import cache
            cache_key = f'epub_chapters:{imported_book.id}'
            chapters = cache.get(cache_key)
            
            if not chapters:
                # Extract chapters
                file_path = imported_book.file.file_path
                from django.core.files.storage import default_storage
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.epub') as tmp:
                    with default_storage.open(file_path, 'rb') as f:
                        tmp.write(f.read())
                    tmp_path = tmp.name
                
                try:
                    chapters = EPUBProcessor.extract_chapters(tmp_path)
                    cache.set(cache_key, chapters, 60 * 60 * 24)
                finally:
                    import os
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
        except Exception as e:
            import logging
            logging.error(f'Error loading chapters: {e}')
    
    context = {
        'imported_book': imported_book,
        'chapters': chapters,
        'current_chapter': chapter_id or (0 if chapters else None),
        'reading_progress': reading_progress,
        'bookmarks': [],
        'highlights': [],
    }
    
    if request.user.is_authenticated:
        context['bookmarks'] = ReadingBookmark.objects.filter(
            user=request.user,
            imported_book=imported_book,
        ).order_by('chapter_identifier')
        
        context['highlights'] = ReadingHighlight.objects.filter(
            user=request.user,
            imported_book=imported_book,
        ).order_by('chapter_identifier')
    
    return render(request, 'books/reader.html', context)


@login_required
@require_http_methods(["GET"])
def api_reader_chapter(request, imported_book_id, chapter_index):
    """Get chapter content for reader."""
    imported_book = get_object_or_404(
        ImportedBook.objects.select_related('file'),
        id=imported_book_id,
        status=ImportedBook.IMPORTED
    )
    
    if not imported_book.file_exists:
        return JsonResponse({'error': 'Book file not found'}, status=404)
    
    try:
        chapter_index = int(chapter_index)
        
        # Load from cache or extract
        from django.core.cache import cache
        cache_key = f'epub_chapters:{imported_book.id}'
        chapters = cache.get(cache_key)
        
        if not chapters:
            # Extract chapters
            file_path = imported_book.file.file_path
            from django.core.files.storage import default_storage
            
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.epub') as tmp:
                with default_storage.open(file_path, 'rb') as f:
                    tmp.write(f.read())
                tmp_path = tmp.name
            
            try:
                chapters = EPUBProcessor.extract_chapters(tmp_path)
                cache.set(cache_key, chapters, 60 * 60 * 24)
            finally:
                import os
                try:
                    os.unlink(tmp_path)
                except:
                    pass
        
        if chapter_index < 0 or chapter_index >= len(chapters):
            return JsonResponse({'error': 'Chapter not found'}, status=404)
        
        chapter = chapters[chapter_index]
        
        return JsonResponse({
            'title': chapter.get('title', 'Chapter'),
            'content': chapter.get('html_content', ''),
            'index': chapter_index,
            'total': len(chapters),
        })
    
    except Exception as e:
        import logging
        logging.error(f'Error loading chapter: {e}')
        return JsonResponse({'error': 'Error loading chapter'}, status=500)


@login_required
@require_POST
def api_reading_progress(request, imported_book_id):
    """Update reading progress."""
    imported_book = get_object_or_404(ImportedBook, id=imported_book_id)
    catalog_book = imported_book.catalog_book
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    chapter = data.get('chapter', '')
    progress_percent = int(data.get('progress', 0))
    
    progress, created = ReadingProgress.objects.update_or_create(
        user=request.user,
        book=catalog_book,
        defaults={
            'chapter': chapter,
            'percent': max(0, min(100, progress_percent)),
        }
    )
    
    return JsonResponse({
        'success': True,
        'progress': progress.percent,
    })


@login_required
@require_POST
def api_bookmark(request, imported_book_id):
    """Create/update bookmark."""
    imported_book = get_object_or_404(ImportedBook, id=imported_book_id)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    chapter = data.get('chapter', '')
    label = data.get('label', '')
    position_info = data.get('position', {})
    
    bookmark, created = ReadingBookmark.objects.update_or_create(
        user=request.user,
        imported_book=imported_book,
        chapter_identifier=chapter,
        defaults={
            'label': label,
            'position_info': position_info,
        }
    )
    
    return JsonResponse({
        'success': True,
        'bookmark_id': bookmark.id,
    })


@login_required
@require_POST
def api_highlight(request, imported_book_id):
    """Create highlight/annotation."""
    imported_book = get_object_or_404(ImportedBook, id=imported_book_id)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    text_excerpt = data.get('text', '')
    chapter = data.get('chapter', '')
    note = data.get('note', '')
    color = data.get('color', 'yellow')
    location_info = data.get('location', {})
    
    if not text_excerpt:
        return JsonResponse({'error': 'Text excerpt required'}, status=400)
    
    highlight = ReadingHighlight.objects.create(
        user=request.user,
        imported_book=imported_book,
        text_excerpt=text_excerpt,
        chapter_identifier=chapter,
        note=note,
        color=color,
        location_info=location_info,
    )
    
    return JsonResponse({
        'success': True,
        'highlight_id': highlight.id,
    })


@login_required
def api_highlights(request, imported_book_id):
    """Get all highlights for a book."""
    imported_book = get_object_or_404(ImportedBook, id=imported_book_id)
    
    highlights = ReadingHighlight.objects.filter(
        user=request.user,
        imported_book=imported_book,
    ).order_by('chapter_identifier', '-created_at')
    
    return JsonResponse({
        'highlights': [
            {
                'id': h.id,
                'text': h.text_excerpt,
                'chapter': h.chapter_identifier,
                'note': h.note,
                'color': h.color,
                'created_at': h.created_at.isoformat(),
            }
            for h in highlights
        ]
    })
