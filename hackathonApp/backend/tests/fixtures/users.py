"""Test user fixture data."""

ADMIN_USER = {
    'workday_id': 'ADMIN001',
    'email': 'admin@test.com',
    'password': 'adminpass',
    'name': 'Admin User',
    'role': 'admin',
}

REGULAR_USER = {
    'workday_id': 'USER001',
    'email': 'user@test.com',
    'password': 'userpass',
    'name': 'Regular User',
    'role': 'hacker',
}

EXPERT_USER = {
    'workday_id': 'EXPERT001',
    'email': 'expert@test.com',
    'password': 'expertpass',
    'name': 'Expert User',
    'role': 'expert',
}

INACTIVE_USER = {
    'workday_id': 'INACTIVE001',
    'email': 'inactive@test.com',
    'password': 'inactivepass',
    'name': 'Inactive User',
    'role': 'hacker',
    'is_active': False,
}

UNREGISTERED_USER = {
    'workday_id': 'UNREG001',
    'email': 'unregistered@test.com',
    'name': 'Unregistered User',
    'role': 'hacker',
}


def bulk_users(count=10):
    """Generate a list of test users."""
    return [
        {
            'workday_id': f'BULK{i:04d}',
            'email': f'bulk{i}@test.com',
            'password': f'bulkpass{i}',
            'name': f'Bulk User {i}',
            'role': 'hacker',
        }
        for i in range(1, count + 1)
    ]
