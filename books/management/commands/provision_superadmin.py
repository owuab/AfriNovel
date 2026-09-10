from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q


class Command(BaseCommand):
    help = 'Demote all other admin accounts and create or reset one superadmin.'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True)
        parser.add_argument('--password', required=True)

    def handle(self, *args, **options):
        username = options['username'].strip()
        password = options['password']
        if not username or not password:
            raise CommandError('A username and password are required.')

        user_model = get_user_model()
        demoted = user_model.objects.exclude(username=username).filter(
            Q(is_staff=True) | Q(is_superuser=True)
        ).update(is_staff=False, is_superuser=False)

        user, created = user_model.objects.get_or_create(username=username)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()
        if not user.check_password(password):
            raise CommandError('The superadmin password could not be verified after saving.')

        action = 'Created' if created else 'Reset'
        self.stdout.write(self.style.SUCCESS(
            f'{action} superadmin {username!r}; verified its password and removed admin privileges from {demoted} other account(s).'
        ))
