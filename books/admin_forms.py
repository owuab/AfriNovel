"""
Admin forms for user management, content approval, and moderation
"""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from .admin_models import (
    AdminRole, UserSuspension, BookApprovalStatus,
)
from .models import Book, ContentReport


User = get_user_model()


class UserSuspensionForm(forms.ModelForm):
    """Form for suspending users"""
    
    class Meta:
        model = UserSuspension
        fields = ['suspension_type', 'reason', 'description']
        widgets = {
            'suspension_type': forms.RadioSelect(choices=UserSuspension.SUSPENSION_TYPE_CHOICES),
            'reason': forms.Select(choices=UserSuspension.REASON_CHOICES),
            'description': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Enter detailed reason for suspension...',
                'class': 'form-control'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('description'):
            raise forms.ValidationError('Please provide a detailed reason for suspension.')
        return cleaned_data


class BookApprovalForm(forms.ModelForm):
    """Form for approving/rejecting books"""
    action = forms.ChoiceField(
        choices=[
            ('approve', 'Approve'),
            ('reject', 'Reject'),
            ('revision', 'Request Revision'),
        ],
        widget=forms.RadioSelect(),
        required=True
    )
    feedback = forms.CharField(
        label='Feedback for Author',
        widget=forms.Textarea(attrs={
            'rows': 5,
            'placeholder': 'Enter feedback...',
            'class': 'form-control'
        }),
        required=False
    )
    rejection_reason = forms.CharField(
        label='Rejection Reason',
        widget=forms.Textarea(attrs={
            'rows': 5,
            'placeholder': 'Enter reason for rejection...',
            'class': 'form-control'
        }),
        required=False
    )
    
    class Meta:
        model = BookApprovalStatus
        fields = []
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        
        if action == 'reject' and not cleaned_data.get('rejection_reason'):
            raise forms.ValidationError('Rejection reason is required.')
        
        return cleaned_data


class ContentReportForm(forms.ModelForm):
    """Form for reporting content"""
    
    class Meta:
        model = ContentReport
        fields = ['reason', 'details']
        widgets = {
            'reason': forms.Select(),
            'details': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Describe the issue in detail...',
                'class': 'form-control'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('details') or len(cleaned_data.get('details', '')) < 20:
            raise forms.ValidationError('Please provide a detailed description (at least 20 characters).')
        return cleaned_data


class ContentReportResolutionForm(forms.Form):
    """Form for resolving content reports"""
    mark_resolved = forms.BooleanField(
        label='Mark as Resolved',
        required=False
    )
    resolution_notes = forms.CharField(
        label='Resolution Notes',
        widget=forms.Textarea(attrs={
            'rows': 5,
            'placeholder': 'Explain how the report was resolved...',
            'class': 'form-control'
        }),
        required=True
    )


class AdminRoleForm(forms.ModelForm):
    """Form for assigning admin roles"""
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_superuser=False).exclude(admin_role__isnull=False),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Select User'
    )
    role = forms.ChoiceField(
        choices=AdminRole.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        widget=forms.CheckboxSelectMultiple(),
        required=False,
        label='Additional Permissions'
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Notes about this assignment...',
            'class': 'form-control'
        }),
        required=False
    )
    
    class Meta:
        model = AdminRole
        fields = ['user', 'role', 'permissions', 'notes']


class UserEditForm(forms.ModelForm):
    """Form for editing user information"""
    
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'is_active', 'is_staff']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class BulkActionForm(forms.Form):
    """Form for performing bulk actions on users"""
    action = forms.ChoiceField(
        choices=[
            ('suspend', 'Suspend Selected Users'),
            ('unsuspend', 'Unsuspend Selected Users'),
            ('activate', 'Activate Selected Users'),
            ('deactivate', 'Deactivate Selected Users'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Reason for action (if applicable)...',
            'class': 'form-control'
        }),
        required=False
    )


class AdvancedSearchForm(forms.Form):
    """Form for advanced user/content search"""
    query = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Search...',
            'class': 'form-control'
        }),
        required=False
    )
    search_type = forms.ChoiceField(
        choices=[
            ('username', 'Username'),
            ('email', 'Email'),
            ('display_name', 'Display Name'),
            ('ip_address', 'IP Address'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )
    date_from = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control'
        }),
        required=False
    )
    date_to = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control'
        }),
        required=False
    )


class NotificationPreferencesForm(forms.Form):
    """Form for admin notification preferences"""
    new_reports = forms.BooleanField(required=False, label='New Content Reports')
    pending_approvals = forms.BooleanField(required=False, label='Pending Book Approvals')
    user_suspensions = forms.BooleanField(required=False, label='User Suspensions')
    system_alerts = forms.BooleanField(required=False, label='System Alerts')
    email_digest = forms.ChoiceField(
        choices=[
            ('immediate', 'Immediate'),
            ('daily', 'Daily Digest'),
            ('weekly', 'Weekly Digest'),
            ('never', 'Never'),
        ],
        widget=forms.RadioSelect(),
        label='Email Notifications'
    )


class AdminAnalyticsFilterForm(forms.Form):
    """Form for filtering admin analytics"""
    date_range = forms.ChoiceField(
        choices=[
            ('today', 'Today'),
            ('week', 'This Week'),
            ('month', 'This Month'),
            ('year', 'This Year'),
            ('custom', 'Custom Range'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='month'
    )
    action_filter = forms.ChoiceField(
        choices=[
            ('all', 'All Actions'),
            ('user_management', 'User Management'),
            ('content_approval', 'Content Approval'),
            ('content_moderation', 'Content Moderation'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='all',
        required=False
    )
    admin_filter = forms.ModelChoiceField(
        queryset=User.objects.filter(is_staff=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False,
        label='Filter by Admin'
    )
