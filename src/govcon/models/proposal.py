"""Proposal models for proposal generation and management."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from govcon.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from govcon.models.opportunity import Opportunity
    from govcon.models.pricing import PricingWorkbook


class ProposalStatus(str, enum.Enum):
    """Status of a proposal in development."""

    DRAFT = "draft"
    COMPLIANCE_REVIEW = "compliance_review"
    TECHNICAL_WRITING = "technical_writing"
    PRICING = "pricing"
    PINK_TEAM = "pink_team"
    RED_TEAM = "red_team"
    GOLD_TEAM = "gold_team"
    READY_FOR_SUBMISSION = "ready_for_submission"
    SUBMITTED = "submitted"


class VolumeType(str, enum.Enum):
    """Types of proposal volumes."""

    ADMINISTRATIVE = "administrative"
    TECHNICAL = "technical"
    PRICING = "pricing"
    PAST_PERFORMANCE = "past_performance"
    OTHER = "other"


class Proposal(Base, TimestampMixin, SoftDeleteMixin):
    """Proposal for a federal opportunity."""

    __tablename__ = "proposals"

    # Primary Key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )

    # Foreign Key
    opportunity_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False
    )

    # Basic Information
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="1.0", nullable=False)
    status: Mapped[ProposalStatus] = mapped_column(
        Enum(ProposalStatus), default=ProposalStatus.DRAFT, nullable=False
    )

    # Compliance & RTM (from spec Section 4)
    compliance_matrix: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    rtm: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # Requirements Traceability Matrix
    required_certifications: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    page_limits: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    font_requirements: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    submission_portal: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # SDVOSB/VOSB Narrative (from spec Section 5 & 11)
    sdvosb_narrative: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vetcert_required: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Content
    executive_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    technical_approach: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    management_approach: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Q&A Tracking (from spec Section 7)
    questions: Mapped[Optional[list[dict]]] = mapped_column(JSON, nullable=True)
    amendments: Mapped[Optional[list[dict]]] = mapped_column(JSON, nullable=True)

    # Document Management
    output_files: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # MinIO paths
    templates_used: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Review History
    pink_team_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    red_team_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gold_team_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Submission
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    submission_confirmation: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Metadata
    extra_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    # Relationships
    opportunity: Mapped["Opportunity"] = relationship("Opportunity", back_populates="proposals")
    volumes: Mapped[list["ProposalVolume"]] = relationship(
        "ProposalVolume", back_populates="proposal", cascade="all, delete-orphan"
    )
    pricing: Mapped[Optional["PricingWorkbook"]] = relationship(
        "PricingWorkbook", back_populates="proposal", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<Proposal {self.id}: {self.title[:50]}>"


class ProposalVolume(Base, TimestampMixin):
    """Individual volumes of a proposal."""

    __tablename__ = "proposal_volumes"

    # Primary Key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )

    # Foreign Key
    proposal_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("proposals.id", ondelete="CASCADE"), nullable=False
    )

    # Basic Information
    volume_type: Mapped[VolumeType] = mapped_column(Enum(VolumeType), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    order: Mapped[int] = mapped_column(default=0, nullable=False)

    # Content
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sections: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Constraints
    page_limit: Mapped[Optional[int]] = mapped_column(nullable=True)
    current_page_count: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Document Management
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_format: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Citations (from spec Section 5)
    chunk_citations: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)

    # Metadata
    extra_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    # Relationships
    proposal: Mapped["Proposal"] = relationship("Proposal", back_populates="volumes")

    def __repr__(self) -> str:
        """String representation."""
        return f"<ProposalVolume {self.volume_type.value}: {self.title}>"
