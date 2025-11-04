"""SAM.gov API client for opportunity discovery."""

from datetime import datetime, timedelta
from typing import Any, Optional

import httpx

from govcon.utils.config import get_settings
from govcon.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

def _extract_place_of_performance(opportunity: dict[str, Any]) -> Optional[str]:
    """Safely extract place of performance city name from nested structures."""
    place = opportunity.get("placeOfPerformance")
    if isinstance(place, dict):
        city = place.get("city")
        if isinstance(city, dict):
            return city.get("name")
        if isinstance(city, str):
            return city
    return None


class SAMGovClient:
    """Client for SAM.gov Opportunities API."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Initialize SAM.gov client.

        Args:
            api_key: SAM.gov API key (defaults to settings)
        """
        self.api_key = api_key or settings.sam_gov_api_key
        self.base_url = settings.sam_gov_base_url
        self.timeout = 30.0

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        return headers

    async def search_opportunities(
        self, params: dict[str, Any], limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Search for opportunities on SAM.gov.

        Args:
            params: Search parameters
            limit: Maximum number of results

        Returns:
            List of opportunity dictionaries
        """
        url = f"{self.base_url}/opportunities/v2/search"
        params["limit"] = limit

        logger.info(f"Searching SAM.gov opportunities: {params}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params, headers=self._get_headers())
                response.raise_for_status()

                data = response.json()
                opportunities = data.get("opportunitiesData", [])

                logger.info(f"Found {len(opportunities)} opportunities from SAM.gov")
                return self._normalize_opportunities(opportunities)

        except httpx.HTTPError as e:
            logger.error(f"SAM.gov API error: {e}")
            if settings.testing:
                # Return mock data for testing
                return self._get_mock_data()
            raise

    def _normalize_opportunities(self, raw_opps: list[dict]) -> list[dict[str, Any]]:
        """
        Normalize SAM.gov opportunity data.

        Args:
            raw_opps: Raw opportunities from SAM.gov API

        Returns:
            Normalized opportunity dictionaries
        """
        normalized = []

        for opp in raw_opps:
            try:
                place_of_performance = _extract_place_of_performance(opp)

                normalized.append(
                    {
                        "solicitation_number": opp.get("noticeId"),
                        "title": opp.get("title"),
                        "description": opp.get("description"),
                        "agency": opp.get("fullParentPathName", ""),
                        "office": opp.get("subtierName"),
                        "posted_date": opp.get("postedDate"),
                        "response_deadline": opp.get("responseDeadLine"),
                        "naics_code": opp.get("naicsCode"),
                        "psc_code": opp.get("classificationCode"),
                        "set_aside": opp.get("typeOfSetAside"),
                        "source_url": opp.get("uiLink"),
                        "external_id": opp.get("noticeId"),
                        "contract_type": opp.get("type"),
                        "place_of_performance": place_of_performance,
                    }
                )
            except Exception as e:
                logger.warning(f"Error normalizing opportunity: {e}")
                continue

        return normalized

    def _get_mock_data(self) -> list[dict[str, Any]]:
        """Get mock data for testing."""
        now = datetime.utcnow()
        return [
            {
                "solicitation_number": "TEST-2024-001",
                "title": "Zero Trust Architecture Implementation",
                "description": "Implement Zero Trust security architecture for agency network",
                "agency": "Department of Veterans Affairs",
                "office": "Office of Information Technology",
                "posted_date": now.isoformat(),
                "response_deadline": (now + timedelta(days=30)).isoformat(),
                "naics_code": "541512",
                "psc_code": "D310",
                "set_aside": "SDVOSB",
                "source_url": "https://sam.gov/test",
                "external_id": "TEST-2024-001",
                "contract_type": "Firm Fixed Price",
                "place_of_performance": "Washington, DC",
            }
        ]
