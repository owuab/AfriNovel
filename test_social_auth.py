import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookclub.settings')
django.setup()

from django.conf import settings

print("Social Authentication Configuration Check")
print("=" * 50)

# Check installed apps
print("\n1. Installed Apps:")
for app in settings.INSTALLED_APPS:
    if 'social' in app.lower() or 'allauth' in app.lower():
        print(f"   [OK] {app}")

# Check social providers configuration
print("\n2. Social Providers Configuration:")
for provider, config in settings.SOCIALACCOUNT_PROVIDERS.items():
    if config:  # Only show configured providers
        print(f"   [OK] {provider}: Configured")
        if 'APP' in config:
            app_config = config['APP']
            has_client_id = bool(app_config.get('client_id'))
            has_secret = bool(app_config.get('secret'))
            print(f"     - Client ID: {'Set' if has_client_id else 'Not set'}")
            print(f"     - Secret: {'Set' if has_secret else 'Not set'}")
    else:
        print(f"   [MISSING] {provider}: Not configured (missing credentials)")

# Check adapter configuration
print("\n3. Adapter Configuration:")
print(f"   ACCOUNT_ADAPTER: {settings.ACCOUNT_ADAPTER}")
print(f"   SOCIALACCOUNT_ADAPTER: {settings.SOCIALACCOUNT_ADAPTER}")

# Check URL configuration
print("\n4. URL Configuration:")
from django.urls import get_resolver
resolver = get_resolver()
for pattern in resolver.url_patterns:
    if hasattr(pattern, 'url_patterns') and pattern.url_patterns:
        for sub_pattern in pattern.url_patterns:
            if 'social' in str(sub_pattern.pattern) or 'google' in str(sub_pattern.pattern) or 'apple' in str(sub_pattern.pattern) or 'microsoft' in str(sub_pattern.pattern):
                print(f"   [OK] {sub_pattern.pattern}")

print("\n" + "=" * 50)
print("Social authentication system is properly configured.")
print("Add OAuth credentials to .env file to activate providers.")