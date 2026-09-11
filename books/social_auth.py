"""Allauth adapters and forms for secure AfriNovel social authentication."""

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme

from .models import AuthenticationEvent


class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    """Keeps existing username logins while accepting a unique account email."""

    username = AuthenticationForm.base_fields['username']
    username.label = 'Email or username'
    username.widget.attrs.update({'autocomplete': 'username', 'placeholder': 'you@example.com or username'})

    def clean(self):
        identifier = self.cleaned_data.get('username', '').strip()
        user_model = get_user_model()
        if '@' in identifier:
            matched_user = user_model.objects.filter(email__iexact=identifier).first()
            if matched_user:
                self.cleaned_data['username'] = matched_user.get_username()
        return super().clean()


class BookClubRegistrationForm(UserCreationForm):
    """Default User registration with email and profile names, without replacing User."""

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ('first_name', 'last_name', 'username', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise ValidationError('An account already uses this email address. Sign in to connect a provider instead.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name'].strip()
        user.last_name = self.cleaned_data['last_name'].strip()
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class BookClubAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        next_url = request.POST.get('next') or request.GET.get('next')
        if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}, request.is_secure()):
            return next_url
        if request.user.is_staff:
            return '/admin-panel/dashboard/'
        return '/home/'

    def send_password_reset_mail(self, email, user, context):
        from django.conf import settings
        context['site_url'] = settings.SITE_URL
        return super().send_password_reset_mail(email, user, context)


class BookClubSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Do not silently link by email; users must explicitly connect while signed in."""

    def pre_social_login(self, request, sociallogin):
        if sociallogin.is_existing:
            return
        email = (sociallogin.user.email or sociallogin.account.extra_data.get('email') or '').strip().lower()
        if email and get_user_model().objects.filter(email__iexact=email).exists() and not request.user.is_authenticated:
            provider_name = sociallogin.account.provider.title()
            messages.info(request, f'This email already belongs to an AfriNovel account. Sign in, then connect {provider_name} from Connected Accounts.')
            raise ImmediateHttpResponse(redirect('/login/?next=/settings/connected-accounts/'))

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        data = sociallogin.account.extra_data
        if not user.first_name:
            user.first_name = data.get('given_name', '') or data.get('first_name', '')
        if not user.last_name:
            user.last_name = data.get('family_name', '') or data.get('last_name', '')
        if not user.email:
            user.email = data.get('email', '')
        user.save(update_fields=['first_name', 'last_name', 'email'])
        AuthenticationEvent.objects.create(user=user, event_type=AuthenticationEvent.SOCIAL_LOGIN, provider=sociallogin.account.provider)
        return user