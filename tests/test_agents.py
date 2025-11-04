"""Tests for agent functionality."""

from datetime import datetime

import pytest

from govcon.agents.bid_nobid import BidNoBidAgent
from govcon.agents.discovery import DiscoveryAgent
from govcon.models import Opportunity, SetAsideType


@pytest.mark.asyncio
async def test_discovery_agent():
    """Test discovery agent."""
    agent = DiscoveryAgent()

    result = await agent.discover(days_back=7)

    assert result is not None
    assert result.execution_time > 0


@pytest.mark.asyncio
async def test_bid_nobid_agent():
    """Test bid/no-bid agent scoring."""
    agent = BidNoBidAgent()

    opportunity = Opportunity(
        id="test-opp-1",
        solicitation_number="TEST-001",
        title="Cybersecurity Services",
        agency="Department of Veterans Affairs",
        posted_date=datetime.utcnow(),
        naics_code="541512",
        psc_code="D310",
        set_aside=SetAsideType.SDVOSB,
        naics_match=0.9,
        psc_match=0.8,
        shapeable=False,
    )

    score = await agent.score(opportunity)

    assert score is not None
    assert score.total_score >= 0.0
    assert score.recommendation in ["BID", "NO_BID", "REVIEW"]
