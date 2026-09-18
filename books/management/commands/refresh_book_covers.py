import json
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand

from books.models import Book, CatalogBook


class Command(BaseCommand):
    help = 'Replace Gutenberg cover URLs with clean Open Library cover URLs.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0)

    def handle(self, *args, **options):
        records = CatalogBook.objects.filter(source='gutenberg').order_by('pk')
        if options['limit']:
            records = records[:options['limit']]

        refreshed = 0
        skipped = 0
        for catalog_book in records:
            cover_id = self._find_cover_id(catalog_book.title)
            if not cover_id:
                catalog_book.cover_url = ''
                catalog_book.save(update_fields=['cover_url', 'updated_at'])
                Book.objects.filter(catalog_book=catalog_book, cover_url__contains='gutenberg.org').update(cover_url='')
                skipped += 1
                self.stdout.write(self.style.WARNING(f'No clean cover found: {catalog_book.title}'))
                continue

            cover_url = f'https://covers.openlibrary.org/b/id/{cover_id}-L.jpg'
            catalog_book.cover_url = cover_url
            catalog_book.save(update_fields=['cover_url', 'updated_at'])
            Book.objects.filter(catalog_book=catalog_book).update(cover_url=cover_url)
            refreshed += 1

        self.stdout.write(self.style.SUCCESS(f'Refreshed {refreshed} cover(s); skipped {skipped}.'))

    @staticmethod
    def _find_cover_id(title):
        url = 'https://openlibrary.org/search.json?title=' + quote(title) + '&limit=5&fields=title,cover_i'
        request = Request(url, headers={'User-Agent': 'AfriNovel cover refresh/1.0'})
        try:
            with urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode('utf-8'))
        except (OSError, ValueError):
            return None

        normalized_title = title.casefold().strip()
        for document in payload.get('docs', []):
            cover_id = document.get('cover_i')
            document_title = str(document.get('title', '')).casefold().strip()
            if cover_id and (document_title == normalized_title or normalized_title in document_title):
                return cover_id
        return next((document.get('cover_i') for document in payload.get('docs', []) if document.get('cover_i')), None)