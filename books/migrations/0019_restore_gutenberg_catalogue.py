from django.db import migrations


BOOKS = [
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


def restore_gutenberg_records(apps, schema_editor):
    CatalogBook = apps.get_model('books', 'CatalogBook')
    BookSource = apps.get_model('books', 'BookSource')
    for external_id, title, author, subjects in BOOKS:
        book, _ = CatalogBook.objects.update_or_create(
            source='gutenberg',
            external_id=external_id,
            defaults={
                'title': title,
                'authors': [author],
                'subjects': subjects,
                'languages': ['en'],
                'original_language': 'en',
                'cover_url': f'https://www.gutenberg.org/cache/epub/{external_id}/pg{external_id}.cover.medium.jpg',
                'source_url': f'https://www.gutenberg.org/ebooks/{external_id}',
                'reading_url': f'https://www.gutenberg.org/cache/epub/{external_id}/pg{external_id}.txt',
                'access_type': 'public_domain',
                'copyright_status': 'public_domain',
                'license': 'Project Gutenberg public-domain edition',
                'license_url': 'https://www.gutenberg.org/policy/license.html',
                'full_text_available': True,
            },
        )
        BookSource.objects.update_or_create(
            provider='gutenberg',
            external_id=external_id,
            defaults={
                'book': book,
                'source_url': f'https://www.gutenberg.org/ebooks/{external_id}',
                'reading_url': f'https://www.gutenberg.org/cache/epub/{external_id}/pg{external_id}.txt',
                'access_type': 'public_domain',
                'copyright_status': 'public_domain',
                'license': 'Project Gutenberg public-domain edition',
                'internal_reading_allowed': True,
                'is_primary': True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ('books', '0018_remove_gutenberg_catalogue'),
    ]

    operations = [
        migrations.RunPython(restore_gutenberg_records, migrations.RunPython.noop),
    ]