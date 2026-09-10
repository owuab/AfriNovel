#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookclub.settings')
django.setup()

from django.contrib.auth import get_user_model
from books.admin_models import AdminRole

User = get_user_model()

# Create or get superuser
user, created = User.objects.get_or_create(
    username='admin',
    defaults={
        'email': 'admin@bookclub.local',
        'is_staff': True,
        'is_superuser': True
    }
)

# Ensure user has correct permissions
if not user.is_staff or not user.is_superuser:
    user.is_staff = True
    user.is_superuser = True
    user.set_password('admin123')
    user.save()
    print(f"✅ Admin user updated with staff and superuser permissions")
elif created:
    user.set_password('admin123')
    user.save()
    print(f"✅ Admin user created: {user.username}")
else:
    print(f"ℹ️ Admin user already exists: {user.username}")

# Create admin role if not exists
admin_role, role_created = AdminRole.objects.get_or_create(
    user=user,
    defaults={
        'role': AdminRole.SUPER_ADMIN,
        'assigned_by': user
    }
)

if role_created:
    print(f"✅ Super Admin role assigned")
else:
    print(f"ℹ️ Admin role already exists")

print(f"User: {user.username}, Staff: {user.is_staff}, Superuser: {user.is_superuser}")
print(f"✅ Admin setup complete! Username: admin, Password: admin123")
