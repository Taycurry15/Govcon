"""Discovery Agent - Finds and ingests federal opportunities.

This agent implements the Discovery logic from spec Section 2:
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from govcon.models import Opportunity, SetAsideType
from govcon.services.llm import ChatMessage, llm_service
from govcon.services.sam_gov import SAMGovClient
from govcon.services.neco import NecoClient, NecoSearchFilters
from govcon.utils.config import get_settings
from govcon.utils.database import get_async_db
from govcon.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

DISCOVERY_AGENT_INSTRUCTIONS_TEMPLATE = """Role
    You are the Discovery Agent responsible for top-of-funnel pipeline generation for The Bronze Shield.

Company Profile (use for tailoring)
    • Primary domains: cybersecurity, zero trust, ICAM, RMF, data management, translation/ASL services.
    • Certifications: SDVOSB, VOSB capable, Small Business - verify current status via config before claiming.
    • Past performance strengths: VA, DoD, DHS, HHS, DOJ, USDA.

Search Configuration
    • NAICS codes to prioritize: {naics_list}
    • PSC codes to prioritize: {psc_list}
    • Preferred set-aside order: SDVOSB -> VOSB -> SB -> Open.
    • Keyword focus: "zero trust", "ICAM", "RMF", "CMMC", "cybersecurity", "translation", "ASL", "language access".
    • Cadence: default to the last seven days unless the user overrides with `days_back`.

Evaluation Framework
    • NAICS Match: score 1.0 for exact, 0.7 for industry group (first four digits), 0.4 for sector (first two digits).
    • PSC Match: score 1.0 for exact, 0.5 for same initial letter/category.
    • Shapeable Indicator: mark true if the title or description includes "sources sought", "RFI", "market research",
      "industry day", "draft RFP", or "pre-solicitation".
    • Strategic Fit: boost opportunities aligned with target agencies, repeat customers, or strategic IDIQ/BPA vehicles.
    • Risk Flags: capture tight deadlines (<10 calendar days), missing attachments, VetCert prerequisites, or incumbents noted.

Process Steps
    1. Build search filters based on configuration and user overrides.
    2. Call SAM.gov (or mock client) and normalize results (dates, values, URLs).
    3. Compute match scores, shapeable flag, and strategic notes for each record.
    4. Deduplicate against existing pipeline when historical data is available.
    5. Surface immediate actions: deadlines, questions due, site visits, or follow-up tasks.

Output Expectations
    • Provide a summary count of opportunities found/ingested/updated.
    • For each opportunity, capture: solicitation number, title, agency, office, posted date, response deadline, set-aside,
      estimated value, NAICS/PSC, match scores, shapeable flag, and recommended priority (High/Medium/Low).
    • Highlight rationale for High-priority items and list any missing data or recommended follow-up.
    • Log the exact search criteria used for auditability."""


class OpportunitySearchResult(BaseModel):
    """Result from opportunity search."""

    model_config = {"extra": "forbid"}

    solicitation_number: str
    title: str
    description: Optional[str] = None
    agency: str
    office: Optional[str] = None
    posted_date: datetime
    response_deadline: Optional[datetime] = None
    naics_code: Optional[str] = None
    psc_code: Optional[str] = None
    set_aside: Optional[str] = None
    source_url: Optional[str] = None
    external_id: Optional[str] = None
    estimated_value: Optional[float] = None
    naics_match: float = Field(default=0.0, ge=0.0, le=1.0)
    psc_match: float = Field(default=0.0, ge=0.0, le=1.0)
    shapeable: bool = False


class DiscoveryResult(BaseModel):
    """Result from discovery run."""

    model_config = {"extra": "forbid"}

    opportunities_found: int
    opportunities_ingested: int
    opportunities_updated: int
    opportunities_shapeable: int
    search_criteria: Any
    execution_time: float
    analysis_summary: Optional[str] = None
    opportunities: list[OpportunitySearchResult] = Field(default_factory=list)


async def search_sam_gov(
    days_back: int = 7,
    set_aside_types: Optional[list[str]] = None,
    naics_codes: Optional[list[str]] = None,
    psc_codes: Optional[list[str]] = None,
    keywords: Optional[list[str]] = None,
) -> Any:
    """
    Search SAM.gov for federal opportunities.

    Args:
        days_back: Number of days to search back
        set_aside_types: Filter by set-aside types (SDVOSBC, WOSB, SBA, etc.)
        naics_codes: Filter by NAICS codes
        psc_codes: Filter by PSC codes
        keywords: Additional keywords to search for

    Returns:
        List of opportunity dictionaries
    """
    logger.info(
        f"Searching SAM.gov: days_back={days_back}, set_asides={set_aside_types}, "
        f"naics={naics_codes}, psc={psc_codes}"
    )

    client = SAMGovClient()

    try:
        # Calculate date range
        posted_from = datetime.utcnow() - timedelta(days=days_back)

        # Build search parameters
        # NOTE: SAM.gov API filters work as AND conditions, which can be too restrictive.
        # We use a broader search (keywords + date) and filter results client-side.
        params: dict[str, Any] = {
            "postedFrom": posted_from.strftime("%m/%d/%Y"),
            "postedTo": datetime.utcnow().strftime("%m/%d/%Y"),
        }

        # Add keywords to narrow down results
        if keywords:
            params["q"] = " OR ".join(keywords)

        # Execute search with broad parameters
        results = await client.search_opportunities(params)

        logger.info(f"Retrieved {len(results)} opportunities from SAM.gov before filtering")

        # Apply client-side filters for better OR logic support
        filtered_results = results

        # Filter by set-aside types
        if set_aside_types:
            filtered_results = [
                r for r in filtered_results
                if r.get("set_aside") in set_aside_types or r.get("set_aside") == "NONE"
            ]
            logger.info(
                f"After set-aside filter: {len(filtered_results)} opportunities "
                f"(types: {set_aside_types})"
            )

        # Note: NAICS and PSC codes are used for scoring, not hard filtering
        # We don't eliminate opportunities without matching codes since keywords
        # may identify relevant opportunities that aren't classified correctly

        logger.info(
            f"Keeping all {len(filtered_results)} opportunities "
            f"(NAICS/PSC used for scoring, not filtering)"
        )

        logger.info(f"Found {len(filtered_results)} opportunities from SAM.gov after all filters")
        return filtered_results

    except Exception as e:
        logger.error(f"Error searching SAM.gov: {e}")
        return []


def calculate_naics_match(naics_code: str, allowed_naics: list[str]) -> float:
    """
    Calculate NAICS match score.

    Args:
        naics_code: NAICS code from opportunity
        allowed_naics: List of allowed NAICS codes

    Returns:
        Match score from 0.0 to 1.0
    """
    if not naics_code:
        return 0.0

    # Exact match
    if naics_code in allowed_naics:
        return 1.0

    # Partial match on first 4 digits (industry group)
    naics_group = naics_code[:4]
    for allowed in allowed_naics:
        if allowed.startswith(naics_group):
            return 0.7

    # Partial match on first 2 digits (sector)
    naics_sector = naics_code[:2]
    for allowed in allowed_naics:
        if allowed.startswith(naics_sector):
            return 0.4

    return 0.0


def calculate_psc_match(psc_code: str, allowed_psc: list[str]) -> float:
    """
    Calculate PSC match score.

    Args:
        psc_code: PSC code from opportunity
        allowed_psc: List of allowed PSC codes

    Returns:
        Match score from 0.0 to 1.0
    """
    if not psc_code:
        return 0.0

    # Exact match
    if psc_code in allowed_psc:
        return 1.0

    # Partial match on first character (major category)
    psc_category = psc_code[0]
    for allowed in allowed_psc:
        if allowed.startswith(psc_category):
            return 0.5

    return 0.0


def _parse_datetime(value: Any) -> Optional[datetime]:
    """Parse various timestamp formats returned by SAM.gov."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        cleaned = cleaned.replace("Z", "+00:00")
        for parser in (
            datetime.fromisoformat,
            lambda v: datetime.strptime(v, "%m/%d/%Y"),
            lambda v: datetime.strptime(v, "%Y-%m-%d"),
            lambda v: datetime.strptime(v, "%Y-%m-%dT%H:%M:%S"),
        ):
            try:
                return parser(cleaned)
            except (ValueError, TypeError):
                continue

    return None


def _ensure_timezone(value: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime objects are timezone-aware, defaulting to UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def is_shapeable_opportunity(title: str, description: Optional[str]) -> bool:
    """
    Determine if opportunity is shapeable (Sources Sought/RFI).

    Args:
        title: Opportunity title
        description: Opportunity description

    Returns:
        True if shapeable, False otherwise
    """
    shapeable_keywords = [
        "sources sought",
        "source sought",
        "rfi",
        "request for information",
        "market research",
        "industry day",
        "industry engagement",
        "pre-solicitation",
        "draft rfp",
    ]

    combined_text = f"{title} {description or ''}".lower()

    return any(keyword in combined_text for keyword in shapeable_keywords)


class DiscoveryAgent:
    """Discovery Agent for finding federal opportunities."""

    def __init__(self) -> None:
        """Initialize Discovery Agent."""
        self.settings = settings
        self.logger = logger
        self.llm_provider = (
            self.settings.discovery_agent_llm_provider or self.settings.default_llm_provider
        )
        self.llm_model = self.settings.discovery_agent_llm_model
        self.llm_temperature = self.settings.openai_temperature
        self.instructions = DISCOVERY_AGENT_INSTRUCTIONS_TEMPLATE.format(
            naics_list=", ".join(self.settings.allowed_naics),
            psc_list=", ".join(self.settings.allowed_psc),
        )

    async def discover(
        self,
        days_back: int = 7,
        set_aside_filter: Optional[list[str]] = None,
        naics_codes: Optional[list[str]] = None,
        psc_codes: Optional[list[str]] = None,
        keywords: Optional[list[str]] = None,
    ) -> DiscoveryResult:
        """
        Run discovery to find new opportunities.

        Args:
            days_back: Number of days to search back
            set_aside_filter: Filter by specific set-aside types

        Returns:
            DiscoveryResult with summary statistics
        """
        start_time = datetime.utcnow()

        # Use default set-aside preferences from config
        if set_aside_filter is None:
            set_aside_filter = self.settings.set_aside_prefs

        naics_filter = self.settings.allowed_naics if naics_codes is None else naics_codes
        psc_filter = self.settings.allowed_psc if psc_codes is None else psc_codes
        keyword_filter = getattr(self.settings, "discovery_keywords", None)
        if keywords is not None:
            keyword_filter = keywords

        self.logger.info(
            f"Starting discovery: days_back={days_back}, set_aside_filter={set_aside_filter}"
        )

        sources_config = [
            source.lower()
            for source in getattr(self.settings, "discovery_sources", []) or ["sam_gov"]
        ]

        raw_results: list[dict[str, Any]] = []

        if "sam_gov" in sources_config:
            raw_results.extend(
                await search_sam_gov(
                    days_back=days_back,
                    set_aside_types=set_aside_filter,
                    naics_codes=naics_filter,
                    psc_codes=psc_filter,
                    keywords=keyword_filter,
                )
            )

        if "neco" in sources_config:
            raw_results.extend(await self._search_neco(days_back=days_back))

        opportunities: list[OpportunitySearchResult] = []
        seen_solicitations: set[str] = set()

        for raw in raw_results:
            solicitation_number = raw.get("solicitation_number") or raw.get("noticeId")
            title = raw.get("title")
            agency = raw.get("agency") or raw.get("fullParentPathName")

            posted_date = _parse_datetime(raw.get("posted_date"))
            response_deadline = _parse_datetime(raw.get("response_deadline"))

            if not solicitation_number or not title or not agency or not posted_date:
                self.logger.debug(
                    "Skipping incomplete opportunity: %s",
                    {"solicitation_number": solicitation_number, "title": title},
                )
                continue

            if solicitation_number in seen_solicitations:
                self.logger.debug("Duplicate solicitation %s skipped.", solicitation_number)
                continue
            seen_solicitations.add(solicitation_number)

            naics_code = raw.get("naics_code")
            psc_code = raw.get("psc_code")
            description = raw.get("description")

            naics_match = calculate_naics_match(naics_code or "", self.settings.allowed_naics)
            psc_match = calculate_psc_match(psc_code or "", self.settings.allowed_psc)
            shapeable = is_shapeable_opportunity(title, description)

            opportunity = OpportunitySearchResult(
                solicitation_number=solicitation_number,
                title=title,
                description=description,
                agency=agency,
                office=raw.get("office"),
                posted_date=posted_date,
                response_deadline=response_deadline,
                naics_code=naics_code,
                psc_code=psc_code,
                set_aside=raw.get("set_aside"),
                source_url=raw.get("source_url"),
                external_id=raw.get("external_id"),
                estimated_value=raw.get("estimated_value"),
                naics_match=naics_match,
                psc_match=psc_match,
                shapeable=shapeable,
            )
            opportunities.append(opportunity)

        opportunities_ingested = 0
        opportunities_updated = 0

        if opportunities:
            persisted_ingested, persisted_updated = await self._persist_opportunities(opportunities)
            opportunities_ingested = persisted_ingested
            opportunities_updated = persisted_updated

        opportunities_found = len(opportunities)
        opportunities_shapeable = sum(1 for opp in opportunities if opp.shapeable)

        execution_time = (datetime.utcnow() - start_time).total_seconds()
        analysis_summary = await self._summarize_discovery(
            opportunities_found=opportunities_found,
            opportunities_shapeable=opportunities_shapeable,
            search_criteria={
                "days_back": days_back,
                "set_aside_filter": set_aside_filter,
                "naics_codes": naics_filter,
                "psc_codes": psc_filter,
                "keywords": keyword_filter,
                "sources": sources_config,
            },
        )

        return DiscoveryResult(
            opportunities_found=opportunities_found,
            opportunities_ingested=opportunities_ingested,
            opportunities_updated=opportunities_updated,
            opportunities_shapeable=opportunities_shapeable,
            search_criteria={
                "days_back": days_back,
                "set_aside_filter": set_aside_filter,
                "naics_codes": naics_filter,
                "psc_codes": psc_filter,
                "keywords": keyword_filter,
                "sources": sources_config,
            },
            execution_time=execution_time,
            analysis_summary=analysis_summary,
            opportunities=opportunities,
        )



    async def _search_neco(self, *, days_back: int) -> list[dict[str, Any]]:
        """Fetch opportunities from NECO."""
        client = NecoClient()
        filters = NecoSearchFilters(days_back=days_back, status="open")

        try:
            return await client.search_opportunities(filters=filters)
        except Exception as exc:  # pragma: no cover - external dependency
            self.logger.warning("NECO search failed: %s", exc)
            return []

    async def _persist_opportunities(
        self, opportunities: list[OpportunitySearchResult]
    ) -> tuple[int, int]:
        """Persist opportunities to the database; returns (ingested, updated)."""
        ingested = 0
        updated = 0

        try:
            async with get_async_db() as session:
                ingested, updated = await self._upsert_opportunities(session, opportunities)
        except SQLAlchemyError as exc:  # pragma: no cover - database unavailable in tests
            self.logger.warning("Discovery persistence skipped due to database error: %s", exc)
        except Exception as exc:  # pragma: no cover - resilience against unexpected errors
            self.logger.warning("Discovery persistence encountered unexpected error: %s", exc)

        return ingested, updated

    async def _upsert_opportunities(
        self, session: AsyncSession, opportunities: list[OpportunitySearchResult]
    ) -> tuple[int, int]:
        """Insert or update opportunities using the provided session."""
        ingested = 0
        updated = 0

        for opportunity in opportunities:
            result = await session.execute(
                select(Opportunity).where(
                    Opportunity.solicitation_number == opportunity.solicitation_number
                )
            )
            existing = result.scalar_one_or_none()

            set_aside_value = None
            if opportunity.set_aside:
                try:
                    set_aside_value = SetAsideType(opportunity.set_aside)
                except ValueError:
                    set_aside_value = None

            posted_date = _ensure_timezone(opportunity.posted_date)
            response_deadline = _ensure_timezone(opportunity.response_deadline)

            if existing:
                existing.title = opportunity.title
                existing.description = opportunity.description
                existing.agency = opportunity.agency
                existing.office = opportunity.office
                existing.posted_date = posted_date or existing.posted_date
                existing.response_deadline = response_deadline
                existing.naics_code = opportunity.naics_code
                existing.psc_code = opportunity.psc_code
                existing.set_aside = set_aside_value
                existing.source_url = opportunity.source_url
                existing.external_id = opportunity.external_id
                existing.estimated_value = opportunity.estimated_value
                existing.naics_match = opportunity.naics_match
                existing.psc_match = opportunity.psc_match
                existing.shapeable = opportunity.shapeable
                updated += 1
            else:
                session.add(
                    Opportunity(
                        solicitation_number=opportunity.solicitation_number,
                        title=opportunity.title,
                        description=opportunity.description,
                        agency=opportunity.agency,
                        office=opportunity.office,
                        posted_date=posted_date or datetime.utcnow().replace(tzinfo=timezone.utc),
                        response_deadline=response_deadline,
                        naics_code=opportunity.naics_code,
                        psc_code=opportunity.psc_code,
                        set_aside=set_aside_value,
                        source_url=opportunity.source_url,
                        external_id=opportunity.external_id,
                        estimated_value=opportunity.estimated_value,
                        naics_match=opportunity.naics_match,
                        psc_match=opportunity.psc_match,
                        shapeable=opportunity.shapeable,
                    )
                )
                ingested += 1

        if ingested or updated:
            await session.commit()

        return ingested, updated

    async def _summarize_discovery(
        self,
        *,
        opportunities_found: int,
        opportunities_shapeable: int,
        search_criteria: dict[str, Any],
    ) -> str:
        """Generate an LLM summary of the discovery run for quick review."""
        prompt = (
            "Summarize the opportunity discovery run in two bullet points. "
            "Highlight the number of total and shapeable opportunities and note any follow-up. "
            "Respond in plain text Markdown bullet list.\n"
            f"Opportunities found: {opportunities_found}\n"
            f"Shapeable opportunities: {opportunities_shapeable}\n"
            f"Search criteria: {json.dumps(search_criteria, indent=2)}"
        )
        messages = [
            ChatMessage(role="system", content=self.instructions),
            ChatMessage(role="user", content=prompt),
        ]
        try:
            return await llm_service.chat(
                messages,
                provider=self.llm_provider,
                model=self.llm_model,
                temperature=self.llm_temperature,
                max_output_tokens=400,
            )
        except Exception as exc:  # pragma: no cover
            self.logger.warning("Failed to summarize discovery run via LLM: %s", exc)
            return f"- Unable to summarize discovery run (error: {exc})"
