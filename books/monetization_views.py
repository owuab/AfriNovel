import json
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import (
    Advertisement,
    MonetizationPayment,
    Notification,
    PremiumSubscription,
    SubscriptionPlan,
    WriterProfile,
)
from .monetization import (
    PaystackClient,
    PaymentProviderError,
    create_payment,
    finalize_withdrawal,
    has_active_subscription,
    notify_user,
    process_paystack_renewal,
    process_paystack_refund,
    qualify_reader_session,
    record_ad_click,
    request_withdrawal,
    subscription_dashboard_context,
    verify_and_activate_subscription,
)
from .monetization_forms import WriterApplicationForm, WithdrawalRequestForm


@login_required
def subscription_plans(request):
    context = subscription_dashboard_context(request.user)
    context['payment_configured'] = bool(PaystackClient().secret_key)
    context['writer_profile'] = WriterProfile.objects.filter(user=request.user).first()
    return render(request, 'books/subscription_plans.html', context)


@login_required
@require_POST
def subscription_checkout(request, plan_slug):
    plan = get_object_or_404(SubscriptionPlan, slug=plan_slug, is_active=True)
    if plan.currency != 'NGN' or plan.price <= 0:
        messages.error(request, 'This plan is not configured for Nigerian card payments.')
        return redirect('subscription_plans')
    if not request.user.email:
        messages.error(request, 'Add an email address to your account before subscribing.')
        return redirect('subscription_plans')
    payment = create_payment(request.user, plan)
    try:
        checkout = PaystackClient().initialize(payment, request.build_absolute_uri(reverse('paystack_callback')))
    except PaymentProviderError as error:
        payment.status = MonetizationPayment.FAILED
        payment.metadata = {'error': str(error)}
        payment.save(update_fields=['status', 'metadata'])
        messages.error(request, str(error))
        return redirect('subscription_plans')
    payment.status = MonetizationPayment.INITIALIZED
    payment.checkout_url = checkout.get('authorization_url', '')
    payment.provider_reference = str(checkout.get('access_code') or '')
    payment.save(update_fields=['status', 'checkout_url', 'provider_reference'])
    if not payment.checkout_url:
        payment.status = MonetizationPayment.FAILED
        payment.save(update_fields=['status'])
        messages.error(request, 'The payment provider did not return a checkout link.')
        return redirect('subscription_plans')
    return redirect(payment.checkout_url)


@login_required
def paystack_callback(request):
    reference = request.GET.get('reference') or request.GET.get('trxref', '')
    payment = MonetizationPayment.objects.filter(reference=reference).first()
    if not payment or payment.user_id != request.user.pk:
        raise Http404
    try:
        verify_and_activate_subscription(reference)
    except PaymentProviderError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, 'Payment confirmed. Premium is now active.')
    return redirect('subscription_plans')


@csrf_exempt
@require_POST
def paystack_webhook(request):
    client = PaystackClient()
    signature = request.headers.get('x-paystack-signature', '')
    if not client.valid_webhook_signature(request.body, signature):
        return HttpResponseForbidden('Invalid provider signature.')
    try:
        event = json.loads(request.body or b'{}')
    except (TypeError, json.JSONDecodeError):
        return HttpResponseBadRequest('Invalid webhook payload.')
    event_type = event.get('event')
    data = event.get('data') or {}
    try:
        if event_type == 'charge.success':
            reference = str(data.get('reference', ''))
            if MonetizationPayment.objects.filter(reference=reference).exists():
                verify_and_activate_subscription(reference)
            else:
                process_paystack_renewal(data)
        elif event_type == 'subscription.create':
            email = (data.get('customer') or {}).get('email', '')
            plan_code = str((data.get('plan') or {}).get('plan_code') or '')
            plan = SubscriptionPlan.objects.filter(provider_plan_code=plan_code).first()
            if plan:
                PremiumSubscription.objects.filter(
                    user__email__iexact=email, plan=plan, status=PremiumSubscription.ACTIVE,
                ).update(provider_subscription_code=str(data.get('subscription_code') or ''))
        elif event_type == 'charge.failed':
            reference = str(data.get('reference') or '')
            payment = MonetizationPayment.objects.filter(reference=reference).first()
            if payment and payment.status not in {MonetizationPayment.SUCCESS, MonetizationPayment.REFUNDED}:
                payment.status = MonetizationPayment.FAILED
                payment.save(update_fields=['status'])
                notify_user(payment.user, Notification.PAYMENT_FAILED, 'Your subscription payment failed. No premium access was activated.')
        elif event_type == 'refund.processed':
            process_paystack_refund(str(data.get('transaction_reference') or data.get('reference') or ''))
        elif event_type in {'transfer.success', 'transfer.failed'}:
            finalize_withdrawal(
                str(data.get('reference') or data.get('transfer_code') or ''),
                success=event_type == 'transfer.success',
                reason=str(data.get('reason') or data.get('failure_reason') or 'Provider transfer failed.'),
            )
    except PaymentProviderError:
        # A verified event may be retried by the provider; no local entitlement is granted here.
        return HttpResponse('Verification pending.', status=202)
    return HttpResponse('ok')


@login_required
@require_POST
def cancel_subscription(request):
    subscription = get_object_or_404(
        PremiumSubscription,
        user=request.user,
        status=PremiumSubscription.ACTIVE,
        ends_at__gt=timezone.now(),
    )
    if subscription.provider_subscription_code:
        email_token = request.POST.get('email_token', '').strip()
        if not email_token:
            messages.error(request, 'Enter the cancellation code Paystack sent to your email.')
            return redirect('subscription_plans')
        try:
            PaystackClient().disable_subscription(subscription.provider_subscription_code, email_token)
        except PaymentProviderError as error:
            messages.error(request, str(error))
            return redirect('subscription_plans')
    subscription.cancel_at_period_end = True
    subscription.save(update_fields=['cancel_at_period_end', 'updated_at'])
    messages.success(request, 'Your subscription will remain active until its renewal date and will not renew again.')
    return redirect('subscription_plans')


@login_required
def writer_program(request):
    profile = WriterProfile.objects.filter(user=request.user).first()
    if request.method == 'POST' and (profile is None or profile.status in {WriterProfile.REJECTED, WriterProfile.PENDING}):
        form = WriterApplicationForm(request.POST, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.status = WriterProfile.PENDING
            profile.reviewed_by = None
            profile.reviewed_at = None
            profile.save()
            messages.success(request, 'Your writer-program application is pending admin approval.')
            return redirect('writer_dashboard')
    else:
        form = WriterApplicationForm(instance=profile)
    return render(request, 'books/writer_program.html', {'form': form, 'writer_profile': profile})


@login_required
@require_POST
def save_payout_details(request):
    profile = get_object_or_404(WriterProfile, user=request.user, status=WriterProfile.APPROVED)
    name = request.POST.get('account_name', '').strip()[:120]
    account_number = re.sub(r'\D', '', request.POST.get('account_number', ''))
    bank_code = request.POST.get('bank_code', '').strip()[:32]
    if not name or len(account_number) != 10 or not bank_code:
        messages.error(request, 'Enter an account name, 10-digit Nigerian account number, and bank code.')
        return redirect('writer_dashboard')
    try:
        recipient = PaystackClient().create_transfer_recipient(name, account_number, bank_code)
    except PaymentProviderError as error:
        messages.error(request, str(error))
        return redirect('writer_dashboard')
    profile.payout_recipient_code = str(recipient.get('recipient_code') or '')
    profile.payout_account_name = name
    profile.payout_account_last4 = account_number[-4:]
    profile.payout_bank_code = bank_code
    profile.save(update_fields=['payout_recipient_code', 'payout_account_name', 'payout_account_last4', 'payout_bank_code', 'updated_at'])
    messages.success(request, f'Payout account saved securely, ending in {profile.payout_account_last4}.')
    return redirect('writer_dashboard')


@login_required
@require_POST
def create_withdrawal(request):
    profile = get_object_or_404(WriterProfile, user=request.user, status=WriterProfile.APPROVED)
    form = WithdrawalRequestForm(request.POST)
    if not form.is_valid():
        messages.error(request, form.errors.get('amount', ['Enter a valid amount.'])[0])
        return redirect('writer_dashboard')
    try:
        request_withdrawal(profile, form.cleaned_data['amount'])
    except ValueError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, 'Withdrawal request submitted for review.')
    return redirect('writer_dashboard')


@login_required
@require_POST
def qualify_read(request):
    valid, message = qualify_reader_session(request, request.POST.get('token', ''))
    return JsonResponse({'ok': valid, 'message': message}, status=200 if valid else 400)


def ad_click(request, ad_id):
    ad = get_object_or_404(Advertisement, pk=ad_id, is_active=True)
    now = timezone.now()
    if (ad.starts_at and ad.starts_at > now) or (ad.ends_at and ad.ends_at <= now):
        raise Http404
    if has_active_subscription(request.user):
        raise Http404
    record_ad_click(ad, request)
    return redirect(ad.destination_url)