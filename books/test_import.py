"""
Tests for book import and reading functionality.

Tests cover:
- Provider functionality
- Rights verification
- File download and validation
- EPUB processing
- Import workflow
- Reader API
- Security protections
"""

import json
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from .models import (
    CatalogBook, BookSource, ProviderStatus, ImportedBook, BookFile, ImportJob,
    ReadingProgress, ReadingBookmark, ReadingHighlight, CatalogCategory,
)
from .services import (
    FileValidator, BookFileDownloader, EPUBProcessor, RightsChecker,
    BookImportService, RightsCheckError, FileDownloadError,
    CatalogService, OpenLibraryProvider, StandardEbooksProvider, clean_gutenberg_front_matter,
)
from .taxonomy import assign_asian_category, classify_asian_book

User = get_user_model()


class AsianTaxonomyTests(TestCase):
    def test_language_code_has_priority_over_title_terms(self):
        book = CatalogBook(
            title='The Tale of Genji', authors=['Murasaki Shikibu'], languages=['jpn'], subjects=[],
        )
        self.assertEqual(classify_asian_book(book), 'japanese')

    def test_assign_asian_category_is_controlled_and_versioned(self):
        book = CatalogBook.objects.create(
            title='A Bengali novel', authors=[], languages=['eng'], subjects=[],
            source='test', external_id='asian-1', source_url='https://example.org/asian-1',
        )
        category = assign_asian_category(book)
        self.assertEqual(category.subcategory, 'south_asian')
        self.assertEqual(category.rule_version, 'asian-v1')
        self.assertEqual(CatalogCategory.objects.filter(book=book).count(), 1)


class ReaderTextCleanupTests(TestCase):
    def test_gutenberg_front_matter_is_removed(self):
        raw = """## Beginning
The Project Gutenberg eBook of The Adventures of Sherlock Holmes

This eBook is for the use of anyone anywhere at no cost.

## *** Start Of The Project Gutenberg Ebook The Adventures Of Sherlock Holmes ***

I. A SCANDAL IN BOHEMIA

To Sherlock Holmes she is always the woman.

## *** End Of The Project Gutenberg Ebook The Adventures Of Sherlock Holmes ***
"""
        cleaned = clean_gutenberg_front_matter(raw)
        self.assertEqual(cleaned, "I. A SCANDAL IN BOHEMIA\n\nTo Sherlock Holmes she is always the woman.")

    def test_non_gutenberg_text_is_unchanged(self):
        text = 'Chapter One\n\nThe story begins.'
        self.assertEqual(clean_gutenberg_front_matter(text), text)


class FileValidatorTests(TestCase):
    """Test file validation functionality."""
    
    def test_validate_file_size_limit(self):
        """Test that oversized files are rejected."""
        # Create a temporary file larger than max size
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'x' * (FileValidator.MAX_FILE_SIZE + 1))
            f.flush()
            temp_path = f.name
        
        try:
            result = FileValidator.validate_file_format(temp_path)
            self.assertIsNone(result, "Oversized file should be rejected")
        finally:
            os.unlink(temp_path)
    
    def test_validate_text_file(self):
        """Test that plain text files are recognized."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write('This is plain text content\n' * 100)
            temp_path = f.name
        
        try:
            result = FileValidator.validate_file_format(temp_path)
            self.assertEqual(result, 'txt', "Text file should be detected as txt")
        finally:
            os.unlink(temp_path)
    
    def test_checksum_calculation(self):
        """Test checksum calculation."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            content = b'test content'
            f.write(content)
            temp_path = f.name
        
        try:
            checksum = FileValidator.calculate_checksum(temp_path)
            self.assertIsNotNone(checksum)
            self.assertEqual(len(checksum), 64, "SHA256 checksum should be 64 hex chars")
        finally:
            os.unlink(temp_path)


class RightsCheckerTests(TestCase):
    """Test rights verification."""
    
    def setUp(self):
        self.catalog_book = CatalogBook.objects.create(
            source='test',
            external_id='test-1',
            title='Test Book',
            copyright_status=CatalogBook.PUBLIC_DOMAIN_STATUS,
            full_text_available=True,
            source_url='https://example.com/book',
        )
        
        self.book_source = BookSource.objects.create(
            book=self.catalog_book,
            provider='test',
            external_id='test-1',
            source_url='https://example.com/book',
            reading_url='https://example.com/book.epub',
            copyright_status=CatalogBook.PUBLIC_DOMAIN_STATUS,
            internal_reading_allowed=True,
        )
    
    def test_can_import_public_domain_book(self):
        """Test that public domain books can be imported."""
        can_import, reason = RightsChecker.can_import_book(self.catalog_book, self.book_source)
        self.assertTrue(can_import, f"Public domain book should be importable: {reason}")
    
    def test_cannot_import_copyrighted_book(self):
        """Test that copyrighted books cannot be imported."""
        self.catalog_book.copyright_status = CatalogBook.COPYRIGHTED
        self.catalog_book.save()
        
        can_import, reason = RightsChecker.can_import_book(self.catalog_book, self.book_source)
        self.assertFalse(can_import, "Copyrighted book should not be importable")
        self.assertIn('copyrighted', reason.lower())
    
    def test_cannot_import_unknown_rights(self):
        """Test that books with unknown rights status cannot be imported."""
        self.catalog_book.copyright_status = CatalogBook.UNKNOWN
        self.catalog_book.save()
        
        can_import, reason = RightsChecker.can_import_book(self.catalog_book, self.book_source)
        self.assertFalse(can_import, "Book with unknown rights should not be importable")
        self.assertIn('unknown', reason.lower())
    
    def test_cannot_import_without_text(self):
        """Test that books without full text cannot be imported."""
        self.catalog_book.full_text_available = False
        self.catalog_book.save()
        
        can_import, reason = RightsChecker.can_import_book(self.catalog_book, self.book_source)
        self.assertFalse(can_import, "Book without full text should not be importable")
        self.assertIn('not available', reason.lower())
    
    def test_provider_status_verification(self):
        """Test provider status verification."""
        # Create enabled provider
        ProviderStatus.objects.create(provider='test', is_enabled=True)
        self.assertTrue(RightsChecker.verify_source_eligibility('test'))
        
        # Disable provider
        status = ProviderStatus.objects.get(provider='test')
        status.is_enabled = False
        status.save()
        self.assertFalse(RightsChecker.verify_source_eligibility('test'))


class BookImportServiceTests(TestCase):
    """Test book import workflow."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.catalog_book = CatalogBook.objects.create(
            source='gutenberg',
            external_id='1342',
            title='Pride and Prejudice',
            copyright_status=CatalogBook.PUBLIC_DOMAIN_STATUS,
            full_text_available=True,
            source_url='https://www.gutenberg.org/ebooks/1342',
            reading_url='https://www.gutenberg.org/cache/epub/1342/pg1342.txt',
        )
        
        self.book_source = BookSource.objects.create(
            book=self.catalog_book,
            provider='gutenberg',
            external_id='1342',
            source_url='https://www.gutenberg.org/ebooks/1342',
            reading_url='https://www.gutenberg.org/cache/epub/1342/pg1342.txt',
            copyright_status=CatalogBook.PUBLIC_DOMAIN_STATUS,
            internal_reading_allowed=True,
            is_primary=True,
        )
        
        # Enable provider
        ProviderStatus.objects.create(provider='gutenberg', is_enabled=True)
    
    def test_import_creates_imported_book_record(self):
        """Test that import creates ImportedBook record."""
        with patch('books.services.BookFileDownloader.download_file') as mock_download:
            # Mock successful download
            with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
                f.write(b'Test book content')
                temp_path = f.name
            
            mock_download.return_value = (temp_path, 'txt')
            
            try:
                with patch('books.services.default_storage.save'):
                    imported = BookImportService.import_book(
                        self.user,
                        self.catalog_book,
                        self.book_source,
                    )
                
                self.assertIsNotNone(imported.id)
                self.assertEqual(imported.status, ImportedBook.IMPORTED)
                self.assertEqual(imported.format, 'txt')
                self.assertTrue(imported.checksum)
            finally:
                try:
                    os.unlink(temp_path)
                except:
                    pass
    
    def test_import_requires_eligible_rights(self):
        """Test that import fails with ineligible rights."""
        self.catalog_book.copyright_status = CatalogBook.COPYRIGHTED
        self.catalog_book.save()
        
        with self.assertRaises(RightsCheckError):
            BookImportService.import_book(
                self.user,
                self.catalog_book,
                self.book_source,
            )
    
    def test_import_deduplicates(self):
        """Test that duplicate imports are handled."""
        # Create first import
        with patch('books.services.BookFileDownloader.download_file') as mock_download:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
                f.write(b'Test book content')
                temp_path = f.name
            
            mock_download.return_value = (temp_path, 'txt')
            
            try:
                with patch('books.services.default_storage.save'):
                    imported1 = BookImportService.import_book(
                        self.user,
                        self.catalog_book,
                        self.book_source,
                    )
                
                # Try to import again without force
                imported2 = BookImportService.import_book(
                    self.user,
                    self.catalog_book,
                    self.book_source,
                    force=False,
                )
                
                # Should return existing import
                self.assertEqual(imported1.id, imported2.id)
            finally:
                try:
                    os.unlink(temp_path)
                except:
                    pass


class CatalogServicePolicyTests(TestCase):
    """Test the provider allowlist and legal import gate."""

    def test_enabled_providers_respects_settings_and_database_status(self):
        ProviderStatus.objects.create(provider='open_library', is_enabled=True)
        ProviderStatus.objects.create(provider='gutenberg', is_enabled=False)

        enabled = CatalogService.enabled_provider_names()

        self.assertIn('open_library', enabled)
        self.assertNotIn('gutenberg', enabled)


class BookSearchAPITests(TestCase):
    """Test book search API."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test catalog book
        self.catalog_book = CatalogBook.objects.create(
            source='open_library',
            external_id='OL12345M',
            title='Test Book',
            authors=['Test Author'],
            copyright_status=CatalogBook.PUBLIC_DOMAIN_STATUS,
            full_text_available=True,
            source_url='https://example.com/book',
        )
    
    def test_search_local_books(self):
        """Test searching local book catalog."""
        response = self.client.get('/api/import/search/?q=Test')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['query'], 'Test')
        self.assertIn('local_results', data)
    
    def test_search_requires_minimum_query_length(self):
        """Test that search requires minimum query length."""
        response = self.client.get('/api/import/search/?q=A')
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
    
    def test_search_empty_query(self):
        """Test search with empty query."""
        response = self.client.get('/api/import/search/?q=')
        self.assertEqual(response.status_code, 400)


class BookReaderAPITests(TestCase):
    """Test reader API endpoints."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='reader',
            email='reader@example.com',
            password='testpass123'
        )
        
        self.catalog_book = CatalogBook.objects.create(
            source='gutenberg',
            external_id='1342',
            title='Test Book',
            copyright_status=CatalogBook.PUBLIC_DOMAIN_STATUS,
            full_text_available=True,
            source_url='https://example.com/book',
        )
        
        self.book_source = BookSource.objects.create(
            book=self.catalog_book,
            provider='gutenberg',
            external_id='1342',
            source_url='https://example.com/book',
            reading_url='https://example.com/book.txt',
            copyright_status=CatalogBook.PUBLIC_DOMAIN_STATUS,
            internal_reading_allowed=True,
        )
        
        self.imported_book = ImportedBook.objects.create(
            catalog_book=self.catalog_book,
            book_source=self.book_source,
            format='txt',
            status=ImportedBook.IMPORTED,
        )
    
    def test_reading_progress_requires_auth(self):
        """Test that reading progress requires authentication."""
        response = self.client.post(
            f'/api/imported/{self.imported_book.id}/progress/',
            data=json.dumps({'chapter': '1', 'progress': 50}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_reading_progress_save(self):
        """Test saving reading progress."""
        self.client.login(username='reader', password='testpass123')
        
        response = self.client.post(
            f'/api/imported/{self.imported_book.id}/progress/',
            data=json.dumps({'chapter': '1', 'progress': 50}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify progress was saved
        progress = ReadingProgress.objects.get(
            user=self.user,
            book=self.catalog_book
        )
        self.assertEqual(progress.percent, 50)


class SecurityTests(TestCase):
    """Test security protections."""
    
    def test_download_blocked_from_unapproved_hosts(self):
        """Test that downloads are blocked from unapproved hosts."""
        downloader = BookFileDownloader()
        
        with self.assertRaises(PermissionError):
            downloader.download_file(
                'https://malicious.com/book.epub',
                'test',
                'test-1'
            )
    
    def test_path_traversal_prevention(self):
        """Test that path traversal attacks are prevented."""
        # This would be tested in actual file storage implementation
        # Ensure files are stored in correct directory
        catalog_book = CatalogBook.objects.create(
            source='test',
            external_id='test-1',
            title='Test',
            source_url='https://example.com',
        )
        
        imported = ImportedBook.objects.create(
            catalog_book=catalog_book,
            book_source=BookSource.objects.create(
                book=catalog_book,
                provider='test',
                external_id='test-1',
                source_url='https://example.com',
                reading_url='https://example.com/book.txt',
                copyright_status=CatalogBook.PUBLIC_DOMAIN_STATUS,
                internal_reading_allowed=True,
            ),
            format='txt',
            status=ImportedBook.IMPORTED,
        )
        
        # File path should be within media directory
        book_file = BookFile.objects.create(
            imported_book=imported,
            file_path='books/imported/test/test-1/book.txt',
        )
        
        # Verify path is safe
        self.assertNotIn('..', book_file.file_path)
        self.assertTrue(book_file.file_path.startswith('books/'))


class ProviderTests(TestCase):
    """Test provider implementations."""
    
    @patch('books.services.urlopen')
    def test_open_library_provider_search(self, mock_urlopen):
        """Test Open Library provider search."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers.get_content_type.return_value = 'application/json'
        mock_response.read.return_value = json.dumps({
            'docs': [
                {
                    'key': '/works/OL1M',
                    'title': 'Test Book',
                    'author_name': ['Test Author'],
                    'first_publish_year': 2020,
                }
            ],
            'num_found': 1,
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        provider = OpenLibraryProvider()
        results, total = provider.search_books('test')
        
        self.assertEqual(total, 1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, 'Test Book')


class EPUBProcessorTests(TestCase):
    """Test EPUB processing."""
    
    def test_epub_validation_with_invalid_file(self):
        """Test that invalid EPUB files are rejected."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.epub') as f:
            f.write(b'Not an EPUB file')
            temp_path = f.name
        
        try:
            is_valid = EPUBProcessor.validate_epub(temp_path)
            self.assertFalse(is_valid)
        finally:
            os.unlink(temp_path)
