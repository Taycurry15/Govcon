"""Opportunity model for federal contracting opportunities."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from govcon.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from govcon.models.proposal import Proposal


class OpportunityStatus(str, enum.Enum):
    """Status of an opportunity in the pipeline."""

    DISCOVERED = "discovered"
    SCREENING = "screening"
    AWAITING_PINK_TEAM = "awaiting_pink_team"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    AWAITING_GOLD_TEAM = "awaiting_gold_team"
    SUBMITTED = "submitted"
    AWARDED = "awarded"
    LOST = "lost"
    WITHDRAWN = "withdrawn"


class SetAsideType(str, enum.Enum):
    """Set-aside types for federal opportunities."""

    SDVOSB = "SDVOSB"  # Service-Disabled Veteran-Owned Small Business
    VOSB = "VOSB"  # Veteran-Owned Small Business
    SB = "SB"  # Small Business
    WOSB = "WOSB"  # Women-Owned Small Business
    HUBZONE = "HUBZone"  # Historically Underutilized Business Zone
    EIGHT_A = "8(a)"  # 8(a) Business Development Program
    OPEN = "Open"  # Open/unrestricted


class Opportunity(Base, TimestampMixin, SoftDeleteMixin):
    """Federal contracting opportunity."""

    __tablename__ = "opportunities"

    # Primary Key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )

    # Basic Information
    solicitation_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    agency: Mapped[str] = mapped_column(String(200), nullable=False)
    office: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # URLs and External IDs
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Dates
    posted_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    response_deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    archive_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Classification
    naics_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    psc_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    set_aside: Mapped[Optional[SetAsideType]] = mapped_column(Enum(SetAsideType), nullable=True)

    # Contract Details
    contract_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    place_of_performance: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Value Estimates
    estimated_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Pipeline Status
    status: Mapped[OpportunityStatus] = mapped_column(
        Enum(OpportunityStatus), default=OpportunityStatus.DISCOVERED, nullable=False
    )

    # Scoring & Analysis (from spec Section 2 & 3)
    naics_match: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0.0 to 1.0
    psc_match: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0.0 to 1.0
    shapeable: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # Sources Sought/RFI

    # Bid/No-Bid Scoring (from spec Section 3)
    bid_score_total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bid_score_set_aside: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bid_score_scope: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bid_score_timeline: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bid_score_competition: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bid_score_staffing: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bid_score_pricing: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bid_score_strategic: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bid_recommendation: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # BID, NO_BID, REVIEW
    bid_analysis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Approval Gates
    pink_team_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pink_team_approved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pink_team_approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    gold_team_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    gold_team_approved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    gold_team_approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Document Management
    attachments: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # List of attachment metadata
    parsed_sections: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # Parsed C/L/M sections

    # Vector Embeddings
    embedding_ids: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Qdrant IDs

    # Metadata
    keywords: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    tags: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    # Relationships
    proposals: Mapped[list["Proposal"]] = relationship(
        "Proposal", back_populates="opportunity", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<Opportunity {self.solicitation_number}: {self.title[:50]}>"

    def is_set_aside_match(self, preferences: list[str]) -> bool:
        """Check if opportunity matches set-aside preferences."""
        if not self.set_aside:
            return False
        return self.set_aside.value in preferences

    def is_naics_match(self, allowed_naics: list[str]) -> bool:
        """Check if NAICS code is in allowed list."""
        if not self.naics_code:
            return False
        return self.naics_code in allowed_naics

    def is_psc_match(self, allowed_psc: list[str]) -> bool:
        """Check if PSC code is in allowed list."""
        if not self.psc_code:
            return False
        return self.psc_code in allowed_psc

    def days_until_deadline(self) -> Optional[int]:
        """Calculate days until response deadline."""
        response_deadline = self.response_deadline
        if response_deadline is None:
            return None
        delta = response_deadline - datetime.utcnow()
        return int(delta.days)

    def is_va_procurement(self) -> bool:
        """Check if this is a VA procurement (triggers Vets First logic)."""
        if not self.agency:
            return False
        return "VA" in self.agency.upper() or "VETERAN" in self.agency.upper()
