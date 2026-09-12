# OAuth Social Authentication Setup Guide

This guide explains how to activate Google, Apple, and Microsoft sign-in/sign-up for AfriNovel.

## Current Status

✅ **Django Configuration**: Social authentication is already configured in `bookclub/settings.py`
✅ **Template Integration**: Social login buttons are already integrated in login/signup pages
✅ **Custom Adapters**: BookClubSocialAccountAdapter is configured for secure authentication
⚠️ **OAuth Credentials**: Need to be configured in `.env` file

## Required Actions

### 1. Configure OAuth Credentials

You need to obtain OAuth credentials from each provider and add them to your `.env` file:

#### Google OAuth 2.0
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new project or select existing one
3. Enable Google+ API
4. Create OAuth 2.0 Client ID (Web application)
5. Add authorized redirect URI: `http://127.0.0.1:8000/accounts/google/login/callback/`
6. Copy Client ID and Client Secret to `.env`:
   ```
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   ```

#### Microsoft Identity Platform
1. Go to [Azure Portal](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
2. Register a new application
3. Set Redirect URI: `http://127.0.0.1:8000/accounts/microsoft/login/callback/`
4. Copy Application (client) ID and Client secret to `.env`:
   ```
   MICROSOFT_CLIENT_ID=your_microsoft_client_id
   MICROSOFT_CLIENT_SECRET=your_microsoft_client_secret
   MICROSOFT_TENANT=common
   ```

#### Sign in with Apple
1. Go to [Apple Developer](https://developer.apple.com/account/resources/identifiers/list)
2. Create a new App ID with "Sign in with Apple" capability
3. Create a Service ID for web authentication
4. Generate and download Apple client secret JWT
5. Add redirect URL: `http://127.0.0.1:8000/accounts/apple/login/callback/`
6. Copy credentials to `.env`:
   ```
   APPLE_CLIENT_ID=your_apple_client_id
   APPLE_CLIENT_SECRET=your_apple_client_secret_jwt
   APPLE_TEAM_ID=your_apple_team_id
   APPLE_KEY_ID=your_apple_key_id
   APPLE_PRIVATE_KEY=your_apple_private_key_content
   ```

### 2. Update Redirect URLs for Production

For production deployment, update the redirect URLs in OAuth provider consoles:
- Replace `http://127.0.0.1:8000` with your production domain
- Update `.env` file with production `SITE_URL` and `SOCIAL_AUTH_REDIRECT_BASE_URL`

### 3. Restart the Server

After updating the `.env` file, restart the Django server:
```bash
python manage.py runserver
```

## Testing the Setup

1. Navigate to the login page: `http://127.0.0.1:8000/login/`
2. You should see enabled social login buttons (Google, Apple, Microsoft)
3. Click on any enabled provider to test the OAuth flow
4. Complete the authentication on the provider's page
5. You should be redirected back to AfriNovel and logged in

## Current Configuration Status

The system is configured to:
- ✅ Display social login buttons when credentials are configured
- ✅ Show disabled buttons with helpful messages when credentials are missing
- ✅ Handle OAuth callbacks securely
- ✅ Prevent automatic account linking by email
- ✅ Support user profile data from OAuth providers
- ✅ Handle authentication events for security auditing

## Security Notes

- OAuth credentials are stored in `.env` file (not committed to git)
- The social authentication prevents silent account linking for security
- Authentication events are logged for audit purposes
- Redirect URLs are validated to prevent open redirect attacks

## Troubleshooting

**Social buttons appear disabled**: Check that the corresponding OAuth credentials are set in `.env` file.

**OAuth callback fails**: Verify that the redirect URLs in OAuth provider consoles match your SITE_URL.

**Email configuration**: For password reset functionality, configure email settings in `.env` file.

## File Reference

- **Settings**: `bookclub/settings.py` (SOCIALACCOUNT_PROVIDERS configuration)
- **Adapters**: `books/social_auth.py` (BookClubSocialAccountAdapter)
- **Templates**: `templates/books/login.html` (social login buttons)
- **Context**: `books/views.py` (configured_social_providers function)
- **Environment**: `.env` (OAuth credentials storage)