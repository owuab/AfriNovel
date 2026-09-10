# Admin Dashboard - Data Model & Entity Relationship Diagram

## 📊 Database Schema

### Entity-Relationship Diagram (ERD)

```
┌────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│                         ADMIN RBAC DATA MODEL                               │
│                                                                              │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                          ┌──────────────┐                                   │
│                          │    User      │                                   │
│                          ├──────────────┤                                   │
│                          │ id (PK)      │                                   │
│                          │ username     │                                   │
│                          │ email        │                                   │
│                          │ password_h   │                                   │
│                          │ full_name    │                                   │
│                          │ is_active    │                                   │
│                          │ created_at   │                                   │
│                          │ updated_at   │                                   │
│                          │ last_login   │                                   │
│                          └────┬─────────┘                                   │
│                               │                                             │
│                    ┌──────────┼──────────┐                                  │
│                    │          │          │                                  │
│                    │          ▼          │                                  │
│                    │  ┌──────────────┐   │                                  │
│              ┌─────┤  │  AdminRole   │   │                                  │
│              │     │  ├──────────────┤   │                                  │
│              │     │  │ id (PK)      │   │                                  │
│              │     │  │ user_id (FK) ├──┘                                  │
│              │     │  │ role_id (FK) ├─────────────────────┐               │
│              │     │  │ assigned_at  │                     │               │
│              │     │  │ assigned_by  │                     │               │
│              │     │  └──────────────┘                     │               │
│              │     │                                       │               │
│              │     │  ┌──────────────────────┐         ┌───┴────────────┐  │
│              │     │  │ UserSuspension       │         │      Role      │  │
│              │     └─►│ ├──────────────────────┤         ├────────────────┤  │
│              │        │ id (PK)              │         │ id (PK)        │  │
│              │        │ user_id (FK)         │         │ name           │  │
│              │        │ suspended_by (FK)    │         │ display_name   │  │
│              │        │ suspension_type      │         │ description    │  │
│              │        │ reason               │         │ priority       │  │
│              │        │ description          │         │ inherited_from │──┐│
│              │        │ suspended_at         │         │ is_active      │ ││
│              │        │ suspended_until      │         │ created_at     │ ││
│              │        │ is_active            │         │ updated_at     │ ││
│              │        │ appeal_reason        │         └────┬───────────┘ ││
│              │        │ unsuspended_at       │              │             ││
│              │        └──────────────────────┘              │             ││
│              │                                              │             ││
│              │         ┌──────────────────────┐             │             ││
│              │         │ AdminAuditLog        │             │             ││
│              └────────►│ ├──────────────────────┤             │             ││
│                        │ id (PK)              │             │             ││
│                        │ admin_user_id (FK)   │             │             ││
│                        │ action               │             │             ││
│                        │ description          │             │             ││
│                        │ target_user_id (FK)  │             │             ││
│                        │ target_role_id (FK)  │◄────────────┴─────────────┘│
│                        │ ip_address           │             │              │
│                        │ user_agent           │             │              │
│                        │ changes (JSON)       │             │              │
│                        │ created_at           │             │              │
│                        │ status               │             │              │
│                        └──────────────────────┘             │              │
│                                                              │              │
│                   ┌────────────────────────────┐             │              │
│                   │ RolePermission             │◄────────────┘              │
│                   │ (Junction Table)           │                           │
│                   ├────────────────────────────┤                           │
│                   │ id (PK)                    │                           │
│                   │ role_id (FK) ──────────────┼──────────────┐            │
│                   │ permission_id (FK) ────────┼──┐           │            │
│                   │ granted_at                 │  │           │            │
│                   │ granted_by (FK) ───────────┼─►│           │            │
│                   │ revoked_at                 │  │           │            │
│                   └────────────────────────────┘  │           │            │
│                                                    │           │            │
│                    ┌──────────────────────────┐   │           │            │
│                    │ Permission               │◄──┘           │            │
│                    ├──────────────────────────┤               │            │
│                    │ id (PK)                  │               │            │
│                    │ name                     │               │            │
│                    │ module                   │               │            │
│                    │ action                   │               │            │
│                    │ description              │               │            │
│                    │ created_at               │               │            │
│                    │ updated_at               │               │            │
│                    └──────────────────────────┘               │            │
│                                                               │            │
│                    ┌──────────────────────────┐               │            │
│                    │ NotificationPreference   │◄──────────────┘            │
│                    ├──────────────────────────┤                            │
│                    │ id (PK)                  │                            │
│                    │ user_id (FK)             │                            │
│                    │ new_reports              │                            │
│                    │ pending_approvals        │                            │
│                    │ user_suspensions         │                            │
│                    │ role_changes             │                            │
│                    │ email_digest             │                            │
│                    │ digest_frequency         │                            │
│                    │ created_at               │                            │
│                    │ updated_at               │                            │
│                    └──────────────────────────┘                            │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ Related Models (Existing):                                           │  │
│  │ - BookApprovalStatus (Book model link)                               │  │
│  │ - ContentReport (User/Content moderation)                            │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 🗄️ Detailed Table Schemas

### 1. ROLE (Core RBAC Entity)

```sql
CREATE TABLE role (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    priority INT DEFAULT 5,
    -- Inheritance support
    inherited_from_id BIGINT REFERENCES role(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE,
    -- Audit fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by_id BIGINT REFERENCES user(id),
    
    -- Indexes for performance
    INDEX idx_name (name),
    INDEX idx_is_active (is_active),
    INDEX idx_inherited_from (inherited_from_id),
    INDEX idx_priority (priority)
);
```

**Key Features:**
- `inherited_from_id`: Supports role inheritance (e.g., Moderator inherits from Admin)
- `priority`: Hierarchical role ordering (higher = more powerful)
- `is_active`: Soft delete of roles (users can still view history)

### 2. PERMISSION (Granular Permission Entity)

```sql
CREATE TABLE permission (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    -- Naming: module:action format
    name VARCHAR(100) NOT NULL UNIQUE,
    module VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    description TEXT,
    -- Categorization
    category VARCHAR(50),
    is_system BOOLEAN DEFAULT FALSE,
    -- Audit fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_module_action (module, action),
    INDEX idx_name (name),
    UNIQUE KEY unique_module_action (module, action)
);
```

**Key Features:**
- `name`: Standardized format "module:action" (e.g., "users:create")
- `module`: Groups permissions by functional area
- `action`: Specific operation (create, read, update, delete, etc.)
- `is_system`: Flag for system-reserved permissions

### 3. ROLE_PERMISSION (Junction Table)

```sql
CREATE TABLE role_permission (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    role_id BIGINT NOT NULL REFERENCES role(id) ON DELETE CASCADE,
    permission_id BIGINT NOT NULL REFERENCES permission(id) ON DELETE CASCADE,
    -- Tracking who granted this permission
    granted_by_id BIGINT REFERENCES user(id),
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Support for permission revocation
    revoked_at TIMESTAMP NULL,
    revoked_by_id BIGINT REFERENCES user(id),
    
    -- Constraints and indexes
    UNIQUE KEY unique_role_permission (role_id, permission_id),
    INDEX idx_role_id (role_id),
    INDEX idx_permission_id (permission_id),
    INDEX idx_granted_at (granted_at)
);
```

**Key Features:**
- Many-to-many relationship between roles and permissions
- Tracks who granted/revoked permissions (audit trail)
- Soft delete via `revoked_at` (can see permission history)

### 4. ADMIN_ROLE (User-to-Role Assignment)

```sql
CREATE TABLE admin_role (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    role_id BIGINT NOT NULL REFERENCES role(id) ON DELETE RESTRICT,
    -- Audit fields
    assigned_by_id BIGINT REFERENCES user(id),
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Support for role revocation
    revoked_at TIMESTAMP NULL,
    revoked_by_id BIGINT REFERENCES user(id),
    -- Optional notes
    notes TEXT,
    
    -- Constraints and indexes
    UNIQUE KEY unique_user_role (user_id, role_id, revoked_at IS NULL),
    INDEX idx_user_id (user_id),
    INDEX idx_role_id (role_id),
    INDEX idx_assigned_at (assigned_at),
    INDEX idx_user_active_roles (user_id, revoked_at)
);
```

**Key Features:**
- Tracks user role assignments with history
- `revoked_at`: Soft delete (users can see when role was removed)
- `notes`: Context about why role was assigned
- Unique constraint ensures only one active role per user per role type

### 5. USER_SUSPENSION (User Suspension Tracking)

```sql
CREATE TABLE user_suspension (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    -- Suspension details
    suspension_type ENUM('temporary', 'permanent') DEFAULT 'temporary',
    reason ENUM(
        'harassment', 'spam', 'content_violation',
        'tos_violation', 'abuse', 'other'
    ) DEFAULT 'other',
    description TEXT,
    -- Timeline
    suspended_by_id BIGINT REFERENCES user(id),
    suspended_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    suspended_until TIMESTAMP NULL,
    -- Unsuspension
    unsuspended_at TIMESTAMP NULL,
    unsuspended_by_id BIGINT REFERENCES user(id),
    unsuspension_reason TEXT,
    -- Appeals
    appeal_reason TEXT,
    appeal_submitted_at TIMESTAMP NULL,
    
    -- Indexes
    INDEX idx_user_id (user_id),
    INDEX idx_suspended_at (suspended_at),
    INDEX idx_is_active (unsuspended_at),
    INDEX idx_user_active (user_id, unsuspended_at)
);
```

**Key Features:**
- Tracks all user suspensions with reasons
- Support for temporary and permanent suspensions
- Appeal workflow support
- Complete audit trail

### 6. ADMIN_AUDIT_LOG (Complete Audit Trail)

```sql
CREATE TABLE admin_audit_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    -- Who performed the action
    admin_user_id BIGINT NOT NULL REFERENCES user(id),
    -- What action was performed
    action VARCHAR(100) NOT NULL,
    description TEXT,
    -- Who/What was affected
    target_user_id BIGINT REFERENCES user(id),
    target_role_id BIGINT REFERENCES role(id),
    -- What changed (JSON for flexibility)
    changes JSON,
    -- Request details
    ip_address VARCHAR(45),
    user_agent TEXT,
    -- Outcome
    status ENUM('success', 'failure', 'pending') DEFAULT 'success',
    error_message TEXT,
    -- Timeline
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for queries
    INDEX idx_admin_user_id (admin_user_id),
    INDEX idx_action (action),
    INDEX idx_created_at (created_at),
    INDEX idx_target_user (target_user_id),
    INDEX idx_admin_action_date (admin_user_id, action, created_at),
    INDEX idx_created_at_desc (created_at DESC)
);
```

**Key Features:**
- Comprehensive audit trail of all admin actions
- `changes` JSON field stores before/after state
- `ip_address`: For security and compliance
- Indexed for efficient querying and reporting

### 7. NOTIFICATION_PREFERENCE (Admin Notification Settings)

```sql
CREATE TABLE notification_preference (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL UNIQUE REFERENCES user(id) ON DELETE CASCADE,
    -- Notification types
    new_reports BOOLEAN DEFAULT TRUE,
    pending_approvals BOOLEAN DEFAULT TRUE,
    user_suspensions BOOLEAN DEFAULT TRUE,
    role_assignments BOOLEAN DEFAULT TRUE,
    system_alerts BOOLEAN DEFAULT TRUE,
    -- Email digest settings
    email_digest ENUM('none', 'immediate', 'daily', 'weekly', 'monthly') DEFAULT 'daily',
    digest_time TIME DEFAULT '09:00:00',
    -- Audit fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_user_id (user_id)
);
```

---

## 🔗 Relationship Details

### Role Inheritance
```
Super Admin (role_id=1)
    ↓ inherited_from
Admin (role_id=2)
    ├─ Moderator (role_id=3)
    │   └─ Analytics (role_id=5) - read-only
    └─ Content Manager (role_id=4)
```

**Implementation Notes:**
- When checking permissions, recursively check inherited role's permissions
- Child roles inherit all parent permissions but can be restricted
- Circular inheritance prevented by application logic

### Permission Resolution
```
User has permissions through:
1. Direct role assignment (admin_role table)
2. Inherited role permissions (role.inherited_from)
3. All permission assignments (role_permission table)

Query:
SELECT DISTINCT p.* FROM permission p
JOIN role_permission rp ON p.id = rp.permission_id
JOIN admin_role ar ON rp.role_id = ar.role_id
JOIN role r ON ar.role_id = r.id
WHERE ar.user_id = ? 
  AND ar.revoked_at IS NULL 
  AND rp.revoked_at IS NULL
UNION
SELECT DISTINCT p.* FROM permission p
JOIN role_permission rp ON p.id = rp.permission_id
JOIN role r ON rp.role_id = r.id
WHERE r.id IN (SELECT inherited_from_id FROM role WHERE id IN (...))
  AND rp.revoked_at IS NULL
```

---

## 📈 Data Volume Considerations

```
Estimated Volumes (production scale):
- Users: 100,000+
- Roles: 20-50
- Permissions: 100-200
- Admin Users: 50-200
- Audit Logs: 100,000+ per month
- Active Sessions: 1,000+ concurrent

Storage Estimates:
- role: < 1 MB
- permission: < 5 MB
- role_permission: < 50 MB
- admin_role: < 100 MB
- admin_audit_log: 500 MB - 2 GB (monthly growth)
- Total: 1-3 GB (stable with archival)
```

---

## 🔑 Indexing Strategy

### Primary Indexes
1. **admin_audit_log.created_at_desc**: Critical for audit log queries
2. **admin_role.user_id**: For loading user permissions on login
3. **admin_role.role_id**: For viewing role assignments
4. **role_permission.role_id**: For permission matrix
5. **user_suspension.user_id**: For suspension check on user access

### Search Indexes
6. **admin_audit_log.admin_user_id, action, created_at**: Composite for admin activity
7. **user_suspension.suspended_at**: For suspension timeline queries

### Cleanup Indexes
8. **admin_audit_log.created_at**: For archive/retention policies
9. **admin_role.revoked_at**: For soft-deleted role tracking

---

## 🔄 Database Migration Path

### Phase 1: Base Tables (Day 1)
```sql
1. role
2. permission
3. role_permission
```

### Phase 2: User Tables (Day 2)
```sql
4. admin_role
5. user_suspension
```

### Phase 3: Audit (Day 3)
```sql
6. admin_audit_log
7. notification_preference
```

### Data Migration Script
```python
# Migrate existing admin status to new RBAC
for user in User.objects.filter(is_staff=True):
    role = Role.objects.get(name='admin') if user.is_superuser else Role.objects.get(name='moderator')
    AdminRole.objects.create(
        user=user,
        role=role,
        assigned_by_id=1  # system
    )
    
# Backfill audit logs for critical actions
# (This can be done asynchronously)
```

---

## 🛡️ Data Integrity Constraints

1. **No Orphaned Permissions**: Foreign keys prevent orphaned permission assignments
2. **No Circular Roles**: Application logic prevents inheritance cycles
3. **Audit Trail Immutability**: Audit logs are append-only
4. **Soft Deletes**: Historical data preserved via timestamp fields
5. **Transaction Consistency**: Multi-table operations use transactions

---

## 🔐 Security Considerations

1. **Principle of Least Privilege**: Only necessary permissions assigned
2. **Immutable Audit Trail**: No modification of audit logs (append-only)
3. **Permission Revocation**: Can be tracked and reversed
4. **Session-Based Permissions**: Permissions checked on each request
5. **IP Logging**: Tracks location of admin actions
6. **Rate Limiting**: Database query limits prevent abuse

---

*Data model designed for security, auditability, scalability, and compliance.*
