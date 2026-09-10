"""
Admin URL Configuration

Add this to your books/urls.py or create a separate admin_urls.py
and include it in the main urls.py
"""

from django.urls import path
from . import admin_views

# Admin URL namespace
app_name = 'admin'

urlpatterns = [
    # Dashboard
    path('dashboard/', admin_views.admin_dashboard, name='dashboard'),
    
    # User Management
    path('users/', admin_views.UserListView.as_view(), name='users-list'),
    path('users/<int:pk>/', admin_views.UserDetailView.as_view(), name='user-detail'),
    path('users/<int:user_id>/suspend/', admin_views.suspend_user, name='user-suspend'),
    path('users/<int:user_id>/edit/', admin_views.UserEditView.as_view(), name='user-edit'),
    path('suspensions/<int:suspension_id>/unsuspend/', admin_views.unsuspend_user, name='user-unsuspend'),
    
    # Book Approval
    path('books/pending/', admin_views.PendingBooksView.as_view(), name='pending-books'),
    path('books/<int:pk>/approval/', admin_views.BookApprovalView.as_view(), name='book-approval'),
    path('books/<int:book_id>/approve/', admin_views.approve_book, name='approve-book'),
    path('books/<int:book_id>/reject/', admin_views.reject_book, name='reject-book'),
    
    # Content Reports
    path('reports/', admin_views.ContentReportsView.as_view(), name='content-reports'),
    path('reports/<int:pk>/', admin_views.ContentReportDetailView.as_view(), name='report-detail'),
    path('reports/<int:report_id>/resolve/', admin_views.resolve_report, name='resolve-report'),
    path('reports/<int:report_id>/dismiss/', admin_views.dismiss_report, name='dismiss-report'),
    
    # Admin Roles
    path('permissions/matrix/', admin_views.permission_matrix, name='permission-matrix'),
    path('roles/', admin_views.AdminRoleListView.as_view(), name='admin-roles'),
    path('roles/<int:pk>/', admin_views.AdminRoleDetailView.as_view(), name='role-detail'),
    path('roles/assign/', admin_views.AdminRoleCreateView.as_view(), name='role-assign'),
    
    # Audit Logs
    path('audit-logs/', admin_views.AuditLogListView.as_view(), name='audit-logs'),
]

# To include in main urls.py:
# 
# from django.urls import path, include
# from books import admin_urls
# 
# urlpatterns = [
#     ...
#     path('admin-panel/', include(admin_urls)),
#     ...
# ]
