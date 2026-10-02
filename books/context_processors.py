from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from .models import AdImpression, Advertisement
from .monetization import get_monetization_config, has_active_subscription, identity_hash, record_ad_impression


def _select_ad(request, placement, now, fingerprint, frequency_cap):
    ads = Advertisement.objects.filter(
        is_active=True,
        placement=placement,
    ).filter(
        Q(starts_at__isnull=True) | Q(starts_at__lte=now),
        Q(ends_at__isnull=True) | Q(ends_at__gt=now),
    ).order_by('id')
    if not ads.exists():
        return None

    since = now - timedelta(days=1)
    for ad in ads:
        impressions = AdImpression.objects.filter(
            session_hash=fingerprint,
            ad=ad,
            created_at__gte=since,
        ).count()
        if impressions < frequency_cap:
            record_ad_impression(ad, request)
            return ad
    return None


def monetization_context(request):
    empty = {
        'has_active_subscription': False,
        'site_banner_ad': None,
        'home_featured_ad': None,
        'reader_inline_ad': None,
    }
    if request.path.startswith(('/admin/', '/admin-panel/')):
        return empty

    if has_active_subscription(request.user):
        return {**empty, 'has_active_subscription': True}

    config = get_monetization_config()
    fingerprint = identity_hash(request)
    now = timezone.now()
    return {
        'has_active_subscription': False,
        'site_banner_ad': _select_ad(request, Advertisement.SITE_BANNER, now, fingerprint, config.ad_frequency_cap),
        'home_featured_ad': _select_ad(request, Advertisement.HOME_FEATURED, now, fingerprint, config.ad_frequency_cap) if request.path in {'/', '/home/'} else None,
        'reader_inline_ad': _select_ad(request, Advertisement.READER_INLINE, now, fingerprint, config.ad_frequency_cap) if request.path.startswith('/books/') and '/chapter/' in request.path else None,
    }