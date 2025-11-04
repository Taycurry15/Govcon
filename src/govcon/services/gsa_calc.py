"""GSA Contract-Awarded Labor Category (CALC) API client."""

from typing import Any, Optional

import httpx

from govcon.utils.config import get_settings
from govcon.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class GSACALCClient:
    """Client for GSA CALC API."""

    def __init__(self) -> None:
        """Initialize GSA CALC client."""
        self.base_url = settings.gsa_calc_base_url
        self.timeout = 30.0

    async def search_rates(
        self,
        labor_category: str,
        contract_year: Optional[int] = None,
        education: Optional[str] = None,
        min_experience: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """
        Search for labor rates in GSA CALC.

        Args:
            labor_category: Labor category name to search
            contract_year: Contract year filter
            education: Education level filter
            min_experience: Minimum experience years filter

        Returns:
            List of matching rate records
        """
        params: dict[str, Any] = {"q": labor_category, "contract_year": contract_year or "current"}

        if education:
            params["education"] = education
        if min_experience:
            params["min_experience"] = min_experience

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/rates/", params=params)
                response.raise_for_status()

                data = response.json()
                results = data.get("results", [])

                logger.info(f"Found {len(results)} rates for '{labor_category}'")
                return self._normalize_rates(results)

        except httpx.HTTPError as e:
            logger.error(f"GSA CALC API error: {e}")
            return self._get_mock_rates(labor_category)

    def _normalize_rates(self, raw_rates: list[dict]) -> list[dict[str, Any]]:
        """
        Normalize GSA CALC rate data.

        Args:
            raw_rates: Raw rates from API

        Returns:
            Normalized rate dictionaries
        """
        normalized = []

        for rate in raw_rates:
            normalized.append(
                {
                    "labor_category": rate.get("labor_category"),
                    "hourly_rate": float(rate.get("current_price", 0)),
                    "education": rate.get("education_level"),
                    "min_years_experience": rate.get("min_years_experience"),
                    "contractor": rate.get("contractor_name"),
                    "contract_number": rate.get("contract_number"),
                    "sin": rate.get("sin"),
                    "data_source": "GSA CALC",
                }
            )

        return normalized

    def _get_mock_rates(self, labor_category: str) -> list[dict[str, Any]]:
        """Get mock rate data for testing/fallback."""
        lcat_lower = labor_category.lower()

        # Mock rates based on common categories
        if "senior" in lcat_lower and "software" in lcat_lower:
            base_rate = 95.00
        elif "software" in lcat_lower or "developer" in lcat_lower:
            base_rate = 75.00
        elif "cybersecurity" in lcat_lower or "security" in lcat_lower:
            base_rate = 85.00
        elif "project manager" in lcat_lower or "program manager" in lcat_lower:
            base_rate = 90.00
        elif "analyst" in lcat_lower:
            base_rate = 70.00
        else:
            base_rate = 65.00

        return [
            {
                "labor_category": labor_category,
                "hourly_rate": base_rate,
                "education": "Bachelors",
                "min_years_experience": 5,
                "contractor": "Mock Contractor",
                "contract_number": "MOCK-001",
                "sin": "54151S",
                "data_source": "Mock Data (GSA CALC unavailable)",
            }
        ]

    async def get_average_rate(self, labor_category: str, percentile: int = 50) -> dict[str, Any]:
        """
        Get average rate for a labor category.

        Args:
            labor_category: Labor category name
            percentile: Percentile to use (default: 50 = median)

        Returns:
            Dictionary with average rate statistics
        """
        rates = await self.search_rates(labor_category)

        if not rates:
            return {
                "labor_category": labor_category,
                "average_rate": 0.0,
                "min_rate": 0.0,
                "max_rate": 0.0,
                "sample_size": 0,
            }

        hourly_rates = sorted([r["hourly_rate"] for r in rates])

        percentile_index = int(len(hourly_rates) * (percentile / 100))

        return {
            "labor_category": labor_category,
            "average_rate": hourly_rates[percentile_index],
            "min_rate": min(hourly_rates),
            "max_rate": max(hourly_rates),
            "median_rate": hourly_rates[len(hourly_rates) // 2],
            "sample_size": len(rates),
            "percentile": percentile,
            "data_source": "GSA CALC",
        }
