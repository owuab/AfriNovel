# Admin Dashboard Configuration & Documentation

## Overview

This comprehensive admin dashboard system provides complete administrative functionality for TheBookClub platform, including user management, content approval, content moderation, and system monitoring.

## Admin Role Hierarchy

### 1. **Super Admin** 👑
- **Full system access and control**
- Can manage all admins and their roles
- Can override any decision
- Access to all analytics and audit logs
- Permission to assign/revoke admin roles
- Can manually approve/reject any content
- Can permanently suspend/ban users
- View all audit trails

### 2. **Admin** 👔
- **Primary administrative role**
- Manage users (edit profiles, suspend, ban)
- Approve and reject published books
- Moderate content reports
- View detailed analytics
- Cannot assign admin roles
- Cannot override super admin decisions
- Access to audit logs related to their actions

### 3. **Moderator** 👮
- **Content moderation focused**
- Review and resolve content reports
- Manage user suspensions
- Cannot approve/reject books
- Cannot edit user accounts
- Limited analytics access
- Cannot manage other admins

### 4. **Content Manager** 📚
- **Book approval specialist**
- Review and approve/reject books
- Provide feedback to authors
- Request book revisions
- Cannot suspend users
- Cannot manage other content
- View book statistics only

### 5. **Analytics** 📊
- **View-only dashboard access**
- Cannot perform any moderation actions
- Can only view statistics and reports
- Read-only access to audit logs

## Models

### AdminRole
Manages admin user roles and permissions.

```python
from books.admin_models import AdminRole

# Create an admin role
admin = AdminRole.objects.create(
    user=user_object,
    role=AdminRole.ADMIN,
    assigned_by=current_admin,
    notes="Primary admin for content moderation"
)
```

### UserSuspension
Tracks user suspensions and bans.

```python
from books.admin_models import UserSuspension

# Suspend a user
suspension = UserSuspension.objects.create(
    user=user_to_suspend,
    suspended_by=admin_user,
    suspension_type=UserSuspension.TEMPORARY,
    reason=UserSuspension.HARASSMENT,
    description="User was harassing other members"
)

# Unsuspend a user
suspension.unsuspend(admin_user, "Appeal approved")
```

### BookApprovalStatus
Manages the book publication approval workflow.

```python
from books.admin_models import BookApprovalStatus

# Get pending approvals
pending = BookApprovalStatus.objects.filter(status='pending')

# Approve a book
approval = BookApprovalStatus.objects.get(book=book_obj)
approval.approve(admin_user, "Looks great!")

# Reject a book
approval.reject(admin_user, "Needs revision: Fix grammar issues")

# Request revision
approval.request_revision(admin_user, "Please update cover image", deadline_days=7)
```

### ContentReport
Reports inappropriate content for moderation.

```python
from books.admin_models import ContentReport

# Create a report
report = ContentReport.objects.create(
    reporter=user_reporting,
    report_type=ContentReport.HARASSMENT,
    description="User posted harassing comments",
    content_type='post_comment',
    object_id=comment_id,
    reported_user=offending_user
)

# Resolve a report
report.status = ContentReport.RESOLVED
report.reviewed_by = admin_user
report.reviewed_at = timezone.now()
report.action_taken = 'user_suspended'
report.resolution = "User suspended for 48 hours"
report.save()
```

### AdminAuditLog
Logs all admin actions for audit trails and compliance.

```python
from books.admin_models import AdminAuditLog

# Log an action
AdminAuditLog.log_action(
    admin_user=admin,
    action=AdminAuditLog.USER_SUSPENDED,
    description="Suspended user for harassment",
    target_user=suspended_user,
    ip_address="192.168.1.1",
    changes={'reason': 'harassment', 'type': 'temporary'}
)

# Query logs
logs = AdminAuditLog.objects.filter(
    admin_user=admin_user,
    action=AdminAuditLog.USER_SUSPENDED
).order_by('-created_at')
```

### NotificationPreference
Manages admin notification preferences.

```python
from books.admin_models import NotificationPreference

# Set notification preferences
prefs, created = NotificationPreference.objects.get_or_create(user=admin_user)
prefs.new_reports = True
prefs.pending_approvals = True
prefs.email_digest = 'daily'
prefs.save()
```

## Admin Views & URLs

### Dashboard
- **URL**: `/admin/dashboard/`
- **View**: `admin_dashboard`
- **Access**: Staff members with admin role
- **Features**: Statistics, pending items, recent activity

### User Management
- **URL**: `/admin/users/`
- **View**: `UserListView`
- **Access**: Admin, Super Admin
- **Features**: Search, filter, view details, suspend/unsuspend

### Book Approvals
- **URL**: `/admin/books/pending/`
- **View**: `PendingBooksView`
- **Access**: Content Manager, Admin, Super Admin
- **Features**: Review, approve, reject, request revisions

### Content Reports
- **URL**: `/admin/reports/`
- **View**: `ContentReportsView`
- **Access**: Moderator, Admin, Super Admin
- **Features**: Review, resolve, dismiss, take action

### Admin Roles
- **URL**: `/admin/roles/`
- **View**: `AdminRoleListView`
- **Access**: Super Admin only
- **Features**: Assign roles, manage permissions

## Utilities

### AdminNotificationManager
Handles admin notifications and alerts.

```python
from books.admin_utilities import AdminNotificationManager

# Send notification
AdminNotificationManager.send_notification(
    admin_user=admin,
    notification_type='new_reports',
    subject='New Content Report',
    message='A new report requires review'
)

# Notify about new report
AdminNotificationManager.notify_new_report(report_object)
```

### AdminAnalyticsManager
Generates analytics and reports.

```python
from books.admin_utilities import AdminAnalyticsManager

# Get dashboard analytics
analytics = AdminAnalyticsManager.get_dashboard_analytics(days=30)

# Get moderation report
mod_report = AdminAnalyticsManager.get_moderation_report(days=7)

# Get user analytics
user_stats = AdminAnalyticsManager.get_user_analytics(user_id)
```

### AdminPermissionManager
Manages admin permissions.

```python
from books.admin_utilities import AdminPermissionManager

# Check permission
can_approve = AdminPermissionManager.check_permission(admin_user, 'approve_books')

# Get role permissions
perms = AdminPermissionManager.get_role_permissions(AdminRole.ADMIN)
```

### SuspensionManager
Manages user suspensions.

```python
from books.admin_utilities import SuspensionManager

# Check if suspended
is_suspended = SuspensionManager.is_user_suspended(user)

# Get suspension reason
reason = SuspensionManager.get_suspension_reason(user)

# Check appeal eligibility
can_appeal = SuspensionManager.can_appeal_suspension(user)
```

### BookApprovalManager
Manages book approvals.

```python
from books.admin_utilities import BookApprovalManager

# Get pending approvals
pending = BookApprovalManager.get_pending_approvals()

# Get approval stats
stats = BookApprovalManager.get_approval_stats()

# Auto-approve expired reviews
count = BookApprovalManager.auto_approve_review_deadline_books()
```

### AuditLogManager
Manages audit logs.

```python
from books.admin_utilities import AuditLogManager

# Log action
AuditLogManager.log_admin_action(
    admin_user=admin,
    action=AdminAuditLog.USER_SUSPENDED,
    description="User suspended for violation",
    target_user=user
)

# Get user audit history
history = AuditLogManager.get_user_audit_history(user, days=90)
```

## Database Migration

To integrate these models into your project:

1. **Create migration**:
```bash
python manage.py makemigrations
```

2. **Run migration**:
```bash
python manage.py migrate
```

3. **Create initial admin**:
```python
from books.admin_models import AdminRole
from django.contrib.auth import get_user_model

User = get_user_model()
admin_user = User.objects.get(username='your_admin')
AdminRole.objects.create(
    user=admin_user,
    role=AdminRole.SUPER_ADMIN,
    assigned_by=admin_user
)
```

## Settings Configuration

Add to `settings.py`:

```python
# Admin settings
ADMIN_NOTIFICATION_ENABLED = True
ADMIN_AUDIT_LOG_ENABLED = True
ADMIN_EMAIL_FROM = 'noreply@bookclub.local'

# Suspension settings
SUSPENSION_AUTO_UNSUSPEND_DAYS = 30  # Auto-unsuspend temporary suspensions after 30 days

# Book approval settings
BOOK_APPROVAL_REVIEW_DEADLINE_DAYS = 14  # Auto-approve if not reviewed within 14 days
```

## Security Best Practices

1. **Minimal Permissions**: Assign only necessary permissions to each admin
2. **Audit Trails**: Review audit logs regularly for suspicious activity
3. **Role Rotation**: Rotate admin roles every 6 months
4. **IP Whitelisting**: Restrict admin access to specific IP ranges
5. **Two-Factor Authentication**: Require 2FA for admin accounts
6. **Suspension Appeals**: Implement appeals process for permanent bans
7. **Regular Backups**: Backup admin actions and audit logs
8. **Activity Monitoring**: Monitor unusual admin activity patterns

## Common Tasks

### Suspend a User
```python
from books.admin_models import UserSuspension
from books.admin_utilities import AuditLogManager

suspension = UserSuspension.objects.create(
    user=user_to_suspend,
    suspended_by=admin_user,
    suspension_type='temporary',
    reason='spam',
    description='Posting spam messages'
)
user_to_suspend.is_active = False
user_to_suspend.save()

AuditLogManager.log_admin_action(
    admin_user=admin_user,
    action=AdminAuditLog.USER_SUSPENDED,
    description=f'Suspended {user_to_suspend.username}',
    target_user=user_to_suspend
)
```

### Approve a Book
```python
from books.admin_models import BookApprovalStatus
from books.admin_utilities import AuditLogManager

approval = BookApprovalStatus.objects.get(book=book_obj)
approval.approve(admin_user, "Great work! Published successfully.")

AuditLogManager.log_admin_action(
    admin_user=admin_user,
    action=AdminAuditLog.BOOK_APPROVED,
    description=f'Approved book: {book_obj.title}'
)
```

### Resolve a Content Report
```python
from books.admin_models import ContentReport
from books.admin_utilities import AuditLogManager

report = ContentReport.objects.get(id=report_id)
report.status = ContentReport.RESOLVED
report.reviewed_by = admin_user
report.reviewed_at = timezone.now()
report.action_taken = 'user_suspended'
report.resolution = 'User suspended for 48 hours due to harassment'
report.save()

AuditLogManager.log_admin_action(
    admin_user=admin_user,
    action=AdminAuditLog.REPORT_REVIEWED,
    description=f'Resolved report #{report.id}',
    target_user=report.reported_user
)
```

## Testing

Run admin tests:
```bash
python manage.py test books.tests.AdminTests
```

## Support

For issues or questions regarding the admin dashboard:
1. Check audit logs for error details
2. Review error logs in `logs/admin.log`
3. Contact the development team

---

**Last Updated**: 2024
**Version**: 1.0
