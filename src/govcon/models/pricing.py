"""Pricing models for labor rates and cost estimation."""

import enum
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import JSON, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from govcon.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from govcon.models.proposal import Proposal


class DataSource(str, enum.Enum):
    """Source of pricing data."""

    BLS_OES = "bls_oes"  # Bureau of Labor Statistics Occupational Employment Statistics
    SCA_WD = "sca_wd"  # Service Contract Act Wage Determination
    GSA_CALC = "gsa_calc"  # GSA Contract-Awarded Labor Category
    INTERNAL = "internal"  # Internal rate card
    MARKET = "market"  # Market research
    OTHER = "other"


class PricingWorkbook(Base, TimestampMixin):
    """Pricing workbook for a proposal."""

    __tablename__ = "pricing_workbooks"

    # Primary Key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )

    # Foreign Key
    proposal_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("proposals.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Basic Information
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="1.0", nullable=False)

    # Wrap Rates (from spec Section 6)
    fringe_rate: Mapped[float] = mapped_column(Float, default=30.0, nullable=False)  # %
    overhead_rate: Mapped[float] = mapped_column(Float, default=15.0, nullable=False)  # %
    ga_rate: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)  # %
    fee_rate: Mapped[float] = mapped_column(Float, default=8.0, nullable=False)  # %

    # Locality Adjustments
    locality: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    locality_adjustment: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    # Total Cost Estimates
    total_labor_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_odc_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # BOE (Basis of Estimate) - from spec Section 6
    boe_narrative: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assumptions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    data_sources: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Sensitivity Analysis
    sensitivity_analysis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Document Management
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Metadata
    extra_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    # Relationships
    proposal: Mapped["Proposal"] = relationship("Proposal", back_populates="pricing")
    labor_categories: Mapped[list["LaborCategory"]] = relationship(
        "LaborCategory", back_populates="workbook", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<PricingWorkbook {self.name}>"

    def calculate_fully_burdened_rate(self, base_rate: float) -> float:
        """Calculate fully burdened rate from base rate."""
        fringe_rate = float(self.fringe_rate)
        overhead_rate = float(self.overhead_rate)
        ga_rate = float(self.ga_rate)
        fee_rate = float(self.fee_rate)

        fringe = base_rate * (fringe_rate / 100)
        overhead = (base_rate + fringe) * (overhead_rate / 100)
        ga = (base_rate + fringe + overhead) * (ga_rate / 100)
        fee = (base_rate + fringe + overhead + ga) * (fee_rate / 100)
        return float(base_rate + fringe + overhead + ga + fee)


class LaborCategory(Base, TimestampMixin):
    """Labor category with pricing information."""

    __tablename__ = "labor_categories"

    # Primary Key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )

    # Foreign Key
    workbook_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("pricing_workbooks.id", ondelete="CASCADE"), nullable=False
    )

    # Basic Information
    lcat_code: Mapped[str] = mapped_column(String(50), nullable=False)
    lcat_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # SOC Mapping (from spec Section 6)
    soc_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    soc_title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Rates
    base_rate: Mapped[float] = mapped_column(Float, nullable=False)  # $/hour
    fringe: Mapped[float] = mapped_column(Float, nullable=False)
    overhead: Mapped[float] = mapped_column(Float, nullable=False)
    ga: Mapped[float] = mapped_column(Float, nullable=False)
    fee: Mapped[float] = mapped_column(Float, nullable=False)
    fully_burdened_rate: Mapped[float] = mapped_column(Float, nullable=False)

    # Hours/FTEs
    estimated_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    estimated_ftes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Data Source (from spec Section 6)
    data_source: Mapped[DataSource] = mapped_column(Enum(DataSource), nullable=False)
    data_source_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Requirements
    education_requirements: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    experience_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    clearance_required: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Metadata
    extra_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    # Relationships
    workbook: Mapped["PricingWorkbook"] = relationship(
        "PricingWorkbook", back_populates="labor_categories"
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<LaborCategory {self.lcat_code}: {self.lcat_name}>"


class RateCard(Base, TimestampMixin):
    """Company rate card for labor categories."""

    __tablename__ = "rate_cards"

    # Primary Key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )

    # Basic Information
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiration_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Contract Vehicle (if applicable)
    contract_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contract_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Rates
    rates: Mapped[dict] = mapped_column(JSON, nullable=False)  # LCAT -> Rate mapping

    # Geographic Scope
    geographic_scope: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)

    # Approval
    approved: Mapped[bool] = mapped_column(default=False, nullable=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Metadata
    extra_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    def __repr__(self) -> str:
        """String representation."""
        return f"<RateCard {self.name} v{self.version}>"
