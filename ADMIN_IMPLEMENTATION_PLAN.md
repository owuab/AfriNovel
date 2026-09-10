# Admin Dashboard - Phased Implementation Plan & Timeline

## 📋 Implementation Overview

**Total Scope**: 14 major features, 144 acceptance criteria  
**Estimated Total Effort**: ~220 developer-hours  
**Recommended Team**: 2-3 developers + 1 QA  
**Duration**: ~12 weeks (3 months) for full implementation  

---

## 🎯 PHASE 0: FOUNDATION (Week 1-2) - 35 hours

### Objectives
- Create database schema (Permission model + migration)
- Set up development environment and tooling
- Establish coding standards and testing infrastructure
- Create feature branch workflow

### Tasks

#### 0.1 Create Permission Database Model
**Effort**: 4 hours  
**Developer**: Backend Lead  
**Dependencies**: None  

```python
# books/models.py
class Permission(models.Model):
    # Naming: module:action format (e.g., "users:create")
    name = models.CharField(max_length=100, unique=True)
    module = models.CharField(max_length=50)
    action = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, blank=True)
    is_system = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('module', 'action')
        indexes = [
            models.Index(fields=['module', 'action']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return self.name
```

**Acceptance Criteria**:
- [ ] Model created with all required fields
- [ ] Migration generated and tested
- [ ] Can create/read/update/delete permissions via ORM
- [ ] Unique constraints work correctly
- [ ] Indexes created successfully

#### 0.2 Create RolePermission Junction Table
**Effort**: 3 hours  
**Developer**: Backend Lead  
**Dependencies**: 0.1  

```python
# books/models.py
class RolePermission(models.Model):
    role = models.ForeignKey(AdminRole, on_delete=models.CASCADE, related_name='permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')
    granted_at = models.DateTimeField(auto_now_add=True)
    
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    
    class Meta:
        unique_together = ('role', 'permission')
        indexes = [
            models.Index(fields=['role_id']),
            models.Index(fields=['permission_id']),
            models.Index(fields=['granted_at']),
        ]
```

**Acceptance Criteria**:
- [ ] Junction table created
- [ ] Foreign keys link to Role and Permission
- [ ] Audit fields (granted_by, revoked_at) present
- [ ] Can assign/revoke permissions from roles
- [ ] Soft delete via revoked_at works

#### 0.3 Create Database Migration
**Effort**: 2 hours  
**Developer**: Backend Lead  
**Dependencies**: 0.1, 0.2  

```bash
python manage.py makemigrations
python manage.py migrate
```

**Acceptance Criteria**:
- [ ] Migration 0012_permission.py created
- [ ] Migration 0013_rolepermission.py created
- [ ] Both migrations apply without errors
- [ ] Rollback works successfully
- [ ] No data loss on rollback

#### 0.4 Seed Initial Permissions
**Effort**: 6 hours  
**Developer**: Backend Lead  
**Dependencies**: 0.3  

**Command**: `python manage.py seed_permissions`

```python
# books/management/commands/seed_permissions.py
PERMISSIONS = {
    'users': [
        ('create', 'Create new users'),
        ('read', 'View user information'),
        ('update', 'Edit user details'),
        ('delete', 'Delete users'),
        ('suspend', 'Suspend/unsuspend users'),
    ],
    'roles': [
        ('create', 'Create new roles'),
        ('read', 'View roles'),
        ('update', 'Edit roles'),
        ('delete', 'Delete roles'),
    ],
    'reports': [
        ('create', 'Create reports'),
        ('read', 'View reports'),
        ('resolve', 'Resolve/dismiss reports'),
    ],
    'books': [
        ('read', 'View books'),
        ('approve', 'Approve pending books'),
        ('reject', 'Reject books'),
        ('request_revision', 'Request revisions'),
    ],
    'audit': [
        ('read', 'View audit logs'),
        ('export', 'Export audit logs'),
    ],
    'settings': [
        ('read', 'View settings'),
        ('update', 'Modify settings'),
    ],
    'admin': [
        ('manage_admins', 'Manage admin users'),
        ('view_audit', 'View system audit logs'),
    ],
}
```

**Acceptance Criteria**:
- [ ] All 50+ permissions created
- [ ] Permissions properly named (module:action)
- [ ] All modules represented
- [ ] Can query permissions by module
- [ ] Bulk import completes in <5 seconds

#### 0.5 Assign Permissions to Existing Roles
**Effort**: 5 hours  
**Developer**: Backend Lead  
**Dependencies**: 0.4  

**Command**: `python manage.py assign_permissions`

```python
# Map existing roles to permissions
ROLE_PERMISSIONS = {
    'super_admin': ['*'],  # All permissions
    'admin': [
        'users:*',
        'roles:*',
        'reports:*',
        'books:*',
        'audit:*',
        'admin:*',
    ],
    'moderator': [
        'users:read',
        'users:suspend',
        'reports:read',
        'reports:resolve',
        'books:read',
        'books:approve',
        'books:reject',
        'audit:read',
    ],
}
```

**Acceptance Criteria**:
- [ ] All existing roles have permissions assigned
- [ ] Super Admin has all permissions
- [ ] Admin has expected permissions
- [ ] Moderator has expected permissions
- [ ] Permission checks work correctly

#### 0.6 Create Permission Checking Utilities
**Effort**: 8 hours  
**Developer**: Backend Lead  
**Dependencies**: 0.5  

```python
# books/services.py - Add new class
class PermissionService:
    @staticmethod
    def has_permission(user, permission):
        """Check if user has permission"""
        # Check direct role permissions
        # Check inherited role permissions
        # Cache result for performance
        pass
    
    @staticmethod
    def user_permissions(user):
        """Get all permissions for user"""
        pass
    
    @staticmethod
    def require_permission(permission):
        """Decorator for view functions"""
        pass
```

**Acceptance Criteria**:
- [ ] can_user() function works
- [ ] Inheritance checked correctly
- [ ] Permission caching works
- [ ] Performance <10ms per check
- [ ] Decorator works on views

#### 0.7 Testing Infrastructure Setup
**Effort**: 7 hours  
**Developer**: QA Lead  
**Dependencies**: None  

**Setup**:
- [ ] Pytest configuration with fixtures
- [ ] Factory Boy models for test data
- [ ] Selenium for E2E testing
- [ ] Code coverage reporting (Target: 80%+)
- [ ] CI/CD pipeline for tests
- [ ] Mock external services

**Acceptance Criteria**:
- [ ] Tests can run locally: `pytest`
- [ ] Tests run in CI/CD pipeline
- [ ] Code coverage report generated
- [ ] E2E tests can execute

---

## 🎯 PHASE 1: CORE RBAC (Week 3-5) - 48 hours

### Objectives
- Implement permission matrix visualization
- Build role editor interface
- Create user role management endpoints
- Implement permission assignment logic

### Tasks

#### 1.1 Build Permission Matrix View
**Effort**: 12 hours  
**Developer**: Frontend Lead + Backend  
**Dependencies**: Phase 0 complete  

**Deliverables**:
- Django view: `AdminDashboardView.permission_matrix()`
- Template: `admin/permissions/matrix.html`
- JavaScript: `admin/js/permission-matrix.js`
- Styling: `admin/css/permission-matrix.css`

**Acceptance Criteria**:
- [ ] Matrix displays all roles as columns
- [ ] Matrix displays all permissions as rows
- [ ] Shows ✓ for granted, ✗ for denied
- [ ] Can filter by role/module
- [ ] Can search permissions
- [ ] Loads in <2 seconds
- [ ] Mobile responsive
- [ ] Edit button works for each cell

#### 1.2 Build Role Editor Interface
**Effort**: 14 hours  
**Developer**: Frontend Lead  
**Dependencies**: 1.1, Phase 0  

**Deliverables**:
- Django view: `RoleDetailView`, `RoleCreateView`
- Template: `admin/roles/editor.html`
- JavaScript: `admin/js/role-editor.js`
- Forms: `AdminRoleForm`, `RolePermissionFormSet`

**Acceptance Criteria**:
- [ ] Create role form works
- [ ] Edit role form works
- [ ] Permission checkboxes display
- [ ] Can search/filter permissions
- [ ] Audit history visible
- [ ] Undo/redo buttons work
- [ ] Validation prevents invalid states
- [ ] Save completes in <1 second

#### 1.3 Implement Permission Assignment API
**Effort**: 8 hours  
**Developer**: Backend  
**Dependencies**: Phase 0  

**Endpoints**:
- `POST /admin/api/roles/{role_id}/permissions` - Add permission
- `DELETE /admin/api/roles/{role_id}/permissions/{perm_id}` - Remove permission
- `PUT /admin/api/roles/{role_id}/permissions` - Bulk update

**Acceptance Criteria**:
- [ ] API endpoints created
- [ ] Permission checks work
- [ ] Audit logging works
- [ ] Error handling correct
- [ ] Rate limiting applied

#### 1.4 Build User Role Assignment Interface
**Effort**: 10 hours  
**Developer**: Frontend  
**Dependencies**: 1.2  

**Deliverables**:
- User detail modal with role assignment
- Bulk role assignment wizard
- Role history display

**Acceptance Criteria**:
- [ ] Can assign role to single user
- [ ] Bulk wizard works (Step 1-3)
- [ ] Confirmation required
- [ ] Users notified of changes
- [ ] Audit logged

#### 1.5 Implement Role Inheritance
**Effort**: 4 hours  
**Developer**: Backend  
**Dependencies**: Phase 0, 1.3  

```python
# Recursive permission resolution
def get_user_permissions(user):
    permissions = set()
    for admin_role in user.admin_role.filter(revoked_at__isnull=True):
        permissions.update(
            admin_role.role.permissions.filter(revoked_at__isnull=True).values_list('permission_id', flat=True)
        )
        # Add inherited permissions
        permissions.update(get_role_inherited_permissions(admin_role.role))
    return permissions
```

**Acceptance Criteria**:
- [ ] Child roles inherit parent permissions
- [ ] Inheritance chain followed correctly
- [ ] Performance acceptable
- [ ] No infinite loops
- [ ] Tests pass

---

## 🎯 PHASE 2: NAVIGATION & DISCOVERY (Week 6-8) - 42 hours

### Objectives
- Implement global search with Cmd+K
- Create breadcrumb navigation system
- Build keyboard shortcuts system
- Implement back/forward navigation

### Tasks

#### 2.1 Build Global Search API
**Effort**: 10 hours  
**Developer**: Backend + Frontend  
**Dependencies**: Phase 0  

**Endpoints**:
- `GET /admin/api/search?q=john&type=users,books,reports`
- `GET /admin/api/search/suggestions?q=john`

**Search Index**:
- Users (by username, email, full_name)
- Books (by title, author, ISBN)
- Reports (by description, report type)

**Acceptance Criteria**:
- [ ] Search returns results <500ms
- [ ] Results grouped by type
- [ ] Suggestions work
- [ ] Advanced filters work
- [ ] Search history available
- [ ] Frecency ranking works

#### 2.2 Build Command Palette
**Effort**: 12 hours  
**Developer**: Frontend  
**Dependencies**: 2.1  

**Features**:
- Cmd+K opens modal
- Real-time search as you type
- Quick actions section
- Help/shortcuts section
- Keyboard navigation

**Acceptance Criteria**:
- [ ] Opens with Cmd+K / Ctrl+K
- [ ] Closes with Esc
- [ ] Arrow keys navigate
- [ ] Enter executes
- [ ] Mobile keyboard works
- [ ] Focus trap works

#### 2.3 Implement Breadcrumb System
**Effort**: 8 hours  
**Developer**: Frontend  
**Dependencies**: None  

**Components**:
- `BreadcrumbComponent`
- `breadcrumb_middleware` for Django
- CSS styling for mobile

**Acceptance Criteria**:
- [ ] Shows on every page
- [ ] Clickable navigation
- [ ] Current page highlighted
- [ ] Mobile-optimized
- [ ] Works with pagination

#### 2.4 Keyboard Shortcuts System
**Effort**: 8 hours  
**Developer**: Frontend  
**Dependencies**: 2.2  

**Shortcuts**:
- Cmd+K: Search
- Cmd+?: Help
- Cmd+N: New
- Cmd+S: Save
- Cmd+Z: Undo
- Cmd+Y: Redo
- Cmd+F: Find
- Esc: Close
- Arrow keys: Navigate

**Acceptance Criteria**:
- [ ] All shortcuts work
- [ ] Help shows shortcuts
- [ ] Works with Ctrl (Windows)
- [ ] No conflicts with browser shortcuts
- [ ] Can be customized

#### 2.5 Navigation History Stack
**Effort**: 4 hours  
**Developer**: Frontend  
**Dependencies**: 2.3  

**Features**:
- Back/forward buttons in toolbar
- History preserved in session
- Last 20 pages tracked
- Deep linking works

**Acceptance Criteria**:
- [ ] Back button works
- [ ] Forward button appears when needed
- [ ] History survives page refresh
- [ ] URLs shareable
- [ ] No circular navigation

---

## 🎯 PHASE 3: UI & UX POLISH (Week 9-10) - 38 hours

### Objectives
- Build dashboard with real-time updates
- Implement bulk operations wizard
- Create compliance/audit features
- Optimize for mobile

### Tasks

#### 3.1 Dashboard Statistics & Real-time Updates
**Effort**: 12 hours  
**Developer**: Frontend + Backend  
**Dependencies**: Phase 0  

**Features**:
- Metrics cards (Users, Active, Suspended, Pending, Reports, Uptime)
- Real-time updates via WebSocket
- Activity feed
- Quick actions

**Acceptance Criteria**:
- [ ] All metrics display correctly
- [ ] Real-time updates <5 seconds
- [ ] Mobile layout responsive
- [ ] Customizable cards
- [ ] Performance: <2 seconds load

#### 3.2 Bulk Operations Wizard
**Effort**: 14 hours  
**Developer**: Frontend  
**Dependencies**: 1.4, Phase 0  

**Steps**:
1. Select users with checkboxes
2. Choose action and configure
3. Review and confirm

**Features**:
- Multi-step wizard
- Progress tracking
- Batch operations
- Notification to affected users

**Acceptance Criteria**:
- [ ] All 3 steps work
- [ ] Progress bar shows
- [ ] Can cancel operation
- [ ] Results show success/failure
- [ ] Audit logged
- [ ] Batch ID generated

#### 3.3 Audit Log Display & Export
**Effort**: 10 hours  
**Developer**: Frontend + Backend  
**Dependencies**: Phase 0  

**Features**:
- Paginated audit log list
- Filtering by action/user/date
- Expandable details
- CSV/PDF export
- Compliance report generation

**Acceptance Criteria**:
- [ ] List displays correctly
- [ ] Filters work
- [ ] Export formats correct
- [ ] Performance: <1 second for 1M records
- [ ] Report generation works

#### 3.4 Mobile Optimization
**Effort**: 2 hours  
**Developer**: Frontend  
**Dependencies**: All above  

**Changes**:
- Responsive layout adjustments
- Touch target sizes >44px
- Font sizes >16px
- No horizontal scrolling

**Acceptance Criteria**:
- [ ] Works on iPhone 12 (390px)
- [ ] Works on Samsung Galaxy (480px)
- [ ] Works on iPad (768px)
- [ ] No horizontal scrolling
- [ ] Performance acceptable on 4G

---

## 🎯 PHASE 4: COMPLIANCE & SECURITY (Week 11) - 32 hours

### Objectives
- Implement security features
- Ensure compliance standards
- Add advanced audit capabilities
- Performance optimization

### Tasks

#### 4.1 Access Control & Permissions Middleware
**Effort**: 8 hours  
**Developer**: Backend  
**Dependencies**: Phase 0, 1.5  

**Features**:
- Permission checking on every request
- Role-based access control
- Session validation
- IP whitelisting (optional)

**Acceptance Criteria**:
- [ ] Permissions enforced
- [ ] Sessions validated
- [ ] Unauthorized access blocked (403)
- [ ] Rate limiting applied
- [ ] Performance <10ms per check

#### 4.2 Security Hardening
**Effort**: 8 hours  
**Developer**: Backend  
**Dependencies**: None  

**Features**:
- CSRF protection
- SQL injection prevention
- XSS protection
- HTTPS enforcement
- Security headers

**Acceptance Criteria**:
- [ ] No CSRF vulnerabilities
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] Security headers present
- [ ] Passes OWASP Top 10 check

#### 4.3 Compliance Features
**Effort**: 8 hours  
**Developer**: Backend + Frontend  
**Dependencies**: Phase 0  

**Features**:
- GDPR: Data export
- CCPA: Deletion/opt-out
- SOC 2: Audit trail
- Session timeout (30 min)
- Password policy

**Acceptance Criteria**:
- [ ] Data export works
- [ ] Session timeout enforced
- [ ] Audit trail complete
- [ ] Compliance report generates
- [ ] No data breaches

#### 4.4 Performance Optimization
**Effort**: 8 hours  
**Developer**: Backend + Frontend  
**Dependencies**: All above  

**Optimizations**:
- Database query optimization
- Caching strategy (Redis)
- Frontend minification
- Image optimization
- CDN for static assets

**Acceptance Criteria**:
- [ ] Dashboard <2 seconds
- [ ] User list <1 second
- [ ] Queries use indexes
- [ ] Cache hit rate >80%
- [ ] Core Web Vitals pass

---

## 🎯 PHASE 5: TESTING & QA (Week 12) - 25 hours

### Objectives
- Complete test coverage
- E2E testing
- Performance testing
- Security testing

### Tasks

#### 5.1 Unit Tests
**Effort**: 8 hours  
**Developer**: Backend  
**Dependencies**: All above  

**Coverage**:
- Permission model tests
- Role management tests
- User assignment tests
- Audit logging tests

**Acceptance Criteria**:
- [ ] >80% code coverage
- [ ] All tests passing
- [ ] Mocking external services
- [ ] Edge cases covered

#### 5.2 Integration Tests
**Effort**: 8 hours  
**Developer**: Backend + Frontend  
**Dependencies**: All above  

**Coverage**:
- API endpoint tests
- Database transaction tests
- Permission checks
- Audit trail verification

**Acceptance Criteria**:
- [ ] All endpoints tested
- [ ] Happy path works
- [ ] Error paths work
- [ ] Permission checks verified

#### 5.3 E2E Tests (Selenium/Playwright)
**Effort**: 5 hours  
**Developer**: QA  
**Dependencies**: All above  

**Scenarios**:
1. Login → Create role → Assign users
2. Search for user → View details → Suspend
3. Bulk operations: Assign 10 users to role
4. Audit log: View and export

**Acceptance Criteria**:
- [ ] All 4 scenarios pass
- [ ] Tests run reliably
- [ ] No flaky tests
- [ ] Performance acceptable

#### 5.4 Security Testing
**Effort**: 4 hours  
**Developer**: Backend  
**Dependencies**: All above  

**Tests**:
- OWASP ZAP scan
- SQL injection attempts
- XSS payload testing
- Permission boundary testing
- Session hijacking resistance

**Acceptance Criteria**:
- [ ] No critical vulnerabilities
- [ ] No high vulnerabilities
- [ ] Medium vulnerabilities documented
- [ ] Remediation plan in place

---

## 📊 Timeline Summary

| Phase | Duration | Effort | Focus |
|-------|----------|--------|-------|
| 0: Foundation | 2 weeks | 35 hrs | Database, testing setup |
| 1: RBAC | 3 weeks | 48 hrs | Permissions, roles, users |
| 2: Discovery | 3 weeks | 42 hrs | Search, navigation, shortcuts |
| 3: UX Polish | 2 weeks | 38 hrs | Dashboard, bulk ops, mobile |
| 4: Compliance | 1 week | 32 hrs | Security, compliance, perf |
| 5: QA | 1 week | 25 hrs | Testing, verification |
| **Total** | **12 weeks** | **220 hrs** | **Complete system** |

---

## 👥 Team Allocation

**Backend Developer (100% - 220 hours)**
- Weeks 1-2: Database setup, permission logic
- Weeks 3-5: API endpoints, role management
- Weeks 6-8: Search API, breadcrumbs backend
- Weeks 9-10: Dashboard API, bulk operations
- Weeks 11-12: Security, testing

**Frontend Developer (100% - 220 hours)**
- Weeks 1-2: Setup, testing infrastructure
- Weeks 3-5: Permission matrix, role editor UI
- Weeks 6-8: Command palette, keyboard shortcuts
- Weeks 9-10: Dashboard UI, bulk wizard, mobile
- Weeks 11-12: E2E tests, final polish

**QA/Testing (50% - 110 hours)**
- Weeks 1-2: Test infrastructure setup
- Weeks 3-7: Concurrent testing with development
- Weeks 11-12: Full QA, security testing, sign-off

**Product/UX (10% - 22 hours)**
- All phases: Review acceptance criteria
- Weeks 6-10: UX review and polish
- Week 12: Final sign-off

---

## 🚀 Go-Live Criteria

**Code Quality**:
- [ ] >80% test coverage
- [ ] No critical bugs
- [ ] Code review complete
- [ ] Performance benchmarks met

**Functionality**:
- [ ] All 14 features complete
- [ ] All 144 acceptance criteria met
- [ ] E2E tests passing
- [ ] Load testing successful

**Compliance**:
- [ ] Security audit passed
- [ ] WCAG 2.1 AA compliance verified
- [ ] GDPR/CCPA review complete
- [ ] Documentation complete

**Operations**:
- [ ] Deployment runbook ready
- [ ] Rollback plan documented
- [ ] Monitoring/alerts configured
- [ ] Team trained

---

## 📋 Dependencies & Risks

### Critical Path Dependencies
1. Phase 0 (Foundation) must complete before Phase 1
2. API endpoints needed by frontend (sequential)
3. Permission model prerequisite for all auth

### Potential Risks & Mitigation
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| Scope creep | +4 weeks | Medium | Strict requirement management |
| Performance issues | Can't launch | Medium | Early load testing (Phase 4) |
| Security vulnerabilities | Launch delay | Low | Security review (Week 11) |
| Team member unavailable | +2 weeks | Medium | Pair programming, documentation |
| Browser compatibility issues | Launch delay | Low | Regular browser testing |

---

## 📅 Weekly Milestones

- **Week 1**: Database models, initial tests working
- **Week 2**: Permission model complete, CI/CD pipeline working
- **Week 3**: Permission matrix visible, role editor functional
- **Week 4**: User role assignment working, bulk operations started
- **Week 5**: All RBAC features complete, 80% of AC criteria met
- **Week 6**: Global search working, breadcrumbs visible
- **Week 7**: Keyboard shortcuts working, navigation history stable
- **Week 8**: Command palette complete, 95% of navigation AC criteria met
- **Week 9**: Dashboard with real-time updates, metrics showing
- **Week 10**: Bulk operations wizard complete, mobile optimization done
- **Week 11**: Security testing, compliance checks, performance optimization
- **Week 12**: QA testing, bug fixes, final deployment preparation

---

## 💾 Deliverables Checklist

**Week 2 (Phase 0 End)**:
- [ ] Permission database model (code)
- [ ] Initial migrations
- [ ] Permission seeding script
- [ ] Unit tests for permissions (>80% coverage)

**Week 5 (Phase 1 End)**:
- [ ] Permission matrix view + tests
- [ ] Role editor UI + tests
- [ ] User role assignment + tests
- [ ] API endpoints documented
- [ ] Design system updated

**Week 8 (Phase 2 End)**:
- [ ] Global search API + UI
- [ ] Command palette working
- [ ] Breadcrumbs on all pages
- [ ] Keyboard shortcuts system
- [ ] Navigation history working

**Week 10 (Phase 3 End)**:
- [ ] Dashboard with statistics
- [ ] Bulk operations wizard
- [ ] Audit log viewer
- [ ] Mobile-optimized interface
- [ ] Performance benchmarks met

**Week 11 (Phase 4 End)**:
- [ ] Security audit report
- [ ] Compliance documentation
- [ ] WCAG compliance verification
- [ ] Performance optimization complete

**Week 12 (Phase 5 End)**:
- [ ] 100% test coverage target met
- [ ] All acceptance criteria verified
- [ ] Documentation complete
- [ ] Team trained
- [ ] Ready for production deployment

---

*Implementation plan designed for steady progress with quality gates at each phase.*
