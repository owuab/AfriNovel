from django.core.management.base import BaseCommand

from books.services import CatalogService


class Command(BaseCommand):
    help = 'Seed the local catalogue with approved public-domain and open-license books.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=12,
            help='Maximum number of approved public-domain/open-license books to persist locally.',
        )
        parser.add_argument(
            '--query',
            action='append',
            dest='queries',
            default=[],
            help='Optional query term to search for. Repeat to include multiple queries.',
        )

    def handle(self, *args, **options):
        limit = max(1, int(options.get('limit', 12)))
        queries = options.get('queries') or []
        if queries:
            seeded = CatalogService.harvest_public_domain_catalog(query_terms=queries, limit=limit)
        else:
            seeded = CatalogService.ensure_local_public_domain_seed(limit=limit)
        self.stdout.write(
            self.style.SUCCESS(f'Persisted {len(seeded)} approved public-domain/open-license books into the local catalogue.')
        )
