#!/usr/bin/env python3
"""Create Worker rows (invitees) from a CSV so those emails can register.

Usage:
  python seed_invites_from_csv.py [path/to/invites.csv]

CSV format: email, name, role (role optional, default: hacker).
Headers required. Example: backend/invites_example.csv

These workers are created without a password; they set one when they register.
"""
import csv
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Worker, WorkerRole


def seed_invites_from_csv(csv_path: str) -> None:
    app = create_app(os.environ.get("FLASK_ENV", "development"))
    with app.app_context():
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if "email" not in (reader.fieldnames or []):
                print("CSV must have an 'email' column. Optional: name, role.")
                sys.exit(1)
            created = 0
            updated = 0
            skipped = 0
            for row in reader:
                email = (row.get("email") or "").strip().lower()
                if not email:
                    skipped += 1
                    continue
                name = (row.get("name") or "").strip() or email.split("@")[0]
                role_str = (row.get("role") or "hacker").strip().lower()
                try:
                    role = WorkerRole(role_str)
                except ValueError:
                    role = WorkerRole.HACKER
                existing = Worker.query.filter_by(email=email).first()
                if existing:
                    existing.name = name
                    existing.role = role
                    existing.is_active = True
                    db.session.commit()
                    updated += 1
                    print(f"  Updated: {email} ({role.value})")
                else:
                    w = Worker(
                        workday_id=None,
                        email=email,
                        name=name,
                        role=role,
                        is_active=True,
                    )
                    db.session.add(w)
                    db.session.commit()
                    created += 1
                    print(f"  Created: {email} ({role.value})")
            print(f"Done. Created: {created}, updated: {updated}, skipped: {skipped}")
            print("These users can now register at /register with their email and set a password.")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "invites_example.csv"
    )
    if not os.path.isfile(path):
        print(f"File not found: {path}")
        print("Usage: python seed_invites_from_csv.py [path/to/invites.csv]")
        sys.exit(1)
    seed_invites_from_csv(path)
