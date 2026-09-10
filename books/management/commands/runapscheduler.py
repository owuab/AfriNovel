from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore

from books.services import CatalogService


def harvest_public_domain_books():
    CatalogService.ensure_local_public_domain_seed(limit=12)


class Command(BaseCommand):
    help = 'Runs the recurring public-domain harvest scheduler for AfriNovel.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval-minutes',
            type=int,
            default=60,
            help='How often to run the legal catalog harvest in minutes.',
        )

    def handle(self, *args, **options):
        interval_minutes = max(1, int(options['interval_minutes']))
        scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), 'default')
        scheduler.add_job(
            harvest_public_domain_books,
            trigger=CronTrigger(minute=f'*/{interval_minutes}'),
            id='public_domain_catalog_harvest',
            replace_existing=True,
            max_instances=1,
            jobstore='default',
        )
        harvest_public_domain_books()
        self.stdout.write(
            self.style.SUCCESS(
                f'Started public-domain harvest scheduler with a {interval_minutes}-minute interval.'
            )
        )
        try:
            scheduler.start()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Stopping public-domain harvest scheduler.'))
            scheduler.shutdown(wait=False)
