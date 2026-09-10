#!/usr/bin/env python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookclub.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

# Create a test client
client = Client()

# Get the admin user
admin_user = User.objects.get(username='admin')

# Force login using the client
client.force_login(admin_user)

# Test the admin dashboard URL
response = client.get('/admin-panel/dashboard/', HTTP_HOST='localhost:8000')

print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    print("✅ Admin dashboard is accessible!")
    print(f"Content length: {len(response.content)} bytes")
else:
    print(f"❌ Error accessing dashboard: {response.status_code}")
    if 'Redirect' in str(response):
        print(f"Redirected to: {response.url}")
