#!/usr/bin/env python3
"""Seed three users: admin, hacker, expert (all @hackathon.com). Default password: password."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Worker, WorkerRole
from app.utils.auth import hash_password

USERS = [
    ("admin@hackathon.com", "Admin User", WorkerRole.ADMIN),
    ("hacker@hackathon.com", "Hacker User", WorkerRole.HACKER),
    ("expert@hackathon.com", "Expert User", WorkerRole.EXPERT),
]
DEFAULT_PASSWORD = "password"


def seed_users():
    app = create_app("development")
    with app.app_context():
        for email, name, role in USERS:
            existing = Worker.query.filter_by(email=email).first()
            if existing:
                existing.name = name
                existing.role = role
                existing.password_hash = hash_password(DEFAULT_PASSWORD)
                existing.is_active = True
                db.session.commit()
                print(f"  Updated: {email} ({role.value})")
            else:
                w = Worker(
                    workday_id=None,
                    email=email,
                    name=name,
                    password_hash=hash_password(DEFAULT_PASSWORD),
                    role=role,
                    is_active=True,
                )
                db.session.add(w)
                db.session.commit()
                print(f"  Created: {email} ({role.value})")
        print("Done. All three users use password: password")


if __name__ == "__main__":
    seed_users()
