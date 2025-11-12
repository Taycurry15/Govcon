"""Users and authentication API routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from govcon.models import Role, User
from govcon.utils.database import get_db_session
from govcon.utils.logger import get_logger
from govcon.utils.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

logger = get_logger(__name__)
router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/token")


class UserCreate(BaseModel):
    """User creation request."""

    email: EmailStr
    full_name: str
    password: str
    role: Role = Role.VIEWER


class UserResponse(BaseModel):
    """User response model."""

    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    can_manage_certifications: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Token response model."""

    access_token: str
    token_type: str


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db_session)
) -> User:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = await db.get(User, user_id)
    if user is None or user.is_deleted:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return user


@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db_session)
) -> dict[str, str]:
    """
    Login endpoint to get access token.

    Args:
        form_data: OAuth2 password request form
        db: Database session

    Returns:
        Access token
    """
    # Find user by email
    logger.info(f"Login attempt for email: {form_data.username}")
    query = select(User).where(User.email == form_data.username, User.is_deleted.is_(False))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"User not found: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info(f"User found: {user.email}, checking password...")
    password_valid = verify_password(form_data.password, user.hashed_password)
    logger.info(f"Password verification result: {password_valid}")

    if not password_valid:
        logger.warning(f"Invalid password for user: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Update last login
    user.last_login = datetime.utcnow()
    user.failed_login_attempts = 0
    await db.commit()

    # Create access token
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role.value}
    )

    logger.info(f"User {user.email} logged in")

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Create a new user (admin only).

    Args:
        user_data: User creation data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created user
    """
    # Check if current user is admin
    if current_user.role != Role.ADMIN and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Only admins can create users")

    # Check if email already exists
    query = select(User).where(User.email == user_data.email, User.is_deleted.is_(False))
    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hash_password(user_data.password),
        role=user_data.role,
        is_active=True,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"User {user.email} created by {current_user.email}")

    return user


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)) -> User:
    """Get current user information."""
    return current_user
