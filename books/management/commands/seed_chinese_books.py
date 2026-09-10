from django.core.management.base import BaseCommand

from books.models import CatalogBook
from books.services import CatalogService, NormalizedBook


CHINESE_BOOKS = [
    ('132', 'The Art of War', 'Sunzi'),
    ('216', 'The Tao Teh King, or, the Tao and its Characteristics', 'Laozi'),
    ('3330', 'The Analects of Confucius (from the Chinese Classics)', 'Confucius'),
    ('9603', 'Hung Lou Meng, or, the Dream of the Red Chamber, Book I', 'Cao Xueqin'),
    ('20968', 'Three Hundred Tang Poems, Volume 1', 'Various'),
    ('23962', 'Xi You Ji', "Wu Cheng'en"),
    ('24032', 'Ru Lin Wai Shi', 'Wu Jingzi'),
    ('24141', 'Jing Shi Tong Yan', 'Feng Menglong'),
    ('24230', 'Jin Gu Qi Guan', 'Baowenglaoren'),
    ('25559', 'A Brief History of Chinese Fiction', 'Lu Xun'),
    ('49965', 'Dao De Jing: A Minimalist Translation', 'Laozi'),
    ('52200', 'Jin Ping Mei', 'Lanling Xiaoxiaosheng'),
]


class Command(BaseCommand):
    help = 'Seed verified public-domain Chinese books from Project Gutenberg.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=len(CHINESE_BOOKS))

    def handle(self, *args, **options):
        limit = max(1, min(int(options['limit']), len(CHINESE_BOOKS)))
        persisted = []
        for external_id, title, author in CHINESE_BOOKS[:limit]:
            persisted.append(CatalogService.persist(NormalizedBook(
                external_id=external_id,
                source='gutenberg',
                title=f'{title} (Chinese)' if external_id not in {'132', '216', '3330', '9603'} else title,
                authors=[author],
                languages=['zh'],
                source_url=f'https://www.gutenberg.org/ebooks/{external_id}',
                reading_url=f'https://www.gutenberg.org/cache/epub/{external_id}/pg{external_id}.txt',
                access_type=CatalogBook.PUBLIC_DOMAIN,
                copyright_status=CatalogBook.PUBLIC_DOMAIN_STATUS,
                license='Project Gutenberg public-domain edition',
                full_text_available=True,
                provider_sources=({
                    'provider': 'gutenberg',
                    'external_id': external_id,
                    'source_url': f'https://www.gutenberg.org/ebooks/{external_id}',
                    'reading_url': f'https://www.gutenberg.org/cache/epub/{external_id}/pg{external_id}.txt',
                    'access_type': CatalogBook.PUBLIC_DOMAIN,
                    'copyright_status': CatalogBook.PUBLIC_DOMAIN_STATUS,
                    'license': 'Project Gutenberg public-domain edition',
                    'internal_reading_allowed': True,
                    'is_primary': True,
                },),
            )))
        self.stdout.write(self.style.SUCCESS(f'Persisted {len(persisted)} verified Chinese public-domain books.'))