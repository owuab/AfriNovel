from __future__ import annotations

from django.core.management.base import BaseCommand
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution
from django_apscheduler import util
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from books.services import CatalogService


def harvest_books():
    CatalogService.ensure_local_public_domain_seed(limit=12)


class Command(BaseCommand):
    help = 'Schedule a recurring legal public-domain catalog harvest.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval-minutes',
            type=int,
            default=60,
            help='How often to run the harvest in minutes.',
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Remove any existing scheduled jobs before creating the new one.',
        )

    def handle(self, *args, **options):
        scheduler = BlockingScheduler()
        scheduler.add_jobstore(DjangoJobStore(), 'default')

        if options['clear_existing']:
            for job in scheduler.get_jobs():
                scheduler.remove_job(job.id)

        scheduler.add_job(
            harvest_books,
            trigger=CronTrigger(minute=f'*/{max(1, options["interval_minutes"])}'),
            id='public_domain_catalog_harvest',
            replace_existing=True,
            max_instances=1,
            jobstore='default',
        )
        scheduler.start()
