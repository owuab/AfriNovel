from django.db import migrations


def create_missing_upload_approvals(apps, schema_editor):
    Book = apps.get_model('books', 'Book')
    BookApprovalStatus = apps.get_model('books', 'BookApprovalStatus')

    existing_approval_book_ids = BookApprovalStatus.objects.values_list('book_id', flat=True)
    submitted_book_ids = Book.objects.filter(
        uploads__isnull=False,
    ).exclude(
        id__in=existing_approval_book_ids,
    ).values_list('id', flat=True).distinct()
    BookApprovalStatus.objects.bulk_create(
        [BookApprovalStatus(book_id=book_id) for book_id in submitted_book_ids]
    )


class Migration(migrations.Migration):
    dependencies = [
        ('books', '0015_bookupload'),
    ]

    operations = [
        migrations.RunPython(create_missing_upload_approvals, migrations.RunPython.noop),
    ]