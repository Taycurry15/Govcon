"""Create a test opportunity for workflow demonstration."""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))

from govcon.models.opportunity import Opportunity, OpportunityStatus, SetAsideType
from govcon.utils.database import get_async_db


async def create_test_opportunity() -> str:
    """Create a test opportunity in the database."""

    opportunity = Opportunity(
        solicitation_number="TEST-2025-001-DEMO",
        title="Cybersecurity Services for Federal Agency - SDVOSB Set-Aside",
        description="""
        The Department of Veterans Affairs is seeking a qualified Service-Disabled Veteran-Owned Small Business
        (SDVOSB) to provide comprehensive cybersecurity services including:

        - Zero Trust Architecture implementation
        - Identity, Credential, and Access Management (ICAM)
        - Risk Management Framework (RMF) compliance
        - Cybersecurity Maturity Model Certification (CMMC) preparation
        - SOC 2 and ISO 27001 compliance support
        - IT help desk services
        - Program Management Office (PMO) support

        This is a 12-month base period with four 12-month option periods.
        Estimated contract value: $2.5M - $5M.

        NAICS Code: 541512 (Computer Systems Design Services)
        PSC Code: D316 (IT & Telecom - Systems Development)
        """,
        agency="Department of Veterans Affairs",
        office="VA Office of Information and Technology",
        set_aside=SetAsideType.SDVOSB,
        naics_code="541512",
        psc_code="D316",
        posted_date=datetime.utcnow() - timedelta(days=2),
        response_deadline=datetime.utcnow() + timedelta(days=30),
        estimated_value=3500000.0,
        min_value=2500000.0,
        max_value=5000000.0,
        place_of_performance="Washington, DC (Remote work possible)",
        archive_date=datetime.utcnow() + timedelta(days=35),
        status=OpportunityStatus.DISCOVERED,
        naics_match=0.95,
        psc_match=0.90,
        shapeable=False,
        attachments={
            "rfp": "RFP_Document.pdf",
            "sow": "Statement_of_Work.pdf",
            "pricing": "Price_Schedule.xlsx",
            "section_l": "Section_L_Instructions.pdf",
            "section_m": "Section_M_Evaluation.pdf"
        },
        keywords=["cybersecurity", "zero trust", "ICAM", "RMF", "CMMC", "SDVOSB"],
        tags=["high-priority", "set-aside-match", "va-procurement"]
    )

    async with get_async_db() as db:
        db.add(opportunity)
        await db.commit()
        await db.refresh(opportunity)

        print(f"✓ Created test opportunity: {opportunity.id}")
        print(f"  Solicitation Number: {opportunity.solicitation_number}")
        print(f"  Title: {opportunity.title}")
        print(f"  Agency: {opportunity.agency}")
        print(f"  Set-Aside: {opportunity.set_aside.value}")
        print(f"  NAICS: {opportunity.naics_code}")
        print(f"  Estimated Value: ${opportunity.estimated_value:,.2f}")
        print(f"  Response Deadline: {opportunity.response_deadline}")

        return opportunity.id


if __name__ == "__main__":
    opportunity_id = asyncio.run(create_test_opportunity())
    print(f"\nUse this opportunity ID for workflow testing: {opportunity_id}")
