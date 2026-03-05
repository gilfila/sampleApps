#!/usr/bin/env python3
"""Script to create an admin user"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Worker, WorkerRole
from app.utils.auth import hash_password

def create_admin_user(email, password, name="Admin User"):
    """Create an admin user"""
    app = create_app('development')
    
    with app.app_context():
        # Check if user already exists
        existing_user = Worker.query.filter_by(email=email).first()
        if existing_user:
            print(f"User with email {email} already exists.")
            print(f"Updating to admin role and resetting password...")
            existing_user.role = WorkerRole.ADMIN
            existing_user.password_hash = hash_password(password)
            existing_user.name = name
            existing_user.is_active = True
            db.session.commit()
            print(f"✓ Admin user updated successfully!")
            print(f"  Email: {existing_user.email}")
            print(f"  Name: {existing_user.name}")
            print(f"  Role: {existing_user.role.value}")
            return existing_user
        
        # Create new admin user
        admin_user = Worker(
            workday_id=f"admin-{email}",  # Placeholder workday_id
            email=email,
            name=name,
            password_hash=hash_password(password),
            role=WorkerRole.ADMIN,
            is_active=True
        )
        
        db.session.add(admin_user)
        db.session.commit()
        
        print(f"✓ Admin user created successfully!")
        print(f"  Email: {admin_user.email}")
        print(f"  Name: {admin_user.name}")
        print(f"  Role: {admin_user.role.value}")
        print(f"  ID: {admin_user.id}")
        return admin_user

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Create an admin user')
    parser.add_argument('--email', default='admin@hackathon.com', help='Admin email address')
    parser.add_argument('--password', default='password', help='Admin password')
    parser.add_argument('--name', default='Admin User', help='Admin name')
    
    args = parser.parse_args()
    
    create_admin_user(args.email, args.password, args.name)
