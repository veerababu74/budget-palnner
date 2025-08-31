#!/usr/bin/env python3
"""
Database initialization script for PythonAnywhere deployment
"""
import os
import sys

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import Base, engine, get_db, User, pwd_context


def init_database():
    """Initialize the database and create tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

    # Create a default admin user if it doesn't exist
    db = next(get_db())
    try:
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            hashed_password = pwd_context.hash("admin123")  # Change this password!
            admin_user = User(
                username="admin",
                email="admin@example.com",
                hashed_password=hashed_password,
            )
            db.add(admin_user)
            db.commit()
            print("Default admin user created: username='admin', password='admin123'")
            print("Please change the default password after first login!")
        else:
            print("Admin user already exists")
    except Exception as e:
        print(f"Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_database()
