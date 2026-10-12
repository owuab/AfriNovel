from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import RequestFactory
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.models import SocialLogin
from allauth.core.exceptions import ImmediateHttpResponse

from .models import (
    AuthenticationEvent, Author, Book, CatalogBook, CatalogCategory, ContentReport, Genre, Notification,
    PostComment, PostLike, Permission, ReadingProgress, Review, RolePermission,
    SocialPost, UserBookshelf, ReadingList, UserFollow, BookUpload, Chapter,
    Promotion, Competition, CompetitionEntry, Award, AwardCategory, AwardNominee,
    CriticProfile, CriticApplication, ReviewAssignment, CriticReview, CriticEarning,
)
from .admin_models import AdminAuditLog, AdminRole, BookApprovalStatus, UserSuspension
from .admin_utilities import PermissionService
from .services import CatalogService, NormalizedBook
from .social_auth import BookClubSocialAccountAdapter


class PermissionRBACPhase1Tests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='rbac-admin', password='testpass123', is_staff=True)
        self.permission = Permission.objects.create(
            module='users',
            action='read',
            name='users:read',
            description='View user accounts',
            category='users',
            is_system=True,
        )
        self.admin_role = AdminRole.objects.create(user=self.user, role=AdminRole.ADMIN)
        self.user.refresh_from_db()

    def test_permission_service_checks_granted_role_permissions(self):
        RolePermission.objects.create(role_name='admin', permission=self.permission)
        self.assertTrue(PermissionService.has_permission(self.user, 'users:read'))
        self.assertFalse(PermissionService.has_permission(self.user, 'users:delete'))

    def test_permission_matrix_page_is_available_to_admins(self):
        self.client.force_login(self.user)
        response = self.client.get('/admin-panel/permissions/matrix/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Permission Matrix')


class HomePageTests(TestCase):
    def setUp(self):
        self.author = Author.objects.create(name='Amina Yusuf', bio='Writer of literary fiction.')
        self.genre = Genre.objects.create(name='Fiction')
        self.book = Book.objects.create(
            title='The Quiet Horizon',
            slug='the-quiet-horizon',
            author=self.author,
            summary='A thoughtful story about memory and belonging.',
            rating=4.8,
            status=Book.PUBLISHED,
            is_featured=True,
        )
        self.book.genres.add(self.genre)
        self.user = get_user_model().objects.create_user(username='reader1', password='testpass123')
        self.review = Review.objects.create(
            book=self.book,
            user=self.user,
            content='Beautifully written and haunting.'
        )

    def test_home_page_returns_200(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_authenticated_navigation_exposes_writer_dashboard(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'href="/dashboard/writer/" class="nav-link">Write</a>')

    def test_rankings_page_renders_all_ranking_aggregates(self):
        for ranking_type in ('rating', 'reviews', 'trending'):
            with self.subTest(ranking_type=ranking_type):
                response = self.client.get(reverse('rankings'), {'type': ranking_type})
                self.assertEqual(response.status_code, 200)

    def test_home_page_has_book_search_form(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'homepage-search-form')
        self.assertContains(response, 'action="/search/"')
        self.assertContains(response, 'name="q"')

    def test_staff_login_redirects_to_admin_dashboard(self):
        staff_user = get_user_model().objects.create_user(
            username='staff-login',
            password='testpass123',
            is_staff=True,
        )
        response = self.client.post(reverse('login'), {
            'username': staff_user.username,
            'password': 'testpass123',
        })
        self.assertRedirects(response, reverse('admin_panel:dashboard'))

    def test_home_page_contains_brand_name_and_featured_book(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'AfriNovel')
        self.assertContains(response, 'The Quiet Horizon')

    def test_home_page_shows_legal_free_catalog_books_without_login(self):
        CatalogBook.objects.create(
            source='gutenberg',
            external_id='123',
            title='Public Domain Classic',
            authors=['Amina Nkrumah'],
            source_url='https://www.gutenberg.org/ebooks/123',
            reading_url='https://www.gutenberg.org/cache/epub/123/pg123.txt',
            access_type=CatalogBook.PUBLIC_DOMAIN,
            copyright_status=CatalogBook.PUBLIC_DOMAIN_STATUS,
            full_text_available=True,
        )
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Domain Classic')
        self.assertContains(response, 'Free to read')

    def test_home_page_shows_asian_books_section_and_categorized_books(self):
        catalog_book = CatalogBook.objects.create(
            source='gutenberg',
            external_id='asian-1',
            title='A Japanese Tale',
            authors=['Japanese Author'],
            languages=['jpn'],
            source_url='https://www.gutenberg.org/ebooks/asian-1',
            reading_url='https://www.gutenberg.org/cache/epub/asian-1/book.txt',
            access_type=CatalogBook.PUBLIC_DOMAIN,
            copyright_status=CatalogBook.PUBLIC_DOMAIN_STATUS,
            full_text_available=True,
        )
        CatalogCategory.objects.create(
            book=catalog_book,
            category=CatalogCategory.ASIAN,
            subcategory='japanese',
        )
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Asian Books')
        self.assertContains(response, 'Chinese')
        self.assertContains(response, 'Korean')
        self.assertContains(response, 'Japanese')
        self.assertContains(response, 'South Asian')
        self.assertContains(response, 'Southeast Asian')
        self.assertContains(response, 'A Japanese Tale')

    def test_home_page_seeds_free_catalog_books_even_when_regular_books_exist(self):
        CatalogBook.objects.create(
            source='gutenberg',
            external_id='456',
            title='A Free Catalog Novel',
            authors=['Jane Doe'],
            subjects=['Fiction'],
            source_url='https://www.gutenberg.org/ebooks/456',
            reading_url='https://www.gutenberg.org/cache/epub/456/pg456.txt',
            access_type=CatalogBook.PUBLIC_DOMAIN,
            copyright_status=CatalogBook.PUBLIC_DOMAIN_STATUS,
            full_text_available=True,
        )
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A Free Catalog Novel')
        self.assertTrue(Book.objects.filter(title='A Free Catalog Novel').exists())

    @patch.object(CatalogService, 'search', return_value=([
        NormalizedBook(
            external_id='OL912W',
            source='open_library',
            title='Pride and Prejudice',
            authors=['Jane Austen'],
            source_url='https://openlibrary.org/works/OL912W',
            reading_url='https://www.gutenberg.org/cache/epub/912/pg912.txt',
            access_type=CatalogBook.PUBLIC_DOMAIN,
            copyright_status=CatalogBook.PUBLIC_DOMAIN_STATUS,
            full_text_available=True,
        )
    ], 1, []))
    def test_catalog_service_ensures_local_public_domain_seed(self, _search):
        CatalogBook.objects.all().delete()
        seeded = CatalogService.ensure_local_public_domain_seed()
        self.assertTrue(CatalogBook.objects.filter(source='open_library', external_id='OL912W').exists())
        self.assertGreater(len(seeded), 0)

    @patch.object(CatalogService, 'search', return_value=([
        NormalizedBook(
            external_id='OL456W',
            source='open_library',
            title='Alice in Wonderland',
            authors=['Lewis Carroll'],
            source_url='https://openlibrary.org/works/OL456W',
            reading_url='https://www.gutenberg.org/cache/epub/456/pg456.txt',
            access_type=CatalogBook.PUBLIC_DOMAIN,
            copyright_status=CatalogBook.PUBLIC_DOMAIN_STATUS,
            full_text_available=True,
        )
    ], 1, []))
    def test_seed_public_domain_catalog_command_persists_approved_books(self, _search):
        CatalogBook.objects.all().delete()
        call_command('seed_public_domain_catalog', limit=5)
        self.assertTrue(CatalogBook.objects.filter(source='open_library', external_id='OL456W').exists())

    def test_book_detail_page_returns_200(self):
        response = self.client.get(reverse('book_detail', args=[self.book.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The Quiet Horizon')
        self.assertContains(response, 'Beautifully written and haunting.')

    def test_catalogue_book_read_link_opens_actual_reader_without_login(self):
        catalog_book = CatalogBook.objects.create(
            source='gutenberg', external_id='test-1342', title='Pride and Prejudice',
            authors=['Jane Austen'], source_url='https://www.gutenberg.org/ebooks/1342',
            reading_url='https://www.gutenberg.org/cache/epub/1342/pg1342.txt',
            access_type=CatalogBook.PUBLIC_DOMAIN,
            copyright_status=CatalogBook.PUBLIC_DOMAIN_STATUS,
            full_text_available=True,
        )
        imported = Book.objects.create(
            title=catalog_book.title, slug='pride-and-prejudice-test', author=self.author,
            summary='Public domain text', catalog_book=catalog_book, status=Book.PUBLISHED,
        )
        with patch('books.views.fetch_reader_text', return_value='The actual book text.'):
            response = self.client.get(imported.get_reader_url(), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The actual book text.')

    def test_guest_completed_page_contains_no_uncompleted_books(self):
        response = self.client.get(reverse('completed'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Completed books are private to each reader.')
        self.assertNotContains(response, self.book.title)

    def test_reader_dashboard_returns_200(self):
        response = self.client.get(reverse('reader_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Library')

    def test_writer_dashboard_returns_200(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('writer_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Drafts')

    def test_staff_admin_dashboard_returns_200(self):
        staff_user = get_user_model().objects.create_superuser(
            username='dashboard-admin',
            email='dashboard-admin@example.com',
            password='testpass123',
        )
        self.client.force_login(staff_user)
        response = self.client.get('/admin/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Dashboard')

    def test_superuser_can_access_admin_content_without_custom_role(self):
        superuser = get_user_model().objects.create_superuser(
            username='content-admin',
            email='content-admin@example.com',
            password='testpass123',
        )
        self.client.force_login(superuser)
        response = self.client.get('/admin-panel/users/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User Management')

    def test_superuser_can_render_user_detail(self):
        superuser = get_user_model().objects.create_superuser(
            username='detail-admin',
            email='detail-admin@example.com',
            password='testpass123',
        )
        self.client.force_login(superuser)
        response = self.client.get(f'/admin-panel/users/{self.user.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user.username)
        self.assertContains(response, 'Published books')

    def test_superuser_can_render_content_reports(self):
        superuser = get_user_model().objects.create_superuser(
            username='reports-admin',
            email='reports-admin@example.com',
            password='testpass123',
        )
        ContentReport.objects.create(
            reporter=self.user,
            reported_user=superuser,
            reason=ContentReport.SPAM,
            details='Test report details',
        )
        self.client.force_login(superuser)
        response = self.client.get('/admin-panel/reports/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Content Reports')
        self.assertContains(response, 'Test report details')

    def test_superuser_can_render_admin_role_pages(self):
        superuser = get_user_model().objects.create_superuser(
            username='roles-admin',
            email='roles-admin@example.com',
            password='testpass123',
        )
        role = AdminRole.objects.create(
            user=self.user,
            role=AdminRole.ADMIN,
            assigned_by=superuser,
        )
        self.client.force_login(superuser)
        list_response = self.client.get('/admin-panel/roles/')
        detail_response = self.client.get(f'/admin-panel/roles/{role.pk}/')
        form_response = self.client.get('/admin-panel/roles/assign/')
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(form_response.status_code, 200)
        self.assertContains(list_response, 'Admin roles')
        self.assertContains(detail_response, self.user.username)
        self.assertContains(form_response, 'Assign admin role')

    def test_superuser_can_render_audit_logs(self):
        superuser = get_user_model().objects.create_superuser(
            username='audit-admin',
            email='audit-admin@example.com',
            password='testpass123',
        )
        AdminAuditLog.log_action(
            admin_user=superuser,
            action=AdminAuditLog.USER_EDITED,
            description='Updated a user profile',
            target_user=self.user,
        )
        self.client.force_login(superuser)
        response = self.client.get('/admin-panel/audit-logs/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Audit logs')
        self.assertContains(response, 'Updated a user profile')

    def test_admin_can_open_genre_popup_add_form(self):
        superuser = get_user_model().objects.create_superuser(
            username='genre-admin',
            email='genre-admin@example.com',
            password='testpass123',
        )
        self.client.force_login(superuser)
        response = self.client.get('/admin/books/genre/add/?_to_field=id&_popup=1')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id_slug')

    def test_social_feed_post_like_comment_and_follow(self):
        other_user = get_user_model().objects.create_user(username='social-reader', password='testpass123')
        self.client.force_login(self.user)
        created = self.client.post(reverse('create_post'), {'content': 'Reading a wonderful book today.', 'book_id': self.book.pk})
        post = SocialPost.objects.get(author=self.user)
        self.assertRedirects(created, reverse('post_detail', args=[post.pk]))

        self.client.force_login(other_user)
        self.client.post(reverse('toggle_post_like', args=[post.pk]))
        self.client.post(reverse('create_post_comment', args=[post.pk]), {'content': 'Adding this to my list.'})
        self.client.post(reverse('toggle_user_follow', args=[self.user.username]))

        self.assertTrue(PostLike.objects.filter(user=other_user, post=post).exists())
        self.assertTrue(PostComment.objects.filter(author=other_user, post=post).exists())
        self.assertTrue(UserFollow.objects.filter(follower=other_user, followed=self.user).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.user, actor=other_user).exists())

    def test_reader_dashboard_has_working_social_navigation(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('reader_dashboard'))
        self.assertContains(response, reverse('reading_now'))
        self.assertContains(response, reverse('social_reviews'))
        self.assertContains(response, reverse('book_recommendations'))

    def test_social_destination_routes_do_not_resolve_as_feed_tabs(self):
        self.client.force_login(self.user)
        for route_name in ('notifications_page', 'reading_now', 'social_reviews', 'book_recommendations', 'saved_content'):
            response = self.client.get(reverse(route_name))
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, 'Unknown feed.')

    def test_review_create_page_returns_200(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('review_create', args=[self.book.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Write a review')

    def test_review_create_post_creates_review(self):
        user = get_user_model().objects.create_user(username='reviewer2', password='testpass123')
        self.client.force_login(user)
        response = self.client.post(
            reverse('review_create', args=[self.book.slug]),
            {'content': 'A compelling and thoughtful read.'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Review.objects.filter(content='A compelling and thoughtful read.').exists())

    def test_publish_page_creates_book(self):
        user = get_user_model().objects.create_user(username='writer2', password='testpass123')
        self.client.force_login(user)
        response = self.client.post(
            reverse('publish_book'),
            {
                'title': 'New Literary Work',
                'slug': 'new-literary-work',
                'summary': 'A new novel that explores memory and migration.',
                'cover_color': 'linear-gradient(135deg, #dfe7d2, #5f7a54)',
                'status': Book.PUBLISHED,
                'manuscript': SimpleUploadedFile('new-work.epub', b'epub test content', content_type='application/epub+zip'),
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Book.objects.filter(slug='new-literary-work').exists())
        self.assertEqual(Book.objects.get(slug='new-literary-work').status, Book.DRAFT)

    def test_publish_page_rejects_unsupported_manuscript(self):
        user = get_user_model().objects.create_user(username='writer-invalid', password='testpass123')
        self.client.force_login(user)
        response = self.client.post(
            reverse('publish_book'),
            {
                'title': 'Invalid Upload',
                'slug': 'invalid-upload',
                'summary': 'This should not be created.',
                'manuscript': SimpleUploadedFile('malware.exe', b'not allowed', content_type='application/octet-stream'),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'unsupported manuscript format')
        self.assertFalse(Book.objects.filter(slug='invalid-upload').exists())

    def test_provision_superadmin_demotes_other_admin_accounts(self):
        other_admin = get_user_model().objects.create_superuser(
            username='old-admin', email='old-admin@example.com', password='testpass123'
        )
        call_command('provision_superadmin', username='Admin', password='test-superadmin-password')
        admin = get_user_model().objects.get(username='Admin')
        other_admin.refresh_from_db()
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)
        self.assertFalse(other_admin.is_superuser)
        self.assertFalse(other_admin.is_staff)

    def test_provisioned_superadmin_can_log_in_to_custom_admin(self):
        call_command('provision_superadmin', username='Admin', password='test-superadmin-password')
        response = self.client.post('/admin/login/?next=/admin/', {
            'username': 'Admin',
            'password': 'test-superadmin-password',
            'next': '/admin/',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/admin/')

    def test_login_page_returns_200(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign in')

    def test_signup_page_returns_200(self):
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create account')

    def test_social_provider_settings_include_github(self):
        self.assertIn('github', settings.SOCIALACCOUNT_PROVIDERS)
        self.assertTrue(any('github' in app.lower() for app in settings.INSTALLED_APPS))

    def test_register_alias_returns_signup_page(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create account')

    def test_password_login_accepts_existing_email_and_records_event(self):
        self.user.email = 'reader@example.com'
        self.user.save(update_fields=['email'])
        response = self.client.post(reverse('login'), {'username': 'reader@example.com', 'password': 'testpass123'})
        self.assertRedirects(response, reverse('home'))
        self.assertTrue(AuthenticationEvent.objects.filter(user=self.user, event_type=AuthenticationEvent.PASSWORD_LOGIN).exists())

    def test_logout_ends_authenticated_session(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('landing_page'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_accepts_get_navigation_request(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('landing_page'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_registration_persists_email_and_names(self):
        signup_page = self.client.get(reverse('signup'))
        self.assertContains(signup_page, 'name="first_name"')
        self.assertContains(signup_page, 'name="last_name"')
        response = self.client.post(reverse('signup'), {
            'first_name': 'Ada', 'last_name': 'Lovelace', 'username': 'ada',
            'email': 'ada@example.com', 'password1': 'Complex-pass-123', 'password2': 'Complex-pass-123',
        })
        self.assertRedirects(response, reverse('home'))
        user = get_user_model().objects.get(username='ada')
        self.assertEqual(user.email, 'ada@example.com')
        self.assertEqual(user.first_name, 'Ada')
        self.assertTrue(user.check_password('Complex-pass-123'))
        self.client.post(reverse('logout'))
        login_response = self.client.post(reverse('login'), {
            'username': 'ada@example.com',
            'password': 'Complex-pass-123',
        })
        self.assertRedirects(login_response, reverse('home'))

    def test_connected_accounts_requires_login(self):
        response = self.client.get(reverse('connected_accounts'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_cannot_disconnect_only_social_login_without_password(self):
        self.user.set_unusable_password()
        self.user.save()
        account = SocialAccount.objects.create(user=self.user, provider='google', uid='google-user-1', extra_data={'email': 'reader@example.com'})
        self.client.force_login(self.user)
        response = self.client.post(reverse('disconnect_social_account', args=['google']))
        self.assertRedirects(response, reverse('connected_accounts'))
        self.assertTrue(SocialAccount.objects.filter(pk=account.pk).exists())

    def test_registration_rejects_existing_email(self):
        self.user.email = 'reader@example.com'
        self.user.save(update_fields=['email'])
        response = self.client.post(reverse('signup'), {
            'first_name': 'Another', 'last_name': 'Reader', 'username': 'another-reader',
            'email': 'reader@example.com', 'password1': 'Complex-pass-123', 'password2': 'Complex-pass-123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username='another-reader').exists())
        self.assertContains(response, 'already uses this email address')

    def test_password_login_rejects_external_next_redirect(self):
        response = self.client.post(reverse('login'), {
            'username': 'reader1', 'password': 'testpass123', 'next': 'https://unsafe.example/phish',
        })
        self.assertRedirects(response, reverse('home'))

    def test_social_adapter_requires_existing_user_to_link_while_signed_in(self):
        self.user.email = 'reader@example.com'
        self.user.save(update_fields=['email'])
        request = RequestFactory().get('/accounts/google/login/callback/')
        SessionMiddleware(lambda request: None).process_request(request)
        request.session.save()
        MessageMiddleware(lambda request: None).process_request(request)
        request.user = type('Anonymous', (), {'is_authenticated': False})()
        social_login = SocialLogin(
            account=SocialAccount(provider='google', uid='google-identity', extra_data={'email': 'reader@example.com'}),
            user=get_user_model()(email='reader@example.com'),
        )
        with self.assertRaises(ImmediateHttpResponse) as raised:
            BookClubSocialAccountAdapter().pre_social_login(request, social_login)
        self.assertIn(reverse('login'), raised.exception.response.url)

    def test_profile_page_returns_200_for_logged_in_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user.username)

    def test_author_profile_page_returns_200(self):
        response = self.client.get(reverse('author_profile', args=[self.author.name.replace(' ', '-')]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.author.name)

    def test_review_comment_page_returns_200(self):
        response = self.client.get(reverse('review_comments', args=[self.book.slug, self.review.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Comments')

    def test_review_comment_post_creates_comment(self):
        user = get_user_model().objects.create_user(username='commenter1', password='testpass123')
        self.client.force_login(user)
        response = self.client.post(
            reverse('review_comments', args=[self.book.slug, self.review.id]),
            {'content': 'I agree with this review.'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'I agree with this review.')

    def test_follow_author_page_redirects(self):
        user = get_user_model().objects.create_user(username='follower1', password='testpass123')
        self.client.force_login(user)
        response = self.client.post(reverse('follow_author', args=[self.author.id]))
        self.assertEqual(response.status_code, 302)

    def test_genre_page_returns_200(self):
        response = self.client.get(reverse('genre_page', args=[self.genre.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.genre.name)

    def test_search_page_returns_matching_books(self):
        response = self.client.get(reverse('search_books') + '?q=quiet')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The Quiet Horizon')

    def test_add_book_to_bookshelf(self):
        user = get_user_model().objects.create_user(username='bookshelf_user', password='testpass123')
        self.client.force_login(user)
        response = self.client.post(
            reverse('add_to_bookshelf', args=[self.book.slug]),
            {'status': UserBookshelf.CURRENTLY_READING},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(UserBookshelf.objects.filter(user=user, book=self.book).exists())
        bookshelf_item = UserBookshelf.objects.get(user=user, book=self.book)
        self.assertEqual(bookshelf_item.status, UserBookshelf.CURRENTLY_READING)

    def test_view_bookshelf_returns_200(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('view_bookshelf'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Bookshelf')

    def test_update_bookshelf_item(self):
        self.client.force_login(self.user)
        shelf_item = UserBookshelf.objects.create(
            user=self.user,
            book=self.book,
            status=UserBookshelf.WANT_TO_READ,
            progress_percent=0,
        )
        response = self.client.post(
            reverse('update_bookshelf', args=[shelf_item.id]),
            {
                'status': UserBookshelf.CURRENTLY_READING,
                'progress_percent': 45,
                'rating': 4,
                'notes': 'Great book so far!',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        shelf_item.refresh_from_db()
        self.assertEqual(shelf_item.status, UserBookshelf.CURRENTLY_READING)
        self.assertEqual(shelf_item.progress_percent, 45)
        self.assertEqual(shelf_item.rating, 4)

    def test_remove_from_bookshelf(self):
        self.client.force_login(self.user)
        shelf_item = UserBookshelf.objects.create(
            user=self.user,
            book=self.book,
            status=UserBookshelf.WANT_TO_READ,
        )
        response = self.client.post(
            reverse('remove_from_bookshelf', args=[shelf_item.id]),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(UserBookshelf.objects.filter(id=shelf_item.id).exists())

    def test_recommendations_page_returns_200(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('recommendations'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Books for You')

    def test_recommendations_based_on_reading_history(self):
        self.client.force_login(self.user)
        # Add book to reading history
        UserBookshelf.objects.create(
            user=self.user,
            book=self.book,
            status=UserBookshelf.READ,
        )
        # Create another book in same genre
        book2 = Book.objects.create(
            title='Another Fiction',
            slug='another-fiction',
            author=self.author,
            summary='A second fiction book.',
            rating=4.5,
            status=Book.PUBLISHED,
        )
        book2.genres.add(self.genre)
        
        response = self.client.get(reverse('recommendations'))
        self.assertEqual(response.status_code, 200)
        # Recommendations should include book2 but not book (already read)
        self.assertContains(response, 'Another Fiction')

    def test_create_reading_list(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('create_reading_list'),
            {
                'title': 'Summer Reads',
                'description': 'Books to read this summer',
                'is_public': 'on',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ReadingList.objects.filter(title='Summer Reads', user=self.user).exists())

    def test_reading_list_detail_returns_200(self):
        reading_list = ReadingList.objects.create(
            user=self.user,
            title='My List',
            description='Test list',
            is_public=True,
        )
        reading_list.books.add(self.book)
        
        response = self.client.get(
            reverse('reading_list_detail', args=[self.user.username, reading_list.slug])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My List')
        self.assertContains(response, self.book.title)

    def test_add_book_to_reading_list(self):
        self.client.force_login(self.user)
        reading_list = ReadingList.objects.create(
            user=self.user,
            title='My List',
            is_public=True,
        )
        
        response = self.client.post(
            reverse('add_to_reading_list', args=[reading_list.slug, self.book.id]),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(reading_list.books.filter(id=self.book.id).exists())

    def test_my_reading_lists_returns_200(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('my_reading_lists'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Reading Lists')


class PermissionModelTests(TestCase):
    def test_permission_registry_creates_unique_module_action(self):
        permission = Permission.objects.create(
            name='users:read',
            module='users',
            action='read',
            description='Read user accounts',
            category='users',
            is_system=True,
        )

        self.assertEqual(permission.name, 'users:read')
        self.assertTrue(Permission.objects.filter(module='users', action='read').exists())

        with self.assertRaises(Exception):
            Permission.objects.create(
                name='users:read',
                module='users',
                action='read',
            )

    def test_role_permission_tracks_revocation_and_grant_metadata(self):
        user = get_user_model().objects.create_user(username='admin-grantor', password='testpass123')
        role = get_user_model().objects.create_user(username='role-target', password='testpass123')
        permission = Permission.objects.create(
            name='reports:resolve',
            module='reports',
            action='resolve',
            description='Resolve reports',
            category='reports',
        )

        link = RolePermission.objects.create(
            role_name='moderator',
            permission=permission,
            granted_by=user,
        )

        self.assertEqual(link.role_name, 'moderator')
        self.assertEqual(link.permission, permission)
        self.assertIsNone(link.revoked_at)

        link.revoked_by = user
        link.revoked_at = timezone.now()
        link.save()

        self.assertIsNotNone(link.revoked_at)


class CatalogueFeatureTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='catalogue-reader', password='testpass123')
        self.book = CatalogBook.objects.create(
            source='open_library', external_id='OL123W', title='A Public Domain Book',
            authors=['Library Author'], source_url='https://www.gutenberg.org/ebooks/123',
            reading_url='https://www.gutenberg.org/cache/epub/123/pg123.txt',
            access_type=CatalogBook.PUBLIC_DOMAIN,
            copyright_status=CatalogBook.PUBLIC_DOMAIN_STATUS,
            full_text_available=True,
        )

    @patch('books.views.CatalogService.search')
    def test_discover_persists_normalized_legal_results(self, search):
        search.return_value = ([NormalizedBook(
            external_id='OL456W', source='open_library', title='Discoverable Book',
            authors=['Global Author'], source_url='https://openlibrary.org/works/OL456W',
        )], 1, [])
        response = self.client.get(reverse('discover'), {'q': 'global history'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Discoverable Book')
        self.assertTrue(CatalogBook.objects.filter(external_id='OL456W').exists())

    @patch('books.views.fetch_reader_text', return_value='CHAPTER I\n\nAuthorized reading text.')
    def test_authorized_reader_renders_source_text(self, _fetch_text):
        self.client.force_login(self.user)
        response = self.client.get(reverse('catalogue_reader', args=[self.book.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Authorized reading text.')

    def test_progress_api_persists_reader_location(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('api_reading_progress', args=[self.book.pk]),
            data='{"chapter":"Chapter 2","paragraph":4,"percent":42}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        progress = ReadingProgress.objects.get(user=self.user, book=self.book)
        self.assertEqual(progress.chapter, 'Chapter 2')
        self.assertEqual(progress.paragraph, 4)
        self.assertEqual(float(progress.percent), 42)

    @patch('books.views.fetch_reader_text', return_value='CHAPTER I\n\nColonialism is discussed here.\n\nCHAPTER II\n\nAnother legal paragraph.')
    def test_authorized_reader_chapters_and_search_apis(self, _fetch_text):
        self.client.force_login(self.user)
        chapters = self.client.get(reverse('api_reader_chapters', args=[self.book.pk]))
        self.assertEqual(chapters.status_code, 200)
        self.assertEqual(chapters.json()['chapters'][0]['title'], 'Beginning')

        search = self.client.get(reverse('api_search_in_book', args=[self.book.pk]), {'q': 'colonialism'})
        self.assertEqual(search.status_code, 200)
        self.assertEqual(len(search.json()['results']), 1)

    @patch('books.views.CatalogService.search')
    def test_unmatched_legacy_search_uses_corrected_global_catalogue_query(self, search):
        search.side_effect = [([], 0, []), ([NormalizedBook(
            external_id='OL789W', source='open_library', title='Things Fall Apart',
            source_url='https://openlibrary.org/works/OL789W',
        )], 1, [])]
        response = self.client.get(reverse('search_books'), {'q': 'things all apart'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Things Fall Apart')
        self.assertContains(response, 'Showing catalogue results for')


class BookUploadApprovalTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='writer', password='testpass123')
        self.admin = get_user_model().objects.create_user(
            username='content-admin', password='testpass123', is_staff=True,
            email='admin@example.com',
        )
        AdminRole.objects.create(user=self.admin, role=AdminRole.CONTENT_MANAGER)

    @patch('books.views.AdminNotificationManager.notify_pending_approval')
    def test_upload_creates_pending_approval_and_notifies_admin(self, notify):
        self.client.force_login(self.user)
        manuscript = SimpleUploadedFile('manuscript.epub', b'epub content', content_type='application/epub+zip')

        response = self.client.post(reverse('publish_book'), {
            'title': 'A New Story',
            'slug': 'a-new-story',
            'summary': 'A story awaiting review.',
            'status': Book.PUBLISHED,
            'manuscript': manuscript,
        })

        self.assertRedirects(response, reverse('writer_dashboard'))
        book = Book.objects.get(slug='a-new-story')
        self.assertEqual(book.status, Book.DRAFT)
        self.assertEqual(BookApprovalStatus.objects.get(book=book).status, BookApprovalStatus.PENDING)
        self.assertTrue(BookUpload.objects.filter(book=book, kind=BookUpload.MANUSCRIPT).exists())
        notify.assert_called_once_with()

    def test_approve_book_redirects_to_approval_detail(self):
        author = Author.objects.create(name=self.user.username)
        book = Book.objects.create(
            title='Book To Approve',
            slug='book-to-approve',
            author=author,
            summary='A submitted book.',
            status=Book.DRAFT,
        )
        BookApprovalStatus.objects.create(book=book)

        self.client.force_login(self.admin)
        response = self.client.post(reverse('admin_panel:approve-book', args=[book.id]))

        self.assertRedirects(response, reverse('admin_panel:book-approval', args=[book.id]))
        self.assertEqual(BookApprovalStatus.objects.get(book=book).status, BookApprovalStatus.APPROVED)


class WriterWorkspaceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='story-writer', password='testpass123')
        self.other_user = get_user_model().objects.create_user(username='other-writer', password='testpass123')
        self.admin = get_user_model().objects.create_user(username='story-moderator', password='testpass123', is_staff=True)
        self.author = Author.objects.create(name=self.user.username)
        self.genre = Genre.objects.create(name='Speculative Fiction')
        self.book = Book.objects.create(
            title='The River Remembers',
            slug='the-river-remembers',
            owner=self.user,
            author=self.author,
            summary='A story of memory and return.',
            status=Book.DRAFT,
        )
        self.chapter = Chapter.objects.create(
            book=self.book, chapter_number=1, title='First Light', slug='first-light', status=Chapter.DRAFT,
        )

    def test_book_form_uses_single_genre_dropdown_and_checkable_rights_control(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('writer_book_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="genres" class="writer-genre-select"')
        self.assertContains(response, 'type="checkbox" name="original_work"')
        self.assertNotContains(response, 'name="subtitle"')
        self.assertNotContains(response, 'name="subgenre"')
        self.assertNotContains(response, 'name="tags"')

    def test_create_book_requires_rights_confirmation_and_opens_editor(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('writer_book_create'), {
            'title': 'New Story',
            'summary': 'A newly created story.',
            'genres': [self.genre.pk],
            'language': 'English',
            'content_rating': 'teen',
            'novel_status': Book.ONGOING,
            'original_work': 'on',
        })
        form_errors = response.context['form'].errors.as_json() if response.context else ''
        self.assertEqual(response.status_code, 302, form_errors)
        story = Book.objects.get(title='New Story')
        self.assertEqual(story.owner, self.user)
        self.assertTrue(story.rights_confirmed)
        self.assertEqual(story.status, Book.DRAFT)
        self.assertTrue(story.chapters.filter(status=Chapter.DRAFT).exists())
        self.assertIn('/dashboard/writer/books/', response['Location'])

    def test_chapter_autosave_sanitizes_markup_and_updates_counts(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('writer_chapter_editor', args=[self.book.pk, self.chapter.pk]),
            {'action': 'save', 'title': 'First Light', 'content': '<p>Hello <strong>world</strong></p><script>alert(1)</script>'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.chapter.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('<script>', self.chapter.content)
        self.assertIn('<strong>world</strong>', self.chapter.content)
        self.assertEqual(self.chapter.word_count, 3)

    def test_other_user_cannot_edit_owned_book_or_chapter(self):
        self.client.force_login(self.other_user)
        book_response = self.client.get(reverse('writer_book_edit', args=[self.book.pk]))
        chapter_response = self.client.get(reverse('writer_chapter_editor', args=[self.book.pk, self.chapter.pk]))
        self.assertEqual(book_response.status_code, 404)
        self.assertEqual(chapter_response.status_code, 404)

    def test_public_reader_hides_draft_chapters(self):
        self.book.status = Book.PUBLISHED
        self.book.save(update_fields=['status'])
        response = self.client.get(reverse('chapter_detail', args=[self.book.slug, self.chapter.chapter_number]))
        self.assertEqual(response.status_code, 404)
        self.chapter.status = Chapter.PUBLISHED
        self.chapter.save(update_fields=['status'])
        response = self.client.get(reverse('chapter_detail', args=[self.book.slug, self.chapter.chapter_number]))
        self.assertEqual(response.status_code, 200)

    def test_moderation_approval_publishes_only_first_draft_chapter(self):
        second_chapter = Chapter.objects.create(
            book=self.book, chapter_number=2, title='Next Day', slug='next-day', status=Chapter.DRAFT,
        )
        approval = BookApprovalStatus.objects.create(book=self.book)
        approval.approve(self.admin)
        self.chapter.refresh_from_db()
        second_chapter.refresh_from_db()
        self.book.refresh_from_db()
        self.assertEqual(self.book.status, Book.PUBLISHED)
        self.assertEqual(self.chapter.status, Chapter.PUBLISHED)
        self.assertEqual(second_chapter.status, Chapter.DRAFT)

    def test_reader_can_report_a_published_chapter(self):
        self.book.status = Book.PUBLISHED
        self.book.save(update_fields=['status'])
        self.chapter.status = Chapter.PUBLISHED
        self.chapter.save(update_fields=['status'])
        self.client.force_login(self.other_user)
        response = self.client.post(
            reverse('report_chapter', args=[self.book.slug, self.chapter.chapter_number]),
            {'reason': ContentReport.COPYRIGHT, 'details': 'This chapter uses copyrighted text without permission.'},
        )
        report = ContentReport.objects.get(reporter=self.other_user)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(report.book, self.book)
        self.assertEqual(report.chapter, self.chapter)
        self.assertEqual(report.reported_user, self.user)

    @patch('books.views.AdminNotificationManager.notify_pending_approval')
    def test_book_submission_enters_moderation_before_publication(self, notify_admin):
        self.book.rights_confirmed = True
        self.book.save(update_fields=['rights_confirmed'])
        self.chapter.content = '<p>A complete opening chapter.</p>'
        self.chapter.word_count = 4
        self.chapter.save(update_fields=['content', 'word_count'])
        self.client.force_login(self.user)
        response = self.client.post(reverse('writer_submit_book', args=[self.book.pk]), {'rules_confirmed': 'on'})
        self.assertRedirects(response, reverse('writer_dashboard'))
        self.assertEqual(BookApprovalStatus.objects.get(book=self.book).status, BookApprovalStatus.PENDING)
        self.assertEqual(Book.objects.get(pk=self.book.pk).status, Book.DRAFT)

    def test_suspended_writer_cannot_submit_for_review(self):
        UserSuspension.objects.create(
            user=self.user,
            suspended_by=self.admin,
            suspension_type=UserSuspension.TEMPORARY,
            reason=UserSuspension.OTHER,
            description='Publishing privileges suspended for a test.',
        )
        self.client.force_login(self.user)
        self.client.post(reverse('writer_submit_book', args=[self.book.pk]), {'rules_confirmed': 'on'})
        self.assertFalse(BookApprovalStatus.objects.filter(book=self.book).exists())

    @patch('books.views.AdminNotificationManager.notify_pending_approval')
    def test_unpublished_approved_book_can_reenter_review(self, notify_admin):
        self.book.rights_confirmed = True
        self.book.save(update_fields=['rights_confirmed'])
        self.chapter.word_count = 2
        self.chapter.save(update_fields=['word_count'])
        BookApprovalStatus.objects.create(book=self.book, status=BookApprovalStatus.APPROVED)
        self.client.force_login(self.user)
        self.client.post(reverse('writer_submit_book', args=[self.book.pk]), {'rules_confirmed': 'on'})
        self.assertEqual(BookApprovalStatus.objects.get(book=self.book).status, BookApprovalStatus.PENDING)
        notify_admin.assert_called_once_with()

    def test_archived_book_can_be_restored(self):
        self.book.status = Book.ARCHIVED
        self.book.save(update_fields=['status'])
        self.client.force_login(self.user)
        response = self.client.post(reverse('writer_book_action', args=[self.book.pk, 'restore']))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Book.objects.get(pk=self.book.pk).status, Book.DRAFT)


class LiteraryPlatformTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='platform-writer', password='testpass123')
        self.staff = get_user_model().objects.create_user(username='platform-admin', password='testpass123', is_staff=True)
        self.author = Author.objects.create(name='Platform Author')
        self.book = Book.objects.create(
            title='Platform Story', slug='platform-story', owner=self.user,
            author=self.author, summary='A platform story.', status=Book.PUBLISHED,
        )
        self.competition = Competition.objects.create(
            title='AfriNovel Open Call', slug='afrinovel-open-call', description='Submit your best story.',
            rules='Original work only.', opens_at=timezone.now() - timezone.timedelta(days=1),
            closes_at=timezone.now() + timezone.timedelta(days=7), status=Competition.OPEN, created_by=self.staff,
        )

    def test_public_literary_pages_render(self):
        for route_name in ('promotions_page', 'competitions_page', 'writers_awards_page', 'critics_page'):
            with self.subTest(route_name=route_name):
                self.assertEqual(self.client.get(reverse(route_name)).status_code, 200)

    def test_critic_application_is_owned_by_authenticated_user(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('critic_apply'), {
            'experience': 'I have reviewed African speculative fiction for years.',
            'genres_of_interest': 'Fantasy, literary fiction',
            'writing_sample': 'This is a considered sample review with enough detail.',
            'preferred_categories': 'Best African Story',
        })
        self.assertRedirects(response, reverse('critics_page'))
        self.assertTrue(CriticApplication.objects.filter(user=self.user, status=CriticApplication.PENDING).exists())

    def test_competition_entry_rejects_books_not_owned_by_writer(self):
        other_user = get_user_model().objects.create_user(username='other-platform-writer', password='testpass123')
        self.client.force_login(other_user)
        response = self.client.post(reverse('competition_enter', args=[self.competition.slug]), {'book': self.book.pk, 'statement': 'My entry.'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CompetitionEntry.objects.filter(writer=other_user).exists())

    def test_admin_can_configure_award_categories_and_nominees(self):
        award = Award.objects.create(title='Writers Award', year=2026, is_published=True, created_by=self.staff)
        category = AwardCategory.objects.create(award=award, name='Best New Writer')
        nominee = AwardNominee.objects.create(category=category, book=self.book, author=self.user, is_winner=True)
        self.assertEqual(award.categories.get(), category)
        self.assertTrue(nominee.is_winner)
