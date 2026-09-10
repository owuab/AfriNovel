"""Legal book-provider adapters and normalized catalogue operations."""

from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass, field
from html import escape
from typing import Iterable
from xml.etree import ElementTree
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from .models import BookSource, CatalogBook, ProviderStatus
from .taxonomy import assign_asian_category, normalize_language


class ProviderUnavailable(Exception):
    """A provider did not respond safely or in time."""


@dataclass(frozen=True)
class NormalizedBook:
    external_id: str
    source: str
    title: str
    authors: list[str] = field(default_factory=list)
    description: str = ''
    subjects: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    publication_year: int | None = None
    publisher: str = ''
    isbn10: str = ''
    isbn13: str = ''
    cover_url: str = ''
    source_url: str = ''
    reading_url: str = ''
    access_type: str = CatalogBook.UNAVAILABLE
    copyright_status: str = CatalogBook.UNKNOWN
    license: str = ''
    full_text_available: bool = False
    borrowable: bool = False
    page_count: int | None = None
    provider_sources: tuple[dict, ...] = ()

    @property
    def cover_image_url(self):
        if self.cover_url:
            return self.cover_url
        if self.source == 'gutenberg' and self.external_id.isdigit():
            return f'https://www.gutenberg.org/cache/epub/{self.external_id}/pg{self.external_id}.cover.medium.jpg'
        if self.source == 'internet_archive':
            return f'https://archive.org/services/img/{self.external_id}'
        return ''


class BookProvider:
    """Stable interface for providers; the UI never calls a provider directly."""

    name = 'base'

    def search_books(self, query: str, filters: dict | None = None, page: int = 1) -> tuple[list[NormalizedBook], int]:
        raise NotImplementedError

    def get_book(self, external_id: str) -> NormalizedBook | None:
        raise NotImplementedError


class OpenLibraryProvider(BookProvider):
    name = 'open_library'
    endpoint = 'https://openlibrary.org/search.json'
    timeout_seconds = 8
    page_size = 18

    def _request_json(self, url: str) -> dict:
        cache_key = f'open-library:{url}'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        request = Request(url, headers={'User-Agent': settings.BOOK_PROVIDER_USER_AGENT, 'Accept': 'application/json'})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                if response.status != 200:
                    raise ProviderUnavailable('Open Library returned an unexpected response.')
                payload = json.loads(response.read().decode('utf-8'))
                cache.set(cache_key, payload, 60 * 10)
                return payload
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise ProviderUnavailable('Open Library is temporarily unavailable.') from error

    @staticmethod
    def _gutenberg_id(document: dict) -> str:
        for identifier in document.get('ia', []) or []:
            match = re.search(r'(?:gutenberg[-_]?|pg)(\d+)$', str(identifier), flags=re.IGNORECASE)
            if match:
                return match.group(1)
        return ''

    def _normalize(self, document: dict) -> NormalizedBook:
        work_key = str(document.get('key', '')).strip('/')
        external_id = work_key.rsplit('/', 1)[-1]
        ebook_access = document.get('ebook_access', 'no_ebook')
        gutenberg_id = self._gutenberg_id(document)
        isbn_values = document.get('isbn', []) or []
        isbn10 = next((value for value in isbn_values if len(value) == 10), '')
        isbn13 = next((value for value in isbn_values if len(value) == 13), '')
        source_url = f'https://openlibrary.org/{work_key}' if work_key else 'https://openlibrary.org/'
        sources: list[dict] = []

        if gutenberg_id:
            reading_url = f'https://www.gutenberg.org/cache/epub/{gutenberg_id}/pg{gutenberg_id}.txt'
            source_url = f'https://www.gutenberg.org/ebooks/{gutenberg_id}'
            access_type = CatalogBook.PUBLIC_DOMAIN
            copyright_status = CatalogBook.PUBLIC_DOMAIN_STATUS
            license_name = 'Project Gutenberg public-domain edition'
            full_text_available = True
            sources.append({
                'provider': 'gutenberg',
                'external_id': gutenberg_id,
                'source_url': source_url,
                'reading_url': reading_url,
                'access_type': access_type,
                'copyright_status': copyright_status,
                'license': license_name,
                'internal_reading_allowed': True,
            })
        elif ebook_access == 'borrowable':
            reading_url = source_url
            access_type = CatalogBook.BORROW
            copyright_status = CatalogBook.COPYRIGHTED
            license_name = ''
            full_text_available = False
        elif ebook_access == 'public':
            reading_url = source_url
            access_type = CatalogBook.FREE_READ_EXTERNAL
            copyright_status = CatalogBook.UNKNOWN
            license_name = ''
            full_text_available = False
        else:
            reading_url = source_url
            access_type = CatalogBook.UNAVAILABLE
            copyright_status = CatalogBook.UNKNOWN
            license_name = ''
            full_text_available = False

        return NormalizedBook(
            external_id=external_id,
            source=self.name,
            title=document.get('title', 'Untitled'),
            authors=document.get('author_name', [])[:10],
            subjects=document.get('subject', [])[:12],
            languages=document.get('language', [])[:8],
            publication_year=document.get('first_publish_year'),
            publisher=(document.get('publisher', []) or [''])[0],
            isbn10=isbn10,
            isbn13=isbn13,
            cover_url=(f"https://covers.openlibrary.org/b/id/{document['cover_i']}-L.jpg" if document.get('cover_i') else ''),
            source_url=source_url,
            reading_url=reading_url,
            access_type=access_type,
            copyright_status=copyright_status,
            license=license_name,
            full_text_available=full_text_available,
            borrowable=ebook_access == 'borrowable',
            page_count=document.get('number_of_pages_median'),
            provider_sources=tuple(sources),
        )

    def search_books(self, query: str, filters: dict | None = None, page: int = 1) -> tuple[list[NormalizedBook], int]:
        params = {'q': query, 'page': max(page, 1), 'limit': self.page_size, 'fields': 'key,title,author_name,first_publish_year,language,subject,isbn,cover_i,publisher,ebook_access,ia,number_of_pages_median'}
        filters = filters or {}
        for key in ('author', 'language', 'subject', 'isbn', 'publish_year'):
            if filters.get(key):
                params[key] = filters[key]
        payload = self._request_json(f'{self.endpoint}?{urlencode(params)}')
        return [self._normalize(document) for document in payload.get('docs', []) if document.get('key')], payload.get('num_found', 0)

    def get_book(self, external_id: str) -> NormalizedBook | None:
        payload = self._request_json(f'https://openlibrary.org/works/{external_id}.json')
        return NormalizedBook(
            external_id=external_id,
            source=self.name,
            title=payload.get('title', 'Untitled'),
            description=payload.get('description', '') if isinstance(payload.get('description', ''), str) else payload.get('description', {}).get('value', ''),
            subjects=payload.get('subjects', [])[:12],
            source_url=f'https://openlibrary.org/works/{external_id}',
            reading_url=f'https://openlibrary.org/works/{external_id}',
        )


class GutenbergProvider(BookProvider):
    name = 'gutenberg'

    def search_books(self, query: str, filters: dict | None = None, page: int = 1) -> tuple[list[NormalizedBook], int]:
        return [], 0

    def get_book(self, external_id: str) -> NormalizedBook | None:
        if not external_id.isdigit():
            return None
        return NormalizedBook(
            external_id=external_id,
            source=self.name,
            title='Project Gutenberg edition',
            source_url=f'https://www.gutenberg.org/ebooks/{external_id}',
            reading_url=f'https://www.gutenberg.org/cache/epub/{external_id}/pg{external_id}.txt',
            access_type=CatalogBook.PUBLIC_DOMAIN,
            copyright_status=CatalogBook.PUBLIC_DOMAIN_STATUS,
            license='Project Gutenberg public-domain edition',
            full_text_available=True,
        )


class InternetArchiveProvider(OpenLibraryProvider):
    """Internet Archive provider restricted to explicitly public-domain text files."""

    name = 'internet_archive'
    endpoint = 'https://archive.org/advancedsearch.php'
    page_size = 12

    def _download_metadata(self, identifier: str) -> dict:
        return self._request_json(f'https://archive.org/metadata/{quote(identifier)}')

    def _public_text_resource(self, identifier: str) -> tuple[str, str] | None:
        metadata = self._download_metadata(identifier)
        rights = metadata.get('rights', '')
        rights_text = ' '.join(rights) if isinstance(rights, list) else str(rights)
        if 'public domain' not in rights_text.casefold():
            return None
        for file_info in metadata.get('files', []):
            name = str(file_info.get('name', ''))
            file_format = str(file_info.get('format', '')).casefold()
            if file_format in {'text pdf', 'pdf', 'epub', 'text'} or name.casefold().endswith(('.txt', '.epub')):
                return f'https://archive.org/download/{quote(identifier)}/{quote(name)}', rights_text
        return None

    def search_books(self, query: str, filters: dict | None = None, page: int = 1) -> tuple[list[NormalizedBook], int]:
        filters = filters or {}
        clauses = [f'({query})', 'mediatype:texts', 'rights:"Public Domain"']
        if filters.get('language'):
            clauses.append(f'language:{filters["language"]}')
        if filters.get('year') or filters.get('publish_year'):
            clauses.append(f'year:{filters.get("year") or filters.get("publish_year")}')
        params = [
            ('q', ' AND '.join(clauses)), ('rows', str(self.page_size)), ('page', str(max(page, 1))),
            ('output', 'json'), ('fl[]', 'identifier'), ('fl[]', 'title'), ('fl[]', 'creator'),
            ('fl[]', 'year'), ('fl[]', 'language'), ('fl[]', 'subject'), ('fl[]', 'rights'), ('fl[]', 'identifier-access'),
        ]
        payload = self._request_json(f'{self.endpoint}?{urlencode(params)}')
        response = payload.get('response', {})
        books = []
        for document in response.get('docs', []):
            identifier = document.get('identifier')
            if not identifier or not document.get('title'):
                continue
            creators = document.get('creator', [])
            if isinstance(creators, str):
                creators = [creators]
            languages = document.get('language', [])
            if isinstance(languages, str):
                languages = [languages]
            subjects = document.get('subject', [])
            if isinstance(subjects, str):
                subjects = [subjects]
            try:
                resource = self._public_text_resource(identifier)
            except (ProviderUnavailable, KeyError, TypeError):
                resource = None
            if not resource:
                continue
            reading_url, rights = resource
            books.append(NormalizedBook(
                external_id=identifier,
                source=self.name,
                title=document['title'],
                authors=creators[:10], subjects=subjects[:12], languages=languages[:8],
                publication_year=int(document['year']) if str(document.get('year', '')).isdigit() else None,
                source_url=f'https://archive.org/details/{identifier}', reading_url=reading_url,
                access_type=CatalogBook.PUBLIC_DOMAIN, copyright_status=CatalogBook.PUBLIC_DOMAIN_STATUS,
                license=rights, full_text_available=True,
                provider_sources=({
                    'provider': self.name, 'external_id': identifier,
                    'source_url': f'https://archive.org/details/{identifier}', 'reading_url': reading_url,
                    'access_type': CatalogBook.PUBLIC_DOMAIN,
                    'copyright_status': CatalogBook.PUBLIC_DOMAIN_STATUS,
                    'license': rights, 'internal_reading_allowed': True,
                },),
            ))
        return books, response.get('numFound', 0)


class StandardEbooksProvider(BookProvider):
    """
    Standard Ebooks provider for high-quality public-domain books.
    
    Standard Ebooks provides carefully formatted, high-quality public domain books
    with proper metadata and EPUB formatting.
    """
    
    name = 'standard_ebooks'
    base_url = 'https://standardebooks.org'
    api_endpoint = 'https://standardebooks.org/api/v1/books'
    timeout_seconds = 8
    page_size = 12
    
    def _request_json(self, url: str) -> dict:
        cache_key = f'standard-ebooks:{url}'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        request = Request(url, headers={'User-Agent': settings.BOOK_PROVIDER_USER_AGENT, 'Accept': 'application/json'})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                if response.status != 200:
                    raise ProviderUnavailable('Standard Ebooks API returned an unexpected response.')
                payload = json.loads(response.read().decode('utf-8'))
                cache.set(cache_key, payload, 60 * 60)
                return payload
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise ProviderUnavailable('Standard Ebooks API is temporarily unavailable.') from error
    
    def search_books(self, query: str, filters: dict | None = None, page: int = 1) -> tuple[list[NormalizedBook], int]:
        """Search Standard Ebooks catalog."""
        try:
            # Standard Ebooks doesn't have advanced search via API
            # For now, return empty - in production, could scrape or use different approach
            return [], 0
        except Exception:
            return [], 0
    
    def get_book(self, external_id: str) -> NormalizedBook | None:
        """Get a specific book by Standard Ebooks ID."""
        try:
            payload = self._request_json(f'{self.api_endpoint}/{external_id}')
            
            book = payload
            authors = []
            for author in book.get('authors', []):
                if author.get('name'):
                    authors.append(author['name'])
            
            # Get EPUB download URL
            epub_url = f'{self.base_url}/ebooks/{external_id}/downloads/{external_id}.epub'
            
            return NormalizedBook(
                external_id=external_id,
                source=self.name,
                title=book.get('title', 'Untitled'),
                authors=authors,
                description=book.get('description', ''),
                subjects=book.get('tags', [])[:12],
                languages=['en'] if book.get('language') == 'en' else [book.get('language', 'en')],
                publication_year=int(book['publication-year']) if book.get('publication-year') else None,
                publisher='Standard Ebooks',
                cover_url=f'{self.base_url}/ebooks/{external_id}/cover.jpg',
                source_url=f'{self.base_url}/ebooks/{external_id}',
                reading_url=epub_url,
                access_type=CatalogBook.PUBLIC_DOMAIN,
                copyright_status=CatalogBook.PUBLIC_DOMAIN_STATUS,
                license='Public Domain',
                full_text_available=True,
                page_count=None,
                provider_sources=(
                    {
                        'provider': self.name,
                        'external_id': external_id,
                        'source_url': f'{self.base_url}/ebooks/{external_id}',
                        'reading_url': epub_url,
                        'access_type': CatalogBook.PUBLIC_DOMAIN,
                        'copyright_status': CatalogBook.PUBLIC_DOMAIN_STATUS,
                        'license': 'Public Domain',
                        'internal_reading_allowed': True,
                    },
                ),
            )
        except Exception:
            return None


class CatalogService:
    providers: tuple[BookProvider, ...] = (OpenLibraryProvider(), InternetArchiveProvider(), StandardEbooksProvider(), GutenbergProvider())

    @classmethod
    def harvest_public_domain_catalog(cls, query_terms: list[str] | None = None, limit: int = 25) -> list[CatalogBook]:
        """Persist a larger set of approved public-domain and open-license books from the configured providers."""
        approved_statuses = {CatalogBook.PUBLIC_DOMAIN_STATUS, CatalogBook.OPEN_LICENSE, CatalogBook.AUTHORIZED}
        existing = CatalogBook.objects.filter(
            disabled=False,
            full_text_available=True,
            copyright_status__in=approved_statuses,
        )
        limit = max(1, int(limit))
        if existing.count() >= limit:
            return list(existing.order_by('-updated_at')[:limit])

        query_terms = query_terms or [
            'pride and prejudice',
            'alice in wonderland',
            'frankenstein',
            'the secret garden',
            'dracula',
            'adventures of sherlock holmes',
            'war and peace',
            'anna karenina',
            'moby dick',
            'great expectations',
            'the adventures of tom sawyer',
            'little women',
        ]

        seeded: list[CatalogBook] = []
        seen_ids: set[tuple[str, str]] = set()

        for query in query_terms:
            try:
                normalized, _, _ = cls.search(query, page=1)
            except Exception:
                continue
            for result in normalized:
                if not result.full_text_available:
                    continue
                if result.copyright_status not in approved_statuses:
                    continue
                key = (result.source, result.external_id)
                if key in seen_ids:
                    continue
                seen_ids.add(key)
                book = cls.persist(result)
                if book and not book.disabled:
                    seeded.append(book)
                    if len(seeded) >= limit:
                        return seeded

        return seeded

    @classmethod
    def ensure_local_public_domain_seed(cls, limit: int = 12) -> list[CatalogBook]:
        """Persist a local seed set of legal public-domain books from approved providers."""
        seeded = cls.harvest_public_domain_catalog(limit=limit)
        if seeded:
            return seeded
        fallback_books = [
            ('1342', 'Pride and Prejudice', 'Jane Austen', ['Romance', 'Fiction']),
            ('11', "Alice's Adventures in Wonderland", 'Lewis Carroll', ['Fantasy', 'Fiction']),
            ('84', 'Frankenstein', 'Mary Shelley', ['Science Fiction', 'Fiction']),
            ('345', 'Dracula', 'Bram Stoker', ['Fantasy', 'Mystery']),
            ('98', 'A Tale of Two Cities', 'Charles Dickens', ['Fiction', 'History']),
            ('2701', 'Moby Dick; or, The Whale', 'Herman Melville', ['Fiction', 'Adventure']),
            ('74', 'The Adventures of Tom Sawyer', 'Mark Twain', ['Adventure', 'Fiction']),
            ('514', 'Little Women', 'Louisa May Alcott', ['Fiction', 'Romance']),
            ('1661', 'The Adventures of Sherlock Holmes', 'Arthur Conan Doyle', ['Mystery', 'Fiction']),
            ('5200', 'Metamorphosis', 'Franz Kafka', ['Fiction', 'Fantasy']),
            ('520', 'The Invisible Man', 'H. G. Wells', ['Science Fiction', 'Fiction']),
            ('1260', 'Jane Eyre', 'Charlotte Bronte', ['Romance', 'Fiction']),
        ]
        return [
            cls.persist(NormalizedBook(
                external_id=external_id, source='gutenberg', title=title, authors=[author], subjects=subjects,
                cover_url=f'https://www.gutenberg.org/cache/epub/{external_id}/pg{external_id}.cover.medium.jpg',
                source_url=f'https://www.gutenberg.org/ebooks/{external_id}',
                reading_url=f'https://www.gutenberg.org/cache/epub/{external_id}/pg{external_id}.txt',
                access_type=CatalogBook.PUBLIC_DOMAIN, copyright_status=CatalogBook.PUBLIC_DOMAIN_STATUS,
                license='Project Gutenberg public-domain edition', full_text_available=True,
                provider_sources=({
                    'provider': 'gutenberg', 'external_id': external_id,
                    'source_url': f'https://www.gutenberg.org/ebooks/{external_id}',
                    'reading_url': f'https://www.gutenberg.org/cache/epub/{external_id}/pg{external_id}.txt',
                    'access_type': CatalogBook.PUBLIC_DOMAIN,
                    'copyright_status': CatalogBook.PUBLIC_DOMAIN_STATUS,
                    'license': 'Project Gutenberg public-domain edition',
                    'internal_reading_allowed': True,
                },),
            ))
            for external_id, title, author, subjects in fallback_books[:max(1, int(limit))]
        ]

    @classmethod
    def enabled_provider_names(cls) -> list[str]:
        """Return provider names currently allowed by settings and database policy."""
        enabled = []
        configured = getattr(settings, 'BOOK_PROVIDERS_ENABLED', {})
        for provider in cls.providers:
            if not configured.get(provider.name, True):
                continue
            status = ProviderStatus.objects.filter(provider=provider.name).first()
            if status is not None and not status.is_enabled:
                continue
            enabled.append(provider.name)
        return enabled

    @classmethod
    def search(cls, query: str, filters: dict | None = None, page: int = 1) -> tuple[list[NormalizedBook], int, list[str]]:
        results: list[NormalizedBook] = []
        errors: list[str] = []
        total = 0
        seen: set[tuple[str, str]] = set()
        enabled_names = set(cls.enabled_provider_names())
        for provider in cls.providers:
            if provider.name not in enabled_names:
                continue
            try:
                provider_results, provider_total = provider.search_books(query, filters, page)
                total = max(total, provider_total)
                cls._record_success(provider.name)
            except ProviderUnavailable:
                errors.append(provider.name)
                cls._record_failure(provider.name, 'Provider request failed.')
                continue
            for result in provider_results:
                key = (result.isbn13 or result.isbn10 or result.title.casefold(), (result.authors[0] if result.authors else '').casefold())
                if key not in seen:
                    seen.add(key)
                    results.append(result)
        return results, total, errors

    @staticmethod
    def _record_success(provider: str) -> None:
        ProviderStatus.objects.update_or_create(provider=provider, defaults={'last_success_at': timezone.now(), 'last_error': '', 'failure_count': 0})

    @staticmethod
    def _record_failure(provider: str, message: str) -> None:
        status, _ = ProviderStatus.objects.get_or_create(provider=provider)
        status.failure_count += 1
        status.last_error = message
        status.save(update_fields=['failure_count', 'last_error'])

    @staticmethod
    def persist(result: NormalizedBook) -> CatalogBook:
        normalized_languages = [normalize_language(language) for language in result.languages[:8]]
        rights_verified = result.copyright_status in {
            CatalogBook.PUBLIC_DOMAIN_STATUS,
            CatalogBook.OPEN_LICENSE,
            CatalogBook.AUTHORIZED,
        }
        license_url = 'https://www.gutenberg.org/policy/license.html' if result.source == 'gutenberg' or 'gutenberg.org' in result.source_url else ''
        defaults = {
            'title': result.title, 'authors': result.authors, 'description': result.description,
            'subjects': result.subjects, 'languages': normalized_languages, 'original_language': normalized_languages[0] if normalized_languages else '',
            'publication_year': result.publication_year,
            'publisher': result.publisher, 'isbn10': result.isbn10, 'isbn13': result.isbn13,
            'cover_url': result.cover_url, 'source_url': result.source_url, 'reading_url': result.reading_url,
            'access_type': result.access_type, 'copyright_status': result.copyright_status, 'license': result.license,
            'license_url': license_url, 'license_verified_at': timezone.now() if rights_verified else None,
            'full_text_available': result.full_text_available, 'borrowable': result.borrowable, 'page_count': result.page_count,
        }
        identifier_query = Q()
        if result.isbn13:
            identifier_query |= Q(isbn13=result.isbn13)
        if result.isbn10:
            identifier_query |= Q(isbn10=result.isbn10)
        book = CatalogBook.objects.filter(identifier_query).first() if identifier_query else None
        if book:
            metadata_fields = (
                'title', 'authors', 'description', 'subjects', 'languages', 'original_language',
                'publication_year', 'publisher', 'isbn10', 'isbn13', 'cover_url', 'page_count',
            )
            for field in metadata_fields:
                value = defaults[field]
                if value not in ('', [], None, False):
                    setattr(book, field, value)
            # An external-only edition must never replace an existing authorized reader source.
            if result.full_text_available or not book.full_text_available:
                for field in ('source_url', 'reading_url', 'access_type', 'copyright_status', 'license', 'full_text_available', 'borrowable'):
                    setattr(book, field, defaults[field])
            book.save()
        else:
            book, _ = CatalogBook.objects.update_or_create(source=result.source, external_id=result.external_id, defaults=defaults)
        for source in result.provider_sources:
            BookSource.objects.update_or_create(provider=source['provider'], external_id=source['external_id'], defaults={'book': book, **source})
        if book.source != result.source or book.external_id != result.external_id:
            BookSource.objects.update_or_create(
                provider=result.source, external_id=result.external_id,
                defaults={
                    'book': book, 'source_url': result.source_url, 'reading_url': result.reading_url,
                    'access_type': result.access_type, 'copyright_status': result.copyright_status,
                    'license': result.license, 'internal_reading_allowed': result.full_text_available,
                },
            )
        assign_asian_category(book)
        return book


def fetch_reader_text(book: CatalogBook) -> str:
    """Retrieve plain text only from an explicitly authorized source."""
    if not book.can_read_in_app:
        raise PermissionError('This source is not authorized for in-app reading.')
    parsed = urlparse(book.reading_url)
    if parsed.scheme != 'https' or parsed.hostname not in {'www.gutenberg.org', 'gutenberg.org'}:
        raise PermissionError('This reading source is not on the authorized allowlist.')
    cache_key = f'catalogue-text:{book.pk}:{book.updated_at.timestamp()}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    request = Request(book.reading_url, headers={'User-Agent': settings.BOOK_PROVIDER_USER_AGENT, 'Accept': 'text/plain'})
    try:
        with urlopen(request, timeout=10) as response:
            if response.status != 200 or 'text' not in response.headers.get_content_type():
                raise ProviderUnavailable('The reading source returned an unsupported format.')
            raw = response.read(2_000_000).decode('utf-8', errors='replace')
    except (HTTPError, URLError, TimeoutError) as error:
        raise ProviderUnavailable('The reading source is temporarily unavailable.') from error
    text = clean_gutenberg_front_matter(re.sub(r'\r\n?', '\n', raw)).strip()
    cache.set(cache_key, text, 60 * 60)
    return text


def clean_gutenberg_front_matter(text: str) -> str:
    """Remove Gutenberg licensing and metadata around the work itself."""
    start_marker = re.compile(
        r'^\s*(?:#+\s*)?\*{3}\s*start\s+of\s+(?:the\s+)?project\s+gutenberg\s+ebook\b[^\n]*\n',
        re.IGNORECASE | re.MULTILINE,
    )
    end_marker = re.compile(
        r'\n\s*(?:#+\s*)?\*{3}\s*end\s+of\s+(?:the\s+)?project\s+gutenberg\s+ebook\b[^\n]*',
        re.IGNORECASE,
    )
    start_match = start_marker.search(text)
    cleaned = text[start_match.end():].lstrip() if start_match else text
    end_match = end_marker.search(cleaned)
    return cleaned[:end_match.start()].rstrip() if end_match else cleaned


def split_reader_sections(text: str) -> list[dict]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r'\n\s*\n', text) if paragraph.strip()]
    sections: list[dict] = []
    title = 'Beginning'
    content: list[str] = []
    for paragraph in paragraphs:
        is_heading = len(paragraph) < 100 and (paragraph.isupper() or re.match(r'^(CHAPTER|BOOK|PART)\s+[IVXLC\d]', paragraph, re.IGNORECASE))
        if is_heading and content:
            sections.append({'title': title.title() if title.isupper() else title, 'paragraphs': content})
            title, content = paragraph, []
        else:
            content.append(paragraph)
    if content:
        sections.append({'title': title.title() if title.isupper() else title, 'paragraphs': content})
    return sections or [{'title': 'Beginning', 'paragraphs': []}]


def _docx_paragraphs(upload) -> list[dict]:
    if upload.original_filename.lower().endswith('.docx'):
        with upload.file.open('rb') as manuscript:
            with zipfile.ZipFile(manuscript) as archive:
                document = ElementTree.fromstring(archive.read('word/document.xml'))
        namespace = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        paragraphs = []
        for paragraph in document.findall('.//w:p', namespace):
            text_parts = []
            html_parts = []
            for run in paragraph.findall('./w:r', namespace):
                run_properties = run.find('./w:rPr', namespace)
                styles = []
                if run_properties is not None:
                    if run_properties.find('./w:b', namespace) is not None:
                        styles.append('strong')
                    if run_properties.find('./w:i', namespace) is not None:
                        styles.append('em')
                    if run_properties.find('./w:u', namespace) is not None:
                        styles.append('u')
                    if run_properties.find('./w:strike', namespace) is not None:
                        styles.append('s')
                    vertical = run_properties.find('./w:vertAlign', namespace)
                    if vertical is not None and vertical.get('{%s}val' % namespace['w']) == 'superscript':
                        styles.append('sup')
                    if vertical is not None and vertical.get('{%s}val' % namespace['w']) == 'subscript':
                        styles.append('sub')
                run_text = ''.join(node.text or '' for node in run.findall('./w:t', namespace))
                if run.find('./w:tab', namespace) is not None:
                    run_text += '\t'
                if run.find('./w:br', namespace) is not None:
                    run_text += '\n'
                text_parts.append(run_text)
                formatted = escape(run_text).replace('\n', '<br>').replace('\t', '&emsp;')
                for tag in styles:
                    formatted = f'<{tag}>{formatted}</{tag}>'
                html_parts.append(formatted)
            text = ''.join(text_parts).strip()
            if text:
                paragraph_properties = paragraph.find('./w:pPr', namespace)
                style = paragraph_properties.find('./w:pStyle', namespace) if paragraph_properties is not None else None
                style_name = style.get('{%s}val' % namespace['w'], '') if style is not None else ''
                numbering = paragraph_properties.find('./w:numPr', namespace) if paragraph_properties is not None else None
                is_bullet = numbering is not None and style_name.lower().find('list') >= 0
                paragraphs.append({
                    'text': text,
                    'html': ('&bull; ' if is_bullet else '') + ''.join(html_parts),
                    'is_heading': style_name.lower().startswith('heading') or (len(text) < 100 and text.isupper()),
                })
        return paragraphs
    raise ProviderUnavailable('This uploaded manuscript format cannot be read in the browser.')


def fetch_uploaded_book_text(upload) -> str:
    """Extract plain text from an uploaded DOCX manuscript."""
    return '\n\n'.join(paragraph['text'] for paragraph in _docx_paragraphs(upload))


def fetch_uploaded_book_sections(upload) -> list[dict]:
    paragraphs = _docx_paragraphs(upload)
    sections = []
    title = 'Beginning'
    content = []
    for paragraph in paragraphs:
        if paragraph['is_heading'] and content:
            sections.append({'title': title.title() if title.isupper() else title, 'paragraphs': content})
            title, content = paragraph['text'], []
        else:
            content.append(paragraph)
    if content:
        sections.append({'title': title.title() if title.isupper() else title, 'paragraphs': content})
    return sections or [{'title': 'Beginning', 'paragraphs': []}]


# ============================================================================
# EPUB PROCESSING SERVICE
# ============================================================================

import hashlib
import io
import os
import tempfile
import zipfile
from pathlib import Path

from ebooklib import epub
from lxml import etree
import bleach


class EPUBProcessingError(Exception):
    """Error during EPUB processing."""
    pass


class EPUBProcessor:
    """Process and extract metadata/content from EPUB files."""
    
    ALLOWED_HTML_TAGS = {'p', 'br', 'strong', 'em', 'b', 'i', 'a', 'span', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'ul', 'ol', 'li'}
    ALLOWED_ATTRIBUTES = {'a': ['href'], 'span': ['class'], 'div': ['class']}
    
    @staticmethod
    def validate_epub(file_path: str) -> bool:
        """Validate that file is a valid EPUB."""
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                # EPUB must have mimetype as first file
                if zf.namelist()[0] != 'mimetype':
                    return False
                
                mimetype_content = zf.read('mimetype').decode('utf-8').strip()
                if mimetype_content != 'application/epub+zip':
                    return False
                
                # Must have META-INF/container.xml
                if 'META-INF/container.xml' not in zf.namelist():
                    return False
                
                return True
        except (zipfile.BadZipFile, Exception):
            return False
    
    @staticmethod
    def extract_metadata(file_path: str) -> dict:
        """Extract title, author, language from EPUB."""
        metadata = {
            'title': 'Untitled',
            'authors': [],
            'language': 'en',
            'publisher': '',
            'publication_date': None,
        }
        
        try:
            book = epub.read_epub(file_path)
            
            # Title
            if book.get('title'):
                metadata['title'] = book.get('title')
            
            # Author
            for author in book.get_authors():
                if author:
                    metadata['authors'].append(author)
            
            # Language
            if book.get('lang'):
                metadata['language'] = book.get('lang')
            
            # Publisher
            for item in book.get_items():
                if item.get_name() == 'metadata':
                    if hasattr(item, 'publisher'):
                        metadata['publisher'] = item.publisher
                        break
            
        except Exception as e:
            import logging
            logging.error(f'Error extracting EPUB metadata: {e}')
        
        return metadata
    
    @staticmethod
    def extract_chapters(file_path: str, max_chapters: int = 500) -> list[dict]:
        """
        Extract chapters from EPUB.
        
        Returns list of dicts with 'title' and 'html_content' keys.
        HTML content is sanitized.
        """
        chapters = []
        
        try:
            book = epub.read_epub(file_path)
            
            for item in book.get_items():
                if item.get_type() == epub.ITEM_DOCUMENT:
                    try:
                        # Get the HTML content
                        html_content = item.get_content().decode('utf-8', errors='replace')
                        
                        # Parse and extract text
                        root = etree.HTML(html_content)
                        
                        # Extract chapter title if available
                        title = 'Chapter'
                        for heading in root.xpath('//h1 | //h2 | //h3'):
                            if heading.text:
                                title = heading.text
                                break
                        
                        # Sanitize HTML
                        sanitized_html = bleach.clean(
                            html_content,
                            tags=EPUBProcessor.ALLOWED_HTML_TAGS,
                            attributes=EPUBProcessor.ALLOWED_ATTRIBUTES,
                            strip=True
                        )
                        
                        chapters.append({
                            'title': title,
                            'html_content': sanitized_html,
                            'file_name': item.file_name,
                        })
                        
                        if len(chapters) >= max_chapters:
                            break
                    
                    except Exception as e:
                        import logging
                        logging.warning(f'Error processing chapter: {e}')
                        continue
        
        except Exception as e:
            import logging
            logging.error(f'Error extracting EPUB chapters: {e}')
        
        return chapters


# ============================================================================
# FILE DOWNLOADER & VALIDATOR
# ============================================================================

class FileDownloadError(Exception):
    """Error during file download."""
    pass


class FileValidator:
    """Validate downloaded book files."""
    
    # Maximum file size: 500 MB
    MAX_FILE_SIZE = 500 * 1024 * 1024
    
    # Allowed MIME types for downloads
    ALLOWED_MIMETYPES = {
        'application/epub+zip': 'epub',
        'application/pdf': 'pdf',
        'text/plain': 'txt',
    }
    
    @staticmethod
    def calculate_checksum(file_path: str, algorithm: str = 'sha256') -> str:
        """Calculate checksum of file."""
        hasher = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    @staticmethod
    def validate_file_format(file_path: str) -> str | None:
        """
        Validate downloaded file format.
        
        Returns the detected format (epub, pdf, txt) or None if invalid.
        """
        try:
            # Check file size
            if os.path.getsize(file_path) > FileValidator.MAX_FILE_SIZE:
                return None
            
            # Check EPUB
            if FileValidator._is_valid_epub(file_path):
                return 'epub'
            
            # Check if it's plain text
            with open(file_path, 'rb') as f:
                header = f.read(4)
                if header == b'%PDF':
                    return 'pdf'
                
                # Try to read as text
                try:
                    with open(file_path, 'r', encoding='utf-8') as tf:
                        tf.read(1000)
                    return 'txt'
                except (UnicodeDecodeError, Exception):
                    pass
            
            return None
        
        except Exception:
            return None
    
    @staticmethod
    def _is_valid_epub(file_path: str) -> bool:
        """Check if file is valid EPUB."""
        try:
            return EPUBProcessor.validate_epub(file_path)
        except Exception:
            return False


class BookFileDownloader:
    """Download book files from approved sources."""
    
    TIMEOUT_SECONDS = 30
    CHUNK_SIZE = 8192
    
    def __init__(self, user_agent: str = None):
        self.user_agent = user_agent or settings.BOOK_PROVIDER_USER_AGENT
    
    def download_file(self, url: str, source: str, external_id: str, temp_dir: str = None) -> tuple[str, str]:
        """
        Download file from URL.
        
        Args:
            url: Download URL
            source: Source provider name (for validation)
            external_id: External book ID (for validation)
            temp_dir: Temporary directory (uses system temp if not provided)
        
        Returns:
            Tuple of (file_path, detected_format)
        
        Raises:
            FileDownloadError: If download fails or file is invalid
            PermissionError: If source/URL is not approved
        """
        # Security: Only allow downloads from approved sources
        approved_hosts = self._get_approved_hosts()
        
        parsed_url = urlparse(url)
        if parsed_url.hostname not in approved_hosts:
            raise PermissionError(f'Host {parsed_url.hostname} is not approved for downloads.')
        
        # Create temp file
        if temp_dir is None:
            temp_dir = tempfile.gettempdir()
        
        temp_file = os.path.join(temp_dir, f'book_download_{source}_{external_id}_{int(timezone.now().timestamp())}.tmp')
        
        try:
            # Download file
            request = Request(url, headers={'User-Agent': self.user_agent})
            with urlopen(request, timeout=self.TIMEOUT_SECONDS) as response:
                if response.status != 200:
                    raise FileDownloadError(f'Server returned status {response.status}')
                
                # Check content length
                content_length = response.headers.get('Content-Length')
                if content_length and int(content_length) > FileValidator.MAX_FILE_SIZE:
                    raise FileDownloadError(f'File is too large ({content_length} bytes)')
                
                # Download with size limit
                bytes_downloaded = 0
                with open(temp_file, 'wb') as f:
                    while True:
                        chunk = response.read(self.CHUNK_SIZE)
                        if not chunk:
                            break
                        f.write(chunk)
                        bytes_downloaded += len(chunk)
                        if bytes_downloaded > FileValidator.MAX_FILE_SIZE:
                            raise FileDownloadError('File is too large')
            
            # Validate format
            detected_format = FileValidator.validate_file_format(temp_file)
            if not detected_format:
                raise FileDownloadError('File format is invalid or not supported')
            
            return temp_file, detected_format
        
        except FileDownloadError:
            raise
        except (HTTPError, URLError, TimeoutError) as e:
            raise FileDownloadError(f'Download failed: {e}') from e
        except Exception as e:
            raise FileDownloadError(f'Unexpected error during download: {e}') from e
        finally:
            # Clean up if something failed
            pass
    
    @staticmethod
    def _get_approved_hosts() -> set[str]:
        """Get set of approved hosts for downloads."""
        hosts = {
            'www.gutenberg.org',
            'gutenberg.org',
            'standardebooks.org',
            'www.standardebooks.org',
            'archive.org',
            'www.archive.org',
        }
        
        # Allow configuration override
        if hasattr(settings, 'BOOK_IMPORT_APPROVED_HOSTS'):
            hosts.update(settings.BOOK_IMPORT_APPROVED_HOSTS)
        
        return hosts


# ============================================================================
# BOOK IMPORT WORKFLOW SERVICE
# ============================================================================

class RightsCheckError(Exception):
    """Error during rights verification."""
    pass


class RightsChecker:
    """Verify that a book can be legally imported and stored."""
    
    ALLOWED_COPYRIGHT_STATUSES = {
        CatalogBook.PUBLIC_DOMAIN_STATUS,
        CatalogBook.OPEN_LICENSE,
        CatalogBook.AUTHORIZED,
    }
    
    @staticmethod
    def can_import_book(catalog_book: 'CatalogBook', book_source: 'BookSource') -> tuple[bool, str]:
        """
        Check if a book can be imported.
        
        Returns:
            Tuple of (can_import, reason)
        """
        # Must have redistributable access
        if not book_source.internal_reading_allowed:
            return False, 'Source does not permit internal reading'
        
        # Must have full text available
        if not catalog_book.full_text_available:
            return False, 'Full text is not available'
        
        # Must have approved rights status
        if catalog_book.copyright_status not in RightsChecker.ALLOWED_COPYRIGHT_STATUSES:
            if catalog_book.copyright_status == CatalogBook.UNKNOWN:
                return False, 'Rights status is unknown - cannot import'
            elif catalog_book.copyright_status == CatalogBook.COPYRIGHTED:
                return False, 'Book is copyrighted and cannot be imported'
            else:
                return False, f'Copyright status "{catalog_book.copyright_status}" does not allow import'
        
        # Must have reading URL
        if not book_source.reading_url:
            return False, 'No reading URL available'
        
        return True, ''
    
    @staticmethod
    def verify_source_eligibility(provider: str) -> bool:
        """Check if a provider is enabled for importing."""
        configured = getattr(settings, 'BOOK_PROVIDERS_ENABLED', {})
        if provider in configured and not configured[provider]:
            return False

        try:
            status = ProviderStatus.objects.get(provider=provider)
            return status.is_enabled
        except ProviderStatus.DoesNotExist:
            # If not in DB, the provider is only approved when explicitly enabled in settings.
            return bool(configured.get(provider, False))


class BookImportService:
    """Orchestrate the complete book import workflow."""
    
    @staticmethod
    def import_book(
        user: 'User',
        catalog_book: 'CatalogBook',
        book_source: 'BookSource',
        force: bool = False,
    ) -> 'ImportedBook':
        """
        Import a book from an external source.
        
        Args:
            user: User initiating the import
            catalog_book: The discovered book
            book_source: The specific edition/source
            force: Force reimport even if already imported
        
        Returns:
            ImportedBook instance
        
        Raises:
            RightsCheckError: If rights verification fails
            FileDownloadError: If download fails
            EPUBProcessingError: If processing fails
        """
        from .models import ImportedBook, BookFile, ImportJob
        
        # Check if already imported
        try:
            existing = ImportedBook.objects.get(catalog_book=catalog_book)
            if existing.status == ImportedBook.IMPORTED and not force:
                return existing
            if not force:
                raise ValueError('Book is already being imported or was imported')
        except ImportedBook.DoesNotExist:
            pass
        
        # Verify rights
        can_import, reason = RightsChecker.can_import_book(catalog_book, book_source)
        if not can_import:
            raise RightsCheckError(f'Cannot import book: {reason}')
        
        # Verify provider is enabled
        if not RightsChecker.verify_source_eligibility(book_source.provider):
            raise RightsCheckError(f'Provider {book_source.provider} is not enabled for imports')
        
        # Create ImportedBook record
        imported_book = ImportedBook.objects.create(
            catalog_book=catalog_book,
            book_source=book_source,
            status=ImportedBook.QUEUED,
        )
        
        # Create ImportJob
        import_job = ImportJob.objects.create(
            imported_book=imported_book,
            initiated_by=user,
            status=ImportJob.PENDING,
        )
        
        try:
            # Download file
            import_job.status = ImportJob.PROCESSING
            import_job.current_step = 'Downloading...'
            import_job.save(update_fields=['status', 'current_step'])
            
            imported_book.status = ImportedBook.DOWNLOADING
            imported_book.save(update_fields=['status'])
            
            downloader = BookFileDownloader()
            temp_file, detected_format = downloader.download_file(
                book_source.reading_url,
                book_source.provider,
                book_source.external_id,
            )
            
            # Calculate checksum
            checksum = FileValidator.calculate_checksum(temp_file)
            
            # Process file
            import_job.current_step = 'Processing...'
            import_job.save(update_fields=['current_step'])
            
            imported_book.status = ImportedBook.PROCESSING
            imported_book.format = detected_format
            imported_book.checksum = checksum
            imported_book.file_size = os.path.getsize(temp_file)
            imported_book.save(update_fields=['status', 'format', 'checksum', 'file_size'])
            
            # Store file permanently
            from django.core.files.base import File as DjangoFile
            from django.core.files.storage import default_storage
            
            storage_dir = f'books/imported/{catalog_book.source}/{catalog_book.external_id}'
            storage_filename = f'book.{detected_format}'
            storage_path = f'{storage_dir}/{storage_filename}'
            
            with open(temp_file, 'rb') as f:
                default_storage.save(storage_path, DjangoFile(f))
            
            # Create BookFile record
            book_file = BookFile.objects.create(
                imported_book=imported_book,
                file_path=storage_path,
                file_size=os.path.getsize(temp_file),
                checksum=checksum,
            )
            
            # Process EPUB if applicable
            if detected_format == 'epub':
                try:
                    chapters = EPUBProcessor.extract_chapters(temp_file)
                    book_file.chapters_count = len(chapters)
                except Exception as e:
                    import logging
                    logging.warning(f'Error extracting EPUB chapters: {e}')
            
            book_file.processed_at = timezone.now()
            book_file.save(update_fields=['chapters_count', 'processed_at'])
            
            # Mark as imported
            imported_book.status = ImportedBook.IMPORTED
            imported_book.imported_at = timezone.now()
            imported_book.save(update_fields=['status', 'imported_at'])
            
            import_job.status = ImportJob.SUCCESS
            import_job.progress_percent = 100
            import_job.completed_at = timezone.now()
            import_job.save(update_fields=['status', 'progress_percent', 'completed_at'])
            
            return imported_book
        
        except Exception as e:
            # Mark as failed
            imported_book.status = ImportedBook.FAILED
            imported_book.import_error = str(e)
            imported_book.save(update_fields=['status', 'import_error'])
            
            import_job.status = ImportJob.FAILED
            import_job.error_message = str(e)
            import_job.completed_at = timezone.now()
            import_job.save(update_fields=['status', 'error_message', 'completed_at'])
            
            # Clean up temp file
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass
            
            raise