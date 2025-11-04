"""Tests for database models."""

from datetime import datetime

from govcon.models import Opportunity, OpportunityStatus, Proposal, ProposalStatus, SetAsideType


def test_opportunity_creation(db_session, mock_opportunity_data):
    """Test opportunity model creation."""
    opportunity = Opportunity(
        solicitation_number=mock_opportunity_data["solicitation_number"],
        title=mock_opportunity_data["title"],
        agency=mock_opportunity_data["agency"],
        posted_date=datetime.utcnow(),
        naics_code=mock_opportunity_data["naics_code"],
        set_aside=SetAsideType.SDVOSB,
    )

    db_session.add(opportunity)
    db_session.commit()

    assert opportunity.id is not None
    assert opportunity.status == OpportunityStatus.DISCOVERED
    assert opportunity.is_deleted is False


def test_opportunity_set_aside_match(db_session):
    """Test set-aside matching logic."""
    opportunity = Opportunity(
        solicitation_number="TEST-001",
        title="Test",
        agency="VA",
        posted_date=datetime.utcnow(),
        set_aside=SetAsideType.SDVOSB,
    )

    assert opportunity.is_set_aside_match(["SDVOSB", "VOSB"]) is True
    assert opportunity.is_set_aside_match(["WOSB"]) is False


def test_opportunity_va_procurement_detection(db_session):
    """Test VA procurement detection."""
    va_opp = Opportunity(
        solicitation_number="TEST-001",
        title="Test",
        agency="Department of Veterans Affairs",
        posted_date=datetime.utcnow(),
    )

    non_va_opp = Opportunity(
        solicitation_number="TEST-002",
        title="Test",
        agency="Department of Defense",
        posted_date=datetime.utcnow(),
    )

    assert va_opp.is_va_procurement() is True
    assert non_va_opp.is_va_procurement() is False


def test_proposal_creation(db_session):
    """Test proposal model creation."""
    # Create opportunity first
    opportunity = Opportunity(
        solicitation_number="TEST-001",
        title="Test Opportunity",
        agency="VA",
        posted_date=datetime.utcnow(),
    )
    db_session.add(opportunity)
    db_session.commit()

    # Create proposal
    proposal = Proposal(
        opportunity_id=opportunity.id,
        title="Test Proposal",
        version="1.0",
        status=ProposalStatus.DRAFT,
    )

    db_session.add(proposal)
    db_session.commit()

    assert proposal.id is not None
    assert proposal.opportunity_id == opportunity.id
    assert proposal.status == ProposalStatus.DRAFT


def test_soft_delete(db_session):
    """Test soft delete functionality."""
    opportunity = Opportunity(
        solicitation_number="TEST-001",
        title="Test",
        agency="VA",
        posted_date=datetime.utcnow(),
    )

    db_session.add(opportunity)
    db_session.commit()

    assert opportunity.is_deleted is False

    opportunity.soft_delete()
    db_session.commit()

    assert opportunity.is_deleted is True
    assert opportunity.deleted_at is not None
