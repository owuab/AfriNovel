"""Non-sensitive audit events for provider account lifecycle changes."""

from allauth.socialaccount.signals import social_account_added, social_account_updated
from django.conf import settings
from django.contrib.sites.models import Site
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from urllib.parse import urlparse

from .models import AuthenticationEvent


@receiver(social_account_added)
def record_social_account_added(request, sociallogin, **kwargs):
    AuthenticationEvent.objects.create(
        user=sociallogin.user,
        event_type=AuthenticationEvent.ACCOUNT_LINKED,
        provider=sociallogin.account.provider,
    )


@receiver(social_account_updated)
def record_social_account_login(request, sociallogin, **kwargs):
    AuthenticationEvent.objects.create(
        user=sociallogin.user,
        event_type=AuthenticationEvent.SOCIAL_LOGIN,
        provider=sociallogin.account.provider,
    )


@receiver(post_migrate)
def configure_current_site(sender, **kwargs):
    """Keep allauth callback host generation aligned with the configured deployment URL."""
    if sender.name != 'books':
        return
    parsed = urlparse(settings.SITE_URL)
    domain = parsed.netloc or parsed.path
    Site.objects.update_or_create(id=settings.SITE_ID, defaults={'domain': domain, 'name': 'BookClub'})