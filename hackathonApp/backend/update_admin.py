#!/usr/bin/env python3
"""Script to update admin user credentials"""
import sys
import os
import sqlite3

# Direct database access without Flask app
def update_admin_user(email, password):
    """Update admin user directly in database"""
    # Check multiple possible database locations
    db_paths = [
        os.path.join(os.path.dirname(__file__), 'hackathon_app.db'),
        os.path.join(os.path.dirname(__file__), 'instance', 'hackathon_app.db'),
        os.path.join(os.path.dirname(__file__), '..', 'hackathon_app.db'),
    ]
    
    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        # Try to find any .db file
        for root, dirs, files in os.walk(os.path.dirname(__file__)):
            for file in files:
                if file.endswith('.db'):
                    db_path = os.path.join(root, file)
                    break
            if db_path:
                break
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return False
    
    # Import bcrypt for password hashing
    import bcrypt
    
    # Hash password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if user exists
        cursor.execute("SELECT id, email, role FROM workers WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if user:
            user_id, user_email, user_role = user
            print(f"✓ Found user: {user_email} (ID: {user_id}, Role: {user_role})")
            
            # Update password and ensure admin role
            cursor.execute("""
                UPDATE workers 
                SET password_hash = ?, role = 'admin', is_active = 1
                WHERE email = ?
            """, (password_hash, email))
            
            conn.commit()
            print(f"✓ Admin user updated successfully!")
            print(f"  Email: {email}")
            print(f"  Password: {password}")
            print(f"  Role: admin")
            return True
        else:
            # Create new admin user
            cursor.execute("""
                INSERT INTO workers (workday_id, email, name, password_hash, role, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (f"admin-{email}", email, "Admin User", password_hash, "admin", 1))
            
            conn.commit()
            print(f"✓ Admin user created successfully!")
            print(f"  Email: {email}")
            print(f"  Password: {password}")
            print(f"  Role: admin")
            return True
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    update_admin_user('admin@hackathon.com', 'password')
