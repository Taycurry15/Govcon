#!/usr/bin/env python3
"""Create initial admin user for GovCon AI Pipeline."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from govcon.models.base import Base
from govcon.models.user import Role, User
from govcon.utils.config import get_settings
from govcon.utils.security import hash_password

settings = get_settings()


async def create_tables():
    """Create database tables."""
    # Convert postgres:// to postgresql+asyncpg://
    url = settings.postgres_url.replace("postgresql://", "postgresql+asyncpg://").replace(
        "postgres://", "postgresql+asyncpg://"
    )

    engine = create_async_engine(url, echo=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return engine


async def create_admin_user(engine):
    """Create initial admin user."""
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if admin user already exists
        result = await session.execute(select(User).where(User.email == "admin@bronzeshield.com"))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print("\n⚠️  Admin user already exists!")
            print("   Email: admin@bronzeshield.com")
            return

        # Create admin user
        admin_user = User(
            email="admin@bronzeshield.com",
            full_name="System Administrator",
            hashed_password=hash_password("Admin123!"),
            role=Role.ADMIN,
            is_active=True,
            is_superuser=True,
            can_manage_certifications=True,
        )

        session.add(admin_user)
        await session.commit()
        await session.refresh(admin_user)

        print("\n✅ Admin user created successfully!")
        print(f"   User ID: {admin_user.id}")
        print(f"   Email: {admin_user.email}")
        print(f"   Role: {admin_user.role.value}")

    await engine.dispose()


async def main():
    """Main function."""
    print("=" * 60)
    print("GovCon AI Pipeline - Admin User Setup")
    print("=" * 60)
    print()
    print(
        f"Database: {settings.postgres_url.split('@')[1] if '@' in settings.postgres_url else settings.postgres_url}"
    )
    print()

    try:
        print("Creating database tables...")
        engine = await create_tables()
        print("✅ Tables created/verified")
        print()

        print("Creating admin user...")
        await create_admin_user(engine)
        print()

        print("=" * 60)
        print("LOGIN CREDENTIALS")
        print("=" * 60)
        print()
        print("  API Base URL:  http://localhost:8000")
        print("  Email:         admin@bronzeshield.com")
        print("  Password:      Admin123!")
        print()
        print("  Frontend URL:  http://localhost")
        print()
        print("=" * 60)
        print()
        print("📝 IMPORTANT NOTES:")
        print("   1. Change the admin password after first login")
        print("   2. The API is currently not starting due to agent")
        print("      initialization issues with strict JSON schema")
        print("   3. Once logged in, you can create additional users")
        print("      with different roles (Capture Manager, Writer, etc.)")
        print()
        print("🔐 API Authentication:")
        print("   POST /api/users/token")
        print("   Body: {")
        print('     "username": "admin@bronzeshield.com",')
        print('     "password": "Admin123!"')
        print("   }")
        print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
