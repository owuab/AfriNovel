"""
Admin utility functions for notifications, analytics, and reporting
"""
from functools import wraps
from django.db.models import Count, Q
from django.core.mail import send_mail
from django.http import HttpResponseForbidden
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta

from .models import (
    Book, Review, SocialPost, Permission, RolePermission, ContentReport,
)
from .admin_models import (
    AdminAuditLog, AdminRole, UserSuspension, BookApprovalStatus,
    NotificationPreference
)


class AdminNotificationManager:
    """Manage admin notifications and alerts"""
    
    @staticmethod
    def send_notification(admin_user, notification_type, subject, message, context=None):
        """Send notification to admin user"""
        prefs = NotificationPreference.objects.get_or_create(user=admin_user)[0]
        
        # Check if notifications are enabled
        if not getattr(prefs, notification_type, False):
            return False
        
        # Send email unless the admin disabled email notifications.
        if prefs.email_digest != 'never':
            AdminNotificationManager.send_email_notification(
                admin_user, subject, message, context
            )
        
        return True
    
    @staticmethod
    def send_email_notification(user, subject, template_name, context=None):
        """Send email notification to admin"""
        if context is None:
            context = {}
        
        context['admin_name'] = user.first_name or user.username
        
        html_message = None
        if template_name:
            html_message = render_to_string(f'admin/emails/{template_name}.html', context)
        
        send_mail(
            subject,
            message=template_name or subject,
            from_email='noreply@bookclub.local',
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=True,
        )
    
    @staticmethod
    def notify_new_report(report):
        """Notify admins of new content report"""
        admins = AdminAuditLog.objects.filter(
            action=AdminAuditLog.REPORT_REVIEWED
        ).values_list('admin_user', flat=True).distinct()[:5]
        
        for admin_user in admins:
            try:
                AdminNotificationManager.send_notification(
                    admin_user=admin_user,
                    notification_type='new_reports',
                    subject='New Content Report',
                    message='',
                    context={
                        'report': report,
                    }
                )
            except Exception:
                pass
    
    @staticmethod
    def notify_pending_approval():
        """Notify content managers of pending approvals"""
        pending_count = BookApprovalStatus.objects.filter(
            status='pending'
        ).count()
        
        if pending_count > 0:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            managers = User.objects.filter(
                is_staff=True,
            ).filter(
                Q(is_superuser=True) |
                Q(admin_role__role__in=[
                    AdminRole.SUPER_ADMIN,
                    AdminRole.ADMIN,
                    AdminRole.CONTENT_MANAGER,
                ])
            ).distinct()
            
            for manager in managers:
                try:
                    AdminNotificationManager.send_notification(
                        admin_user=manager,
                        notification_type='pending_approvals',
                        subject=f'{pending_count} Books Awaiting Approval',
                        message='',
                        context={
                            'count': pending_count,
                        }
                    )
                except Exception:
                    pass


class AdminAnalyticsManager:
    """Generate admin analytics and reports"""
    
    @staticmethod
    def get_dashboard_analytics(days=30):
        """Get comprehensive dashboard analytics"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        start_date = timezone.now() - timedelta(days=days)
        
        return {
            'users': {
                'total': User.objects.count(),
                'new': User.objects.filter(date_joined__gte=start_date).count(),
                'active': User.objects.filter(is_active=True).count(),
                'suspended': UserSuspension.objects.filter(
                    suspended_at__gte=start_date,
                    is_active=True
                ).count(),
            },
            'books': {
                'total': Book.objects.count(),
                'published': Book.objects.filter(status='published').count(),
                'pending_approval': BookApprovalStatus.objects.filter(
                    status='pending'
                ).count(),
                'approved': BookApprovalStatus.objects.filter(
                    status='approved',
                    reviewed_at__gte=start_date
                ).count(),
                'rejected': BookApprovalStatus.objects.filter(
                    status='rejected',
                    reviewed_at__gte=start_date
                ).count(),
            },
            'reports': {
                'total': ContentReport.objects.count(),
                'pending': ContentReport.objects.filter(status='pending').count(),
                'resolved': ContentReport.objects.filter(
                    status='resolved',
                    reviewed_at__gte=start_date
                ).count(),
                'by_type': dict(
                    ContentReport.objects.filter(
                        reported_at__gte=start_date
                    ).values('report_type').annotate(count=Count('id')).values_list('report_type', 'count')
                ),
            },
            'audit': {
                'total_actions': AdminAuditLog.objects.filter(
                    created_at__gte=start_date
                ).count(),
                'by_action': dict(
                    AdminAuditLog.objects.filter(
                        created_at__gte=start_date
                    ).values('action').annotate(count=Count('id')).values_list('action', 'count')
                ),
            },
        }
    
    @staticmethod
    def get_user_analytics(user_id, days=30):
        """Get detailed analytics for a specific user"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.get(id=user_id)
        start_date = timezone.now() - timedelta(days=days)
        
        return {
            'user': user,
            'activity': {
                'reviews_created': Review.objects.filter(
                    user=user,
                    created_at__gte=start_date
                ).count(),
                'posts_created': SocialPost.objects.filter(
                    author=user,
                    created_at__gte=start_date
                ).count(),
                'books_published': Book.objects.filter(
                    created_at__gte=start_date
                ).count(),
            },
            'suspensions': UserSuspension.objects.filter(user=user),
            'audit_logs': AdminAuditLog.objects.filter(
                target_user=user,
                created_at__gte=start_date
            ),
        }
    
    @staticmethod
    def get_moderation_report(days=30):
        """Get comprehensive moderation report"""
        start_date = timezone.now() - timedelta(days=days)
        
        reports = ContentReport.objects.filter(
            reported_at__gte=start_date
        )
        
        return {
            'period': f'Last {days} days',
            'total_reports': reports.count(),
            'by_type': dict(
                reports.values('report_type').annotate(count=Count('id')).values_list('report_type', 'count')
            ),
            'by_status': dict(
                reports.values('status').annotate(count=Count('id')).values_list('status', 'count')
            ),
            'by_content_type': dict(
                reports.values('content_type').annotate(count=Count('id')).values_list('content_type', 'count')
            ),
            'most_reported_users': reports.values('reported_user').annotate(
                count=Count('id')
            ).order_by('-count')[:10],
            'most_active_reporters': reports.values('reporter').annotate(
                count=Count('id')
            ).order_by('-count')[:10],
            'resolution_time_avg': AdminAuditLog.objects.filter(
                action=AdminAuditLog.REPORT_REVIEWED,
                created_at__gte=start_date
            ).count(),
        }


class PermissionService:
    """Resolve custom permission names assigned to admin roles."""

    @staticmethod
    def _normalize_permission_name(permission_name):
        if not permission_name:
            return ''
        return permission_name.strip()

    @staticmethod
    def user_permissions(user):
        is_authenticated = getattr(user, 'is_authenticated', False)
        if not user or (callable(is_authenticated) and not is_authenticated()) or (not callable(is_authenticated) and not is_authenticated):
            return set()

        permissions = set()
        if getattr(user, 'is_superuser', False):
            return set(Permission.objects.values_list('name', flat=True))

        admin_role = getattr(user, 'admin_role', None)
        if admin_role:
            permission_names = RolePermission.objects.filter(
                role_name=admin_role.role,
                revoked_at__isnull=True,
            ).values_list('permission__name', flat=True)
            permissions.update(permission_names)

        return permissions

    @staticmethod
    def has_permission(user, permission_name):
        normalized = PermissionService._normalize_permission_name(permission_name)
        if not normalized:
            return False

        is_authenticated = getattr(user, 'is_authenticated', False)
        if not user or (callable(is_authenticated) and not is_authenticated()) or (not callable(is_authenticated) and not is_authenticated):
            return False

        if getattr(user, 'is_superuser', False):
            return True

        user_perms = PermissionService.user_permissions(user)
        if '*' in user_perms:
            return True

        if normalized in user_perms:
            return True

        module_name = normalized.split(':', 1)[0]
        module_wildcard = f'{module_name}:*'
        return module_wildcard in user_perms

    @staticmethod
    def require_permission(permission_name):
        def decorator(view_func):
            @wraps(view_func)
            def wrapped_view(request, *args, **kwargs):
                if not PermissionService.has_permission(request.user, permission_name):
                    return HttpResponseForbidden('You do not have permission to perform this action.')
                return view_func(request, *args, **kwargs)
            return wrapped_view
        return decorator


class AdminPermissionManager:
    """Manage admin permissions and roles"""
    
    @staticmethod
    def get_role_permissions(role):
        """Get all permissions for a specific role."""
        from .admin_models import AdminRole

        role_permissions = {
            AdminRole.SUPER_ADMIN: ['*'],
            AdminRole.ADMIN: ['users:*', 'roles:*', 'reports:*', 'books:*', 'audit:*', 'admin:*'],
            AdminRole.MODERATOR: ['users:read', 'users:suspend', 'reports:read', 'reports:resolve', 'books:read', 'books:approve', 'books:reject', 'audit:read'],
            AdminRole.CONTENT_MANAGER: ['books:read', 'books:approve', 'books:reject', 'books:revision', 'reports:read'],
            AdminRole.ANALYTICS: ['analytics:read', 'dashboard:read', 'reports:read'],
        }
        return role_permissions.get(role, [])

    @staticmethod
    def check_permission(admin_user, permission):
        """Check if admin user has specific permission."""
        if not admin_user.is_staff:
            return False

        if admin_user.is_superuser:
            return True

        admin_role = getattr(admin_user, 'admin_role', None)
        if not admin_role:
            return False

        permissions = AdminPermissionManager.get_role_permissions(admin_role.role)
        if '*' in permissions:
            return True
        if permission in permissions:
            return True

        module_name = permission.split(':', 1)[0]
        return f'{module_name}:*' in permissions


class SuspensionManager:
    """Manage user suspensions and bans"""
    
    @staticmethod
    def get_active_suspensions():
        """Get all active user suspensions"""
        return UserSuspension.objects.filter(
            is_active=True,
            unsuspended_at__isnull=True
        ).select_related('user', 'suspended_by')
    
    @staticmethod
    def is_user_suspended(user):
        """Check if user is currently suspended"""
        return UserSuspension.objects.filter(
            user=user,
            is_active=True,
            unsuspended_at__isnull=True
        ).exists()
    
    @staticmethod
    def get_suspension_reason(user):
        """Get the reason for user suspension"""
        suspension = UserSuspension.objects.filter(
            user=user,
            is_active=True,
            unsuspended_at__isnull=True
        ).first()
        
        if suspension:
            return {
                'type': suspension.get_suspension_type_display(),
                'reason': suspension.get_reason_display(),
                'description': suspension.description,
                'suspended_at': suspension.suspended_at,
            }
        
        return None
    
    @staticmethod
    def can_appeal_suspension(user):
        """Check if user can appeal their suspension"""
        suspension = UserSuspension.objects.filter(
            user=user,
            is_active=True
        ).first()
        
        if not suspension:
            return False
        
        # Can only appeal temporary suspensions after 24 hours
        if suspension.suspension_type == 'permanent':
            return False
        
        appeal_eligible_date = suspension.suspended_at + timedelta(hours=24)
        return timezone.now() >= appeal_eligible_date


class BookApprovalManager:
    """Manage book approval workflow"""
    
    @staticmethod
    def get_pending_approvals():
        """Get all pending book approvals"""
        return BookApprovalStatus.objects.filter(
            status__in=['pending', 'revision_needed']
        ).select_related('book', 'book__author').order_by('-submitted_at')
    
    @staticmethod
    def get_approval_stats():
        """Get book approval statistics"""
        return {
            'pending': BookApprovalStatus.objects.filter(status='pending').count(),
            'approved': BookApprovalStatus.objects.filter(status='approved').count(),
            'rejected': BookApprovalStatus.objects.filter(status='rejected').count(),
            'revision_needed': BookApprovalStatus.objects.filter(status='revision_needed').count(),
        }
    
    @staticmethod
    def auto_approve_review_deadline_books():
        """Auto-approve books if reviewer doesn't respond within deadline"""
        deadline_passed = BookApprovalStatus.objects.filter(
            status='pending',
            submitted_at__lt=timezone.now() - timedelta(days=14)
        )
        
        count = 0
        for approval in deadline_passed:
            approval.status = 'approved'
            approval.reviewed_by = None
            approval.reviewed_at = timezone.now()
            approval.feedback = 'Auto-approved due to review deadline'
            approval.save()
            count += 1
        
        return count


class AuditLogManager:
    """Manage admin audit logs"""
    
    @staticmethod
    def log_admin_action(admin_user, action, description, target_user=None, ip_address=None, changes=None):
        """Create audit log entry"""
        return AdminAuditLog.log_action(
            admin_user=admin_user,
            action=action,
            description=description,
            target_user=target_user,
            ip_address=ip_address,
            changes=changes
        )
    
    @staticmethod
    def get_user_audit_history(user, days=90):
        """Get audit history for a specific user"""
        start_date = timezone.now() - timedelta(days=days)
        
        return AdminAuditLog.objects.filter(
            Q(admin_user=user) | Q(target_user=user),
            created_at__gte=start_date
        ).order_by('-created_at')
    
    @staticmethod
    def export_audit_log(start_date, end_date):
        """Export audit logs for a date range"""
        return AdminAuditLog.objects.filter(
            created_at__range=[start_date, end_date]
        ).order_by('-created_at')
