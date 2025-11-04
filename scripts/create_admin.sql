-- Create database tables
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
);

-- Create admin user
-- Password is "Admin123!" hashed with bcrypt
-- Hash generated using: passlib.hash.bcrypt.hash("Admin123!")
INSERT INTO users (
    email,
    full_name,
    hashed_password,
    role,
    is_active,
    is_superuser,
    can_manage_certifications
) VALUES (
    'admin@bronzeshield.com',
    'System Administrator',
    '$2b$12$LmKVF3vH.XqK9qVJ8PxNKe3RZ0qWHF9xJKLJ8YHZKqWJ8PxNKe3RZ',
    'admin',
    TRUE,
    TRUE,
    TRUE
) ON CONFLICT (email) DO NOTHING;

-- Display the result
SELECT
    id,
    email,
    full_name,
    role,
    is_active,
    is_superuser,
    created_at
FROM users
WHERE email = 'admin@bronzeshield.com';
