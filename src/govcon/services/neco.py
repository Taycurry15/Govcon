"""Client for the Navy Electronic Commerce Online (NECO) opportunity search."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup

from govcon.utils.config import get_settings
from govcon.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

_ZONE_MAPPING = {
    "Eastern Time": "America/New_York",
    "Central Time": "America/Chicago",
    "Mountain Time": "America/Denver",
    "Pacific Time": "America/Los_Angeles",
    "Alaska Time": "America/Anchorage",
    "Hawaii-Aleutian Time": "Pacific/Honolulu",
}

_DATE_PATTERN = re.compile(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{2}, \d{4}")
_DUE_DATE_PATTERN = re.compile(
    r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun), (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{2}, \d{4}"
)


@dataclass(slots=True)
class NecoSearchFilters:
    """Filter parameters accepted by NECO search."""

    days_back: int = 7
    status: str = "open"  # "open" or "closed"
    uic: Optional[str] = None
    transaction_purpose: Optional[str] = None  # "original", "cancellation", "replace", "draft"
    solicitation_number: Optional[str] = None
    psc: Optional[str] = None
    cage_code: Optional[str] = None


class NecoClient:
    """HTTP client for NECO opportunity listings."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        verify_ssl: Optional[bool] = None,
        max_pages: Optional[int] = None,
    ) -> None:
        config = settings
        self.base_url = (base_url or config.neco_base_url).rstrip("/")
        self.verify_ssl = config.neco_verify_ssl if verify_ssl is None else verify_ssl
        self.timeout = config.neco_timeout
        self.max_pages = max_pages or config.neco_max_pages
        self.headers = {
            "User-Agent": config.neco_user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }

    async def search_opportunities(
        self,
        *,
        filters: Optional[NecoSearchFilters] = None,
    ) -> list[dict[str, Any]]:
        """Search NECO for opportunities and return normalized records."""
        filters = filters or NecoSearchFilters()

        async with httpx.AsyncClient(
            headers=self.headers,
            verify=self.verify_ssl,
            timeout=httpx.Timeout(self.timeout, connect=self.timeout),
        ) as client:
            search_page = await client.get(self._url("biz_ops/search_edi.aspx"))
            search_page.raise_for_status()

            hidden_fields = self._extract_hidden_fields(search_page.text)
            payload = self._build_search_payload(filters, hidden_fields)

            logger.debug("Submitting NECO search with payload keys: %s", list(payload.keys()))
            response = await client.post(
                self._url("biz_ops/search_edi.aspx"), data=payload, follow_redirects=False
            )
            if response.status_code not in (200, 302):
                logger.warning(
                    "Unexpected NECO search response status %s", response.status_code
                )

            results_html = await self._fetch_results_page(client)
            if results_html is None:
                return []

            opportunities: list[dict[str, Any]] = []
            current_html = results_html
            page = 1

            while current_html and page <= self.max_pages:
                hkeys = self._extract_hkeys(current_html)
                if not hkeys:
                    logger.debug("No NECO results found on page %s", page)
                    break

                for hkey in hkeys:
                    try:
                        record = await self._fetch_opportunity(client, hkey)
                    except Exception as exc:  # pragma: no cover - defensive guard
                        logger.warning("Failed to fetch NECO opportunity %s: %s", hkey, exc)
                        continue
                    if record:
                        opportunities.append(record)

                if page >= self.max_pages:
                    break

                page += 1
                current_html = await self._load_next_page(client, current_html, page)

            return opportunities

    async def _fetch_opportunity(
        self, client: httpx.AsyncClient, hkey: str
    ) -> Optional[dict[str, Any]]:
        summary_url = self._url(f"biz_ops/search_edi_summary.aspx?hkey={hkey}")
        detail_url = self._url(f"biz_ops/840-v5static.aspx?hkey={hkey}")

        summary_resp = await client.get(summary_url)
        if summary_resp.status_code != 200:
            logger.debug("NECO summary fetch returned %s for %s", summary_resp.status_code, hkey)
            return None
        detail_resp = await client.get(detail_url)
        if detail_resp.status_code != 200:
            logger.debug("NECO detail fetch returned %s for %s", detail_resp.status_code, hkey)
            return None

        summary_data = self._parse_summary(summary_resp.text)
        detail_data = self._parse_detail(detail_resp.text)
        if not detail_data.get("Solicitation Number"):
            logger.debug("Skipping NECO record with missing solicitation number (hkey=%s)", hkey)
            return None

        return self._normalize_record(hkey, summary_data, detail_data)

    async def _fetch_results_page(self, client: httpx.AsyncClient) -> Optional[str]:
        resp = await client.get(self._url("biz_ops/search_edi_results.aspx"))
        if resp.status_code != 200:
            logger.warning("NECO results page returned status %s", resp.status_code)
            return None
        return resp.text

    async def _load_next_page(
        self, client: httpx.AsyncClient, current_html: str, page_number: int
    ) -> Optional[str]:
        hidden = self._extract_hidden_fields(current_html)
        hidden["__EVENTTARGET"] = "GridView"
        hidden["__EVENTARGUMENT"] = f"Page${page_number}"
        resp = await client.post(self._url("biz_ops/search_edi_results.aspx"), data=hidden)
        if resp.status_code != 200:
            logger.debug("Failed to load NECO page %s (status=%s)", page_number, resp.status_code)
            return None
        return resp.text

    def _extract_hidden_fields(self, html: str) -> dict[str, str]:
        soup = BeautifulSoup(html, "html.parser")
        fields: dict[str, str] = {}
        for tag in soup.select("input[type=hidden][name]"):
            fields[tag["name"]] = tag.get("value", "")
        return fields

    def _extract_hkeys(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        hkeys: list[str] = []
        for anchor in soup.select("table#GridView a[href*='hkey=']"):
            href = anchor.get("href", "")
            if "hkey=" not in href:
                continue
            hkey = href.split("hkey=", 1)[1]
            if hkey:
                hkeys.append(hkey)
        return hkeys

    def _build_search_payload(
        self, filters: NecoSearchFilters, hidden_fields: dict[str, str]
    ) -> dict[str, str]:
        payload = dict(hidden_fields)

        status_value = "1" if filters.status.lower() != "closed" else "0"
        payload["ctl00$BodyContent$Status"] = status_value
        payload["ctl00$BodyContent$UicList"] = filters.uic or ""
        payload["ctl00$BodyContent$TransactionPurpose"] = self._map_transaction(filters.transaction_purpose)
        payload["ctl00$BodyContent$SolicitationNumber"] = filters.solicitation_number or ""
        payload["ctl00$BodyContent$Psc"] = filters.psc or ""
        payload["ctl00$BodyContent$CageCode"] = filters.cage_code or ""
        payload["ctl00$BodyContent$ctl02"] = "   Search   "

        payload["ctl00$BodyContent$DateRange"] = self._select_date_range(filters.days_back)

        return payload

    def _select_date_range(self, days_back: int) -> str:
        options = [0, 1, 7, 14, 21, 30, 45, 60, 90]
        closest = min(options, key=lambda value: abs(value - days_back))
        return str(closest if closest != 0 else -1)

    def _map_transaction(self, transaction: Optional[str]) -> str:
        if transaction is None:
            return ""
        lookup = {
            "cancellation": "01",
            "cancel": "01",
            "original": "00",
            "replace": "05",
            "replacement": "05",
            "draft": "24",
        }
        return lookup.get(transaction.lower(), "")

    def _parse_summary(self, html: str) -> dict[str, str]:
        soup = BeautifulSoup(html, "html.parser")
        data: dict[str, str] = {}
        for row in soup.select("table#tbl1 tr"):
            cells = row.select("td")
            if len(cells) != 2:
                continue
            label = cells[0].get_text(strip=True).rstrip(":")
            value = cells[1].get_text(" ", strip=True)
            if label:
                data[label] = value
        return data

    def _parse_detail(self, html: str) -> dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        data: dict[str, Any] = {"attachments": []}

        for row in soup.find_all("tr"):
            cells_raw = row.find_all("td")
            if not cells_raw:
                continue

            cells = [cell.get_text(" ", strip=True) for cell in cells_raw]
            if not cells:
                continue

            if len(cells) >= 3 and cells[0].startswith("Quote to be Received By"):
                data["Quote Deadline"] = {
                    "date": cells[0],
                    "timezone": cells[1] if len(cells) > 1 else "",
                    "time": cells[2] if len(cells) > 2 else "",
                }
                continue

            label = cells[0].rstrip(":")
            value = cells[1] if len(cells) > 1 else ""
            if not label:
                continue

            if label == "Solicitation Number":
                value = value.replace("Submit Bid", "").strip()

            if label == "Download File":
                if value:
                    attachments = data.setdefault("attachments", [])
                    if value not in attachments:
                        attachments.append(value)
                continue

            data[label] = value

        return data

    def _normalize_record(
        self, hkey: str, summary: dict[str, str], detail: dict[str, Any]
    ) -> dict[str, Any]:
        solicitation_number = detail.get("Solicitation Number")
        general_desc = detail.get("General Desc")
        detail_desc = detail.get("Detail Desc")

        title = general_desc or detail_desc or f"NECO Opportunity {solicitation_number}"
        title = self._clean_text(title)

        description_parts = []
        if general_desc:
            description_parts.append(self._clean_text(general_desc))
        if detail_desc and detail_desc != general_desc:
            description_parts.append(self._clean_text(detail_desc))

        attachments = detail.get("attachments") or []
        if attachments:
            description_parts.append("Attachments: " + ", ".join(attachments))

        description = "\n\n".join(description_parts) if description_parts else None

        agency = detail.get("Entity Identifier") or summary.get("Entity Identifier")
        if agency:
            agency = self._clean_text(agency)
            agency = agency.split("  ", 1)[-1].strip() if "  " in agency else agency

        office = detail.get("City/State/Zip") or summary.get("City/State/Zip")
        office = self._clean_text(office) if office else None

        posted_date = self._parse_issue_date(detail.get("Issue Date") or summary.get("Issue Date"))
        response_deadline = self._parse_deadline(detail.get("Quote Deadline") or summary.get("Date/Time Reference"))

        psc_code = detail.get("Federal Supply Classification")
        if psc_code:
            psc_code = psc_code.split()[0]

        source_url = self._url(f"biz_ops/840-v5static.aspx?hkey={hkey}")

        return {
            "solicitation_number": solicitation_number,
            "title": title,
            "description": description,
            "agency": agency or "U.S. Navy",
            "office": office,
            "posted_date": posted_date,
            "response_deadline": response_deadline,
            "naics_code": None,
            "psc_code": psc_code,
            "set_aside": None,
            "source_url": source_url,
            "external_id": solicitation_number,
            "estimated_value": None,
            "contract_type": summary.get("Trans. Purpose") or detail.get("Trans. Purpose"),
            "place_of_performance": None,
            "attachments": attachments,
        }

    def _parse_issue_date(self, raw: Optional[str]) -> Optional[datetime]:
        if not raw:
            return None
        match = _DATE_PATTERN.search(raw)
        if not match:
            return None
        value = match.group()
        try:
            parsed = datetime.strptime(value, "%b %d, %Y")
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            logger.debug("Failed to parse NECO issue date '%s'", raw)
            return None

    def _parse_deadline(self, raw: Any) -> Optional[datetime]:
        if isinstance(raw, dict):
            date_text = raw.get("date")
            time_text = raw.get("time")
            tz_text = raw.get("timezone")
        else:
            date_text = raw
            time_text = None
            tz_text = None

        if not date_text:
            return None

        match = _DUE_DATE_PATTERN.search(date_text)
        if not match:
            return None

        date_value = match.group()
        time_value = time_text or "11:59 PM"

        try:
            date_part = datetime.strptime(date_value, "%a, %b %d, %Y").date()
            time_part = datetime.strptime(time_value, "%I:%M %p").time()
        except ValueError:
            logger.debug("Failed to parse NECO deadline '%s' / '%s'", date_value, time_value)
            return None

        dt = datetime.combine(date_part, time_part)

        if tz_text:
            zone_name = _ZONE_MAPPING.get(tz_text.strip())
            if zone_name:
                dt = dt.replace(tzinfo=ZoneInfo(zone_name))
            else:
                logger.debug("Unknown NECO timezone label '%s'", tz_text)
                dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    def _clean_text(self, value: str) -> str:
        return " ".join(value.split())

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"
