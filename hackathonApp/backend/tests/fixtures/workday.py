"""Mock Workday API response data."""

WORKER_RESPONSE = {
    'id': 'WD-12345',
    'descriptor': 'John Smith',
    'primaryWorkEmail': 'john.smith@example.com',
    'employeeID': 'EMP001',
    'department': 'Engineering',
    'businessTitle': 'Software Engineer',
    'manager': 'Jane Doe',
}

WORKER_CUSTOM_OBJECT = {
    'table': 'T-14',
    'team_name': 'Alpha Team',
    'tenant_url': 'https://tenant.workday.com',
    'company': 'Acme Corp',
}

WORKER_RESPONSE_UPDATED = {
    **WORKER_RESPONSE,
    'businessTitle': 'Senior Software Engineer',
}

WORKER_CUSTOM_OBJECT_UPDATED = {
    **WORKER_CUSTOM_OBJECT,
    'table': 'T-16',
}

WORKDAY_ERROR_500 = {
    'error': 'Internal Server Error',
    'status_code': 500,
}

WORKDAY_ERROR_401 = {
    'error': 'Unauthorized',
    'status_code': 401,
}

WORKDAY_ERROR_429 = {
    'error': 'Too Many Requests',
    'status_code': 429,
    'retry_after': 60,
}

WORKDAY_PARTIAL_RESPONSE = {
    'id': 'WD-12345',
    'descriptor': 'John Smith',
    'primaryWorkEmail': 'john.smith@example.com',
    # Missing custom object fields
}


def bulk_worker_responses(count=150):
    """Generate mock Workday responses for bulk sync testing."""
    return [
        {
            'id': f'WD-{i:05d}',
            'descriptor': f'Worker {i}',
            'primaryWorkEmail': f'worker{i}@example.com',
            'employeeID': f'EMP{i:04d}',
            'department': 'Engineering',
            'businessTitle': 'Software Engineer',
            'manager': 'Jane Doe',
        }
        for i in range(1, count + 1)
    ]
