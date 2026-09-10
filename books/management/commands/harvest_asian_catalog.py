from django.core.management.base import BaseCommand

from books.models import CatalogBook
from books.services import CatalogService


class Command(BaseCommand):
    help = 'Harvest legally available Asian books from enabled catalogue providers.'

    DEFAULT_QUERIES = [
        'Chinese literature', 'Korean literature', 'Japanese literature',
        'South Asian literature', 'Southeast Asian literature',
    ]

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=100)
        parser.add_argument('--query', action='append', dest='queries', default=[])

    def handle(self, *args, **options):
        limit = max(1, int(options['limit']))
        queries = options['queries'] or self.DEFAULT_QUERIES
        approved = {CatalogBook.PUBLIC_DOMAIN_STATUS, CatalogBook.OPEN_LICENSE, CatalogBook.AUTHORIZED}
        seen = set()
        persisted = 0

        for query in queries:
            if persisted >= limit:
                break
            results, _, errors = CatalogService.search(query, page=1)
            for result in results:
                key = (result.source, result.external_id)
                if key in seen or not result.full_text_available or result.copyright_status not in approved:
                    continue
                seen.add(key)
                CatalogService.persist(result)
                persisted += 1
                if persisted >= limit:
                    break
            for provider in errors:
                self.stderr.write(self.style.WARNING(f'Provider unavailable: {provider}'))

        self.stdout.write(self.style.SUCCESS(f'Persisted {persisted} verified Asian free books.'))