"""Server-side subscription, payment, reader verification, and payout rules."""

import calendar
import hashlib
import hmac
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F, Q, Sum
from django.utils import timezone

from .models import (
    AdClick,
    AdImpression,
    Chapter,
    MonetizationConfig,
    MonetizationPayment,
    Notification,
    PremiumSubscription,
    ReaderSession,
    SubscriptionPlan,
    WithdrawalAllocation,
    WriterEarning,
    WriterProfile,
    WriterWithdrawal,
)


class PaymentProviderError(Exception):
    """A payment provider request failed or returned invalid data."""


class PaystackClient:
    base_url = 'https://api.paystack.co'
    timeout = (5, 20)

    @property
    def secret_key(self):
        return getattr(settings, 'PAYSTACK_SECRET_KEY', '')

    def _request(self, method, path, payload=None):
        if not self.secret_key:
            raise PaymentProviderError('Paystack has not been configured by the platform owner.')
        try:
            response = requests.request(
                method,
                f'{self.base_url}{path}',
                headers={'Authorization': f'Bearer {self.secret_key}', 'Accept': 'application/json'},
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as error:
            raise PaymentProviderError('The payment provider is temporarily unavailable.') from error
        if not data.get('status'):
            raise PaymentProviderError(data.get('message') or 'The payment provider rejected the request.')
        return data.get('data') or {}

    def initialize(self, payment, callback_url):
        payload = {
            'email': payment.user.email,
            'amount': int(payment.amount * 100),
            'currency': payment.currency,
            'reference': payment.reference,
            'callback_url': callback_url,
            'metadata': {'payment_id': payment.pk, 'user_id': payment.user_id, 'plan_id': payment.plan_id},
        }
        if payment.plan and payment.plan.provider_plan_code:
            payload['plan'] = payment.plan.provider_plan_code
        return self._request('POST', '/transaction/initialize', payload)

    def verify(self, reference):
        return self._request('GET', f'/transaction/verify/{reference}')

    def create_transfer_recipient(self, name, account_number, bank_code):
        return self._request('POST', '/transferrecipient', {
            'type': 'nuban', 'name': name, 'account_number': account_number,
            'bank_code': bank_code, 'currency': 'NGN',
        })

    def transfer(self, withdrawal, writer):
        return self._request('POST', '/transfer', {
            'source': 'balance',
            'amount': int(withdrawal.amount * 100),
            'recipient': writer.payout_recipient_code,
            'reference': str(withdrawal.reference),
            'reason': f'AfriNovels writer payout {withdrawal.reference}',
        })

    def disable_subscription(self, subscription_code, email_token):
        return self._request('POST', '/subscription/disable', {
            'code': subscription_code,
            'token': email_token,
        })

    def valid_webhook_signature(self, body, signature):
        if not self.secret_key or not signature:
            return False
        expected = hmac.new(self.secret_key.encode(), body, hashlib.sha512).hexdigest()
        return hmac.compare_digest(expected, signature)


def get_monetization_config():
    config, _ = MonetizationConfig.objects.get_or_create(pk=1)
    return config


def notify_user(user, notification_type, message, actor=None):
    if not user:
        return None
    return Notification.objects.create(
        recipient=user,
        actor=actor or user,
        notification_type=notification_type,
        message=message[:280],
    )


def expire_due_subscriptions(user=None):
    now = timezone.now()
    due = PremiumSubscription.objects.filter(status=PremiumSubscription.ACTIVE, ends_at__lte=now)
    if user is not None:
        due = due.filter(user=user)
    for subscription in due.select_related('user').iterator():
        changed = PremiumSubscription.objects.filter(
            pk=subscription.pk, status=PremiumSubscription.ACTIVE,
        ).update(status=PremiumSubscription.EXPIRED, updated_at=now)
        if changed:
            notify_user(
                subscription.user,
                Notification.SUBSCRIPTION_EXPIRED,
                f'Your {subscription.plan.name} subscription has expired. Ads are restored until you renew.',
            )


def active_subscription_for(user):
    if not user or not user.is_authenticated:
        return None
    expire_due_subscriptions(user)
    return PremiumSubscription.objects.filter(
        user=user,
        status=PremiumSubscription.ACTIVE,
        starts_at__lte=timezone.now(),
        ends_at__gt=timezone.now(),
    ).select_related('plan').first()


def has_active_subscription(user):
    return active_subscription_for(user) is not None


def subscription_dashboard_context(user):
    current = active_subscription_for(user)
    return {
        'current_subscription': current,
        'subscription_plans': SubscriptionPlan.objects.filter(is_active=True),
        'recent_subscription_payments': MonetizationPayment.objects.filter(user=user).select_related('plan')[:5] if user.is_authenticated else [],
        'payment_configured': bool(getattr(settings, 'PAYSTACK_SECRET_KEY', '')),
    }


def subscription_end(start, billing_period):
    months = 12 if billing_period == SubscriptionPlan.YEARLY else 1
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return start.replace(year=year, month=month, day=day)


def create_payment(user, plan):
    return MonetizationPayment.objects.create(
        user=user,
        plan=plan,
        amount=plan.price,
        currency=plan.currency,
        reference=uuid4().hex,
        status=MonetizationPayment.PENDING,
    )


def verify_and_activate_subscription(reference):
    payment = MonetizationPayment.objects.select_related('user', 'plan').filter(reference=reference).first()
    if not payment:
        raise PaymentProviderError('Payment reference was not found.')
    if payment.status == MonetizationPayment.SUCCESS and payment.subscription_id:
        return payment.subscription
    verified = PaystackClient().verify(reference)
    expected_amount = int(payment.amount * 100)
    if (
        verified.get('status') != 'success'
        or verified.get('reference') != payment.reference
        or int(verified.get('amount', -1)) != expected_amount
        or verified.get('currency') != payment.currency
    ):
        MonetizationPayment.objects.filter(pk=payment.pk, status__in=[MonetizationPayment.PENDING, MonetizationPayment.INITIALIZED]).update(status=MonetizationPayment.FAILED)
        notify_user(payment.user, Notification.PAYMENT_FAILED, 'We could not verify your subscription payment. No subscription was activated.')
        raise PaymentProviderError('Payment verification did not match the expected amount and currency.')

    now = timezone.now()
    with transaction.atomic():
        payment = MonetizationPayment.objects.select_for_update().select_related('user', 'plan').get(pk=payment.pk)
        if payment.status == MonetizationPayment.SUCCESS and payment.subscription_id:
            return payment.subscription
        previous = PremiumSubscription.objects.select_for_update().filter(
            user=payment.user, status=PremiumSubscription.ACTIVE,
        )
        previous.update(status=PremiumSubscription.CANCELLED, cancel_at_period_end=False, updated_at=now)
        subscription = PremiumSubscription.objects.create(
            user=payment.user,
            plan=payment.plan,
            status=PremiumSubscription.ACTIVE,
            starts_at=now,
            ends_at=subscription_end(now, payment.plan.billing_period),
        )
        payment.status = MonetizationPayment.SUCCESS
        payment.provider_reference = str(verified.get('id') or payment.reference)
        payment.verified_at = now
        payment.subscription = subscription
        payment.metadata = {**payment.metadata, 'channel': verified.get('channel', '')}
        payment.save(update_fields=['status', 'provider_reference', 'verified_at', 'subscription', 'metadata'])
        notify_user(payment.user, Notification.SUBSCRIPTION, f'{payment.plan.name} is active. Ads are now hidden.')
        notify_user(payment.user, Notification.PAYMENT_RECEIVED, f'Payment of {payment.currency} {payment.amount:,.2f} was confirmed.')
        return subscription


def process_paystack_renewal(event_data):
    reference = str(event_data.get('reference', ''))
    if not reference:
        raise PaymentProviderError('Renewal event has no transaction reference.')
    customer_email = (event_data.get('customer') or {}).get('email', '').strip().lower()
    plan_code = str((event_data.get('plan') or {}).get('plan_code') or '')
    if not customer_email or not plan_code:
        raise PaymentProviderError('Renewal event is missing customer or plan details.')
    user = get_user_model().objects.filter(email__iexact=customer_email).first()
    if not user:
        raise PaymentProviderError('Renewal customer was not found.')
    subscription = PremiumSubscription.objects.filter(
        user=user,
        plan__provider_plan_code=plan_code,
        status=PremiumSubscription.ACTIVE,
    ).select_related('plan').first()
    if not subscription:
        raise PaymentProviderError('No active subscription matches this renewal.')
    verified = PaystackClient().verify(reference)
    if (
        verified.get('status') != 'success'
        or verified.get('reference') != reference
        or int(verified.get('amount', -1)) != int(subscription.plan.price * 100)
        or verified.get('currency') != subscription.plan.currency
    ):
        raise PaymentProviderError('Renewal verification did not match the configured plan.')
    with transaction.atomic():
        subscription = PremiumSubscription.objects.select_for_update().select_related('plan', 'user').get(pk=subscription.pk)
        base = max(subscription.ends_at or timezone.now(), timezone.now())
        subscription.ends_at = subscription_end(base, subscription.plan.billing_period)
        subscription.save(update_fields=['ends_at', 'updated_at'])
        payment, created = MonetizationPayment.objects.get_or_create(
            reference=reference,
            defaults={
                'user': subscription.user,
                'plan': subscription.plan,
                'subscription': subscription,
                'amount': subscription.plan.price,
                'currency': subscription.plan.currency,
                'provider': 'paystack',
                'status': MonetizationPayment.SUCCESS,
                'provider_reference': str(verified.get('id') or reference),
                'verified_at': timezone.now(),
            },
        )
        if created:
            notify_user(subscription.user, Notification.SUBSCRIPTION, f'{subscription.plan.name} renewed successfully.')
            notify_user(subscription.user, Notification.PAYMENT_RECEIVED, f'Renewal payment of {subscription.plan.currency} {subscription.plan.price:,.2f} was confirmed.')
        return subscription


@transaction.atomic
def process_paystack_refund(reference):
    payment = MonetizationPayment.objects.select_for_update().select_related('user', 'subscription').filter(reference=reference).first()
    if not payment:
        return None
    if payment.status == MonetizationPayment.REFUNDED:
        return payment
    payment.status = MonetizationPayment.REFUNDED
    payment.save(update_fields=['status'])
    if payment.subscription_id:
        payment.subscription.status = PremiumSubscription.CANCELLED
        payment.subscription.cancel_at_period_end = False
        payment.subscription.save(update_fields=['status', 'cancel_at_period_end', 'updated_at'])
    notify_user(payment.user, Notification.PAYMENT_FAILED, 'A subscription payment was refunded and premium access has ended.')
    return payment


def identity_hash(request):
    if request.user.is_authenticated:
        identity = f'user:{request.user.pk}'
        return hmac.new(settings.SECRET_KEY.encode(), identity.encode(), hashlib.sha256).hexdigest()
    if not request.session.session_key:
        request.session.create()
    identity = f'guest:{request.session.session_key}'
    return hmac.new(settings.SECRET_KEY.encode(), identity.encode(), hashlib.sha256).hexdigest()


def get_reader_session(request, book, chapter):
    fingerprint = identity_hash(request)
    defaults = {'book': book, 'reader': request.user if request.user.is_authenticated else None}
    session, _ = ReaderSession.objects.get_or_create(
        chapter=chapter,
        identity_hash=fingerprint,
        read_date=timezone.localdate(),
        defaults=defaults,
    )
    return session


@transaction.atomic
def qualify_reader_session(request, token):
    try:
        session = ReaderSession.objects.select_for_update().select_related('book', 'chapter', 'book__owner').get(token=token)
    except (ReaderSession.DoesNotExist, ValueError, TypeError):
        return False, 'This reading session is invalid.'
    if not hmac.compare_digest(session.identity_hash, identity_hash(request)):
        return False, 'This reading session belongs to another browser session.'
    if session.qualified_at:
        return True, 'This read has already been counted.'
    config = get_monetization_config()
    if (timezone.now() - session.started_at).total_seconds() < config.minimum_read_seconds:
        return False, 'Keep reading a little longer before this read can qualify.'
    session.qualified_at = timezone.now()
    session.save(update_fields=['qualified_at'])
    if session.chapter_id:
        Chapter.objects.filter(pk=session.chapter_id).update(view_count=F('view_count') + 1)
    writer = WriterProfile.objects.filter(user_id=session.book.owner_id, status=WriterProfile.APPROVED).first()
    if not request.user.is_authenticated or not writer or not has_active_subscription(writer.user) or not session.book.owner_id:
        return True, 'Read recorded.'
    if request.user.is_authenticated and request.user.pk == writer.user_id:
        return True, 'Author reads do not qualify for earnings.'
    amount = config.earning_per_read
    if config.earning_formula == MonetizationConfig.ENGAGEMENT and config.engagement_bonus:
        dwell = (session.qualified_at - session.started_at).total_seconds()
        if dwell >= config.minimum_read_seconds * 2:
            amount += config.engagement_bonus
    if amount > 0:
        WriterEarning.objects.get_or_create(
            reader_session=session,
            defaults={
                'writer': writer,
                'book': session.book,
                'chapter': session.chapter,
                'activity_type': WriterEarning.QUALIFYING_READ,
                'amount': amount,
                'currency': 'NGN',
                'status': WriterEarning.PENDING,
                'available_at': timezone.now() + timedelta(days=7),
            },
        )
        notify_user(writer.user, Notification.EARNING_CREATED, f'A qualifying read was recorded for {session.book.title}.')
    return True, 'Read recorded.'


def release_matured_earnings(writer):
    now = timezone.now()
    WriterEarning.objects.filter(
        writer=writer,
        status=WriterEarning.PENDING,
        available_at__lte=now,
    ).update(status=WriterEarning.AVAILABLE)


def writer_balances(writer):
    release_matured_earnings(writer)
    totals = WriterEarning.objects.filter(writer=writer).aggregate(
        total=Sum('amount'),
        pending=Sum('amount', filter=Q(status=WriterEarning.PENDING)),
        available=Sum('amount', filter=Q(status=WriterEarning.AVAILABLE)),
    )
    reserved = WithdrawalAllocation.objects.filter(
        earning__writer=writer,
        withdrawal__status__in=[WriterWithdrawal.PENDING, WriterWithdrawal.PROCESSING],
    ).aggregate(amount=Sum('amount'))['amount'] or Decimal('0')
    paid = WithdrawalAllocation.objects.filter(
        earning__writer=writer,
        withdrawal__status=WriterWithdrawal.PAID,
    ).aggregate(amount=Sum('amount'))['amount'] or Decimal('0')
    available = max((totals['available'] or Decimal('0')) - reserved - paid, Decimal('0'))
    return {
        'total': totals['total'] or Decimal('0'),
        'pending': totals['pending'] or Decimal('0'),
        'available': available,
        'withdrawn': paid,
        'reserved': reserved,
    }


@transaction.atomic
def request_withdrawal(writer, amount):
    writer = WriterProfile.objects.select_for_update().get(pk=writer.pk)
    if writer.status != WriterProfile.APPROVED:
        raise ValueError('Your writer profile must be approved before requesting a payout.')
    if not writer.payout_recipient_code:
        raise ValueError('Add verified payout details before requesting a payout.')
    if not has_active_subscription(writer.user):
        raise ValueError('An active subscription is required for writer earnings and withdrawals.')
    amount = Decimal(str(amount)).quantize(Decimal('0.01'))
    config = get_monetization_config()
    if amount < config.minimum_withdrawal:
        raise ValueError(f'The minimum withdrawal is NGN {config.minimum_withdrawal:,.2f}.')
    earnings = list(WriterEarning.objects.select_for_update().filter(
        writer=writer, status=WriterEarning.AVAILABLE,
    ).order_by('created_at'))
    reserved_by_earning = {
        row['earning_id']: row['amount'] or Decimal('0')
        for row in WithdrawalAllocation.objects.filter(
            earning__writer=writer,
            withdrawal__status__in=[WriterWithdrawal.PENDING, WriterWithdrawal.PROCESSING, WriterWithdrawal.PAID],
        ).values('earning_id').annotate(amount=Sum('amount'))
    }
    remaining = amount
    available_allocations = []
    for earning in earnings:
        free_amount = earning.amount - reserved_by_earning.get(earning.pk, Decimal('0'))
        if free_amount <= 0:
            continue
        allocation = min(free_amount, remaining)
        available_allocations.append((earning, allocation))
        remaining -= allocation
        if remaining <= 0:
            break
    if remaining > 0:
        raise ValueError('The requested amount exceeds your available earnings.')
    withdrawal = WriterWithdrawal.objects.create(writer=writer, amount=amount)
    WithdrawalAllocation.objects.bulk_create([
        WithdrawalAllocation(withdrawal=withdrawal, earning=earning, amount=allocation)
        for earning, allocation in available_allocations
    ])
    notify_user(writer.user, Notification.WITHDRAWAL_REQUESTED, f'Your NGN {amount:,.2f} withdrawal request was received.')
    return withdrawal


def submit_withdrawal(withdrawal_id, admin_user):
    withdrawal = WriterWithdrawal.objects.select_related('writer').get(pk=withdrawal_id)
    if withdrawal.status not in {WriterWithdrawal.PENDING, WriterWithdrawal.FAILED}:
        raise ValueError('Only pending or failed withdrawals can be processed.')
    if not withdrawal.writer.payout_recipient_code:
        raise ValueError('The writer has no verified payout recipient.')
    result = PaystackClient().transfer(withdrawal, withdrawal.writer)
    withdrawal.status = WriterWithdrawal.PROCESSING
    withdrawal.provider_reference = str(result.get('transfer_code') or result.get('reference') or '')
    withdrawal.processed_by = admin_user
    withdrawal.processed_at = timezone.now()
    withdrawal.failure_reason = ''
    withdrawal.save(update_fields=['status', 'provider_reference', 'processed_by', 'processed_at', 'failure_reason'])
    return withdrawal


@transaction.atomic
def finalize_withdrawal(reference, success, reason=''):
    withdrawal = WriterWithdrawal.objects.select_for_update().select_related('writer__user').filter(
        reference=reference,
    ).first()
    if not withdrawal:
        withdrawal = WriterWithdrawal.objects.select_for_update().select_related('writer__user').filter(
            provider_reference=reference,
        ).first()
    if not withdrawal:
        return None
    if withdrawal.status == WriterWithdrawal.PAID:
        return withdrawal
    if success:
        withdrawal.status = WriterWithdrawal.PAID
        withdrawal.failure_reason = ''
        withdrawal.processed_at = timezone.now()
        withdrawal.save(update_fields=['status', 'failure_reason', 'processed_at'])
        for earning in WriterEarning.objects.select_for_update().filter(
            withdrawal_allocations__withdrawal=withdrawal,
        ).distinct():
            paid_allocations = WithdrawalAllocation.objects.filter(
                earning=earning,
                withdrawal__status=WriterWithdrawal.PAID,
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            if paid_allocations >= earning.amount:
                earning.status = WriterEarning.WITHDRAWN
                earning.withdrawn_at = timezone.now()
                earning.save(update_fields=['status', 'withdrawn_at'])
        notify_user(withdrawal.writer.user, Notification.WITHDRAWAL_APPROVED, f'Your NGN {withdrawal.amount:,.2f} withdrawal has been paid.')
    else:
        withdrawal.status = WriterWithdrawal.FAILED
        withdrawal.failure_reason = reason[:1000]
        withdrawal.save(update_fields=['status', 'failure_reason'])
        notify_user(withdrawal.writer.user, Notification.WITHDRAWAL_REJECTED, f'Your NGN {withdrawal.amount:,.2f} withdrawal could not be paid.')
    return withdrawal


def record_ad_impression(ad, request, path=None):
    fingerprint = identity_hash(request)
    key = hashlib.sha256(f'{ad.pk}:{fingerprint}:{path or request.path}:{uuid4()}'.encode()).hexdigest()
    return AdImpression.objects.create(
        ad=ad,
        user=request.user if request.user.is_authenticated else None,
        session_hash=fingerprint,
        path=(path or request.path)[:500],
        impression_key=key,
    )


def record_ad_click(ad, request):
    return AdClick.objects.create(
        ad=ad,
        user=request.user if request.user.is_authenticated else None,
        session_hash=identity_hash(request),
    )