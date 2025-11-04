"""Audit logging models for compliance and tracking."""

import enum
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from govcon.models.base import Base


class AuditAction(str, enum.Enum):
    """Types of auditable actions."""

    # Discovery
    OPPORTUNITY_DISCOVERED = "opportunity_discovered"
    OPPORTUNITY_UPDATED = "opportunity_updated"

    # Bid/No-Bid
    BID_ANALYSIS_RUN = "bid_analysis_run"
    BID_DECISION_MADE = "bid_decision_made"

    # Approvals
    PINK_TEAM_APPROVED = "pink_team_approved"
    PINK_TEAM_REJECTED = "pink_team_rejected"
    GOLD_TEAM_APPROVED = "gold_team_approved"
    GOLD_TEAM_REJECTED = "gold_team_rejected"

    # Proposal
    PROPOSAL_CREATED = "proposal_created"
    PROPOSAL_UPDATED = "proposal_updated"
    VOLUME_GENERATED = "volume_generated"
    COMPLIANCE_MATRIX_GENERATED = "compliance_matrix_generated"
    RTM_GENERATED = "rtm_generated"

    # Pricing
    PRICING_GENERATED = "pricing_generated"
    PRICING_UPDATED = "pricing_updated"
    RATE_CARD_CREATED = "rate_card_created"

    # Communications
    QUESTION_DRAFTED = "question_drafted"
    EMAIL_DRAFTED = "email_drafted"

    # Submission
    PROPOSAL_SUBMITTED = "proposal_submitted"
    SUBMISSION_CONFIRMED = "submission_confirmed"

    # Security
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    PERMISSION_DENIED = "permission_denied"
    CERTIFICATION_ACCESSED = "certification_accessed"

    # Agent Actions
    AGENT_TOOL_CALLED = "agent_tool_called"
    AGENT_ERROR = "agent_error"

    # Data
    FILE_UPLOADED = "file_uploaded"
    FILE_DOWNLOADED = "file_downloaded"
    FILE_DELETED = "file_deleted"

    # Other
    OTHER = "other"


class AuditLog(Base):
    """Audit log for tracking all system actions."""

    __tablename__ = "audit_logs"

    # Primary Key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )

    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Action
    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction), nullable=False)
    action_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Actor
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    user_email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    user_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    agent_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Target
    resource_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # opportunity, proposal, etc.
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Details
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Request Context
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Security Context
    is_security_event: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_compliance_event: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Hash for integrity (from spec Section 12)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    def __repr__(self) -> str:
        """String representation."""
        return f"<AuditLog {self.action.value} by {self.user_email or self.agent_name} at {self.timestamp}>"
