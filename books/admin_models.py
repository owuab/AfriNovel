"""
Admin-related models for managing users, content approval, and moderation
"""
from django.db import models
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.utils import timezone
from django.db.models import Q


class AdminRole(models.Model):
    """Define custom admin roles and their permissions"""
    SUPER_ADMIN = 'super_admin'
    ADMIN = 'admin'
    MODERATOR = 'moderator'
    CONTENT_MANAGER = 'content_manager'
    ANALYTICS = 'analytics'
    
    ROLE_CHOICES = [
        (SUPER_ADMIN, 'Super Admin - Full system access'),
        (ADMIN, 'Admin - Manage users and content'),
        (MODERATOR, 'Moderator - Review and moderate content'),
        (CONTENT_MANAGER, 'Content Manager - Approve/reject books'),
        (ANALYTICS, 'Analytics - View-only access to reports'),
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='admin_role')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    permissions = models.ManyToManyField(Permission, blank=True, related_name='admin_roles')
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='assigned_admin_roles'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, help_text='Notes about this admin assignment')
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-assigned_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
    
    def has_permission(self, permission_name):
        """Check if admin has a specific permission"""
        if self.role == self.SUPER_ADMIN:
            return True
        return self.permissions.filter(codename=permission_name).exists()


class UserSuspension(models.Model):
    """Track user suspension/ban events"""
    TEMPORARY = 'temporary'
    PERMANENT = 'permanent'
    SUSPENSION_TYPE_CHOICES = [
        (TEMPORARY, 'Temporary Suspension'),
        (PERMANENT, 'Permanent Ban'),
    ]
    
    SPAM = 'spam'
    HARASSMENT = 'harassment'
    INAPPROPRIATE_CONTENT = 'inappropriate_content'
    VIOLATIONS = 'violations'
    FRAUD = 'fraud'
    OTHER = 'other'
    
    REASON_CHOICES = [
        (SPAM, 'Spam'),
        (HARASSMENT, 'Harassment or Bullying'),
        (INAPPROPRIATE_CONTENT, 'Inappropriate Content'),
        (VIOLATIONS, 'Terms of Service Violations'),
        (FRAUD, 'Fraud or Scam'),
        (OTHER, 'Other'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='suspensions')
    suspended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='suspended_users'
    )
    suspension_type = models.CharField(max_length=20, choices=SUSPENSION_TYPE_CHOICES)
    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    description = models.TextField(help_text='Detailed reason for suspension')
    suspended_at = models.DateTimeField(auto_now_add=True)
    unsuspended_at = models.DateTimeField(null=True, blank=True)
    unsuspended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='unsuspended_users'
    )
    unsuspension_reason = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-suspended_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['-suspended_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_suspension_type_display()}"
    
    @property
    def is_currently_suspended(self):
        """Check if user is currently suspended"""
        return self.is_active and self.unsuspended_at is None
    
    def unsuspend(self, admin_user, reason=''):
        """Unsuspend the user"""
        self.is_active = False
        self.unsuspended_at = timezone.now()
        self.unsuspended_by = admin_user
        self.unsuspension_reason = reason
        self.save()
        self.user.is_active = True
        self.user.save()


class BookApprovalStatus(models.Model):
    """Track book publication approval workflow"""
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    REVISION_NEEDED = 'revision_needed'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending Review'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
        (REVISION_NEEDED, 'Needs Revision'),
    ]
    
    book = models.OneToOneField('books.Book', on_delete=models.CASCADE, related_name='approval_status')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_books'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    feedback = models.TextField(blank=True, help_text='Feedback for author')
    rejection_reason = models.TextField(blank=True, help_text='Reason for rejection')
    revision_deadline = models.DateTimeField(null=True, blank=True)
    is_featured_approved = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-submitted_at']
        verbose_name = "Book Approval Status"
        verbose_name_plural = "Book Approval Statuses"
    
    def __str__(self):
        return f"{self.book.title} - {self.get_status_display()}"
    
    def approve(self, admin_user, feedback=''):
        """Approve the book for publication"""
        self.status = self.APPROVED
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.feedback = feedback
        self.book.status = 'published'
        self.book.published_at = timezone.now()
        self.save()
        self.book.save(update_fields=['status', 'published_at', 'updated_at'])
        from .models import Chapter, Notification

        now = timezone.now()
        first_chapter = self.book.chapters.filter(status=Chapter.DRAFT).order_by('chapter_number').first()
        if first_chapter:
            first_chapter.status = Chapter.PUBLISHED
            first_chapter.published_date = now
            first_chapter.save(update_fields=['status', 'published_date', 'updated_at'])
        recipients = set(self.book.author.followers.values_list('follower_id', flat=True))
        if self.book.owner_id:
            recipients.add(self.book.owner_id)
            recipients.update(self.book.owner.follower_users.values_list('follower_id', flat=True))
        recipients.discard(admin_user.pk)
        Notification.objects.bulk_create([
            Notification(
                recipient_id=recipient_id,
                actor=admin_user,
                notification_type=Notification.BOOK_PUBLISHED,
                book=self.book,
                message=f'{self.book.title} is now published.',
            )
            for recipient_id in recipients
        ])
    
    def reject(self, admin_user, reason=''):
        """Reject the book"""
        self.status = self.REJECTED
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.rejection_reason = reason
        self.save()
    
    def request_revision(self, admin_user, feedback='', deadline_days=7):
        """Request revision from author"""
        self.status = self.REVISION_NEEDED
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.feedback = feedback
        self.revision_deadline = timezone.now() + timezone.timedelta(days=deadline_days)
        self.save()



class AdminAuditLog(models.Model):
    """Log all admin actions for audit trail"""
    LOGIN = 'login'
    LOGOUT = 'logout'
    USER_CREATED = 'user_created'
    USER_EDITED = 'user_edited'
    USER_SUSPENDED = 'user_suspended'
    USER_UNSUSPENDED = 'user_unsuspended'
    BOOK_APPROVED = 'book_approved'
    BOOK_REJECTED = 'book_rejected'
    CONTENT_REMOVED = 'content_removed'
    REPORT_REVIEWED = 'report_reviewed'
    ADMIN_ROLE_ASSIGNED = 'admin_role_assigned'
    ADMIN_ROLE_REMOVED = 'admin_role_removed'
    PERMISSION_CHANGED = 'permission_changed'
    SETTING_CHANGED = 'setting_changed'
    
    ACTION_CHOICES = [
        (LOGIN, 'Admin Login'),
        (LOGOUT, 'Admin Logout'),
        (USER_CREATED, 'User Created'),
        (USER_EDITED, 'User Edited'),
        (USER_SUSPENDED, 'User Suspended'),
        (USER_UNSUSPENDED, 'User Unsuspended'),
        (BOOK_APPROVED, 'Book Approved'),
        (BOOK_REJECTED, 'Book Rejected'),
        (CONTENT_REMOVED, 'Content Removed'),
        (REPORT_REVIEWED, 'Report Reviewed'),
        (ADMIN_ROLE_ASSIGNED, 'Admin Role Assigned'),
        (ADMIN_ROLE_REMOVED, 'Admin Role Removed'),
        (PERMISSION_CHANGED, 'Permission Changed'),
        (SETTING_CHANGED, 'System Setting Changed'),
    ]
    
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_audit_logs'
    )
    description = models.TextField(help_text='Detailed description of the action')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    changes = models.JSONField(default=dict, blank=True, help_text='JSON of changes made')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Admin Audit Log"
        verbose_name_plural = "Admin Audit Logs"
        indexes = [
            models.Index(fields=['admin_user', '-created_at']),
            models.Index(fields=['action', '-created_at']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.admin_user.username} - {self.get_action_display()}"
    
    @classmethod
    def log_action(cls, admin_user, action, description, target_user=None, ip_address=None, changes=None):
        """Helper method to create audit log entry"""
        return cls.objects.create(
            admin_user=admin_user,
            action=action,
            description=description,
            target_user=target_user,
            ip_address=ip_address,
            changes=changes or {}
        )


class NotificationPreference(models.Model):
    """Admin notification preferences"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_prefs')
    new_reports = models.BooleanField(default=True)
    pending_approvals = models.BooleanField(default=True)
    user_suspensions = models.BooleanField(default=True)
    system_alerts = models.BooleanField(default=True)
    email_digest = models.CharField(
        max_length=20,
        choices=[
            ('immediate', 'Immediate'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('never', 'Never'),
        ],
        default='daily'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - Notification Preferences"
