#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookclub.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from books.admin_models import AdminRole

User = get_user_model()

admin_username = os.getenv('ADMIN_USERNAME', 'admin')
admin_email = os.getenv('ADMIN_EMAIL', 'admin@bookclub.local')
admin_password = os.getenv('ADMIN_PASSWORD')
if not admin_password:
    raise SystemExit('Set ADMIN_PASSWORD to a strong password before running this script.')

try:
    validate_password(admin_password)
except ValidationError as error:
    raise SystemExit(f'ADMIN_PASSWORD does not meet the password policy: {"; ".join(error.messages)}') from error

user, created = User.objects.get_or_create(
    username=admin_username,
    defaults={
        'email': admin_email,
        'is_staff': True,
        'is_superuser': True,
    }
)

if user.email != admin_email:
    user.email = admin_email

if not user.is_staff or not user.is_superuser:
    user.is_staff = True
    user.is_superuser = True

user.set_password(admin_password)
user.save()

if created:
    print(f"✅ Admin user created: {user.username}")
else:
    print(f"ℹ️ Admin user already exists: {user.username} (credentials synced)")

admin_role, role_created = AdminRole.objects.get_or_create(
    user=user,
    defaults={
        'role': AdminRole.SUPER_ADMIN,
        'assigned_by': user,
    }
)

if role_created:
    print(f"✅ Super Admin role assigned")
else:
    print(f"ℹ️ Admin role already exists")

print(f"User: {user.username}, Email: {user.email}, Staff: {user.is_staff}, Superuser: {user.is_superuser}")
print(f"✅ Admin setup complete! Username: {admin_username}")
