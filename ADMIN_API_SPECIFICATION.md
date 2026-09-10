# Admin Dashboard - Complete API Specification

## 📡 Overview

This document specifies all REST API endpoints for the BookClub Admin Dashboard, including authentication, request/response formats, error handling, and rate limiting.

**Base URL**: `https://api.bookclub.local/admin/v1`  
**Authentication**: JWT Bearer Token or Session Cookie  
**Content-Type**: `application/json`  
**Rate Limit**: 1000 requests/hour per user/token  

---

## 🔐 Authentication

### Login Endpoint
```
POST /auth/login
Authorization: Basic base64(username:password)
```

**Request:**
```json
{
  "username": "admin_user",
  "password": "secure_password",
  "remember_me": false
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "user": {
      "id": 1,
      "username": "admin_user",
      "email": "admin@bookclub.local",
      "role": "super_admin",
      "permissions": ["*"],
      "avatar_url": "https://..."
    },
    "expires_in": 3600
  }
}
```

**Response (401 Unauthorized):**
```json
{
  "status": "error",
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Username or password is incorrect",
    "details": null
  }
}
```

### Token Refresh
```
POST /auth/refresh
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

**Response (200 OK):**
```json
{
  "status": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "expires_in": 3600
  }
}
```

### Logout Endpoint
```
POST /auth/logout
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Logged out successfully"
}
```

---

## 👥 USER MANAGEMENT ENDPOINTS

### List Users
```
GET /users?page=1&limit=50&role=admin&status=active&search=john
Authorization: Bearer {token}
```

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| page | int | 1 | Page number (1-indexed) |
| limit | int | 50 | Results per page (max: 500) |
| role | string | null | Filter by role (admin, moderator, etc.) |
| status | string | null | active, suspended, deleted |
| search | string | null | Search by name/email |
| sort_by | string | -created_at | Field to sort by, prefix `-` for desc |
| include_deleted | bool | false | Include deleted users |

**Response (200 OK):**
```json
{
  "status": "success",
  "data": {
    "users": [
      {
        "id": 1,
        "username": "john_doe",
        "email": "john@example.com",
        "full_name": "John Doe",
        "role": "admin",
        "permissions": ["users:read", "users:write", "books:approve"],
        "status": "active",
        "is_suspended": false,
        "suspension_reason": null,
        "suspension_until": null,
        "created_at": "2024-01-15T10:30:00Z",
        "last_login": "2024-09-01T14:22:00Z",
        "last_activity": "2024-09-01T15:45:30Z",
        "activity_count_today": 23,
        "avatar_url": "https://...",
        "metadata": {
          "login_attempts": 0,
          "failed_login_attempts": 0,
          "two_factor_enabled": false
        }
      },
      // ... more users
    ],
    "pagination": {
      "page": 1,
      "limit": 50,
      "total": 2543,
      "pages": 51,
      "has_next": true,
      "has_previous": false
    },
    "filters_applied": {
      "role": "admin",
      "status": "active"
    }
  }
}
```

### Get User Details
```
GET /users/{user_id}
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "data": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "full_name": "John Doe",
    "bio": "Platform administrator",
    "role": "admin",
    "role_assigned_at": "2023-01-15T10:30:00Z",
    "role_assigned_by": {"id": 0, "username": "system"},
    "permissions": ["users:read", "users:write", "books:approve"],
    "is_suspended": false,
    "suspension_history": [
      {
        "id": 1,
        "suspended_at": "2024-08-01T10:00:00Z",
        "suspended_until": "2024-08-04T10:00:00Z",
        "reason": "spam",
        "status": "unsuspended",
        "unsuspended_at": "2024-08-04T10:00:00Z",
        "unsuspended_by": {"id": 2, "username": "admin_user"}
      }
    ],
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-09-01T14:22:00Z",
    "last_login": "2024-09-01T14:22:00Z",
    "metadata": {
      "total_publications": 3,
      "total_reports": 0,
      "verified_email": true,
      "two_factor_enabled": false
    },
    "audit_log_count": 45
  }
}
```

### Update User Role
```
PUT /users/{user_id}/role
Authorization: Bearer {token}
Content-Type: application/json
```

**Request:**
```json
{
  "role": "moderator",
  "notes": "Promoted from contributor",
  "notify_user": true
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "User role updated successfully",
  "data": {
    "id": 1,
    "username": "john_doe",
    "role": "moderator",
    "permissions": ["reports:read", "reports:write"],
    "updated_at": "2024-09-01T16:00:00Z",
    "audit_entry": {
      "id": 12345,
      "action": "role_changed",
      "timestamp": "2024-09-01T16:00:00Z"
    }
  }
}
```

### Suspend User
```
PUT /users/{user_id}/suspend
Authorization: Bearer {token}
Content-Type: application/json
```

**Request:**
```json
{
  "reason": "harassment",
  "type": "temporary",
  "duration_days": 7,
  "description": "Multiple reports of user harassment",
  "notify_user": true,
  "notify_email": true
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "User suspended successfully",
  "data": {
    "id": 1,
    "username": "john_doe",
    "is_suspended": true,
    "suspension_reason": "harassment",
    "suspension_type": "temporary",
    "suspended_at": "2024-09-01T16:00:00Z",
    "suspended_until": "2024-09-08T16:00:00Z",
    "suspension_id": 56789
  }
}
```

### Unsuspend User
```
PUT /users/{user_id}/unsuspend
Authorization: Bearer {token}
Content-Type: application/json
```

**Request:**
```json
{
  "reason": "Appeal approved",
  "notify_user": true
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "User unsuspended successfully",
  "data": {
    "id": 1,
    "username": "john_doe",
    "is_suspended": false,
    "unsuspended_at": "2024-09-01T17:00:00Z"
  }
}
```

### Delete User (Soft Delete)
```
DELETE /users/{user_id}?archive=true
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "User deleted and archived",
  "data": {
    "id": 1,
    "username": "john_doe",
    "deleted_at": "2024-09-01T17:00:00Z",
    "archived": true
  }
}
```

---

## 🔐 ROLE & PERMISSION MANAGEMENT ENDPOINTS

### List All Roles
```
GET /roles?include_permissions=true&include_users=true
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "data": {
    "roles": [
      {
        "id": 1,
        "name": "super_admin",
        "display_name": "Super Administrator",
        "description": "Full system access and control",
        "priority": 10,
        "user_count": 1,
        "permissions": ["*"],
        "inherited_from": null,
        "is_active": true,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-09-01T16:00:00Z"
      },
      {
        "id": 2,
        "name": "moderator",
        "display_name": "Moderator",
        "description": "Content moderation focused",
        "priority": 5,
        "user_count": 23,
        "permissions": [
          "reports:read",
          "reports:write",
          "reports:resolve",
          "users:read",
          "users:suspend",
          "audit:read"
        ],
        "inherited_from": "admin",
        "is_active": true,
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-09-01T16:00:00Z"
      },
      // ... more roles
    ]
  }
}
```

### Get Role Details
```
GET /roles/{role_id}
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "data": {
    "id": 2,
    "name": "moderator",
    "display_name": "Moderator",
    "description": "Content moderation focused",
    "priority": 5,
    "permissions": [
      {
        "id": 1,
        "name": "reports:read",
        "module": "reports",
        "action": "read",
        "description": "View content reports"
      },
      // ... more permissions
    ],
    "inherited_from": "admin",
    "inheritance_chain": ["super_admin", "admin", "moderator"],
    "users": [
      {
        "id": 10,
        "username": "jane_moderator",
        "assigned_at": "2024-05-10T14:30:00Z",
        "last_activity": "2024-09-01T14:22:00Z"
      },
      // ... more users
    ],
    "audit_history": [
      {
        "id": 1,
        "action": "created",
        "changed_by": {"id": 1, "username": "super_admin"},
        "timestamp": "2024-01-15T10:30:00Z",
        "changes": {}
      },
      {
        "id": 2,
        "action": "permission_added",
        "changed_by": {"id": 1, "username": "super_admin"},
        "timestamp": "2024-08-15T10:30:00Z",
        "changes": {"permission": "audit:read"}
      }
    ],
    "is_active": true,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-09-01T16:00:00Z"
  }
}
```

### Create New Role
```
POST /roles
Authorization: Bearer {token}
Content-Type: application/json
```

**Request:**
```json
{
  "name": "content_reviewer",
  "display_name": "Content Reviewer",
  "description": "Reviews and approves published content",
  "priority": 4,
  "inherited_from": "moderator",
  "permissions": [
    "reports:read",
    "reports:write",
    "books:read",
    "books:approve",
    "audit:read"
  ],
  "notes": "Specialized role for content review team"
}
```

**Response (201 Created):**
```json
{
  "status": "success",
  "message": "Role created successfully",
  "data": {
    "id": 10,
    "name": "content_reviewer",
    "display_name": "Content Reviewer",
    "description": "Reviews and approves published content",
    "priority": 4,
    "permissions": [
      {
        "id": 1,
        "name": "reports:read",
        "module": "reports",
        "action": "read"
      },
      // ... all permissions
    ],
    "inherited_from": "moderator",
    "created_at": "2024-09-01T16:30:00Z",
    "created_by": {"id": 1, "username": "super_admin"}
  }
}
```

### Update Role
```
PUT /roles/{role_id}
Authorization: Bearer {token}
Content-Type: application/json
```

**Request:**
```json
{
  "display_name": "Senior Content Reviewer",
  "description": "Senior reviews and approves published content",
  "priority": 5,
  "permissions": [
    "reports:read",
    "reports:write",
    "reports:resolve",
    "books:read",
    "books:approve",
    "books:reject",
    "audit:read",
    "audit:export"
  ]
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Role updated successfully",
  "data": {
    "id": 10,
    "name": "content_reviewer",
    "display_name": "Senior Content Reviewer",
    "permissions": [ /* updated list */ ],
    "updated_at": "2024-09-01T17:00:00Z",
    "changed_by": {"id": 1, "username": "super_admin"},
    "changes": {
      "display_name": "Content Reviewer → Senior Content Reviewer",
      "permissions": ["reports:resolve", "books:reject", "audit:export"] // newly added
    }
  }
}
```

### Delete Role
```
DELETE /roles/{role_id}?reassign_to={fallback_role_id}
Authorization: Bearer {token}
```

**Request:**
```json
{
  "reassign_users_to": 2,
  "reason": "Role no longer needed",
  "notify_users": true
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Role deleted and users reassigned",
  "data": {
    "role_id": 10,
    "users_affected": 5,
    "reassigned_to": {
      "id": 2,
      "name": "moderator"
    },
    "deleted_at": "2024-09-01T17:00:00Z"
  }
}
```

### Get Permission Matrix
```
GET /permissions/matrix?include_roles=true&include_modules=true
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "data": {
    "matrix": [
      {
        "module": "users",
        "permissions": [
          {
            "name": "users:create",
            "display_name": "Create Users",
            "description": "Create new user accounts",
            "roles_with_permission": ["super_admin", "admin"],
            "role_count": 2,
            "last_modified_at": "2024-08-15T10:30:00Z",
            "last_modified_by": {"id": 1, "username": "super_admin"}
          },
          {
            "name": "users:read",
            "display_name": "Read Users",
            "description": "View user information",
            "roles_with_permission": ["super_admin", "admin", "moderator", "analytics"],
            "role_count": 4
          },
          // ... more permissions
        ]
      },
      {
        "module": "reports",
        "permissions": [ /* ... */ ]
      },
      // ... more modules
    ],
    "summary": {
      "total_modules": 8,
      "total_permissions": 48,
      "total_roles": 5
    }
  }
}
```

### Assign Role to Users (Bulk)
```
POST /roles/{role_id}/assign-users
Authorization: Bearer {token}
Content-Type: application/json
```

**Request:**
```json
{
  "user_ids": [10, 15, 20, 35],
  "override_existing": true,
  "notify_users": true,
  "reason": "Promotion campaign"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Role assigned to 4 users",
  "data": {
    "role_id": 2,
    "users_assigned": [
      {
        "id": 10,
        "username": "user_10",
        "previous_role": "contributor",
        "new_role": "moderator",
        "assigned_at": "2024-09-01T17:00:00Z"
      },
      // ... more users
    ],
    "total": 4,
    "batch_id": "batch_123456"
  }
}
```

---

## 📚 BOOK MANAGEMENT ENDPOINTS

### List Pending Books for Approval
```
GET /books/pending?page=1&limit=50&days_since_submitted=7
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "data": {
    "books": [
      {
        "id": 1,
        "title": "The Great Novel",
        "author": {
          "id": 100,
          "username": "author_john",
          "email": "author@example.com"
        },
        "cover_url": "https://...",
        "description": "A compelling story...",
        "status": "pending",
        "submitted_at": "2024-08-28T10:30:00Z",
        "submitted_by": {"id": 100, "username": "author_john"},
        "days_pending": 4,
        "review_deadline": "2024-09-11T10:30:00Z",
        "previous_rejections": 1,
        "reviewer_notes": [
          {
            "created_at": "2024-08-29T14:00:00Z",
            "reviewer": {"id": 5, "username": "reviewer_1"},
            "note": "Needs grammar review"
          }
        ]
      },
      // ... more books
    ],
    "pagination": {
      "page": 1,
      "limit": 50,
      "total": 12,
      "pages": 1
    }
  }
}
```

### Approve Book
```
PUT /books/{book_id}/approve
Authorization: Bearer {token}
Content-Type: application/json
```

**Request:**
```json
{
  "message": "Excellent work! Published immediately.",
  "send_notification": true,
  "notification_type": "email"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Book approved successfully",
  "data": {
    "id": 1,
    "title": "The Great Novel",
    "status": "published",
    "approved_at": "2024-09-01T17:00:00Z",
    "approved_by": {"id": 1, "username": "reviewer"},
    "audit_entry": {
      "id": 54321,
      "action": "book_approved",
      "timestamp": "2024-09-01T17:00:00Z"
    }
  }
}
```

### Reject Book
```
PUT /books/{book_id}/reject
Authorization: Bearer {token}
Content-Type: application/json
```

**Request:**
```json
{
  "reason": "Content violation",
  "message": "Please review our content policy and resubmit",
  "send_notification": true
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Book rejected successfully",
  "data": {
    "id": 1,
    "title": "The Great Novel",
    "status": "rejected",
    "rejection_reason": "Content violation",
    "rejected_at": "2024-09-01T17:00:00Z",
    "rejected_by": {"id": 1, "username": "reviewer"}
  }
}
```

### Request Book Revision
```
PUT /books/{book_id}/request-revision
Authorization: Bearer {token}
Content-Type: application/json
```

**Request:**
```json
{
  "message": "Please fix grammar issues and resubmit",
  "deadline_days": 14,
  "required_changes": [
    "Fix grammar on page 5",
    "Update metadata",
    "Improve cover design"
  ]
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Revision requested successfully",
  "data": {
    "id": 1,
    "status": "revision_requested",
    "revision_deadline": "2024-09-15T17:00:00Z",
    "revision_requested_at": "2024-09-01T17:00:00Z"
  }
}
```

---

## 🚩 CONTENT REPORT ENDPOINTS

### List Content Reports
```
GET /reports?page=1&limit=50&status=open&type=harassment
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "data": {
    "reports": [
      {
        "id": 1234,
        "type": "harassment",
        "status": "open",
        "reported_at": "2024-09-01T10:30:00Z",
        "reporter": {
          "id": 50,
          "username": "user_50",
          "email": "user50@example.com"
        },
        "reported_user": {
          "id": 15,
          "username": "offending_user",
          "email": "user15@example.com"
        },
        "description": "User posted harassing comments",
        "content_type": "post_comment",
        "content_id": 5678,
        "priority": "high",
        "assigned_to": {
          "id": 2,
          "username": "moderator_jane"
        },
        "created_at": "2024-09-01T10:30:00Z"
      },
      // ... more reports
    ],
    "pagination": {
      "page": 1,
      "limit": 50,
      "total": 7,
      "pages": 1
    },
    "summary": {
      "open": 7,
      "in_progress": 2,
      "resolved": 145,
      "dismissed": 18
    }
  }
}
```

### Resolve Content Report
```
PUT /reports/{report_id}/resolve
Authorization: Bearer {token}
Content-Type: application/json
```

**Request:**
```json
{
  "action_taken": "user_suspended",
  "resolution": "User suspended for 48 hours due to harassment",
  "notify_reporter": true,
  "notify_reported_user": true
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Report resolved successfully",
  "data": {
    "id": 1234,
    "status": "resolved",
    "resolved_at": "2024-09-01T17:00:00Z",
    "resolved_by": {"id": 2, "username": "moderator_jane"},
    "action_taken": "user_suspended",
    "resolution_summary": "User suspended for 48 hours due to harassment"
  }
}
```

### Dismiss Content Report
```
PUT /reports/{report_id}/dismiss
Authorization: Bearer {token}
Content-Type: application/json
```

**Request:**
```json
{
  "reason": "report_frivolous",
  "notes": "User misunderstood the comment context"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Report dismissed",
  "data": {
    "id": 1234,
    "status": "dismissed",
    "dismissed_at": "2024-09-01T17:00:00Z",
    "dismissed_by": {"id": 2, "username": "moderator_jane"}
  }
}
```

---

## 📋 AUDIT LOG ENDPOINTS

### List Audit Logs
```
GET /audit-logs?page=1&limit=100&action=user_suspended&admin_id=1&days=30
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "data": {
    "logs": [
      {
        "id": 12345,
        "admin_user": {
          "id": 1,
          "username": "super_admin",
          "email": "admin@example.com"
        },
        "action": "user_suspended",
        "description": "Suspended user for harassment",
        "target_user": {
          "id": 15,
          "username": "offending_user"
        },
        "target_role": null,
        "changes": {
          "reason": "harassment",
          "type": "temporary",
          "duration_days": 7
        },
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0...",
        "created_at": "2024-09-01T16:00:00Z",
        "status": "success"
      },
      // ... more logs
    ],
    "pagination": {
      "page": 1,
      "limit": 100,
      "total": 1024,
      "pages": 11
    },
    "filters": {
      "action": "user_suspended",
      "admin_id": 1,
      "days": 30
    }
  }
}
```

### Export Audit Logs
```
GET /audit-logs/export?format=csv&action=&start_date=2024-08-01&end_date=2024-09-01
Authorization: Bearer {token}
```

**Response (200 OK):**
```
Content-Type: text/csv
Content-Disposition: attachment; filename="audit_logs_2024-08-01_to_2024-09-01.csv"

timestamp,admin_username,action,target_user,target_role,description,ip_address,status
2024-09-01T16:00:00Z,super_admin,user_suspended,offending_user,,Suspended user for harassment,192.168.1.100,success
...
```

---

## 🔍 SEARCH ENDPOINTS

### Global Search
```
GET /search?q=john&type=users,books,reports&limit=50
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "data": {
    "query": "john",
    "results": {
      "users": [
        {
          "id": 1,
          "type": "user",
          "username": "john_doe",
          "email": "john@example.com",
          "role": "admin",
          "score": 0.95
        }
      ],
      "books": [
        {
          "id": 50,
          "type": "book",
          "title": "John's Adventure",
          "author": "John Smith",
          "status": "published",
          "score": 0.87
        }
      ],
      "reports": [
        {
          "id": 1234,
          "type": "report",
          "description": "Report by john_doe",
          "status": "open",
          "score": 0.82
        }
      ]
    },
    "total_results": 3,
    "search_time_ms": 45
  }
}
```

### Advanced Search
```
GET /search/advanced?status:pending&assigned:admin&module:reports
Authorization: Bearer {token}
```

**Response:** Same as global search with advanced filter results

---

## ⚙️ DASHBOARD ENDPOINTS

### Get Dashboard Statistics
```
GET /dashboard/statistics?range=last_30_days
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "data": {
    "summary": {
      "total_users": 2543,
      "active_users": 487,
      "suspended_users": 23,
      "total_books": 1205,
      "pending_approvals": 12,
      "unresolved_reports": 7,
      "system_uptime_percent": 99.8
    },
    "trends": {
      "new_users_today": 12,
      "new_users_this_week": 87,
      "new_users_this_month": 356,
      "user_trend": "up",
      "user_trend_percent": 5.2
    },
    "activity": {
      "reports_created_today": 3,
      "reports_resolved_today": 2,
      "books_submitted_today": 5,
      "books_approved_today": 2,
      "users_suspended_today": 1
    },
    "cache_updated_at": "2024-09-01T15:45:00Z"
  }
}
```

---

## 🔄 WEBSOCKET ENDPOINTS (Real-time)

### Connect to Admin Updates
```
WS /ws/admin/updates?token={token}
```

**Events:**
```json
{
  "type": "report_created",
  "data": {
    "report_id": 1234,
    "type": "harassment",
    "reported_user": "offending_user"
  }
}

{
  "type": "user_suspended",
  "data": {
    "user_id": 15,
    "suspended_by": "moderator_jane"
  }
}

{
  "type": "book_submitted",
  "data": {
    "book_id": 50,
    "title": "New Book",
    "author": "John Smith"
  }
}
```

---

## ⚠️ Error Handling

### Error Response Format
```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "error_details"
    },
    "timestamp": "2024-09-01T16:00:00Z",
    "request_id": "req_123456"
  }
}
```

### Common Error Codes
| Code | Status | Meaning |
|------|--------|---------|
| INVALID_CREDENTIALS | 401 | Username/password incorrect |
| TOKEN_EXPIRED | 401 | JWT token has expired |
| INSUFFICIENT_PERMISSIONS | 403 | User lacks required permissions |
| RESOURCE_NOT_FOUND | 404 | Requested resource does not exist |
| VALIDATION_ERROR | 400 | Invalid request parameters |
| RATE_LIMIT_EXCEEDED | 429 | Too many requests |
| INTERNAL_ERROR | 500 | Server error |

---

## 📊 Rate Limiting

**Default**: 1000 requests/hour per user  
**Burst**: 100 requests/minute  
**Headers:**
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 876
X-RateLimit-Reset: 1693526400
```

---

*API specification follows RESTful principles with consistent naming, error handling, and security best practices.*
