from django.core.management.base import BaseCommand

from books.admin_models import AdminRole
from books.models import Permission, RolePermission


ROLE_PERMISSION_MAP = {
    AdminRole.SUPER_ADMIN: ['*'],
    AdminRole.ADMIN: [
        'users:*', 'roles:*', 'reports:*', 'books:*', 'audit:*', 'admin:*', 'dashboard:*',
        'analytics:*', 'settings:read', 'settings:update', 'notifications:*', 'import:*',
    ],
    AdminRole.MODERATOR: [
        'users:read', 'users:suspend', 'reports:read', 'reports:resolve', 'books:read',
        'books:approve', 'books:reject', 'audit:read', 'dashboard:read', 'notifications:read',
    ],
    AdminRole.CONTENT_MANAGER: [
        'books:read', 'books:approve', 'books:reject', 'books:revision', 'books:feature',
        'reports:read', 'content:moderate', 'content:remove', 'dashboard:read', 'analytics:read',
    ],
    AdminRole.ANALYTICS: [
        'analytics:read', 'dashboard:read', 'reports:read', 'audit:read', 'settings:read',
    ],
}


def _matches(permission_name: str, target: str) -> bool:
    if target == '*':
        return True
    if target.endswith(':*'):
        prefix = target[:-2]
        return permission_name == prefix or permission_name.startswith(f'{prefix}:')
    return permission_name == target


class Command(BaseCommand):
    help = 'Assign permission entries to the existing admin role types.'

    def handle(self, *args, **options):
        permissions = list(Permission.objects.all())
        mapping_count = 0

        for role_name, allowed in ROLE_PERMISSION_MAP.items():
            for permission in permissions:
                name = permission.name
                if any(_matches(name, target) for target in allowed):
                    _, created = RolePermission.objects.get_or_create(
                        role_name=role_name,
                        permission=permission,
                    )
                    if created:
                        mapping_count += 1

        self.stdout.write(self.style.SUCCESS(f'Assigned {mapping_count} role-permission links.'))
