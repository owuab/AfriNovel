# Provider Integration Guide

This guide explains how to integrate new book providers into the BookClub import system.

## Provider Interface

All providers must implement the `BookProvider` abstract base class:

```python
from books.services import BookProvider

class MyProvider(BookProvider):
    PROVIDER_NAME = 'my_provider'
    PROVIDER_DISPLAY_NAME = 'My Book Provider'
    
    def search_books(self, query, offset=0, limit=20):
        """
        Search for books matching query.
        
        Args:
            query: Search string (minimum 3 characters)
            offset: Results offset for pagination
            limit: Maximum results to return
        
        Returns:
            tuple: (list of DiscoveredBook, total_count)
            
        Raises:
            ProviderUnavailable: If API is down
            ProviderError: If search fails
        """
        pass
    
    def get_reading_url(self, book):
        """
        Get direct download URL for book.
        
        Args:
            book: DiscoveredBook instance
        
        Returns:
            str: Direct URL to book file (EPUB/PDF/TXT)
        """
        pass
    
    def get_copyright_status(self, book):
        """
        Get copyright status of book.
        
        Args:
            book: DiscoveredBook instance
        
        Returns:
            str: One of CatalogBook copyright status constants
                - 'public_domain'
                - 'open_license'
                - 'copyrighted'
                - 'unknown'
        """
        pass
```

## DiscoveredBook Data Structure

Each provider returns `DiscoveredBook` instances:

```python
from books.services import DiscoveredBook

class DiscoveredBook:
    title: str                           # Book title
    authors: List[str]                  # Author names
    external_id: str                    # Provider's unique ID
    description: str                    # Book summary
    publication_year: int               # Year published
    language: str                       # ISO 639-1 code (e.g., 'en')
    page_count: int                     # Number of pages (optional)
    cover_url: str                      # URL to cover image (optional)
    source_url: str                     # Link to provider's page
    reading_url: str                    # Direct URL to book file
    provider: str                       # Provider name (e.g., 'gutenberg')
    copyright_status: str               # Copyright status
    formats: List[str]                  # Available formats ['epub', 'pdf', 'txt']
```

## Example 1: Open Library Provider

Here's how the Open Library provider is implemented:

```python
from urllib.request import urlopen
from urllib.error import HTTPError
import json
from .services import BookProvider, DiscoveredBook

class OpenLibraryProvider(BookProvider):
    PROVIDER_NAME = 'open_library'
    PROVIDER_DISPLAY_NAME = 'Open Library'
    BASE_URL = 'https://openlibrary.org/api/'
    
    def search_books(self, query, offset=0, limit=20):
        """Search via Open Library Search API"""
        try:
            url = (
                f"{self.BASE_URL}search.json"
                f"?q={query}"
                f"&offset={offset}"
                f"&limit={limit}"
            )
            
            with urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
            
            books = []
            for doc in data.get('docs', []):
                # Skip books without full text available
                if not doc.get('has_fulltext'):
                    continue
                
                book = DiscoveredBook(
                    title=doc['title'],
                    authors=doc.get('author_name', []),
                    external_id=doc['key'].split('/')[-1],
                    description=doc.get('first_sentence', ''),
                    publication_year=doc.get('first_publish_year', 0),
                    language=doc.get('language', ['en'])[0] if doc.get('language') else 'en',
                    page_count=doc.get('number_of_pages', 0),
                    cover_url=f"https://covers.openlibrary.org/b/id/{doc.get('cover_i')}-M.jpg" if doc.get('cover_i') else None,
                    source_url=f"https://openlibrary.org{doc['key']}",
                    reading_url=self._get_reading_url(doc['key']),
                    provider=self.PROVIDER_NAME,
                    copyright_status=self._get_copyright_status(doc),
                    formats=['epub', 'pdf', 'txt'],
                )
                books.append(book)
            
            return books, data.get('num_found', 0)
        
        except HTTPError as e:
            if e.code == 503:
                raise ProviderUnavailable(f"Open Library API temporarily down: {e}")
            raise ProviderError(f"Search failed: {e}")
    
    def get_reading_url(self, book):
        """Open Library links to Internet Archive for full text"""
        # Try multiple formats
        for edition_key in self._get_edition_keys(book.external_id):
            url = f"https://openlibrary.org/edition/{edition_key}"
            # Fetch edition details to find reading links
            try:
                with urlopen(url + '.json', timeout=10) as response:
                    data = json.loads(response.read().decode())
                
                # Check for various reading links
                if 'ia_loaded_id' in data:
                    ia_id = data['ia_loaded_id']
                    return f"https://archive.org/download/{ia_id}/{ia_id}.epub"
            except:
                continue
        
        return None
    
    def get_copyright_status(self, book):
        """Determine copyright status from publication year"""
        if book.publication_year and book.publication_year < 1928:
            return 'public_domain'
        return 'unknown'
```

## Example 2: Project Gutenberg Provider

```python
class GutenbergProvider(BookProvider):
    PROVIDER_NAME = 'gutenberg'
    PROVIDER_DISPLAY_NAME = 'Project Gutenberg'
    API_URL = 'https://gutendex.com/books'
    
    def search_books(self, query, offset=0, limit=20):
        """Search via Gutendex API (Gutenberg data)"""
        try:
            url = f"{self.API_URL}?search={query}&page={offset // limit + 1}"
            
            with urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
            
            books = []
            for result in data.get('results', []):
                book = DiscoveredBook(
                    title=result['title'],
                    authors=[a['name'] for a in result.get('authors', [])],
                    external_id=str(result['id']),
                    description=result.get('description', ''),
                    publication_year=0,
                    language='en',
                    cover_url=result.get('cover_image'),
                    source_url=f"https://www.gutenberg.org/ebooks/{result['id']}",
                    reading_url=self._get_epub_url(result['id']),
                    provider=self.PROVIDER_NAME,
                    copyright_status='public_domain',  # Gutenberg books are public domain
                    formats=result.get('formats', {}),
                )
                books.append(book)
            
            return books, data.get('count', 0)
        
        except Exception as e:
            raise ProviderError(f"Gutenberg search failed: {e}")
    
    def _get_epub_url(self, book_id):
        """Get direct EPUB URL for Gutenberg book"""
        return f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt.utf-8"
    
    def get_reading_url(self, book):
        return f"https://www.gutenberg.org/cache/epub/{book.external_id}/pg{book.external_id}.txt.utf-8"
    
    def get_copyright_status(self, book):
        return 'public_domain'
```

## Example 3: Internet Archive Provider

```python
class InternetArchiveProvider(BookProvider):
    PROVIDER_NAME = 'internet_archive'
    PROVIDER_DISPLAY_NAME = 'Internet Archive'
    SEARCH_URL = 'https://archive.org/advancedsearch.php'
    
    def search_books(self, query, offset=0, limit=20):
        """Search Internet Archive's books collection"""
        try:
            # IA uses Lucene query syntax
            params = {
                'q': f'(title:({query}) OR creator:({query})) AND mediatype:texts',
                'output': 'json',
                'rows': limit,
                'start': offset,
            }
            
            url = f"{self.SEARCH_URL}?" + urlencode(params)
            
            with urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
            
            books = []
            for doc in data['response'].get('docs', []):
                # Only include books with text available
                if doc.get('has_text') != 'true':
                    continue
                
                book = DiscoveredBook(
                    title=doc['title'],
                    authors=[doc['creator']] if 'creator' in doc else [],
                    external_id=doc['identifier'],
                    description=doc.get('description', ''),
                    publication_year=int(doc['year'][0]) if 'year' in doc else 0,
                    language=doc.get('language', ['en'])[0] if 'language' in doc else 'en',
                    cover_url=f"https://archive.org/download/{doc['identifier']}/page/cover.jpg",
                    source_url=f"https://archive.org/details/{doc['identifier']}",
                    reading_url=self._get_reading_url(doc),
                    provider=self.PROVIDER_NAME,
                    copyright_status=self._get_copyright_status(doc),
                    formats=['epub', 'pdf', 'txt'],
                )
                books.append(book)
            
            return books, data['response'].get('numFound', 0)
        
        except Exception as e:
            raise ProviderError(f"Internet Archive search failed: {e}")
    
    def _get_reading_url(self, doc):
        """Get EPUB URL from Internet Archive metadata"""
        ia_id = doc['identifier']
        # IA's book reading API
        return f"https://archive.org/download/{ia_id}/{ia_id}.epub"
    
    def _get_copyright_status(self, doc):
        """Determine from collection metadata"""
        if 'public_domain' in doc.get('collection', []):
            return 'public_domain'
        
        # Check license
        license_field = doc.get('licenseurl', '')
        if 'creativecommons' in license_field or 'cc' in license_field:
            return 'open_license'
        
        return 'unknown'
    
    def get_reading_url(self, book):
        return f"https://archive.org/download/{book.external_id}/{book.external_id}.epub"
    
    def get_copyright_status(self, book):
        # Query IA metadata API for latest status
        try:
            url = f"https://archive.org/metadata/{book.external_id}"
            with urlopen(url, timeout=10) as response:
                metadata = json.loads(response.read().decode())
            
            if metadata['metadata'].get('publicdate'):
                return 'public_domain'
            return 'unknown'
        except:
            return 'unknown'
```

## Example 4: Custom Provider with Authentication

```python
class PrivateLibraryProvider(BookProvider):
    """Example: Custom provider with API authentication"""
    PROVIDER_NAME = 'private_library'
    PROVIDER_DISPLAY_NAME = 'My Private Library'
    API_KEY = os.getenv('PRIVATE_LIBRARY_API_KEY')
    BASE_URL = 'https://api.private-library.com/v1'
    
    def search_books(self, query, offset=0, limit=20):
        """Search private library API"""
        headers = {
            'Authorization': f'Bearer {self.API_KEY}',
            'Content-Type': 'application/json',
        }
        
        params = {
            'q': query,
            'offset': offset,
            'limit': limit,
        }
        
        try:
            url = f"{self.BASE_URL}/books?" + urlencode(params)
            req = Request(url, headers=headers)
            
            with urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
            
            books = []
            for item in data['books']:
                # Only import books with redistribution rights
                if not item.get('redistribution_allowed'):
                    continue
                
                book = DiscoveredBook(
                    title=item['title'],
                    authors=item.get('authors', []),
                    external_id=item['id'],
                    description=item.get('description', ''),
                    publication_year=item.get('year', 0),
                    language=item.get('language', 'en'),
                    cover_url=item.get('cover_url'),
                    source_url=item.get('url'),
                    reading_url=item['download_url'],  # Private URL
                    provider=self.PROVIDER_NAME,
                    copyright_status='open_license' if item.get('license') else 'unknown',
                    formats=['epub'],
                )
                books.append(book)
            
            return books, data.get('total', 0)
        
        except Exception as e:
            raise ProviderError(f"Private library search failed: {e}")
    
    def get_reading_url(self, book):
        """Get authenticated download URL"""
        return f"{self.BASE_URL}/books/{book.external_id}/download?token={self.API_KEY}"
    
    def get_copyright_status(self, book):
        return 'open_license'
```

## Registering a Provider

1. **Implement the provider class** in `books/services.py`

2. **Register in CatalogService**:

```python
class CatalogService:
    PROVIDERS = [
        OpenLibraryProvider(),
        InternetArchiveProvider(),
        GutenbergProvider(),
        StandardEbooksProvider(),
        YourNewProvider(),  # Add here
    ]
```

3. **Add to Django settings** if needed:

```python
# bookclub/settings.py
BOOK_IMPORT_APPROVED_HOSTS.add('your-provider.com')

BOOK_PROVIDERS_ENABLED = {
    # ... existing ...
    'your_provider': os.getenv('PROVIDER_YOUR_PROVIDER_ENABLED', 'True') == 'True',
}
```

4. **Create ProviderStatus** record:

```python
from books.models import ProviderStatus

ProviderStatus.objects.create(
    provider='your_provider',
    is_enabled=True,
    last_checked=timezone.now(),
)
```

## Error Handling

Providers should raise appropriate exceptions:

```python
from books.services import (
    ProviderError,
    ProviderUnavailable,
    ProviderQuotaExceeded,
)

# API temporarily down
raise ProviderUnavailable("Gutenberg API returning 503")

# Search syntax error or invalid query
raise ProviderError("Invalid search query")

# Rate limited
raise ProviderQuotaExceeded("API rate limit exceeded, retry in 1 hour")
```

## Testing a Provider

```python
def test_my_provider():
    provider = MyProvider()
    
    # Test search
    books, total = provider.search_books('python')
    assert len(books) > 0
    assert total >= len(books)
    
    # Test first result
    book = books[0]
    assert book.title
    assert book.authors
    assert book.reading_url
    
    # Test reading URL
    url = provider.get_reading_url(book)
    assert url
    assert 'my-provider.com' in url
    
    # Test copyright status
    status = provider.get_copyright_status(book)
    assert status in ['public_domain', 'open_license', 'copyrighted', 'unknown']
```

## Best Practices

1. **Always validate URLs** against approved hosts in BookFileDownloader
2. **Handle API errors gracefully** with appropriate exceptions
3. **Implement timeout handling** for API calls
4. **Cache results** when possible to reduce API calls
5. **Validate data** before creating DiscoveredBook instances
6. **Document copyright status** clearly for legal compliance
7. **Rate limit API calls** to respect provider policies
8. **Verify full-text availability** before returning results
9. **Use standard formats** (EPUB > PDF > TXT) for best compatibility
10. **Monitor provider status** with ProviderStatus model
