"""Database models for early opportunity signals."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class SignalType(str, Enum):
    """Types of early opportunity signals."""

    SOURCES_SOUGHT = "sources_sought"
    RFI = "rfi"
    DRAFT_RFP = "draft_rfp"
    INDUSTRY_DAY = "industry_day"
    AGENCY_FORECAST = "agency_forecast"
    BUDGET_JUSTIFICATION = "budget_justification"
    EXPIRING_CONTRACT = "expiring_contract"
    PRE_SOLICITATION = "pre_solicitation"
    VENDOR_OUTREACH = "vendor_outreach"


class SignalStatus(str, Enum):
    """Status of early signal tracking."""

    NEW = "new"
    TRACKING = "tracking"
    RESPONDED = "responded"
    CONVERTED_TO_RFP = "converted_to_rfp"
    EXPIRED = "expired"
    NOT_PURSUED = "not_pursued"


class EarlySignal(Base):
    """Early opportunity signal detected before full RFP release."""

    __tablename__ = "early_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Signal identification
    signal_type = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    agency = Column(String(200), nullable=False)
    office = Column(String(200), nullable=True)

    # Details
    description = Column(Text, nullable=True)
    estimated_value = Column(Float, nullable=True)
    naics_code = Column(String(20), nullable=True)
    psc_code = Column(String(20), nullable=True)
    set_aside = Column(String(50), nullable=True)

    # Timeline
    signal_date = Column(DateTime, nullable=False)  # When we found this signal
    expected_rfp_date = Column(DateTime, nullable=True)  # Estimated RFP release
    response_deadline = Column(DateTime, nullable=True)  # If this signal needs response

    # Source information
    source_url = Column(String(1000), nullable=True)
    source_document = Column(String(500), nullable=True)  # Path to downloaded doc
    solicitation_number = Column(String(100), nullable=True)  # If available

    # Tracking
    status = Column(String(50), default=SignalStatus.NEW.value)
    converted_opportunity_id = Column(Integer, nullable=True)  # Links to Opportunity table

    # Scoring (how promising is this?)
    relevance_score = Column(Float, nullable=True)  # 0-100
    strategic_value = Column(Float, nullable=True)  # 0-100
    win_probability = Column(Float, nullable=True)  # 0-100

    # Action tracking
    actions_taken = Column(Text, nullable=True)  # JSON array of actions
    contacted_pco = Column(Boolean, default=False)
    attended_event = Column(Boolean, default=False)
    submitted_response = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(Text, nullable=True)

    def __repr__(self) -> str:
        """String representation."""
        return f"<EarlySignal(id={self.id}, type='{self.signal_type}', title='{self.title[:50]}...')>"


class AgencyForecast(Base):
    """Agency acquisition forecast tracking."""

    __tablename__ = "agency_forecasts"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Forecast identification
    agency = Column(String(200), nullable=False)
    fiscal_year = Column(Integer, nullable=False)
    quarter = Column(String(10), nullable=True)  # Q1, Q2, Q3, Q4

    # Forecast details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    estimated_value = Column(Float, nullable=True)
    naics_code = Column(String(20), nullable=True)
    psc_code = Column(String(20), nullable=True)
    set_aside = Column(String(50), nullable=True)

    # Timeline
    planned_award_date = Column(DateTime, nullable=True)
    planned_solicitation_date = Column(DateTime, nullable=True)

    # Source
    forecast_document_url = Column(String(1000), nullable=True)
    forecast_line_number = Column(String(50), nullable=True)

    # Tracking
    matched_to_signal_id = Column(Integer, nullable=True)  # Links to EarlySignal
    rfp_released = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        """String representation."""
        return f"<AgencyForecast(id={self.id}, agency='{self.agency}', FY{self.fiscal_year}, title='{self.title[:50]}...')>"


class IndustryDay(Base):
    """Industry day and vendor outreach event tracking."""

    __tablename__ = "industry_days"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Event details
    title = Column(String(500), nullable=False)
    agency = Column(String(200), nullable=False)
    office = Column(String(200), nullable=True)
    event_type = Column(String(50), nullable=False)  # industry_day, vendor_outreach, one_on_one

    # When/where
    event_date = Column(DateTime, nullable=False)
    location = Column(String(500), nullable=True)  # Virtual, or physical address
    is_virtual = Column(Boolean, default=True)
    registration_url = Column(String(1000), nullable=True)
    registration_deadline = Column(DateTime, nullable=True)

    # Related opportunity
    related_program = Column(String(500), nullable=True)
    estimated_value = Column(Float, nullable=True)
    naics_code = Column(String(20), nullable=True)
    set_aside = Column(String(50), nullable=True)

    # Tracking
    registered = Column(Boolean, default=False)
    attended = Column(Boolean, default=False)
    linked_signal_id = Column(Integer, nullable=True)

    # Notes
    key_contacts = Column(Text, nullable=True)  # JSON array
    meeting_notes = Column(Text, nullable=True)
    action_items = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        """String representation."""
        return f"<IndustryDay(id={self.id}, title='{self.title[:50]}...', date='{self.event_date}')>"
