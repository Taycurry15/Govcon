"""Security utilities for authentication and authorization."""

import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional

import bcrypt
from jose import JWTError, jwt

from govcon.models.user import Role, User
from govcon.utils.config import get_settings
from govcon.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash."""
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.

    Args:
        data: Payload data to encode
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiry_hours)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    encoded_jwt = jwt.encode(to_encode, settings.jwt_signing_key, algorithm=settings.jwt_algorithm)

    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """
    Decode and verify JWT access token.

    Args:
        token: JWT token to decode

    Returns:
        Decoded payload or None if invalid
    """
    try:
        payload = jwt.decode(token, settings.jwt_signing_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


def check_permission(user: User, required_role: Role) -> bool:
    """
    Check if user has required role.

    Args:
        user: User to check
        required_role: Required role

    Returns:
        True if user has permission
    """
    if user.is_superuser:
        return True

    # Role hierarchy
    role_hierarchy = {
        Role.ADMIN: 100,
        Role.CAPTURE_MANAGER: 80,
        Role.SDVOSB_OFFICER: 70,
        Role.PROPOSAL_WRITER: 60,
        Role.PRICER: 60,
        Role.REVIEWER: 40,
        Role.VIEWER: 20,
    }

    user_level = role_hierarchy.get(user.role, 0)
    required_level = role_hierarchy.get(required_role, 0)

    return user_level >= required_level


def hash_content(content: str) -> str:
    """
    Generate SHA-256 hash of content for audit integrity.

    Args:
        content: Content to hash

    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(content.encode()).hexdigest()


def encrypt_data(data: str, key: Optional[str] = None) -> str:
    """
    Encrypt sensitive data (placeholder - implement with proper encryption).

    Args:
        data: Data to encrypt
        key: Encryption key (optional, uses settings if not provided)

    Returns:
        Encrypted data
    """
    if key:
        logger.debug("Custom key provided to encrypt_data placeholder.")
    # TODO: Implement actual encryption (AES-256, Fernet, etc.)
    # This is a placeholder
    logger.warning("encrypt_data is a placeholder - implement proper encryption")
    return data


def decrypt_data(encrypted_data: str, key: Optional[str] = None) -> str:
    """
    Decrypt sensitive data (placeholder - implement with proper decryption).

    Args:
        encrypted_data: Data to decrypt
        key: Decryption key (optional, uses settings if not provided)

    Returns:
        Decrypted data
    """
    if key:
        logger.debug("Custom key provided to decrypt_data placeholder.")
    # TODO: Implement actual decryption
    logger.warning("decrypt_data is a placeholder - implement proper decryption")
    return encrypted_data
