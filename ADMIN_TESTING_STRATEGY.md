# Admin Dashboard - Testing Strategy & Quality Assurance Plan

## 📊 Testing Overview

**Total Test Scope**: 
- Unit Tests: 120+ test cases
- Integration Tests: 80+ test cases
- E2E Tests: 25+ scenarios
- Performance Tests: 15+ benchmarks
- Security Tests: 20+ vulnerability checks

**Target Code Coverage**: 85%+ overall, 95%+ for critical paths

**Testing Timeline**: Concurrent with development (not sequential)

---

## 🧪 UNIT TESTING STRATEGY

### Test Framework
- **Framework**: pytest + pytest-django
- **Mocking**: unittest.mock, responses (HTTP mocking)
- **Fixtures**: Factory Boy for test data
- **Assertions**: pytest assertions

### Test Categories

#### 1. Permission Model Tests (15 tests)

```python
# tests/unit/test_permission_model.py

class TestPermissionModel:
    def test_permission_creation(self):
        """Create permission with valid data"""
        perm = Permission.objects.create(
            name="users:create",
            module="users",
            action="create"
        )
        assert perm.id is not None
        assert str(perm) == "users:create"
    
    def test_permission_uniqueness(self):
        """Duplicate permission names rejected"""
        Permission.objects.create(name="users:create", module="users", action="create")
        with pytest.raises(IntegrityError):
            Permission.objects.create(name="users:create", module="users", action="create")
    
    def test_permission_module_action_index(self):
        """Composite index on module + action"""
        perms = Permission.objects.filter(module="users", action="create")
        # Verify query uses index (check query plan)
        assert len(perms) == 1
```

**Acceptance Criteria**:
- [ ] All permission CRUD operations tested
- [ ] Constraints enforced (unique, required fields)
- [ ] Queries use indexes (performance verified)
- [ ] Edge cases covered (empty strings, special chars, etc.)

#### 2. Role Model Tests (20 tests)

```python
# tests/unit/test_role_model.py

class TestRoleModel:
    def test_role_creation(self):
        """Create role with hierarchy"""
        parent = AdminRole.objects.create(name="admin", display_name="Admin")
        child = AdminRole.objects.create(
            name="moderator",
            display_name="Moderator",
            inherited_from=parent
        )
        assert child.inherited_from_id == parent.id
    
    def test_role_permission_assignment(self):
        """Assign permissions to role"""
        role = AdminRole.objects.create(name="moderator")
        perm = Permission.objects.create(name="reports:read", module="reports", action="read")
        
        rp = RolePermission.objects.create(role=role, permission=perm)
        assert rp.role_id == role.id
        assert rp.permission_id == perm.id
    
    def test_role_permission_revocation(self):
        """Revoke permission from role"""
        role = AdminRole.objects.create(name="moderator")
        perm = Permission.objects.create(name="reports:delete", module="reports", action="delete")
        
        rp = RolePermission.objects.create(role=role, permission=perm)
        rp.revoked_at = timezone.now()
        rp.revoked_by = User.objects.first()
        rp.save()
        
        # Check soft delete
        assert RolePermission.objects.filter(
            role=role, 
            permission=perm, 
            revoked_at__isnull=True
        ).count() == 0
```

**Acceptance Criteria**:
- [ ] Role creation with/without inheritance
- [ ] Permission assignment/revocation
- [ ] Soft delete via revoked_at
- [ ] Circular inheritance prevented
- [ ] Queries optimized with indexes

#### 3. Permission Service Tests (25 tests)

```python
# tests/unit/test_permission_service.py

class TestPermissionService:
    def test_user_has_permission_direct(self):
        """User has permission directly assigned"""
        user = UserFactory()
        role = AdminRole.objects.create(name="moderator")
        admin_role = admin_role = AdminRole.objects.create(user=user, role=role)
        
        perm = Permission.objects.create(name="users:suspend", module="users", action="suspend")
        RolePermission.objects.create(role=role, permission=perm)
        
        assert PermissionService.has_permission(user, "users:suspend") is True
    
    def test_user_has_permission_inherited(self):
        """User has permission through inherited role"""
        user = UserFactory()
        
        # Create inheritance chain: admin -> moderator
        admin_role_obj = AdminRole.objects.create(name="admin")
        mod_role = AdminRole.objects.create(name="moderator", inherited_from=admin_role_obj)
        
        # Assign moderator to user
        admin_role = admin_role = AdminRole.objects.create(user=user, role=mod_role)
        
        # Assign permission to parent (admin)
        perm = Permission.objects.create(name="reports:read", module="reports", action="read")
        RolePermission.objects.create(role=admin_role_obj, permission=perm)
        
        # Check if user has inherited permission
        assert PermissionService.has_permission(user, "reports:read") is True
    
    def test_user_lacks_permission(self):
        """User does not have permission"""
        user = UserFactory()
        role = AdminRole.objects.create(name="contributor")
        admin_role = admin_role = AdminRole.objects.create(user=user, role=role)
        
        # Don't assign any permissions
        
        assert PermissionService.has_permission(user, "admin:manage") is False
    
    def test_permission_cache_performance(self):
        """Permission checking uses cache for performance"""
        user = UserFactory()
        perm_name = "users:read"
        
        # First call: misses cache, fetches from DB
        start = time.time()
        result1 = PermissionService.has_permission(user, perm_name)
        time1 = time.time() - start
        
        # Second call: hits cache
        start = time.time()
        result2 = PermissionService.has_permission(user, perm_name)
        time2 = time.time() - start
        
        assert result1 == result2
        assert time2 < time1  # Cache hit faster
        assert time2 < 1e-3  # Cache hit <1ms
```

**Acceptance Criteria**:
- [ ] Direct permission checks work
- [ ] Inherited permission checks work
- [ ] Negative checks work (no permission)
- [ ] Permission caching improves performance
- [ ] All edge cases covered

#### 4. Audit Logging Tests (15 tests)

```python
# tests/unit/test_audit_logging.py

class TestAuditLogging:
    def test_audit_log_user_suspended(self):
        """Audit log records user suspension"""
        admin = UserFactory(is_staff=True)
        target_user = UserFactory()
        
        # Perform action
        suspension = UserSuspension.objects.create(
            user=target_user,
            suspended_by=admin,
            reason="harassment"
        )
        
        # Verify audit log created
        audit_log = AdminAuditLog.objects.get(
            action="user_suspended",
            target_user=target_user
        )
        
        assert audit_log.admin_user == admin
        assert audit_log.status == "success"
        assert audit_log.changes["reason"] == "harassment"
    
    def test_audit_log_immutability(self):
        """Audit logs cannot be modified (append-only)"""
        log = AdminAuditLog.objects.create(
            admin_user=UserFactory(is_staff=True),
            action="test_action"
        )
        
        # Try to modify
        log.description = "Modified"
        
        with pytest.raises(PermissionError):
            log.save()
```

**Acceptance Criteria**:
- [ ] Actions logged automatically
- [ ] Audit logs include: who, what, when, where (IP)
- [ ] Changes captured as JSON
- [ ] Immutability enforced
- [ ] No performance impact

### Performance Benchmarks (Unit)

```python
# tests/unit/test_performance.py

class TestPerformance:
    @pytest.mark.benchmark
    def test_permission_check_performance(self, benchmark):
        """Permission check completes in <10ms"""
        user = UserFactory()
        result = benchmark(PermissionService.has_permission, user, "users:read")
        assert result is not None
        # Benchmark plugin will verify <10ms
    
    @pytest.mark.benchmark
    def test_user_permissions_load_performance(self, benchmark):
        """Loading all user permissions <50ms"""
        user = UserFactory()
        result = benchmark(PermissionService.user_permissions, user)
        assert len(result) > 0
```

---

## 🔌 INTEGRATION TESTING STRATEGY

### Test Scenarios

#### 1. API Endpoint Tests (30 tests)

```python
# tests/integration/test_admin_api.py

class TestUserManagementAPI:
    def test_list_users_endpoint(self, admin_user, client):
        """GET /admin/api/users returns list"""
        client.force_login(admin_user)
        response = client.get('/admin/api/users?page=1&limit=50')
        
        assert response.status_code == 200
        data = response.json()
        assert 'users' in data
        assert 'pagination' in data
        assert len(data['users']) <= 50
    
    def test_list_users_permission_check(self, moderator_user, client):
        """Non-admin user cannot list users"""
        client.force_login(moderator_user)
        response = client.get('/admin/api/users')
        
        assert response.status_code == 403
        assert response.json()['error']['code'] == 'INSUFFICIENT_PERMISSIONS'
    
    def test_suspend_user_endpoint(self, admin_user, target_user, client):
        """PUT /admin/api/users/{id}/suspend"""
        client.force_login(admin_user)
        
        response = client.put(f'/admin/api/users/{target_user.id}/suspend', {
            'reason': 'harassment',
            'type': 'temporary',
            'duration_days': 7
        }, content_type='application/json')
        
        assert response.status_code == 200
        
        # Verify suspension in DB
        suspension = UserSuspension.objects.get(user=target_user)
        assert suspension.reason == "harassment"
        
        # Verify audit logged
        audit = AdminAuditLog.objects.get(
            action="user_suspended",
            target_user=target_user
        )
        assert audit.admin_user == admin_user
```

**Acceptance Criteria**:
- [ ] All CRUD endpoints tested
- [ ] Permission checks enforced
- [ ] Response formats correct
- [ ] Error handling works
- [ ] Status codes correct

#### 2. Database Transaction Tests (15 tests)

```python
# tests/integration/test_transactions.py

class TestTransactions:
    def test_bulk_assign_atomicity(self, admin_user):
        """Bulk role assignment all-or-nothing"""
        users = [UserFactory() for _ in range(5)]
        role = AdminRole.objects.create(name="moderator")
        
        # Simulate failure on user 3
        with pytest.raises(Exception):
            with transaction.atomic():
                for i, user in enumerate(users):
                    if i == 3:
                        raise Exception("Simulated failure")
                    AdminRole.objects.create(user=user, role=role)
        
        # Check: no users assigned (rollback)
        assert AdminRole.objects.filter(role=role).count() == 0
```

**Acceptance Criteria**:
- [ ] Multi-table operations atomic
- [ ] Rollback works on failure
- [ ] No partial writes
- [ ] Performance acceptable

#### 3. Permission Check Integration (20 tests)

```python
# tests/integration/test_permission_integration.py

class TestPermissionIntegration:
    def test_permission_check_in_view(self, admin_user, client):
        """Permission decorator enforces access in views"""
        client.force_login(admin_user)
        
        # With permission
        response = client.get('/admin-panel/users/')
        assert response.status_code == 200
        
        # Remove permission
        admin_user.admin_role.filter(role__name="admin").update(revoked_at=timezone.now())
        
        # Without permission
        response = client.get('/admin-panel/users/')
        assert response.status_code == 403
    
    def test_permission_check_in_api(self, admin_user, client):
        """API endpoints enforce permissions"""
        client.force_login(admin_user)
        
        # Moderator trying to delete user (no permission)
        mod_user = UserFactory()
        mod_role = AdminRole.objects.create(name="moderator")
        AdminRole.objects.create(user=mod_user, role=mod_role)
        
        client.force_login(mod_user)
        response = client.delete(f'/admin/api/users/{admin_user.id}/')
        assert response.status_code == 403
```

**Acceptance Criteria**:
- [ ] Permission checks in all views
- [ ] Permission checks in all APIs
- [ ] Inheritance respected
- [ ] Performance acceptable

---

## 🌐 END-TO-END TESTING STRATEGY

### E2E Test Framework
- **Framework**: Selenium + pytest
- **Browser**: Chrome (headless)
- **Waits**: Implicit (10s), Explicit where needed
- **Screenshots**: On failure

### Test Scenarios

#### Scenario 1: Create Role & Assign Users

```python
# tests/e2e/test_role_creation.py

class TestRoleCreation:
    @pytest.mark.e2e
    def test_create_moderator_role_and_assign_users(self, selenium, live_server):
        """Create Moderator role and assign 5 users"""
        
        # 1. Login as admin
        selenium.get(f"{live_server.url}/admin-panel/login/")
        username_field = selenium.find_element(By.ID, "id_username")
        password_field = selenium.find_element(By.ID, "id_password")
        username_field.send_keys("admin")
        password_field.send_keys("admin_pass")
        selenium.find_element(By.ID, "login_button").click()
        
        # Wait for redirect
        WebDriverWait(selenium, 10).until(
            lambda d: d.current_url.endswith("/admin-panel/dashboard/")
        )
        
        # 2. Navigate to Roles
        selenium.get(f"{live_server.url}/admin-panel/roles/")
        
        # 3. Create new role
        selenium.find_element(By.ID, "btn_create_role").click()
        
        # 4. Fill form
        name_field = selenium.find_element(By.ID, "id_name")
        name_field.send_keys("moderator")
        
        display_name = selenium.find_element(By.ID, "id_display_name")
        display_name.send_keys("Moderator")
        
        # 5. Select permissions
        perms = ["reports:read", "reports:write", "users:suspend"]
        for perm in perms:
            selenium.find_element(By.ID, f"perm_{perm}").click()
        
        # 6. Save role
        selenium.find_element(By.ID, "btn_save").click()
        
        # 7. Verify success
        WebDriverWait(selenium, 10).until(
            lambda d: "Role created successfully" in d.page_source
        )
        
        # 8. Assign users
        selenium.find_element(By.ID, "btn_add_users").click()
        
        # Select 5 users
        users_list = selenium.find_elements(By.NAME, "user_checkbox")[:5]
        for user_cb in users_list:
            user_cb.click()
        
        # 9. Confirm assignment
        selenium.find_element(By.ID, "btn_next").click()
        selenium.find_element(By.ID, "btn_confirm").click()
        
        # Wait for completion
        WebDriverWait(selenium, 10).until(
            lambda d: "5 users assigned" in d.page_source
        )
```

**Acceptance Criteria**:
- [ ] All steps execute without error
- [ ] Role created in database
- [ ] Users assigned to role
- [ ] Audit logs created
- [ ] Success message shown

#### Scenario 2: Bulk Suspend Users

```python
# tests/e2e/test_bulk_operations.py

class TestBulkOperations:
    @pytest.mark.e2e
    def test_bulk_suspend_workflow(self, selenium, live_server):
        """Bulk suspend 3 users via wizard"""
        
        # 1. Login and navigate
        # ... (login code as above)
        
        # 2. Go to Users
        selenium.get(f"{live_server.url}/admin-panel/users/")
        
        # 3. Click Bulk Operations
        selenium.find_element(By.ID, "btn_bulk_operations").click()
        
        # 4. Step 1: Select users
        user_checkboxes = selenium.find_elements(By.NAME, "user_id")[:3]
        for cb in user_checkboxes:
            cb.click()
        
        selenium.find_element(By.ID, "btn_next").click()
        
        # 5. Step 2: Choose action
        action_select = selenium.find_element(By.ID, "id_action")
        action_select.send_keys("suspend")
        
        reason_select = selenium.find_element(By.ID, "id_reason")
        reason_select.send_keys("harassment")
        
        selenium.find_element(By.ID, "btn_next").click()
        
        # 6. Step 3: Review and confirm
        selenium.find_element(By.ID, "confirm_checkbox").click()
        selenium.find_element(By.ID, "btn_execute").click()
        
        # 7. Wait for completion
        WebDriverWait(selenium, 10).until(
            lambda d: "3 users suspended" in d.page_source
        )
```

**Acceptance Criteria**:
- [ ] Wizard completes successfully
- [ ] Users suspended in database
- [ ] Notifications sent
- [ ] Audit trail created

### Screenshot on Failure

```python
def pytest_runtest_makereport(item, call):
    if call.excinfo is not None:
        selenium = item.funcargs.get('selenium')
        if selenium:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            selenium.save_screenshot(f"screenshots/{item.name}_{timestamp}.png")
```

---

## 🔒 SECURITY TESTING STRATEGY

### Vulnerability Scanning

#### 1. OWASP Top 10 Tests (20 tests)

```python
# tests/security/test_owasp_top10.py

class TestOWASPTopTen:
    def test_sql_injection_user_list(self, admin_user, client):
        """SQL injection in user search blocked"""
        client.force_login(admin_user)
        
        # Attempt SQL injection
        response = client.get('/admin/api/users?search=" OR "1"="1')
        
        assert response.status_code == 200
        # Response should be safe, no SQL error
        assert "mysql_error" not in response.content.decode()
        assert "sqlite3.OperationalError" not in response.content.decode()
    
    def test_xss_in_role_description(self, admin_user, client):
        """XSS in role description sanitized"""
        client.force_login(admin_user)
        
        # Try to inject JavaScript
        response = client.post('/admin/api/roles/', {
            'name': 'test',
            'display_name': 'Test',
            'description': '<img src=x onerror="alert(\'XSS\')">'
        }, content_type='application/json')
        
        # Verify injection neutralized
        role = AdminRole.objects.get(name='test')
        assert '<img src' not in role.description or 'onerror' not in role.description
    
    def test_csrf_protection(self, client):
        """CSRF tokens required for POST"""
        response = client.post('/admin/api/users/', {
            'username': 'test'
        })
        
        assert response.status_code == 403  # CSRF failure
```

**Acceptance Criteria**:
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] CSRF protection working
- [ ] Auth enforcement working
- [ ] Authorization checks working

#### 2. Penetration Testing

```python
# tests/security/test_penetration.py

class TestPenetration:
    def test_privilege_escalation(self, contributor_user, client):
        """Contributor cannot escalate to admin"""
        client.force_login(contributor_user)
        
        # Try to assign admin role to self
        response = client.put(f'/admin/api/users/{contributor_user.id}/role', {
            'role': 'admin'
        }, content_type='application/json')
        
        assert response.status_code == 403
        
        # Verify role unchanged
        contributor_user.refresh_from_db()
        assert contributor_user.admin_role.filter(role__name="admin").count() == 0
    
    def test_session_fixation_resistance(self, client):
        """Session ID changes on login"""
        # Get initial session
        response = client.get('/admin-panel/login/')
        session1 = client.cookies.get('sessionid')
        
        # Login
        client.post('/admin-panel/login/', {'username': 'admin', 'password': 'admin'})
        session2 = client.cookies.get('sessionid')
        
        assert session1 != session2
    
    def test_brute_force_protection(self, client):
        """Failed logins are rate limited"""
        for _ in range(10):
            client.post('/admin-panel/login/', {
                'username': 'admin',
                'password': 'wrong_pass'
            })
        
        # Next attempt should be blocked
        response = client.post('/admin-panel/login/', {
            'username': 'admin',
            'password': 'admin'
        })
        
        assert response.status_code == 429  # Too many requests
```

**Acceptance Criteria**:
- [ ] No privilege escalation possible
- [ ] Session fixation prevented
- [ ] Brute force attacks prevented
- [ ] Injection attacks prevented
- [ ] Authorization bypass impossible

---

## 📊 PERFORMANCE TESTING STRATEGY

### Load Testing with Locust

```python
# tests/performance/locustfile.py

from locust import HttpUser, task, between

class AdminDashboardUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Login
        response = self.client.post('/admin-panel/login/', {
            'username': 'admin',
            'password': 'admin'
        })
        self.client.cookies.set('sessionid', response.cookies.get('sessionid'))
    
    @task(10)
    def view_dashboard(self):
        """View dashboard - most common action"""
        self.client.get('/admin-panel/dashboard/')
    
    @task(5)
    def list_users(self):
        """List users"""
        self.client.get('/admin/api/users?page=1&limit=50')
    
    @task(3)
    def view_permission_matrix(self):
        """View permission matrix"""
        self.client.get('/admin/api/permissions/matrix')
    
    @task(2)
    def search(self):
        """Global search"""
        self.client.get('/admin/api/search?q=test')
```

### Performance Benchmarks

| Operation | Target | Threshold |
|-----------|--------|-----------|
| Dashboard load | <2s | <3s |
| User list load | <1s | <2s |
| Permission matrix | <2s | <3s |
| Role creation | <500ms | <1s |
| Permission check | <10ms | <50ms |
| Bulk ops (100 users) | <10s | <20s |
| Audit log search (1M) | <1s | <2s |

### Load Test Execution

```bash
# Run load test: 100 concurrent users, 5 minute duration
locust -f tests/performance/locustfile.py \
  --host=http://localhost:8000 \
  --users=100 \
  --spawn-rate=10 \
  --run-time=5m \
  --headless
```

**Acceptance Criteria**:
- [ ] Dashboard <2 seconds (cold), <500ms (warm)
- [ ] Concurrent users: 100+
- [ ] CPU utilization <80%
- [ ] Memory usage stable
- [ ] No timeouts

---

## 🎯 TEST COVERAGE TARGETS

### By Module

| Module | Target | Current | Status |
|--------|--------|---------|--------|
| Permission Model | 95% | 0% | Not Started |
| Role Model | 95% | 0% | Not Started |
| Permission Service | 95% | 0% | Not Started |
| Audit Logging | 90% | 0% | Not Started |
| User Management | 85% | 40% | In Progress |
| API Endpoints | 80% | 20% | In Progress |
| Templates | 70% | 10% | In Progress |

### By Test Type

| Type | Count | Target % | Status |
|------|-------|----------|--------|
| Unit Tests | 120 | 50% | Not Started |
| Integration Tests | 80 | 30% | In Progress |
| E2E Tests | 25 | 15% | Not Started |
| Security Tests | 20 | 5% | Not Started |
| Performance Tests | 15 | - | Not Started |
| **Total** | **260** | **100%** | **30% Done** |

---

## 🔄 Continuous Integration Setup

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_DB: bookclub_test
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.10
    
    - name: Install dependencies
      run: pip install -r requirements-test.txt
    
    - name: Run unit tests
      run: pytest tests/unit/ -v --cov=books --cov-report=xml
    
    - name: Run integration tests
      run: pytest tests/integration/ -v
    
    - name: Run security tests
      run: pytest tests/security/ -v
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
    
    - name: Run E2E tests
      run: pytest tests/e2e/ -v || true  # Allowed to fail in CI
```

---

## 📋 QA Sign-Off Checklist

### Before Launch

**Functionality (144 criteria)**
- [ ] All acceptance criteria passed
- [ ] All features working as designed
- [ ] No critical bugs
- [ ] No high-priority bugs
- [ ] Medium bugs documented and prioritized

**Code Quality**
- [ ] >85% code coverage
- [ ] All tests passing
- [ ] No linting errors
- [ ] Code review approved

**Performance**
- [ ] Dashboard <2 seconds
- [ ] User list <1 second
- [ ] API responses <500ms
- [ ] Database queries optimized
- [ ] Load testing passed (100+ users)

**Security**
- [ ] OWASP ZAP scan clean
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] CSRF protection working
- [ ] Authorization checks enforced
- [ ] Encryption in transit/at rest

**Compliance**
- [ ] WCAG 2.1 AA verified
- [ ] GDPR compliance reviewed
- [ ] Privacy policy updated
- [ ] Terms of service updated

**Operations**
- [ ] Deployment runbook ready
- [ ] Rollback plan documented
- [ ] Monitoring configured
- [ ] Alerts configured
- [ ] Team trained on new features

---

*Testing strategy designed for comprehensive quality assurance with focus on security, performance, and user experience.*
