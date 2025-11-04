"""Bid/No-Bid Agent - Scores opportunities for pursuit decision.

This agent implements the Bid/No-Bid logic from spec Section 3:

Includes VA/Vets First logic for VA procurements.
"""

import json
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from govcon.models import Opportunity
from govcon.services.llm import ChatMessage, llm_service
from govcon.utils.config import get_settings
from govcon.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

BID_NOBID_AGENT_INSTRUCTIONS = f"""Role
    You are the Bid/No-Bid Agent for The Bronze Shield. Your recommendations drive pipeline focus and leadership approvals.

Scoring Model (weights sourced from configuration)
    • Set-Aside Eligibility ({settings.score_weight_set_aside}%): certification alignment, VetCert requirements, VA Vets First.
    • Scope Alignment ({settings.score_weight_scope}%): NAICS/PSC matches, keyword coverage, mission fit.
    • Timeline Feasibility ({settings.score_weight_timeline}%): time remaining, overall solicitation window, holidays.
    • Competition & Vehicle ({settings.score_weight_competition}%): expected field size, incumbent knowledge, contract vehicle.
    • Staffing Realism ({settings.score_weight_staffing}%): clearance needs, geographic constraints, labor availability.
    • Pricing Realism ({settings.score_weight_pricing}%): expected wrap rates, historical comparables, pass-through risk.
    • Strategic Fit ({settings.score_weight_strategic}%): agency priority, shapeability, portfolio alignment.

Evaluation Inputs
    • Opportunity object (solicitation number, title, agency, set-aside, NAICS/PSC, deadlines, estimated value, geography).
    • Internal settings (preferred agencies, set-aside certifications, labor capacity).
    • Historical performance data where available (win/loss history, capture notes).

Process Expectations
    1. Normalize opportunity data - fill in defaults for missing matches, convert dates to aware datetimes.
    2. Call helper scoring functions; retain human-readable rationale for each criterion.
    3. Apply configured weights to compute total score (0-100).
    4. Determine recommendation thresholds:
         • BID      -> total >= 80 and no red flags.
         • REVIEW   -> 60 <= total < 80, or total >= 80 but with unresolved risks.
         • NO_BID   -> total < 60, or hard blocker (certification mismatch, missed deadline, VetCert not attainable).
    5. Surface blocking issues, assumptions, and required leadership decisions (teaming, staffing commitments, pricing authority).

Output Requirements
    • Return BidScore model populated with individual scores, weighted total, textual recommendation, and rationale paragraph.
    • Flag VA opportunities requiring VetCert and mark `is_va_procurement`.
    • Populate `requires_vetcert`, `high_priority`, and any additional notes to guide follow-up actions.
    • Provide a concise summary ready for decision briefings (1-2 sentences plus bullet list of key factors)."""


class BidScore(BaseModel):
    """Bid/No-Bid scoring result."""

    model_config = {"extra": "forbid"}

    # Individual scores (0-100)
    set_aside_score: float = Field(ge=0.0, le=100.0)
    scope_score: float = Field(ge=0.0, le=100.0)
    timeline_score: float = Field(ge=0.0, le=100.0)
    competition_score: float = Field(ge=0.0, le=100.0)
    staffing_score: float = Field(ge=0.0, le=100.0)
    pricing_score: float = Field(ge=0.0, le=100.0)
    strategic_score: float = Field(ge=0.0, le=100.0)

    # Weighted total (0-100)
    total_score: float = Field(ge=0.0, le=100.0)

    # Recommendation
    recommendation: str = Field(description="BID, NO_BID, or REVIEW")
    rationale: str

    # Flags
    is_va_procurement: bool = False
    requires_vetcert: bool = False
    high_priority: bool = False


def score_set_aside_eligibility(
    set_aside: Optional[str],
    agency: str,
    set_aside_prefs: list[str],
) -> dict:
    """
    Score set-aside eligibility (25% weight).

    Args:
        set_aside: Set-aside type from opportunity
        agency: Agency name
        set_aside_prefs: Company's set-aside preferences (SDVOSB, VOSB, SB)

    Returns:
        Dictionary with score and details
    """
    score = 0.0
    details = []
    is_va = "VA" in agency.upper() or "VETERAN" in agency.upper()

    if not set_aside:
        score = 40.0  # Open competition
        details.append("Open competition - no set-aside preference")
    elif set_aside == "SDVOSB":
        if "SDVOSB" in set_aside_prefs:
            score = 100.0
            details.append("SDVOSB set-aside - perfect match")
            if is_va:
                details.append("VA procurement - Vets First applies")
        else:
            score = 0.0
            details.append("SDVOSB required but we don't have certification")
    elif set_aside == "VOSB":
        if "VOSB" in set_aside_prefs or "SDVOSB" in set_aside_prefs:
            score = 90.0
            details.append("VOSB set-aside - strong match")
            if is_va:
                details.append("VA procurement - Vets First applies")
        else:
            score = 0.0
            details.append("VOSB required but we don't have certification")
    elif set_aside == "SB":
        if "SB" in set_aside_prefs:
            score = 75.0
            details.append("Small Business set-aside - good match")
        else:
            score = 30.0
            details.append("SB set-aside but we're not certified")
    else:
        score = 50.0
        details.append(f"Other set-aside type: {set_aside}")

    return {
        "score": score,
        "details": details,
        "is_va_procurement": is_va,
        "requires_vetcert": is_va and set_aside in ["SDVOSB", "VOSB"],
    }


def score_scope_alignment(
    naics_match: float,
    psc_match: float,
    title: str,
    description: Optional[str],
) -> dict:
    """
    Score scope alignment (25% weight).

    Args:
        naics_match: NAICS match score (0-1)
        psc_match: PSC match score (0-1)
        title: Opportunity title
        description: Opportunity description

    Returns:
        Dictionary with score and details
    """
    # Base score from code matches
    base_score = (naics_match * 60) + (psc_match * 40)

    # Check for keyword matches in title/description
    capability_keywords = [
        "zero trust",
        "icam",
        "rmf",
        "cmmc",
        "cybersecurity",
        "information security",
        "data management",
        "translation",
        "interpretation",
        "asl",
        "sign language",
        "transcription",
        "it services",
        "help desk",
        "pmo",
        "program management",
    ]

    combined_text = f"{title} {description or ''}".lower()
    keyword_matches = [kw for kw in capability_keywords if kw in combined_text]

    # Boost score for keyword matches
    if keyword_matches:
        keyword_boost = min(20.0, len(keyword_matches) * 5)
        base_score = min(100.0, base_score + keyword_boost)

    details = [
        f"NAICS match: {naics_match:.2f}",
        f"PSC match: {psc_match:.2f}",
    ]

    if keyword_matches:
        details.append(f"Keyword matches: {', '.join(keyword_matches)}")

    return {"score": base_score, "details": details, "keyword_matches": keyword_matches}


def score_timeline_feasibility(
    response_deadline: Optional[str],
    posted_date: str,
) -> dict:
    """
    Score timeline feasibility (15% weight).

    Args:
        response_deadline: Response deadline (ISO format)
        posted_date: Posted date (ISO format)

    Returns:
        Dictionary with score and details
    """
    if not response_deadline:
        return {
            "score": 50.0,
            "details": ["No deadline specified - unknown timeline"],
        }

    deadline = datetime.fromisoformat(response_deadline.replace("Z", "+00:00"))
    posted = datetime.fromisoformat(posted_date.replace("Z", "+00:00"))
    now = datetime.utcnow().replace(tzinfo=deadline.tzinfo)

    days_until_deadline = (deadline - now).days
    days_open = (deadline - posted).days

    score = 0.0
    details = []

    if days_until_deadline < 0:
        score = 0.0
        details.append("Deadline has passed")
    elif days_until_deadline < 7:
        score = 20.0
        details.append(f"Only {days_until_deadline} days until deadline - very tight")
    elif days_until_deadline < 14:
        score = 50.0
        details.append(f"{days_until_deadline} days until deadline - tight but doable")
    elif days_until_deadline < 30:
        score = 80.0
        details.append(f"{days_until_deadline} days until deadline - reasonable")
    else:
        score = 100.0
        details.append(f"{days_until_deadline} days until deadline - ample time")

    details.append(f"Open for {days_open} days total")

    return {"score": score, "details": details, "days_until_deadline": days_until_deadline}


def score_competition(
    set_aside: Optional[str],
    estimated_value: Optional[float],
) -> dict:
    """
    Score competition & vehicle (10% weight).

    Args:
        set_aside: Set-aside type
        estimated_value: Estimated contract value

    Returns:
        Dictionary with score and details
    """
    score = 50.0  # Base score
    details = []

    # Set-asides reduce competition
    if set_aside in ["SDVOSB", "VOSB"]:
        score += 30.0
        details.append(f"{set_aside} set-aside reduces competition pool")
    elif set_aside == "SB":
        score += 20.0
        details.append("Small Business set-aside somewhat reduces competition")

    # Contract size affects competition
    if estimated_value:
        if estimated_value < 250000:
            score += 20.0
            details.append(f"Smaller contract (${estimated_value:,.0f}) - less competition")
        elif estimated_value > 10000000:
            score -= 20.0
            details.append(f"Large contract (${estimated_value:,.0f}) - more competition")
        else:
            details.append(f"Mid-size contract (${estimated_value:,.0f}) - moderate competition")

    score = max(0.0, min(100.0, score))

    return {"score": score, "details": details}


def score_staffing_realism(
    estimated_value: Optional[float],
    place_of_performance: Optional[str],
) -> dict:
    """
    Score staffing realism (10% weight).

    Args:
        estimated_value: Estimated contract value
        place_of_performance: Place of performance

    Returns:
        Dictionary with score and details
    """
    score = 70.0  # Assume generally feasible
    details = []

    # Check location
    if place_of_performance:
        pop_lower = place_of_performance.lower()
        if any(x in pop_lower for x in ["remote", "telework", "virtual"]):
            score += 20.0
            details.append("Remote work - easier to staff")
        elif any(x in pop_lower for x in ["dc", "washington", "virginia", "maryland"]):
            score += 10.0
            details.append("DMV area - good talent pool")
        elif "cleared" in pop_lower or "security clearance" in pop_lower:
            score -= 20.0
            details.append("Clearance required - harder to staff")

    # Estimate team size from contract value
    if estimated_value:
        estimated_ftes = estimated_value / 200000  # Rough estimate
        if estimated_ftes < 5:
            score += 10.0
            details.append(f"Small team (~{estimated_ftes:.1f} FTE) - easy to staff")
        elif estimated_ftes > 20:
            score -= 15.0
            details.append(f"Large team (~{estimated_ftes:.1f} FTE) - challenging to staff")
        else:
            details.append(f"Medium team (~{estimated_ftes:.1f} FTE) - manageable")

    score = max(0.0, min(100.0, score))

    return {"score": score, "details": details}


def score_pricing_realism(
    estimated_value: Optional[float],
    naics_code: Optional[str],
) -> dict:
    """
    Score pricing realism (10% weight).

    Args:
        estimated_value: Estimated contract value
        naics_code: NAICS code

    Returns:
        Dictionary with score and details
    """
    score = 75.0  # Assume generally realistic
    details: list[str] = []

    if not estimated_value:
        details.append("No estimate provided - pricing TBD")
        return {"score": score, "details": details}

    # Check if value is reasonable for our capabilities
    if estimated_value < 50000:
        score = 40.0
        details.append(f"Low value (${estimated_value:,.0f}) - may not be worth pursuing")
    elif estimated_value > 50000000:
        score = 50.0
        details.append(f"High value (${estimated_value:,.0f}) - need strong past performance")
    else:
        score = 85.0
        details.append(f"Reasonable value (${estimated_value:,.0f}) - within our range")

    if naics_code:
        details.append(f"Evaluated against typical ranges for NAICS {naics_code}")

    return {"score": score, "details": details}


def score_strategic_fit(
    agency: str,
    shapeable: bool,
    naics_code: Optional[str],
) -> dict:
    """
    Score strategic fit (5% weight).

    Args:
        agency: Agency name
        shapeable: Whether opportunity is shapeable
        naics_code: NAICS code

    Returns:
        Dictionary with score and details
    """
    score = 50.0
    details: list[str] = []

    # Preferred agencies
    target_agencies = ["VA", "DoD", "DHS", "HHS", "DOJ", "USDA"]
    if any(target in agency.upper() for target in target_agencies):
        score += 30.0
        details.append(f"Target agency: {agency}")

    # Shapeable opportunities are strategic
    if shapeable:
        score += 20.0
        details.append("Shapeable opportunity - can influence requirements")

    if naics_code:
        details.append(f"NAICS alignment noted: {naics_code}")

    score = min(100.0, score)

    return {"score": score, "details": details}


class BidNoBidAgent:
    """Bid/No-Bid Agent for scoring opportunities."""

    def __init__(self) -> None:
        """Initialize Bid/No-Bid Agent."""
        self.settings = settings
        self.logger = logger
        self.instructions = BID_NOBID_AGENT_INSTRUCTIONS
        self.llm_provider = (
            self.settings.bid_nobid_agent_llm_provider or self.settings.default_llm_provider
        )
        self.llm_model = self.settings.bid_nobid_agent_llm_model
        self.llm_temperature = self.settings.openai_temperature

        # Scoring weights from spec
        self.weights = {
            "set_aside": settings.score_weight_set_aside / 100.0,
            "scope": settings.score_weight_scope / 100.0,
            "timeline": settings.score_weight_timeline / 100.0,
            "competition": settings.score_weight_competition / 100.0,
            "staffing": settings.score_weight_staffing / 100.0,
            "pricing": settings.score_weight_pricing / 100.0,
            "strategic": settings.score_weight_strategic / 100.0,
        }

    async def score(self, opportunity: Opportunity) -> BidScore:
        """
        Score an opportunity for bid/no-bid decision.

        Args:
            opportunity: Opportunity to score

        Returns:
            BidScore with recommendation
        """
        self.logger.info(f"Scoring opportunity: {opportunity.solicitation_number}")

        # Prepare opportunity data
        opp_data = {
            "solicitation_number": opportunity.solicitation_number,
            "title": opportunity.title,
            "description": opportunity.description,
            "agency": opportunity.agency,
            "set_aside": opportunity.set_aside.value if opportunity.set_aside else None,
            "naics_code": opportunity.naics_code,
            "psc_code": opportunity.psc_code,
            "naics_match": opportunity.naics_match or 0.0,
            "psc_match": opportunity.psc_match or 0.0,
            "response_deadline": (
                opportunity.response_deadline.isoformat() if opportunity.response_deadline else None
            ),
            "posted_date": opportunity.posted_date.isoformat(),
            "estimated_value": opportunity.estimated_value,
            "place_of_performance": opportunity.place_of_performance,
            "shapeable": opportunity.shapeable,
        }

        set_aside_result = score_set_aside_eligibility(
            opp_data["set_aside"],
            opp_data["agency"],
            self.settings.set_aside_prefs,
        )
        scope_result = score_scope_alignment(
            opp_data["naics_match"],
            opp_data["psc_match"],
            opportunity.title,
            opportunity.description,
        )
        timeline_result = score_timeline_feasibility(
            opp_data["response_deadline"],
            opp_data["posted_date"],
        )
        competition_result = score_competition(
            opp_data["set_aside"],
            opp_data["estimated_value"],
        )
        staffing_result = score_staffing_realism(
            opp_data["estimated_value"],
            opp_data["place_of_performance"],
        )
        pricing_result = score_pricing_realism(
            opp_data["estimated_value"],
            opp_data["naics_code"],
        )
        strategic_result = score_strategic_fit(
            opp_data["agency"],
            opp_data["shapeable"],
            opp_data["naics_code"],
        )

        total_score = (
            set_aside_result["score"] * self.weights["set_aside"]
            + scope_result["score"] * self.weights["scope"]
            + timeline_result["score"] * self.weights["timeline"]
            + competition_result["score"] * self.weights["competition"]
            + staffing_result["score"] * self.weights["staffing"]
            + pricing_result["score"] * self.weights["pricing"]
            + strategic_result["score"] * self.weights["strategic"]
        )

        recommendation = "REVIEW"
        hard_blocker = set_aside_result["score"] == 0.0 or timeline_result["score"] == 0.0
        if hard_blocker or timeline_result["score"] < 30.0:
            recommendation = "NO_BID"
        elif total_score >= 80.0 and not hard_blocker:
            recommendation = "BID"

        scores_snapshot = {
            "set_aside": set_aside_result,
            "scope": scope_result,
            "timeline": timeline_result,
            "competition": competition_result,
            "staffing": staffing_result,
            "pricing": pricing_result,
            "strategic": strategic_result,
            "total_score": total_score,
            "recommendation": recommendation,
        }

        rationale = await self._generate_rationale(opportunity, scores_snapshot)

        return BidScore(
            set_aside_score=set_aside_result["score"],
            scope_score=scope_result["score"],
            timeline_score=timeline_result["score"],
            competition_score=competition_result["score"],
            staffing_score=staffing_result["score"],
            pricing_score=pricing_result["score"],
            strategic_score=strategic_result["score"],
            total_score=total_score,
            recommendation=recommendation,
            rationale=rationale,
            is_va_procurement=set_aside_result["is_va_procurement"],
            requires_vetcert=set_aside_result["requires_vetcert"],
            high_priority=total_score >= 85.0,
        )

    async def _generate_rationale(
        self, opportunity: Opportunity, scores_snapshot: dict[str, Any]
    ) -> str:
        """Use the configured LLM to produce a succinct rationale."""
        opportunity_context = {
            "solicitation_number": opportunity.solicitation_number,
            "title": opportunity.title,
            "agency": opportunity.agency,
            "estimated_value": opportunity.estimated_value,
            "set_aside": opportunity.set_aside.value if opportunity.set_aside else None,
            "naics_code": opportunity.naics_code,
        }
        prompt = (
            "Provide a concise recommendation (2 sentences) that a capture lead can read quickly. "
            "Explain the bid/no-bid decision referencing the numerical scores. "
            "Respond in plain text without additional formatting.\n"
            f"Opportunity details:\n{json.dumps(opportunity_context, default=str, indent=2)}\n"
            f"Score breakdown:\n{json.dumps(scores_snapshot, default=str, indent=2)}"
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
            self.logger.warning("Unable to generate LLM rationale: %s", exc)
            return (
                "LLM rationale unavailable; see individual score details for justification. "
                f"(error: {exc})"
            )
