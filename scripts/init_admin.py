#!/usr/bin/env python3
"""Simple script to create admin user - runs with basic dependencies."""

import uuid

import bcrypt
import psycopg2

# Database connection
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "govcon"
DB_USER = "bronze"
DB_PASSWORD = "password"

# Admin credentials
ADMIN_EMAIL = "admin@bronzeshield.com"
ADMIN_PASSWORD = "Admin123!"
ADMIN_FULL_NAME = "System Administrator"

print("=" * 60)
print("GovCon AI Pipeline - Admin User Setup")
print("=" * 60)
print()

try:
    # Connect to database
    print(f"Connecting to database: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    cursor = conn.cursor()
    print("✅ Connected to database")
    print()

    # Create users table
    print("Creating users table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(200) UNIQUE NOT NULL,
            full_name VARCHAR(200) NOT NULL,
            hashed_password VARCHAR(200) NOT NULL,
            role VARCHAR(50) NOT NULL DEFAULT 'viewer',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
            last_login TIMESTAMP WITH TIME ZONE,
            failed_login_attempts INTEGER NOT NULL DEFAULT 0,
            locked_until TIMESTAMP WITH TIME ZONE,
            can_manage_certifications BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMP WITH TIME ZONE,
            is_deleted BOOLEAN NOT NULL DEFAULT FALSE
        )
    """)
    conn.commit()
    print("✅ Users table created/verified")
    print()

    # Check if admin exists
    cursor.execute("SELECT id, email FROM users WHERE email = %s", (ADMIN_EMAIL,))
    existing = cursor.fetchone()

    if existing:
        print("⚠️  Admin user already exists!")
        print(f"   User ID: {existing[0]}")
        print(f"   Email: {existing[1]}")
    else:
        # Hash password
        print("Hashing password...")
        password_bytes = ADMIN_PASSWORD.encode("utf-8")
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password_bytes, salt).decode("utf-8")
        print("✅ Password hashed")
        print()

        # Create admin user
        print("Creating admin user...")
        user_id = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT INTO users (
                id, email, full_name, hashed_password, role,
                is_active, is_superuser, can_manage_certifications
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s
            )
        """,
            (user_id, ADMIN_EMAIL, ADMIN_FULL_NAME, hashed_password, "admin", True, True, True),
        )
        conn.commit()
        print("✅ Admin user created successfully!")
        print(f"   User ID: {user_id}")
        print(f"   Email: {ADMIN_EMAIL}")
        print("   Role: admin")

    print()
    print("=" * 60)
    print("LOGIN CREDENTIALS")
    print("=" * 60)
    print()
    print("  Frontend URL:  http://localhost")
    print("  Email:         admin@bronzeshield.com")
    print("  Password:      Admin123!")
    print()
    print("  API Base URL:  http://localhost:8000")
    print()
    print("=" * 60)
    print()
    print("📝 IMPORTANT NOTES:")
    print("   1. Change the admin password after first login")
    print("   2. The API is currently not starting due to")
    print("      openai-agents strict JSON schema issues")
    print("   3. To fix the API, the agent Pydantic models need")
    print("      further refactoring or the openai-agents library")
    print("      needs to be updated")
    print()
    print("🔐 API Authentication (when API is working):")
    print("   POST http://localhost:8000/api/users/token")
    print("   Content-Type: application/x-www-form-urlencoded")
    print("   Body: username=admin@bronzeshield.com&password=Admin123!")
    print()

    cursor.close()
    conn.close()

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback

    traceback.print_exc()
    exit(1)
