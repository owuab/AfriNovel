# Admin Dashboard - Annotated Wireframes & Design Specifications

## 📐 System Overview Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      BookClub Admin Dashboard                            │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐                                                        │
│  │ Quick Search │  ┌─────────────────────────────────────────────────┐  │
│  │  Cmd+K       │  │ Breadcrumbs: Admin > Users > Roles              │  │
│  └──────────────┘  └─────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────────┐  ┌─────────────────────────────────────────────┐   │
│  │   SIDE NAV      │  │          MAIN CONTENT AREA                  │   │
│  │ ┌─────────────┐ │  │                                             │   │
│  │ │ Dashboard   │ │  │  ┌──────────────────────────────────────┐   │   │
│  │ │ Users       │ │  │  │ Role Editor                          │   │   │
│  │ │ Roles       │ │  │  │                                      │   │   │
│  │ │ Permissions │ │  │  │ ┌──────────────────────────────────┐ │   │   │
│  │ │ Books       │ │  │  │ │ Role Name: [Moderator        ]  │ │   │   │
│  │ │ Reports     │ │  │  │ │                                  │ │   │   │
│  │ │ Audit Logs  │ │  │  │ │ Permissions:                     │ │   │   │
│  │ │ Settings    │ │  │  │ │ ☑ View Reports                  │ │   │   │
│  │ └─────────────┘ │  │  │ │ ☑ Resolve Reports              │ │   │   │
│  │                 │  │  │ │ ☑ Suspend Users                │ │   │   │
│  │                 │  │  │ │ ☐ Approve Books                │ │   │   │
│  └─────────────────┘  │  │ │ ☐ Manage Admins                │ │   │   │
│                       │  │ └──────────────────────────────────┘ │   │   │
│                       │  │                                      │   │   │
│                       │  │ [Save] [Cancel] [Delete] [More...]  │   │   │
│                       │  └──────────────────────────────────────┘   │   │
│                       │                                             │   │
│  ┌────────────────────┴─────────────────────────────────────────────┘   │
│  │ KEYBOARD SHORTCUTS: Cmd+F (Find) | Cmd+N (New) | Esc (Close)         │
│  └─────────────────────────────────────────────────────────────────────  │
```

---

## 🎯 WIREFRAME 1: Main Dashboard

```
┌──────────────────────────────────────────────────────────────────────────┐
│ < Back  BookClub Admin  [Search...]      Help │ Admin (v) │ Logout      │
├──────────────────────────────────────────────────────────────────────────┤
│ Home > Dashboard                                       [View All] [Help] │
├─────────────────────────────────────┬──────────────────────────────────┤
│                                       │                                  │
│  📊 QUICK STATISTICS                  │  ⚡ QUICK ACTIONS               │
│  ┌──────────────────────────────────┐ │  [+ New User] [Approve Books]  │
│  │ Total Users: 2,543                │ │  [Review Reports] [Edit Roles] │
│  │ Active Today: 487 (19%)           │ │                                │
│  │ Suspended: 23                     │ │  📚 RECENT ITEMS               │
│  │ Pending Approvals: 12             │ │  • Book 1 - 2 hours ago        │
│  │ Unresolved Reports: 7             │ │  • User suspended - 4 hrs ago  │
│  │ System Uptime: 99.8%              │ │  • Report resolved - 1 day ago │
│  └──────────────────────────────────┘ │                                │
│                                       │                                  │
│  👥 RECENT USERS (Show 5, [View All])│  🚩 OPEN REPORTS (5)            │
│  ┌──────────────────────────────────┐ │  ┌────────────────────────────┐│
│  │ User   │ Email    │ Joined   │ Act││  │ Harassment x3              ││
│  │ john   │ j@ex.com │ 2 days  │ ✓  ││  │ Spam x2                    ││
│  │ jane   │ j@ex.com │ 1 week  │ ✓  ││  │ [View All 7]               ││
│  │ bob    │ b@ex.com │ 2 weeks │ ✗  ││  └────────────────────────────┘│
│  └──────────────────────────────────┘ │                                  │
│                                       │                                  │
│  📚 PENDING BOOKS (3)                │  🔐 AUDIT LOG (Last 5)          │
│  ┌──────────────────────────────────┐ │  ┌────────────────────────────┐│
│  │ Title 1 - 3 days pending         │ │  │ admin suspended user_123   ││
│  │ Title 2 - 1 week pending         │ │  │ admin approved book_456    ││
│  │ [View All 12]                    │ │  │ mod resolved report_789    ││
│  └──────────────────────────────────┘ │  │ [View All]                 ││
│                                       │  └────────────────────────────┘│
└─────────────────────────────────────┴──────────────────────────────────┘
│ Page 1 of 1  |  Last Updated: 2 minutes ago  |  Refresh  |  Export      │
└──────────────────────────────────────────────────────────────────────────┘
```

**Annotations:**
- **Top Bar**: Global search (Cmd+K), admin menu, logout
- **Breadcrumbs**: Show navigation path for context
- **Quick Statistics**: Real-time metrics with trend indicators
- **Quick Actions**: Fast access to common tasks (floating or top-fixed)
- **Recent Items**: Shows activity feed with timestamps
- **Sidebar Cards**: Key metrics per domain (users, books, reports)
- **Responsive**: On mobile, side-by-side becomes stacked

---

## 🎯 WIREFRAME 2: Permission Matrix

```
┌──────────────────────────────────────────────────────────────────────────┐
│ < Back  Admin > Roles > Permissions Matrix    [Export] [Help]           │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  Filter by Role: [All Roles ▼] [Super Admin] [Admin] [Moderator] [+]   │
│  Filter by Module: [All ▼]  Search: [__________]                        │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  Module      │ Permission  │SA │ AD │ MOD │ CM │ AN │ Updated│Edit │ │
│  ├──────────────┼─────────────┼───┼────┼─────┼────┼────┼────────┼─────┤ │
│  │ Users        │ Create      │✓  │ ✓  │ ✗   │ ✗  │ ✗  │ 1 day  │ [>] │ │
│  │ Users        │ Edit        │✓  │ ✓  │ ✗   │ ✗  │ ✗  │ 1 day  │ [>] │ │
│  │ Users        │ Delete      │✓  │ ✗  │ ✗   │ ✗  │ ✗  │ 3 days │ [>] │ │
│  │ Users        │ Suspend     │✓  │ ✓  │ ✓   │ ✗  │ ✗  │ 3 days │ [>] │ │
│  │ Users        │ View List   │✓  │ ✓  │ ✓   │ ✓  │ ✗  │ 2 days │ [>] │ │
│  │              │             │   │    │     │    │    │        │     │ │
│  │ Books        │ Approve     │✓  │ ✓  │ ✗   │ ✓  │ ✗  │ 5 days │ [>] │ │
│  │ Books        │ Reject      │✓  │ ✓  │ ✗   │ ✓  │ ✗  │ 5 days │ [>] │ │
│  │ Books        │ Request Rev │✓  │ ✓  │ ✗   │ ✓  │ ✗  │ 5 days │ [>] │ │
│  │              │             │   │    │     │    │    │        │     │ │
│  │ Reports      │ View        │✓  │ ✓  │ ✓   │ ✗  │ ✗  │ 1 week │ [>] │ │
│  │ Reports      │ Resolve     │✓  │ ✓  │ ✓   │ ✗  │ ✗  │ 1 week │ [>] │ │
│  │ Reports      │ Dismiss     │✓  │ ✓  │ ✗   │ ✗  │ ✗  │ 2 days │ [>] │ │
│  │              │             │   │    │     │    │    │        │     │ │
│  │ Admin        │ Assign Role │✓  │ ✗  │ ✗   │ ✗  │ ✗  │ 1 week │ [>] │ │
│  │ Admin        │ View Audit  │✓  │ ✓  │ ✓   │ ✓  │ ✓  │ 2 days │ [>] │ │
│  │ Admin        │ Export Logs │✓  │ ✓  │ ✗   │ ✗  │ ✗  │ 1 day  │ [>] │ │
│  │              │             │   │    │     │    │    │        │     │ │
│  │ Settings     │ View        │✓  │ ✓  │ ✓   │ ✓  │ ✓  │ 3 days │ [>] │ │
│  │ Settings     │ Modify      │✓  │ ✓  │ ✗   │ ✗  │ ✗  │ 1 week │ [>] │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  Legend: SA=Super Admin | AD=Admin | MOD=Moderator | CM=Content Mgr | AN=Analytics
│  [Show History] [Compare Roles] [Export as CSV] [Bulk Edit]              │
│                                                                            │
└──────────────────────────────────────────────────────────────────────────┘
```

**Annotations:**
- **Top Filters**: Filter by role, module, search permissions
- **Matrix Table**: 
  - Rows = Permissions grouped by module
  - Columns = Roles with inheritance shown (✓ = has permission)
  - Last column = When permission was last modified
  - Edit icon = Click to edit this specific permission
- **Export**: CSV export with timestamp
- **History**: View permission change history
- **Bulk Edit**: Select multiple rows to edit together
- **Mobile**: Horizontally scrollable table

---

## 🎯 WIREFRAME 3: Role Editor

```
┌──────────────────────────────────────────────────────────────────────────┐
│ < Back  Admin > Roles > Edit Role              [Clone] [Delete] [More] │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌─ ROLE DETAILS ───────────────────────────────────────────────────────┐ │
│  │ Role Name*: [Moderator_________________]  [Inherited from: Admin ▼] │ │
│  │ Display Name: [Moderator_______________]                            │ │
│  │ Description:                                                        │ │
│  │ ┌──────────────────────────────────────────────────────────────────┐│ │
│  │ │ Reviews user reports and takes moderation actions               ││ │
│  │ └──────────────────────────────────────────────────────────────────┘│ │
│  │ Priority: [5_______]  (1=Lowest, 10=Highest)                       │ │
│  │ Status: ○ Active  ● Inactive                                        │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌─ PERMISSIONS ────────────────────────────────────────────────────────┐ │
│  │ [Search permissions..._______________] [+Add] [Remove Selected]    │ │
│  │                                                                      │ │
│  │ ☑ Users::View                       │ ☑ Reports::View               │ │
│  │ ☑ Users::Suspend                   │ ☑ Reports::Resolve           │ │
│  │ ☐ Users::Delete                    │ ☐ Reports::Create            │ │
│  │ ☑ Books::View                      │ ☑ Settings::View             │ │
│  │ ☐ Books::Approve                   │ ☐ Settings::Modify           │ │
│  │ ☐ Books::Reject                    │ ☐ Admin::ManageAdmins        │ │
│  │ ☑ Audit::View                      │ ☐ Audit::Export              │ │
│  │                                                                      │ │
│  │ [Select All] [Clear All] [+Load Preset: Moderator_v1 ▼]            │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌─ ASSIGNED USERS ──────────────────────────────────────────────────┐  │
│  │ [+ Add Users]  [Bulk Assign]  [Remove Selected]  [Filter...]      │  │
│  │                                                                    │  │
│  │ ☑ john (assigned 2 days ago, last active: 1 hour ago)            │  │
│  │ ☑ jane (assigned 1 week ago, last active: 3 days ago)            │  │
│  │ ☑ bob (assigned 2 weeks ago, last active: 2 weeks ago)           │  │
│  │ ☐ alice (assigned 3 weeks ago, last active: never)               │  │
│  │                                                                    │  │
│  │ Showing 4 of 4 users  [View All]                                  │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌─ AUDIT HISTORY ───────────────────────────────────────────────────┐  │
│  │ [View Full History]                                               │  │
│  │                                                                    │  │
│  │ 2 hours ago - super_admin changed permissions (3 changes)         │  │
│  │ 1 day ago - super_admin assigned user "john"                     │  │
│  │ 3 days ago - super_admin created this role                       │  │
│  │                                                                    │  │
│  │ [View Details] [Undo] [Redo]                                      │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  [Save Changes] [Save & Assign More Users] [Cancel] [Delete Role]       │
│  Last saved: 3 days ago by super_admin                                  │
│                                                                            │
└──────────────────────────────────────────────────────────────────────────┘
```

**Annotations:**
- **Role Details**: Name, display name, description, priority, status
- **Permission Checkboxes**: Organized by module, searchable
- **Presets**: Load common role templates
- **Assigned Users**: See who has this role, bulk operations
- **Audit History**: Track all changes with undo/redo
- **Save Options**: Save only, or save and add more users
- **Mobile**: Sections collapse/expand for mobile view

---

## 🎯 WIREFRAME 4: Global Search / Quick Actions

```
┌──────────────────────────────────────────────────────────────────────────┐
│                  Press Cmd+K anytime to open search                       │
│                                                                            │
│                  ┌───────────────────────────────────────┐                │
│                  │ [🔍] Search users, books, reports... │                │
│                  └───────────────────────────────────────┘                │
│                                                                            │
│  ┌─ RESULTS ──────────────────────────────────────────────────────────┐  │
│  │                                                                    │  │
│  │ 👥 USERS (3 results)                                              │  │
│  │  ► john_doe (active, assigned: Moderator)  [View Profile]        │  │
│  │  ► jane_smith (suspended until 2026-09-15)  [Unsuspend]          │  │
│  │  ► bob_wilson (active, assigned: Admin)  [View Profile]          │  │
│  │                                                                    │  │
│  │ 📚 BOOKS (2 results)                                              │  │
│  │  ► "The Great Novel" (pending approval)  [Review] [Approve]      │  │
│  │  ► "Mystery Book" (published)  [View] [Edit]                     │  │
│  │                                                                    │  │
│  │ 🚩 REPORTS (1 result)                                             │  │
│  │  ► Harassment Report #1234 (open)  [View] [Resolve]              │  │
│  │                                                                    │  │
│  │ ⚙️  QUICK ACTIONS                                                 │  │
│  │  ► New User [+]                                                   │  │
│  │  ► Bulk Suspend Users                                             │  │
│  │  ► Create New Role                                                │  │
│  │  ► View Audit Log                                                 │  │
│  │                                                                    │  │
│  │ 🛠️  SHORTCUTS                                                      │  │
│  │  [?] Help | [n] New | [r] Recent | [a] All Actions               │  │
│  │                                                                    │  │
│  │                                                                    │  │
│  │ More results... [View All]                                        │  │
│  │                                                                    │  │
│  │ Or try: "status:pending" "assigned:admin" "updated:today"        │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│                          Search powered by Algolia                        │
└──────────────────────────────────────────────────────────────────────────┘

QUICK ACTION EXAMPLES:
- Create new user: Cmd+K -> "new user" -> [Tab] -> Fill form -> [Enter]
- Suspend user: Cmd+K -> "john suspend" -> [Enter] -> Confirm
- Approve book: Cmd+K -> "book approve" -> Select book -> [Enter]
- View audit: Cmd+K -> "audit" -> [Enter]
```

**Annotations:**
- **Global Search**: Open with Cmd+K (or Ctrl+K on Windows)
- **Instant Results**: As you type, showing users/books/reports
- **Quick Actions**: Common tasks accessible from search
- **Shortcuts**: Learn keyboard shortcuts inline
- **Advanced Filters**: Use "status:", "assigned:", "updated:" for precision
- **Action Shortcuts**: Select result with arrow keys, press action shortcut

---

## 🎯 WIREFRAME 5: Bulk Operations Panel

```
┌──────────────────────────────────────────────────────────────────────────┐
│ < Back  Admin > Users > Bulk Operations          [Help]                 │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  [←] [→] Step 1 of 3: Select Users                                      │
│                                                                            │
│  ┌─ SELECT USERS ────────────────────────────────────────────────────┐  │
│  │ Filter by Role: [All ▼]  Status: [All ▼]                         │  │
│  │ Search: [_______________________]  [Show last 7 days]             │  │
│  │                                                                    │  │
│  │ ☐ john (Moderator, active, 12 reports)                           │  │
│  │ ☐ jane (Admin, active, 5 reports)                                │  │
│  │ ☐ bob (Moderator, suspended, 0 reports)                          │  │
│  │ ☐ alice (Moderator, active, 8 reports)                           │  │
│  │ ☐ charlie (Admin, active, 3 reports)                             │  │
│  │ ☐ diana (Moderator, active, 11 reports)                          │  │
│  │                                                                    │  │
│  │ [Select All] [Clear All] [Invert Selection]                       │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  Selected: 3 users  [Remove From Selection] [View Selected]              │
│                                                                            │
│  [Cancel] [← Previous] [Next →]                                          │
│                                                                            │
├────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  [←] [→] Step 2 of 3: Select Action                                      │
│                                                                            │
│  ┌─ ACTIONS ─────────────────────────────────────────────────────────┐  │
│  │                                                                    │  │
│  │ ● Assign Role:                                                    │  │
│  │   Select role: [Moderator ▼]                                      │  │
│  │   Override existing role: ☑ Yes  ☐ No                             │  │
│  │                                                                    │  │
│  │ ○ Suspend Users:                                                  │  │
│  │   Reason: [Select reason ▼]                                       │  │
│  │   Duration: [Temporary ▼] (Days: [7])                             │  │
│  │   Send notification: ☑ Yes  ☐ No                                  │  │
│  │                                                                    │  │
│  │ ○ Unsuspend Users                                                 │  │
│  │   ☑ Send notification                                             │  │
│  │                                                                    │  │
│  │ ○ Delete Users (WARNING: Permanent)                               │  │
│  │   ☑ Archive data  ☐ Delete all data                               │  │
│  │                                                                    │  │
│  │ ○ Revoke Roles (Remove all roles)                                 │  │
│  │   Reassign to role: [None ▼]                                      │  │
│  │                                                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  [Cancel] [← Previous] [Next →]                                          │
│                                                                            │
├────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  [←] [→] Step 3 of 3: Review & Confirm                                   │
│                                                                            │
│  ┌─ ACTION SUMMARY ──────────────────────────────────────────────────┐  │
│  │                                                                    │  │
│  │ Action: Assign Role                                               │  │
│  │ Users Affected: 3                                                 │  │
│  │ New Role: Moderator                                               │  │
│  │ Override Existing: Yes                                            │  │
│  │                                                                    │  │
│  │ Users that will be affected:                                      │  │
│  │ • john (changing from Admin → Moderator)                          │  │
│  │ • alice (already Moderator)                                       │  │
│  │ • diana (changing from Admin → Moderator)                         │  │
│  │                                                                    │  │
│  │ Estimated time to complete: < 1 second                            │  │
│  │                                                                    │  │
│  │ ☑ I understand the implications and want to proceed               │  │
│  │                                                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  [Cancel] [← Previous] [Execute Action] [Execute & Send Notifications]   │
│                                                                            │
│  💡 Tip: This action will be logged in Audit Trail for compliance        │
│                                                                            │
└──────────────────────────────────────────────────────────────────────────┘
```

**Annotations:**
- **Step 1**: Select multiple users with checkboxes
- **Step 2**: Choose action and configure options
- **Step 3**: Review impacts before executing
- **Progress**: Visual step indicator (1 of 3)
- **Navigation**: Previous/Next buttons to revisit steps
- **Confirmation**: Must acknowledge implications
- **Audit**: All bulk actions logged automatically
- **Mobile**: Responsive, fits on mobile screens

---

## 🎯 WIREFRAME 6: Navigation Flow

```
USER JOURNEY - COMMON ADMIN TASK: "Approve pending book and notify author"

START: Dashboard (Quick Statistics visible)
  ↓
[Click: "Pending Books (12)"] or [Search: "book approve"]
  ↓
Books Pending Approval List (12 books shown, paginated)
  ├─ Breadcrumbs: Home > Books > Pending
  ├─ Back/Forward: [< Previous] [Next >]
  └─ Quick Actions: [Approve All] [Reject All] [+Options]
  ↓
[Click Book Title] → Book Details + Review Panel
  ├─ Breadcrumbs: Home > Books > Pending > "Book Title"
  ├─ Book Info, Cover, Metadata
  ├─ Author Contact
  ├─ Review Interface
  │  ├─ [✓ Approve] [✗ Reject] [↻ Request Revision]
  │  └─ Message to Author: [Text Area]
  │     [Add Template: Approved_v1 ▼]
  ├─ Sidebar History: "Submitted 5 days ago"
  └─ History: Last 3 actions on this book
  ↓
[Click: Approve]
  ├─ Modal: "Send notification to author?"
  │  ├─ [Send Email] [Send In-App] [Both]
  │  └─ Template: [Approval Notice ▼]
  ↓
[Click: Send Email]
  ├─ Confirmation: "Book approved and author notified"
  ├─ Undo: [↶ Undo this action] (30 seconds)
  └─ Redirect options: [View Next Book] [View All Books] [Back to Dashboard]
  ↓
[Click: View Next Book]
  └─ Shows next pending book in list (seamless flow)

KEYBOARD SHORTCUTS ENABLED THROUGHOUT:
  Cmd+K: Open search/quick actions
  Cmd+S: Save/Submit
  Cmd+Z: Undo
  Cmd+Y: Redo
  Cmd+N: New
  Cmd+F: Find in page
  Esc: Close modal/cancel
  ←/→: Previous/Next item
  ↵: Submit form
```

**Annotations:**
- **Breadcrumbs**: Show full navigation path
- **Back/Forward**: Navigate through recent pages
- **Quick Actions**: Context-aware buttons on each screen
- **Keyboard Shortcuts**: Accessible with Cmd+? or help
- **Undo/Redo**: Reversible actions with time window
- **Seamless Flow**: Navigate to next item without returning to list
- **Mobile**: Buttons larger, text clearer

---

## 📏 Design Tokens

```
RESPONSIVE BREAKPOINTS:
  Mobile:     <= 576px   (single column, stacked)
  Tablet:     577-991px  (2 columns, sidebar left)
  Desktop:    >= 992px   (3+ column layouts available)

COLORS:
  Primary:    #7a4c3d   (BookClub brand)
  Success:    #2f5d50   (Approval/positive)
  Danger:     #9d2929   (Rejection/negative)
  Warning:    #d97706   (Caution/needs attention)
  Info:       #0369a1   (Informational)

TYPOGRAPHY:
  Headings:   Font-weight 700, Size: 2rem
  Body:       Font-weight 400, Size: 1rem
  Small:      Font-weight 400, Size: 0.875rem

SPACING:
  Compact:    0.5rem
  Normal:     1rem (16px)
  Comfortable: 1.5rem
  Spacious:   2rem

ACCESSIBILITY:
  Min Touch Target: 44x44px
  Focus Outline: 3px, Brand color
  Color Contrast: WCAG AA (4.5:1 minimum)
  Keyboard Navigation: Full support (no mouse required)
```

---

## ✨ Key Features of Wireframes

1. **Consistent Navigation**: Breadcrumbs + Back/Forward on every screen
2. **Persistent Sidebar**: Always visible on desktop, collapsible on mobile
3. **Global Search**: Cmd+K accessible from anywhere
4. **Keyboard Shortcuts**: Every screen supports keyboard access
5. **Progressive Disclosure**: Show advanced options only when needed
6. **Confirmation Steps**: Critical actions require explicit confirmation
7. **Undo/Redo**: Users can reverse their actions
8. **Bulk Operations**: Multi-step wizard for complex operations
9. **Audit Trail**: Every action logged and visible
10. **Mobile Responsive**: All screens work on phones/tablets

---

*Wireframes designed following senior product design principles with emphasis on usability, security, and developer handoff quality.*
