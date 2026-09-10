"""
Admin views for user management, content approval, and moderation
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import permission_required
from django.db.models import Count, Q, F
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.contrib import messages
from django.urls import reverse
from django.views.generic import ListView, DetailView, UpdateView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from .models import (
    Book, Review, SocialPost, PostComment, ContentReport, Permission, RolePermission,
)
from .admin_models import (
    AdminRole, UserSuspension, BookApprovalStatus,
    AdminAuditLog, NotificationPreference
)
from .admin_forms import (
    UserSuspensionForm, BookApprovalForm, ContentReportForm,
    AdminRoleForm, UserEditForm
)


User = get_user_model()


class AdminAccessMixin(UserPassesTestMixin):
    """Mixin to check if user has admin access"""
    
    def test_func(self):
        user = self.request.user
        return user.is_superuser or (user.is_staff and hasattr(user, 'admin_role'))
    
    def handle_no_permission(self):
        messages.error(self.request, 'You do not have permission to access this page.')
        return redirect('home')


# ==================== DASHBOARD ====================

@staff_member_required(login_url='/admin/login/')
def admin_dashboard(request):
    """Main admin dashboard with statistics and recent activity"""
    
    # Get admin role
    admin_role = getattr(request.user, 'admin_role', None)
    
    # Statistics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    suspended_users = User.objects.filter(suspensions__is_active=True).distinct().count()
    
    total_books = Book.objects.count()
    pending_books = BookApprovalStatus.objects.filter(status='pending').count()
    published_books = Book.objects.filter(status='published').count()
    
    total_reports = ContentReport.objects.count()
    pending_reports = ContentReport.objects.filter(resolved=False).count()
    
    recent_suspensions = UserSuspension.objects.filter(is_active=True).select_related('user', 'suspended_by')[:5]
    pending_approvals = BookApprovalStatus.objects.filter(status='pending').select_related('book', 'book__author')[:5]
    recent_reports = ContentReport.objects.filter(resolved=False).select_related('reporter', 'reported_user')[:5]
    recent_audit_logs = AdminAuditLog.objects.select_related('admin_user')[:10]
    
    context = {
        'admin_role': admin_role,
        'stats': {
            'total_users': total_users,
            'active_users': active_users,
            'suspended_users': suspended_users,
            'total_books': total_books,
            'pending_books': pending_books,
            'published_books': published_books,
            'total_reports': total_reports,
            'pending_reports': pending_reports,
        },
        'recent_suspensions': recent_suspensions,
        'pending_approvals': pending_approvals,
        'recent_reports': recent_reports,
        'recent_audit_logs': recent_audit_logs,
    }
    
    return render(request, 'admin/dashboard.html', context)


# ==================== USER MANAGEMENT ====================

class UserListView(AdminAccessMixin, ListView):
    """List all users with filtering and search"""
    model = User
    template_name = 'admin/users/user_list.html'
    context_object_name = 'users'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = User.objects.all().annotate(
            suspension_count=Count('suspensions', filter=Q(suspensions__is_active=True))
        ).select_related('admin_role')
        
        # Search
        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
        
        # Filter
        status_filter = self.request.GET.get('status', 'all')
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
        elif status_filter == 'suspended':
            queryset = queryset.filter(suspension_count__gt=0)
        elif status_filter == 'admin':
            queryset = queryset.filter(is_staff=True)
        
        return queryset.order_by('-date_joined')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', 'all')
        return context


class UserDetailView(AdminAccessMixin, DetailView):
    """View detailed user information"""
    model = User
    template_name = 'admin/users/user_detail.html'
    context_object_name = 'user_obj'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        
        context['suspensions'] = UserSuspension.objects.filter(user=user).order_by('-suspended_at')
        context['books_published'] = Book.objects.filter(author__followers__follower=user).count()
        context['reviews'] = Review.objects.filter(user=user).count()
        context['is_suspended'] = UserSuspension.objects.filter(user=user, is_active=True).exists()
        
        return context


@staff_member_required
@require_http_methods(["GET", "POST"])
def suspend_user(request, user_id):
    """Suspend or ban a user"""
    user = get_object_or_404(User, id=user_id)
    
    # Check permissions
    if not (request.user.is_superuser or request.user.admin_role.role == AdminRole.SUPER_ADMIN):
        return HttpResponseForbidden('You do not have permission to suspend users.')
    
    if request.method == 'POST':
        form = UserSuspensionForm(request.POST)
        if form.is_valid():
            suspension = form.save(commit=False)
            suspension.user = user
            suspension.suspended_by = request.user
            suspension.save()
            
            # Deactivate user account
            user.is_active = False
            user.save()
            
            # Log action
            AdminAuditLog.log_action(
                admin_user=request.user,
                action=AdminAuditLog.USER_SUSPENDED,
                description=f'Suspended {user.username}: {suspension.reason}',
                target_user=user,
                ip_address=get_client_ip(request),
                changes={
                    'suspension_type': suspension.suspension_type,
                    'reason': suspension.reason,
                }
            )
            
            messages.success(request, f'{user.username} has been suspended.')
            return redirect('admin_panel:user-detail', pk=user.id)
    else:
        form = UserSuspensionForm()
    
    return render(request, 'admin/users/suspend_user.html', {
        'form': form,
        'user_obj': user,
    })


@staff_member_required
@require_http_methods(["POST"])
def unsuspend_user(request, suspension_id):
    """Unsuspend a user"""
    suspension = get_object_or_404(UserSuspension, id=suspension_id)
    
    # Check permissions
    if not (request.user.is_superuser or request.user.admin_role.role == AdminRole.SUPER_ADMIN):
        return HttpResponseForbidden('You do not have permission to unsuspend users.')
    
    reason = request.POST.get('reason', '')
    suspension.unsuspend(request.user, reason)
    
    # Log action
    AdminAuditLog.log_action(
        admin_user=request.user,
        action=AdminAuditLog.USER_UNSUSPENDED,
        description=f'Unsuspended {suspension.user.username}: {reason}',
        target_user=suspension.user,
        ip_address=get_client_ip(request),
    )
    
    messages.success(request, f'{suspension.user.username} has been unsuspended.')
    return redirect('admin_panel:user-detail', pk=suspension.user.id)


class UserEditView(AdminAccessMixin, UpdateView):
    """Edit user information"""
    model = User
    form_class = UserEditForm
    template_name = 'admin/users/user_edit.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Log action
        AdminAuditLog.log_action(
            admin_user=self.request.user,
            action=AdminAuditLog.USER_EDITED,
            description=f'Edited user {self.object.username}',
            target_user=self.object,
            ip_address=get_client_ip(self.request),
            changes=form.changed_data,
        )
        
        messages.success(self.request, 'User updated successfully.')
        return response
    
    def get_success_url(self):
        return reverse('admin_panel:user-detail', kwargs={'pk': self.object.pk})


# ==================== BOOK APPROVAL ====================

class PendingBooksView(AdminAccessMixin, ListView):
    """List pending books awaiting approval"""
    model = BookApprovalStatus
    template_name = 'admin/books/pending_books.html'
    context_object_name = 'approvals'
    paginate_by = 20
    
    def get_queryset(self):
        return BookApprovalStatus.objects.filter(
            status__in=['pending', 'revision_needed']
        ).select_related('book', 'book__author').order_by('-submitted_at')


class BookApprovalView(AdminAccessMixin, DetailView):
    """Review and approve/reject a book"""
    model = Book
    template_name = 'admin/books/book_approval.html'
    context_object_name = 'book'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book = self.get_object()
        context['approval_status'] = BookApprovalStatus.objects.get(book=book)
        context['form'] = BookApprovalForm()
        return context


@staff_member_required
@require_http_methods(["POST"])
def approve_book(request, book_id):
    """Approve a book for publication"""
    book = get_object_or_404(Book, id=book_id)
    approval = get_object_or_404(BookApprovalStatus, book=book)
    
    # Check permissions
    if not (request.user.is_superuser or request.user.admin_role.role in [AdminRole.SUPER_ADMIN, AdminRole.CONTENT_MANAGER]):
        return HttpResponseForbidden('You do not have permission to approve books.')
    
    feedback = request.POST.get('feedback', '')
    approval.approve(request.user, feedback)
    
    # Log action
    AdminAuditLog.log_action(
        admin_user=request.user,
        action=AdminAuditLog.BOOK_APPROVED,
        description=f'Approved book: {book.title}',
        ip_address=get_client_ip(request),
        changes={'feedback': feedback},
    )
    
    messages.success(request, f'"{book.title}" has been approved for publication.')
    return redirect('admin_panel:book-approval', pk=book.id)


@staff_member_required
@require_http_methods(["POST"])
def reject_book(request, book_id):
    """Reject a book"""
    book = get_object_or_404(Book, id=book_id)
    approval = get_object_or_404(BookApprovalStatus, book=book)
    
    # Check permissions
    if not (request.user.is_superuser or request.user.admin_role.role in [AdminRole.SUPER_ADMIN, AdminRole.CONTENT_MANAGER]):
        return HttpResponseForbidden('You do not have permission to reject books.')
    
    reason = request.POST.get('reason', '')
    approval.reject(request.user, reason)
    
    # Log action
    AdminAuditLog.log_action(
        admin_user=request.user,
        action=AdminAuditLog.BOOK_REJECTED,
        description=f'Rejected book: {book.title}',
        ip_address=get_client_ip(request),
        changes={'reason': reason},
    )
    
    messages.success(request, f'"{book.title}" has been rejected.')
    return redirect('admin_panel:pending-books')


# ==================== CONTENT MODERATION ====================

class ContentReportsView(AdminAccessMixin, ListView):
    """List all content reports"""
    model = ContentReport
    template_name = 'admin/reports/report_list.html'
    context_object_name = 'reports'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = ContentReport.objects.select_related('reporter', 'reported_user', 'post')
        
        # Filter by status
        status_filter = self.request.GET.get('status', 'pending')
        if status_filter == 'pending':
            queryset = queryset.filter(resolved=False)
        elif status_filter == 'resolved':
            queryset = queryset.filter(resolved=True)
        elif status_filter not in ('all', ''):
            status_filter = 'pending'
            queryset = queryset.filter(resolved=False)
        
        # Filter by type
        report_type = self.request.GET.get('type', '')
        if report_type:
            queryset = queryset.filter(report_type=report_type)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_filter'] = self.request.GET.get('status', 'pending')
        context['type_filter'] = self.request.GET.get('type', '')
        context['pending_count'] = ContentReport.objects.filter(resolved=False).count()
        context['resolved_count'] = ContentReport.objects.filter(resolved=True).count()
        context['reviewing_count'] = 0
        return context


class ContentReportDetailView(AdminAccessMixin, DetailView):
    """View detailed report information"""
    model = ContentReport
    template_name = 'admin/reports/report_detail.html'
    context_object_name = 'report'


@staff_member_required
@require_http_methods(["POST"])
def resolve_report(request, report_id):
    """Resolve a content report"""
    report = get_object_or_404(ContentReport, id=report_id)
    
    resolution_notes = request.POST.get('resolution_notes', '')
    
    report.resolved = True
    report.save()
    
    # Log action
    AdminAuditLog.log_action(
        admin_user=request.user,
        action=AdminAuditLog.REPORT_REVIEWED,
        description=f'Resolved report #{report.id}: {report.get_reason_display()}',
        target_user=report.reported_user,
        ip_address=get_client_ip(request),
        changes={'resolved': True, 'resolution_notes': resolution_notes},
    )
    
    messages.success(request, 'Report has been resolved.')
    return redirect('admin_panel:report-detail', pk=report.id)


@staff_member_required
@require_http_methods(["POST"])
def dismiss_report(request, report_id):
    """Dismiss a content report"""
    report = get_object_or_404(ContentReport, id=report_id)
    
    # Mark as resolved (which effectively dismisses it)
    report.resolved = True
    report.save()
    
    messages.success(request, 'Report has been dismissed.')
    return redirect('admin_panel:report-detail', pk=report.id)


# ==================== ADMIN ROLE MANAGEMENT ====================

@staff_member_required(login_url='/login/')
def permission_matrix(request):
    """Render a permission matrix showing which roles have which permissions."""
    if not getattr(request.user, 'is_staff', False):
        return redirect('home')

    roles = [
        AdminRole.SUPER_ADMIN,
        AdminRole.ADMIN,
        AdminRole.MODERATOR,
        AdminRole.CONTENT_MANAGER,
        AdminRole.ANALYTICS,
    ]
    permissions = list(Permission.objects.order_by('module', 'action'))
    role_permission_map = {
        role_name: set()
        for role_name in roles
    }

    for role_name, permission_name in RolePermission.objects.filter(
        role_name__in=roles,
        revoked_at__isnull=True,
    ).values_list('role_name', 'permission__name'):
        role_permission_map.setdefault(role_name, set()).add(permission_name)

    matrix_rows = []
    for permission in permissions:
        row = {
            'permission': permission,
            'cells': [],
        }
        for role in roles:
            row['cells'].append(permission.name in role_permission_map.get(role, set()))
        matrix_rows.append(row)

    module_groups = {}
    for row in matrix_rows:
        module_groups.setdefault(row['permission'].module, []).append(row)

    context = {
        'roles': roles,
        'permission_modules': [
            {'name': module, 'rows': rows}
            for module, rows in sorted(module_groups.items())
        ],
        'matrix_metadata': {
            'total_roles': len(roles),
            'total_permissions': len(permissions),
        },
    }
    return render(request, 'admin/permissions/matrix.html', context)


class AdminRoleListView(AdminAccessMixin, ListView):
    """List all admin users and their roles"""
    model = AdminRole
    template_name = 'admin/roles/role_list.html'
    context_object_name = 'admins'
    paginate_by = 20
    
    def get_queryset(self):
        return AdminRole.objects.select_related('user', 'assigned_by').filter(is_active=True)


class AdminRoleDetailView(AdminAccessMixin, DetailView):
    """View admin role details"""
    model = AdminRole
    template_name = 'admin/roles/role_detail.html'
    context_object_name = 'admin_role'


class AdminRoleCreateView(AdminAccessMixin, CreateView):
    """Assign admin role to a user"""
    model = AdminRole
    form_class = AdminRoleForm
    template_name = 'admin/roles/role_form.html'

    def get_success_url(self):
        return reverse('admin_panel:admin-roles')
    
    def form_valid(self, form):
        form.instance.assigned_by = self.request.user
        response = super().form_valid(form)
        
        # Make user staff
        form.instance.user.is_staff = True
        form.instance.user.save()
        
        # Log action
        AdminAuditLog.log_action(
            admin_user=self.request.user,
            action=AdminAuditLog.ADMIN_ROLE_ASSIGNED,
            description=f'Assigned {form.instance.get_role_display()} role to {form.instance.user.username}',
            target_user=form.instance.user,
            ip_address=get_client_ip(self.request),
        )
        
        messages.success(self.request, f'Admin role assigned to {form.instance.user.username}')
        return response


# ==================== AUDIT LOGS ====================

class AuditLogListView(AdminAccessMixin, ListView):
    """List audit logs"""
    model = AdminAuditLog
    template_name = 'admin/audit_logs.html'
    context_object_name = 'audit_logs'
    paginate_by = 50
    
    def get_queryset(self):
        return AdminAuditLog.objects.select_related('admin_user', 'target_user').order_by('-created_at')


# ==================== UTILITY FUNCTIONS ====================

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
