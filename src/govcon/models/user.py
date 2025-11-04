"""User and RBAC models."""

import enum
from datetime import datetime
from typing import Optional, cast
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from govcon.models.base import Base, SoftDeleteMixin, TimestampMixin


class Role(str, enum.Enum):
    """User roles for RBAC (from spec Section 12)."""

    ADMIN = "admin"  # Full system access
    CAPTURE_MANAGER = "capture_manager"  # Manage opportunities and proposals
    PROPOSAL_WRITER = "proposal_writer"  # Write and edit proposals
    PRICER = "pricer"  # Create and manage pricing
    REVIEWER = "reviewer"  # Review and comment on proposals
    SDVOSB_OFFICER = "sdvosb_officer"  # Manage set-aside certifications and attestations
    VIEWER = "viewer"  # Read-only access


class User(Base, TimestampMixin, SoftDeleteMixin):
    """User account."""

    __tablename__ = "users"

    # Primary Key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )

    # Basic Information
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(200), nullable=False)

    # Role & Permissions
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.VIEWER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Authentication
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # SDVOSB Officer (from spec Section 12)
    can_manage_certifications: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        """String representation."""
        return f"<User {self.email} ({self.role.value})>"

    def has_role(self, role: Role) -> bool:
        """Check if user has a specific role."""
        if self.is_superuser:
            return True
        current_role = cast(Role, self.role)
        return current_role == role

    def has_any_role(self, roles: list[Role]) -> bool:
        """Check if user has any of the specified roles."""
        if self.is_superuser:
            return True
        current_role = cast(Role, self.role)
        return current_role in roles

    def can_approve_pink_team(self) -> bool:
        """Check if user can approve pink team reviews."""
        return self.has_any_role([Role.ADMIN, Role.CAPTURE_MANAGER])

    def can_approve_gold_team(self) -> bool:
        """Check if user can approve gold team reviews."""
        return self.has_any_role([Role.ADMIN, Role.CAPTURE_MANAGER])

    def can_submit_proposal(self) -> bool:
        """Check if user can submit proposals."""
        return self.has_any_role([Role.ADMIN, Role.CAPTURE_MANAGER])

    def is_account_locked(self) -> bool:
        """Check if account is currently locked."""
        if not self.locked_until:
            return False
        return datetime.utcnow() < self.locked_until
