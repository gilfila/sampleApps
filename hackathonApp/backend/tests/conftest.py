"""Pytest fixtures for testing."""
import pytest
import sys
import os

# Add backend directory to path so 'app' and 'config' are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db as _db
from app.models import Worker, WorkerRole


@pytest.fixture(scope='session')
def app():
    """Create application for testing."""
    app = create_app('testing')
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(autouse=True)
def db_session(app):
    """Create a fresh database session for each test.

    Rolls back any changes after the test completes so tests are isolated.
    """
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        # Clean tables between tests
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def admin_user(app, db_session):
    """Create admin user for testing."""
    from app.utils.auth import hash_password
    user = Worker(
        workday_id='ADMIN001',
        email='admin@test.com',
        password_hash=hash_password('adminpass'),
        name='Admin User',
        role=WorkerRole.ADMIN,
        is_active=True,
    )
    db_session.session.add(user)
    db_session.session.commit()
    return user


@pytest.fixture
def regular_user(app, db_session):
    """Create regular user for testing."""
    from app.utils.auth import hash_password
    user = Worker(
        workday_id='USER001',
        email='user@test.com',
        password_hash=hash_password('userpass'),
        name='Regular User',
        role=WorkerRole.HACKER,
        is_active=True,
    )
    db_session.session.add(user)
    db_session.session.commit()
    return user


@pytest.fixture
def expert_user(app, db_session):
    """Create expert user for testing."""
    from app.utils.auth import hash_password
    user = Worker(
        workday_id='EXPERT001',
        email='expert@test.com',
        password_hash=hash_password('expertpass'),
        name='Expert User',
        role=WorkerRole.EXPERT,
        is_active=True,
    )
    db_session.session.add(user)
    db_session.session.commit()
    return user


@pytest.fixture
def inactive_user(app, db_session):
    """Create inactive user for testing."""
    from app.utils.auth import hash_password
    user = Worker(
        workday_id='INACTIVE001',
        email='inactive@test.com',
        password_hash=hash_password('inactivepass'),
        name='Inactive User',
        role=WorkerRole.HACKER,
        is_active=False,
    )
    db_session.session.add(user)
    db_session.session.commit()
    return user


@pytest.fixture
def authenticated_client(client, regular_user):
    """Create an authenticated test client (logged-in regular user)."""
    client.post('/api/auth/login', json={
        'email': 'user@test.com',
        'password': 'userpass',
    })
    return client


@pytest.fixture
def admin_client(client, admin_user):
    """Create an authenticated test client (logged-in admin user)."""
    client.post('/api/auth/login', json={
        'email': 'admin@test.com',
        'password': 'adminpass',
    })
    return client


@pytest.fixture
def expert_client(client, expert_user):
    """Create an authenticated test client (logged-in expert user)."""
    client.post('/api/auth/login', json={
        'email': 'expert@test.com',
        'password': 'expertpass',
    })
    return client
