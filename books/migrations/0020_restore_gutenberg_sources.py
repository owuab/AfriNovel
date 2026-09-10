from django.db import migrations


def restore_gutenberg_sources(apps, schema_editor):
    CatalogBook = apps.get_model('books', 'CatalogBook')
    BookSource = apps.get_model('books', 'BookSource')
    for book in CatalogBook.objects.filter(source='gutenberg'):
        BookSource.objects.update_or_create(
            provider='gutenberg',
            external_id=book.external_id,
            defaults={
                'book': book,
                'source_url': book.source_url,
                'reading_url': book.reading_url,
                'access_type': 'public_domain',
                'copyright_status': 'public_domain',
                'license': 'Project Gutenberg public-domain edition',
                'internal_reading_allowed': True,
                'is_primary': True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ('books', '0019_restore_gutenberg_catalogue'),
    ]

    operations = [
        migrations.RunPython(restore_gutenberg_sources, migrations.RunPython.noop),
    ]