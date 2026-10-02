from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from django.urls import reverse

from .context_processors import monetization_context
from .models import (
    AdClick,
    AdImpression,
    Advertisement,
    Author,
    Book,
    Chapter,
    MonetizationConfig,
    MonetizationPayment,
    PremiumSubscription,
    ReaderSession,
    SubscriptionPlan,
    WriterEarning,
    WriterProfile,
    WriterWithdrawal,
)
from .monetization import (
    PaymentProviderError,
    active_subscription_for,
    get_reader_session,
    qualify_reader_session,
    request_withdrawal,
    verify_and_activate_subscription,
    writer_balances,
)


class MonetizationTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.writer_user = self.user_model.objects.create_user(
            username='monetized-writer', email='writer@example.test', password='testpass123',
        )
        self.reader = self.user_model.objects.create_user(
            username='monetized-reader', email='reader@example.test', password='testpass123',
        )
        self.author = Author.objects.create(name='Monetized Writer')
        self.book = Book.objects.create(
            title='A Verified Story', slug='verified-story', owner=self.writer_user,
            author=self.author, summary='Test story', status=Book.PUBLISHED,
        )
        self.chapter = Chapter.objects.create(
            book=self.book, chapter_number=1, title='First', slug='first', status=Chapter.PUBLISHED,
        )
        self.writer = WriterProfile.objects.create(
            user=self.writer_user, pen_name='Verified Pen', status=WriterProfile.APPROVED,
            payout_recipient_code='RCP_test', payout_account_last4='4321',
        )
        self.plan = SubscriptionPlan.objects.get(slug='premium-monthly')
        now = timezone.now()
        self.subscription = PremiumSubscription.objects.create(
            user=self.writer_user, plan=self.plan, status=PremiumSubscription.ACTIVE,
            starts_at=now - timedelta(days=1), ends_at=now + timedelta(days=30),
        )
        self.config = MonetizationConfig.objects.get(pk=1)

    def _request(self, user, path='/books/verified-story/chapter/1/'):
        request = RequestFactory().get(path)
        SessionMiddleware(lambda request: None).process_request(request)
        request.session.save()
        request.user = user
        return request

    def test_subscription_activates_only_after_verified_amount_and_is_idempotent(self):
        payment = MonetizationPayment.objects.create(
            user=self.reader, plan=self.plan, reference='subscription-test-ref',
            amount=self.plan.price, currency='NGN', status=MonetizationPayment.PENDING,
        )
        verified = {
            'status': 'success', 'reference': payment.reference,
            'amount': int(payment.amount * 100), 'currency': 'NGN', 'id': 12345,
        }
        with patch('books.monetization.PaystackClient.verify', return_value=verified) as verify:
            subscription = verify_and_activate_subscription(payment.reference)
            again = verify_and_activate_subscription(payment.reference)
        self.assertEqual(subscription.pk, again.pk)
        self.assertEqual(verify.call_count, 1)
        self.assertEqual(subscription.status, PremiumSubscription.ACTIVE)
        self.assertEqual(MonetizationPayment.objects.get(pk=payment.pk).status, MonetizationPayment.SUCCESS)

    def test_mismatched_payment_never_activates_subscription(self):
        payment = MonetizationPayment.objects.create(
            user=self.reader, plan=self.plan, reference='subscription-bad-ref',
            amount=self.plan.price, currency='NGN', status=MonetizationPayment.PENDING,
        )
        with patch('books.monetization.PaystackClient.verify', return_value={
            'status': 'success', 'reference': payment.reference,
            'amount': 1, 'currency': 'NGN',
        }):
            with self.assertRaises(PaymentProviderError):
                verify_and_activate_subscription(payment.reference)
        self.assertFalse(PremiumSubscription.objects.filter(user=self.reader, status=PremiumSubscription.ACTIVE).exists())
        self.assertEqual(MonetizationPayment.objects.get(pk=payment.pk).status, MonetizationPayment.FAILED)

    def test_qualifying_read_is_unique_and_writer_owned_reads_do_not_earn(self):
        request = self._request(self.reader)
        session = get_reader_session(request, self.book, self.chapter)
        ReaderSession.objects.filter(pk=session.pk).update(started_at=timezone.now() - timedelta(minutes=2))
        qualified, _ = qualify_reader_session(request, session.token)
        qualified_again, _ = qualify_reader_session(request, session.token)
        self.assertTrue(qualified)
        self.assertTrue(qualified_again)
        self.assertEqual(WriterEarning.objects.filter(reader_session=session).count(), 1)
        self.chapter.refresh_from_db()
        self.assertEqual(self.chapter.view_count, 1)

        author_request = self._request(self.writer_user)
        author_session = get_reader_session(author_request, self.book, self.chapter)
        ReaderSession.objects.filter(pk=author_session.pk).update(started_at=timezone.now() - timedelta(minutes=2))
        qualify_reader_session(author_request, author_session.token)
        self.assertFalse(WriterEarning.objects.filter(reader_session=author_session).exists())

    def test_ads_are_hidden_for_subscribers_and_frequency_capped_for_guests(self):
        self.config.ad_frequency_cap = 1
        self.config.save(update_fields=['ad_frequency_cap'])
        ad = Advertisement.objects.create(
            title='Reading tools', destination_url='https://example.com/sponsor',
            placement=Advertisement.SITE_BANNER, is_active=True,
        )
        guest_request = self._request(AnonymousUser())
        first = monetization_context(guest_request)
        second = monetization_context(guest_request)
        self.assertEqual(first['site_banner_ad'].pk, ad.pk)
        self.assertIsNone(second['site_banner_ad'])
        self.assertEqual(AdImpression.objects.filter(ad=ad).count(), 1)

        subscriber_request = self._request(self.writer_user)
        context = monetization_context(subscriber_request)
        self.assertTrue(context['has_active_subscription'])
        self.assertIsNone(context['site_banner_ad'])

    def test_withdrawal_reserves_balance_and_rejects_double_spend(self):
        self.config.minimum_withdrawal = Decimal('500.00')
        self.config.save(update_fields=['minimum_withdrawal'])
        WriterEarning.objects.create(
            writer=self.writer, book=self.book, chapter=self.chapter,
            amount=Decimal('10000.00'), currency='NGN', status=WriterEarning.AVAILABLE,
        )
        withdrawal = request_withdrawal(self.writer, Decimal('7000.00'))
        self.assertEqual(withdrawal.status, WriterWithdrawal.PENDING)
        balances = writer_balances(self.writer)
        self.assertEqual(balances['reserved'], Decimal('7000.00'))
        self.assertEqual(balances['available'], Decimal('3000.00'))
        with self.assertRaises(ValueError):
            request_withdrawal(self.writer, Decimal('4000.00'))

    def test_expired_subscription_is_deactivated_and_no_longer_entitles_ads_free_access(self):
        self.subscription.ends_at = timezone.now() - timedelta(seconds=1)
        self.subscription.save(update_fields=['ends_at'])
        self.assertIsNone(active_subscription_for(self.writer_user))
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, PremiumSubscription.EXPIRED)

    def test_checkout_fails_closed_without_provider_credentials(self):
        self.client.force_login(self.reader)
        with override_settings(PAYSTACK_SECRET_KEY=''):
            response = self.client.post(reverse('subscription_checkout', args=[self.plan.slug]))
        self.assertRedirects(response, reverse('subscription_plans'))
        payment = MonetizationPayment.objects.get(user=self.reader, plan=self.plan)
        self.assertEqual(payment.status, MonetizationPayment.FAILED)
        self.assertFalse(PremiumSubscription.objects.filter(user=self.reader, status=PremiumSubscription.ACTIVE).exists())

    def test_subscription_callback_cannot_access_another_users_payment(self):
        payment = MonetizationPayment.objects.create(
            user=self.reader, plan=self.plan, reference='private-callback-ref',
            amount=self.plan.price, currency='NGN', status=MonetizationPayment.PENDING,
        )
        self.client.force_login(self.writer_user)
        response = self.client.get(reverse('paystack_callback'), {'reference': payment.reference})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(MonetizationPayment.objects.get(pk=payment.pk).status, MonetizationPayment.PENDING)

    def test_writer_program_application_is_saved_pending(self):
        self.client.force_login(self.reader)
        response = self.client.post(reverse('writer_program'), {'pen_name': 'Reader Pen', 'bio': 'A short writer biography.'})
        self.assertRedirects(response, reverse('writer_dashboard'))
        profile = WriterProfile.objects.get(user=self.reader)
        self.assertEqual(profile.status, WriterProfile.PENDING)

    def test_writer_payout_details_are_tokenized_and_only_last_four_are_stored(self):
        self.client.force_login(self.writer_user)
        with patch('books.monetization_views.PaystackClient.create_transfer_recipient', return_value={'recipient_code': 'RCP_secure'}):
            response = self.client.post(reverse('save_payout_details'), {
                'account_name': 'Verified Writer', 'account_number': '0123456789', 'bank_code': '058',
            })
        self.assertRedirects(response, reverse('writer_dashboard'))
        self.writer.refresh_from_db()
        self.assertEqual(self.writer.payout_recipient_code, 'RCP_secure')
        self.assertEqual(self.writer.payout_account_last4, '6789')
        self.assertFalse(hasattr(self.writer, 'payout_account_number'))

    def test_ad_click_is_tracked_for_free_users_and_denied_for_subscribers(self):
        ad = Advertisement.objects.create(
            title='Reading tools', destination_url='https://example.com/sponsor',
            placement=Advertisement.SITE_BANNER, is_active=True,
        )
        response = self.client.get(reverse('ad_click', args=[ad.pk]))
        self.assertRedirects(response, 'https://example.com/sponsor', fetch_redirect_response=False)
        self.assertEqual(AdClick.objects.filter(ad=ad).count(), 1)
        self.client.force_login(self.writer_user)
        self.assertEqual(self.client.get(reverse('ad_click', args=[ad.pk])).status_code, 404)
        self.assertEqual(AdClick.objects.filter(ad=ad).count(), 1)

    def test_custom_admin_dashboard_renders_monetization_overview(self):
        admin_user = self.user_model.objects.create_user(
            username='monetization-admin', email='admin@example.test', password='testpass123', is_staff=True,
        )
        self.client.force_login(admin_user)
        response = self.client.get('/admin/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Monetization')
        self.assertContains(response, '/admin/books/subscriptionplan/')
        self.assertContains(response, '/admin/books/writerwithdrawal/')