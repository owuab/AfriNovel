from django.db import migrations


def remove_gutenberg_records(apps, schema_editor):
    CatalogBook = apps.get_model('books', 'CatalogBook')
    BookSource = apps.get_model('books', 'BookSource')

    BookSource.objects.filter(provider='gutenberg').delete()
    CatalogBook.objects.filter(source='gutenberg').delete()
    CatalogBook.objects.filter(source_url__icontains='gutenberg.org').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('books', '0017_catalogbook_license_url_and_more'),
    ]

    operations = [
        migrations.RunPython(remove_gutenberg_records, migrations.RunPython.noop),
    ]