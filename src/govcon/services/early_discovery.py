"""Early opportunity discovery service - find opportunities months before RFP."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from govcon.models.early_signals import (
    AgencyForecast,
    Base,
    EarlySignal,
    IndustryDay,
    SignalStatus,
    SignalType,
)
from govcon.utils.config import get_settings
from govcon.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class EarlyDiscoveryService:
    """Service for discovering opportunities before they reach SAM.gov RFP stage."""

    def __init__(self) -> None:
        """Initialize early discovery service."""
        engine = create_engine(settings.postgres_url)
        Base.metadata.create_all(bind=engine)
        self.SessionLocal = sessionmaker(bind=engine)
        self.http_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))

    async def scan_sources_sought(
        self,
        naics_codes: Optional[list[str]] = None,
        set_aside: Optional[str] = None,
        days_back: int = 7,
    ) -> list[EarlySignal]:
        """
        Scan SAM.gov for Sources Sought and RFI notices (pre-RFP signals).

        Args:
            naics_codes: Filter by NAICS codes
            set_aside: Filter by set-aside type (e.g., 'SDVOSB')
            days_back: How many days back to search

        Returns:
            List of EarlySignal objects created
        """
        logger.info("Scanning SAM.gov for Sources Sought notices")

        naics_codes = naics_codes or settings.allowed_naics
        signals_created = []

        try:
            # SAM.gov Opportunities API
            # https://open.gsa.gov/api/opportunities-api/
            base_url = "https://api.sam.gov/opportunities/v2/search"

            params = {
                "api_key": settings.sam_api_key if hasattr(settings, "sam_api_key") else "",
                "postedFrom": (datetime.utcnow() - timedelta(days=days_back)).strftime("%m/%d/%Y"),
                "postedTo": datetime.utcnow().strftime("%m/%d/%Y"),
                "ptype": "r,s,i",  # r=Sources Sought, s=Special Notice, i=Intent to Bundle
                "limit": 100,
            }

            # Add set-aside filter
            if set_aside:
                params["typeOfSetAside"] = set_aside

            response = await self.http_client.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()

            opportunities = data.get("opportunitiesData", [])
            logger.info(f"Found {len(opportunities)} pre-RFP notices on SAM.gov")

            db = self.SessionLocal()
            try:
                for opp in opportunities:
                    # Determine signal type
                    notice_type = opp.get("type", "").lower()
                    if "sources sought" in notice_type or notice_type == "r":
                        signal_type = SignalType.SOURCES_SOUGHT
                    elif "rfi" in notice_type or "information" in notice_type:
                        signal_type = SignalType.RFI
                    elif "presolicitation" in notice_type or "pre-solicitation" in notice_type:
                        signal_type = SignalType.PRE_SOLICITATION
                    else:
                        signal_type = SignalType.SOURCES_SOUGHT  # default

                    # Check if we already have this signal
                    solicitation_number = opp.get("noticeId") or opp.get("solicitationNumber")
                    existing = (
                        db.query(EarlySignal)
                        .filter(EarlySignal.solicitation_number == solicitation_number)
                        .first()
                    )

                    if existing:
                        logger.debug(f"Signal already exists: {solicitation_number}")
                        continue

                    # Extract NAICS and filter
                    naics = opp.get("naicsCode")
                    if naics_codes and naics not in naics_codes:
                        continue

                    # Create signal
                    signal = EarlySignal(
                        signal_type=signal_type.value,
                        title=opp.get("title", "")[:500],
                        agency=opp.get("department", "")[:200] or opp.get("subtier", "")[:200],
                        office=opp.get("office", "")[:200],
                        description=opp.get("description", ""),
                        naics_code=naics,
                        psc_code=opp.get("classificationCode"),
                        set_aside=opp.get("typeOfSetAside"),
                        signal_date=datetime.utcnow(),
                        response_deadline=self._parse_date(opp.get("responseDeadLine")),
                        source_url=f"https://sam.gov/opp/{solicitation_number}/view" if solicitation_number else None,
                        solicitation_number=solicitation_number,
                        status=SignalStatus.NEW.value,
                    )

                    # Score relevance
                    signal.relevance_score = self._score_signal(signal)

                    db.add(signal)
                    signals_created.append(signal)
                    logger.info(f"Created signal: {signal.title[:50]}... (Type: {signal_type.value})")

                db.commit()
                logger.info(f"Created {len(signals_created)} new early signals from Sources Sought")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error scanning Sources Sought: {e}")

        return signals_created

    async def scan_expiring_contracts(
        self,
        naics_codes: Optional[list[str]] = None,
        set_aside: Optional[str] = None,
        months_ahead: int = 12,
    ) -> list[EarlySignal]:
        """
        Find expiring contracts using USASpending.gov API (guaranteed re-competes).

        Args:
            naics_codes: Filter by NAICS codes
            set_aside: Filter by set-aside type
            months_ahead: Look for contracts expiring in next N months

        Returns:
            List of EarlySignal objects for re-compete opportunities
        """
        logger.info(f"Scanning USASpending.gov for contracts expiring in next {months_ahead} months")

        naics_codes = naics_codes or settings.allowed_naics
        signals_created = []

        try:
            # USASpending.gov API v2
            # https://api.usaspending.gov/docs/
            base_url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"

            # Calculate date range
            today = datetime.utcnow().date()
            end_date = today + timedelta(days=months_ahead * 30)

            payload = {
                "filters": {
                    "time_period": [{"start_date": today.isoformat(), "end_date": end_date.isoformat()}],
                    "award_type_codes": ["A", "B", "C", "D"],  # Contract types
                },
                "fields": [
                    "Award ID",
                    "Recipient Name",
                    "Start Date",
                    "End Date",
                    "Award Amount",
                    "Awarding Agency",
                    "NAICS Code",
                    "PSC Code",
                ],
                "limit": 100,
                "page": 1,
            }

            # Add NAICS filter
            if naics_codes:
                payload["filters"]["naics_codes"] = naics_codes

            # Add set-aside filter
            if set_aside:
                payload["filters"]["set_aside_type"] = [set_aside]

            response = await self.http_client.post(base_url, json=payload)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            logger.info(f"Found {len(results)} expiring contracts")

            db = self.SessionLocal()
            try:
                for contract in results:
                    # Check if already tracked
                    award_id = contract.get("Award ID")
                    existing = (
                        db.query(EarlySignal).filter(EarlySignal.solicitation_number == award_id).first()
                    )

                    if existing:
                        continue

                    # Calculate expected RFP date (typically 6-9 months before expiration)
                    end_date_str = contract.get("End Date")
                    if end_date_str:
                        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                        expected_rfp = end_date - timedelta(days=270)  # 9 months before
                    else:
                        expected_rfp = None

                    signal = EarlySignal(
                        signal_type=SignalType.EXPIRING_CONTRACT.value,
                        title=f"Re-compete: {contract.get('Recipient Name', 'Unknown')} - {contract.get('NAICS Code')}",
                        agency=contract.get("Awarding Agency", "")[:200],
                        description=f"Expiring contract {award_id}. Likely re-compete opportunity.",
                        estimated_value=contract.get("Award Amount"),
                        naics_code=contract.get("NAICS Code"),
                        psc_code=contract.get("PSC Code"),
                        signal_date=datetime.utcnow(),
                        expected_rfp_date=expected_rfp,
                        solicitation_number=award_id,
                        status=SignalStatus.TRACKING.value,
                    )

                    signal.relevance_score = self._score_signal(signal)

                    db.add(signal)
                    signals_created.append(signal)

                db.commit()
                logger.info(f"Created {len(signals_created)} expiring contract signals")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error scanning expiring contracts: {e}")

        return signals_created

    async def scan_industry_days(
        self,
        keywords: Optional[list[str]] = None,
        days_ahead: int = 90,
    ) -> list[IndustryDay]:
        """
        Scan for industry day announcements and vendor outreach events.

        Args:
            keywords: Search keywords (e.g., ['cybersecurity', 'Zero Trust'])
            days_ahead: Look for events in next N days

        Returns:
            List of IndustryDay objects
        """
        logger.info("Scanning for industry day events")

        keywords = keywords or ["industry day", "vendor outreach", "small business", "SDVOSB"]
        events_created = []

        try:
            # Search SAM.gov special notices for industry days
            base_url = "https://api.sam.gov/opportunities/v2/search"

            params = {
                "api_key": settings.sam_api_key if hasattr(settings, "sam_api_key") else "",
                "postedFrom": datetime.utcnow().strftime("%m/%d/%Y"),
                "postedTo": (datetime.utcnow() + timedelta(days=days_ahead)).strftime("%m/%d/%Y"),
                "ptype": "s",  # Special Notice
                "q": " OR ".join(keywords),
                "limit": 50,
            }

            response = await self.http_client.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()

            notices = data.get("opportunitiesData", [])
            logger.info(f"Found {len(notices)} potential industry day notices")

            db = self.SessionLocal()
            try:
                for notice in notices:
                    title = notice.get("title", "").lower()

                    # Filter for actual industry days
                    if not any(
                        keyword in title
                        for keyword in ["industry day", "vendor outreach", "small business day", "matchmaking"]
                    ):
                        continue

                    # Check if already tracked
                    notice_id = notice.get("noticeId")
                    existing = db.query(IndustryDay).filter(IndustryDay.title == notice.get("title")).first()

                    if existing:
                        continue

                    event = IndustryDay(
                        title=notice.get("title", "")[:500],
                        agency=notice.get("department", "")[:200],
                        office=notice.get("office", "")[:200],
                        event_type="industry_day",
                        event_date=self._parse_date(notice.get("responseDeadLine"))
                        or datetime.utcnow() + timedelta(days=30),
                        is_virtual=True,  # Default assumption
                        registration_url=f"https://sam.gov/opp/{notice_id}/view" if notice_id else None,
                        related_program=notice.get("title", "")[:500],
                        naics_code=notice.get("naicsCode"),
                    )

                    db.add(event)
                    events_created.append(event)

                db.commit()
                logger.info(f"Created {len(events_created)} industry day events")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error scanning industry days: {e}")

        return events_created

    def _score_signal(self, signal: EarlySignal) -> float:
        """
        Score a signal's relevance (0-100).

        Factors:
        - NAICS match
        - Set-aside match
        - Agency alignment
        - Estimated value
        """
        score = 0.0

        # NAICS match (0-30 points)
        if signal.naics_code in settings.allowed_naics:
            score += 30.0

        # Set-aside match (0-25 points)
        if signal.set_aside in settings.set_aside_prefs:
            score += 25.0

        # Agency alignment (0-20 points)
        if signal.agency in settings.target_agencies:
            score += 20.0

        # Signal type priority (0-15 points)
        type_scores = {
            SignalType.SOURCES_SOUGHT.value: 15.0,
            SignalType.PRE_SOLICITATION.value: 12.0,
            SignalType.RFI.value: 10.0,
            SignalType.INDUSTRY_DAY.value: 10.0,
            SignalType.EXPIRING_CONTRACT.value: 8.0,
        }
        score += type_scores.get(signal.signal_type, 5.0)

        # Estimated value (0-10 points)
        if signal.estimated_value:
            if 100000 <= signal.estimated_value <= 10000000:
                score += 10.0  # Sweet spot for small business
            elif signal.estimated_value > 10000000:
                score += 5.0  # Large but possible
            else:
                score += 3.0  # Small

        return min(score, 100.0)

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse various date formats from SAM.gov."""
        if not date_str:
            return None

        formats = ["%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except (ValueError, TypeError):
                continue

        return None

    async def aclose(self) -> None:
        """Close HTTP client."""
        await self.http_client.aclose()


# Singleton instance
early_discovery_service = EarlyDiscoveryService()

__all__ = ["EarlyDiscoveryService", "early_discovery_service"]
