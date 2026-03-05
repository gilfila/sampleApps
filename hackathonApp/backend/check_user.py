#!/usr/bin/env python3
"""Script to check and verify admin user"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Worker
from app.utils.auth import verify_password, hash_password

def check_user(email):
    """Check user and test password"""
    app = create_app('development')
    
    with app.app_context():
        user = Worker.query.filter_by(email=email).first()
        
        if not user:
            print(f"❌ User with email {email} not found!")
            return
        
        print(f"✓ User found:")
        print(f"  ID: {user.id}")
        print(f"  Email: {user.email}")
        print(f"  Name: {user.name}")
        print(f"  Role: {user.role.value}")
        print(f"  Has password: {user.password_hash is not None}")
        print(f"  Is active: {user.is_active}")
        
        if user.password_hash:
            # Test password
            test_password = "password"
            is_valid = verify_password(test_password, user.password_hash)
            print(f"\n  Testing password 'password': {is_valid}")
            
            if not is_valid:
                print(f"\n  ❌ Password verification failed!")
                print(f"  Re-hashing password...")
                user.password_hash = hash_password(test_password)
                db.session.commit()
                print(f"  ✓ Password re-hashed and saved")
                
                # Test again
                is_valid = verify_password(test_password, user.password_hash)
                print(f"  Testing again: {is_valid}")
        else:
            print(f"\n  ❌ No password hash set!")
            print(f"  Setting password...")
            user.password_hash = hash_password("password")
            db.session.commit()
            print(f"  ✓ Password set")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Check admin user')
    parser.add_argument('--email', default='admin@hackathon.com', help='Admin email address')
    args = parser.parse_args()
    check_user(args.email)
