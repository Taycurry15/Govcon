"""Bureau of Labor Statistics (BLS) API client."""

from datetime import datetime
from typing import Any, Optional

import httpx

from govcon.utils.config import get_settings
from govcon.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class BLSClient:
    """Client for BLS Occupational Employment Statistics (OES) API."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Initialize BLS client.

        Args:
            api_key: BLS API key (defaults to settings)
        """
        self.api_key = api_key or settings.bls_api_key
        self.base_url = settings.bls_base_url
        self.timeout = 30.0

    async def get_oes_wage(
        self, soc_code: str, area_code: str = "0000000", year: Optional[int] = None
    ) -> dict[str, Any]:
        """
        Get OES wage data for a SOC code.

        Args:
            soc_code: Standard Occupational Classification code (e.g., "15-1252")
            area_code: Area code (default: 0000000 for national)
            year: Year (default: most recent)

        Returns:
            Dictionary with wage data
        """
        if not self.api_key:
            logger.warning("No BLS API key configured, using mock data")
            return self._get_mock_wage_data(soc_code)

        # Construct series ID for OES
        # Format: OEUN[area][soc]04 (04 = mean hourly wage)
        series_id = f"OEUN{area_code}{soc_code.replace('-', '')}04"

        if not year:
            year = datetime.now().year - 1  # BLS data is usually 1 year behind

        payload = {
            "seriesid": [series_id],
            "startyear": str(year),
            "endyear": str(year),
            "registrationkey": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/timeseries/data/", json=payload)
                response.raise_for_status()

                data = response.json()

                if data.get("status") == "REQUEST_SUCCEEDED":
                    series_data = data["Results"]["series"][0]["data"]
                    if series_data:
                        latest = series_data[0]
                        return {
                            "soc_code": soc_code,
                            "mean_hourly_wage": float(latest["value"]),
                            "year": latest["year"],
                            "period": latest["period"],
                            "area": "National" if area_code == "0000000" else area_code,
                            "data_source": "BLS OES",
                            "effective_date": f"{latest['year']}-{latest['period']}",
                        }

                logger.warning(f"BLS API returned no data for {soc_code}")
                return self._get_mock_wage_data(soc_code)

        except httpx.HTTPError as e:
            logger.error(f"BLS API error: {e}")
            return self._get_mock_wage_data(soc_code)

    def _get_mock_wage_data(self, soc_code: str) -> dict[str, Any]:
        """Get mock wage data for testing/fallback."""
        # Mock data based on common IT/professional SOC codes
        mock_wages = {
            "15-1252": 55.23,  # Software Developers
            "15-1212": 58.77,  # Information Security Analysts
            "15-1244": 51.84,  # Network and Computer Systems Administrators
            "15-1299": 48.50,  # Computer Occupations, All Other
            "13-1081": 42.15,  # Logisticians
            "13-1111": 66.67,  # Management Analysts
            "27-3091": 28.63,  # Interpreters and Translators
        }

        mean_wage = mock_wages.get(soc_code, 50.00)

        return {
            "soc_code": soc_code,
            "mean_hourly_wage": mean_wage,
            "year": datetime.now().year - 1,
            "period": "Annual",
            "area": "National",
            "data_source": "Mock Data (BLS API unavailable)",
            "effective_date": datetime.now().strftime("%Y-%m"),
        }
