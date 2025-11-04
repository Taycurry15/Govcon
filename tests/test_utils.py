"""Tests for utility functions."""

from govcon.models.user import Role, User
from govcon.utils.security import (
    check_permission,
    create_access_token,
    decode_access_token,
    hash_content,
    hash_password,
    verify_password,
)


def test_password_hashing():
    """Test password hashing and verification."""
    password = "SecurePassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_creation_and_decoding():
    """Test JWT token creation and decoding."""
    data = {"sub": "user123", "email": "user@example.com"}

    token = create_access_token(data)
    assert token is not None

    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user123"
    assert decoded["email"] == "user@example.com"


def test_permission_checking():
    """Test permission checking."""
    admin_user = User(
        id="admin-1",
        email="admin@example.com",
        full_name="Admin User",
        hashed_password="hashed",
        role=Role.ADMIN,
    )

    viewer_user = User(
        id="viewer-1",
        email="viewer@example.com",
        full_name="Viewer User",
        hashed_password="hashed",
        role=Role.VIEWER,
    )

    # Admin can do everything
    assert check_permission(admin_user, Role.ADMIN) is True
    assert check_permission(admin_user, Role.VIEWER) is True

    # Viewer can only view
    assert check_permission(viewer_user, Role.VIEWER) is True
    assert check_permission(viewer_user, Role.ADMIN) is False


def test_content_hashing():
    """Test content hashing for audit integrity."""
    content = "Test content for hashing"
    hash1 = hash_content(content)
    hash2 = hash_content(content)

    # Same content should produce same hash
    assert hash1 == hash2

    # Different content should produce different hash
    hash3 = hash_content("Different content")
    assert hash1 != hash3

    # Hash should be hexadecimal
    assert len(hash1) == 64  # SHA-256 produces 64 hex characters
