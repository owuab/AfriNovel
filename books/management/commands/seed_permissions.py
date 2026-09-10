from django.core.management.base import BaseCommand

from books.models import Permission


PERMISSIONS = [
    ('users', 'create', 'Create admin users'),
    ('users', 'read', 'View user accounts'),
    ('users', 'update', 'Edit user accounts'),
    ('users', 'delete', 'Delete user accounts'),
    ('users', 'suspend', 'Suspend or unsuspend users'),
    ('roles', 'create', 'Create new roles'),
    ('roles', 'read', 'View roles'),
    ('roles', 'update', 'Edit role definitions'),
    ('roles', 'delete', 'Delete roles'),
    ('roles', 'assign', 'Assign roles to users'),
    ('reports', 'create', 'Create reports'),
    ('reports', 'read', 'View reports'),
    ('reports', 'resolve', 'Resolve reports'),
    ('reports', 'export', 'Export reports'),
    ('books', 'read', 'View books and metadata'),
    ('books', 'approve', 'Approve books'),
    ('books', 'reject', 'Reject books'),
    ('books', 'revision', 'Request revisions'),
    ('books', 'feature', 'Feature books on the homepage'),
    ('audit', 'read', 'View audit logs'),
    ('audit', 'export', 'Export audit logs'),
    ('audit', 'delete', 'Delete audit logs'),
    ('settings', 'read', 'View settings pages'),
    ('settings', 'update', 'Change system settings'),
    ('settings', 'maintenance', 'Access maintenance controls'),
    ('admin', 'manage', 'Manage admin accounts'),
    ('admin', 'view', 'View admin dashboard details'),
    ('admin', 'export', 'Export admin data'),
    ('discovery', 'read', 'Browse discovery and catalogue listings'),
    ('discovery', 'manage', 'Manage discovery recommendations'),
    ('content', 'moderate', 'Moderate content flags'),
    ('content', 'remove', 'Remove inappropriate content'),
    ('dashboard', 'read', 'View dashboard metrics'),
    ('dashboard', 'access', 'Access dashboard widgets'),
    ('analytics', 'read', 'View analytics'),
    ('analytics', 'export', 'Export analytics reports'),
    ('notifications', 'read', 'View notification lists'),
    ('notifications', 'send', 'Send system notifications'),
    ('import', 'read', 'View import jobs'),
    ('import', 'create', 'Create import jobs'),
    ('import', 'update', 'Update import jobs'),
    ('import', 'approve', 'Approve imported content'),
    ('library', 'read', 'View library collections'),
    ('library', 'manage', 'Manage library entries'),
    ('social', 'read', 'View social activity'),
    ('social', 'moderate', 'Moderate social posts and comments'),
    ('users', 'ban', 'Ban a user account'),
    ('reports', 'assign', 'Assign reports to reviewers'),
    ('books', 'archive', 'Archive books'),
    ('audit', 'review', 'Review audit trails'),
    ('settings', 'security', 'Manage security settings'),
    ('admin', 'security', 'Manage admin security policies'),
]


class Command(BaseCommand):
    help = 'Seed the custom permission registry for the admin dashboard.'

    def handle(self, *args, **options):
        created = 0
        for module, action, description in PERMISSIONS:
            permission, was_created = Permission.objects.get_or_create(
                module=module,
                action=action,
                defaults={
                    'name': f'{module}:{action}',
                    'description': description,
                    'category': module,
                    'is_system': True,
                },
            )
            permission.name = permission.name or f'{module}:{action}'
            permission.description = permission.description or description
            permission.category = permission.category or module
            permission.is_system = True
            permission.save(update_fields=['name', 'description', 'category', 'is_system'])
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Created {created} permissions; ensured {Permission.objects.count()} total permissions exist.'))
