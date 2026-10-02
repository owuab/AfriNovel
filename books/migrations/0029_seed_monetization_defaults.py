from decimal import Decimal

from django.db import migrations


def create_defaults(apps, schema_editor):
    SubscriptionPlan = apps.get_model('books', 'SubscriptionPlan')
    MonetizationConfig = apps.get_model('books', 'MonetizationConfig')
    benefits = [
        'Ad-free reading and browsing',
        'Ad-free writing workspace',
        'Access to the writer earnings programme after approval',
        'Subscriber-only features and enhanced profile options',
    ]
    SubscriptionPlan.objects.get_or_create(
        slug='premium-monthly',
        defaults={
            'name': 'AfriNovels Premium Monthly',
            'billing_period': 'monthly',
            'price': Decimal('2500.00'),
            'currency': 'NGN',
            'benefits': benefits,
            'display_order': 1,
        },
    )
    SubscriptionPlan.objects.get_or_create(
        slug='premium-yearly',
        defaults={
            'name': 'AfriNovels Premium Yearly',
            'billing_period': 'yearly',
            'price': Decimal('25000.00'),
            'currency': 'NGN',
            'benefits': benefits,
            'display_order': 2,
        },
    )
    MonetizationConfig.objects.get_or_create(pk=1)


class Migration(migrations.Migration):
    dependencies = [('books', '0028_monetization_ledger_links')]

    operations = [migrations.RunPython(create_defaults, migrations.RunPython.noop)]