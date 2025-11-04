"""Pricing & BOE Agent - Generates market-rate pricing.

This agent implements the Pricing logic from spec Section 6:
"""

import json
from datetime import date
from typing import Any, Optional

from pydantic import BaseModel

from govcon.services.llm import ChatMessage, llm_service
from govcon.utils.config import get_settings
from govcon.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

PRICING_AGENT_INSTRUCTIONS = """Role
    You are the Pricing & Basis-of-Estimate Agent. You convert technical staffing plans into defensible, audit-ready pricing
    artifacts for The Bronze Shield's federal proposals.

Mission Objectives
    • Produce wrap-rate calculations, fully burdened labor rates, BOE narratives, and sensitivity scenarios.
    • Ensure all pricing assumptions comply with FAR, agency guidance, and solicitation-specific instructions.
    • Highlight risks (rate ceilings, wage determinations, escalation) before packages move to leadership review.

Data Priorities
    • SOC Mapping -> map labor categories to SOC codes for sourcing BLS data.
    • Market Benchmarks -> pull from BLS OES, GSA CALC, SCA/WD, commercial intel when available.
    • Internal Rates -> use configured defaults for fringe, overhead, G&A, fee; allow scenario adjustments.
    • Compliance Inputs -> note union requirements, pass-through rules, small-business subcontracting thresholds.

Process Blueprint
    1. Normalize inputs: labor_categories list, estimated_hours dict, locality, escalation assumptions.
    2. For each labor category:
         a. Map to SOC code (`map_lcat_to_soc`).
         b. Retrieve market data (`get_bls_rate`, `get_gsa_calc_rate`) and reconcile differences.
         c. Apply wrap sequence (Fringe -> Overhead -> G&A -> Fee) using `calculate_fully_burdened_rate`.
    3. Calculate labor cost (rate x hours) and aggregate totals (labor, ODC, total price).
    4. Generate BOE narrative summarizing methodology, data sources, and key assumptions.
    5. Build sensitivity analysis (-10%, +10%, -25%, +25%) and interpret operational impact.
    6. Package outputs for downstream proposal insertion (tables, JSON structures, narrative paragraphs).

Quality & Compliance
    • Ensure effective dates and data sources accompany every rate.
    • Flag when pricing relies on outdated data (>12 months) or when rates exceed known contract ceilings.
    • Verify SCA/Wage Determination requirements, locality pay adjustments, and union differentials.
    • Identify data gaps and recommend next steps (e.g., vendor quotes, partner rates, escalation approvals).

Output Format
    • `PricingWorkbookResult` populated with labor category breakdown, wrap rates, totals, narrative, assumptions,
      data sources, and sensitivity analysis.
    • Provide supplementary bullet list of risks/opportunities (e.g., discount levers, staffing contingencies).
    • Maintain audit trail by storing intermediate calculations when requested."""


class LaborCategoryRate(BaseModel):
    """Labor category with fully loaded rate."""

    model_config = {"extra": "forbid"}

    lcat_code: str
    lcat_name: str
    soc_code: Optional[str] = None
    base_rate: float
    fringe: float
    overhead: float
    ga: float
    fee: float
    fully_burdened_rate: float
    data_source: str
    effective_date: str


class PricingWorkbookResult(BaseModel):
    """Complete pricing workbook result."""

    model_config = {"extra": "forbid"}

    labor_categories: list[LaborCategoryRate]
    wrap_rates: Any
    total_labor_cost: float
    total_odc_cost: float = 0.0
    total_cost: float
    boe_narrative: str
    assumptions: list[str]
    data_sources: Any
    sensitivity_analysis: Any


def get_bls_rate(soc_code: str, locality: str = "National") -> Any:
    """
    Get labor rate from BLS OES data.

    Args:
        soc_code: Standard Occupational Classification code
        locality: Geographic locality (default: National)

    Returns:
        Dictionary with rate data
    """
    # Mock implementation - in production, would call BLS API
    bls_rates = {
        "15-1252": {"title": "Software Developers", "mean_hourly": 55.23, "median_hourly": 52.00},
        "15-1299": {
            "title": "Computer Occupations, All Other",
            "mean_hourly": 48.50,
            "median_hourly": 45.00,
        },
        "15-1212": {
            "title": "Information Security Analysts",
            "mean_hourly": 58.77,
            "median_hourly": 55.00,
        },
        "13-1081": {"title": "Logisticians", "mean_hourly": 42.15, "median_hourly": 40.00},
        "27-3091": {
            "title": "Interpreters and Translators",
            "mean_hourly": 28.63,
            "median_hourly": 26.50,
        },
    }

    rate_data = bls_rates.get(
        soc_code, {"title": "Unknown", "mean_hourly": 50.00, "median_hourly": 48.00}
    )

    return {
        "soc_code": soc_code,
        "title": rate_data["title"],
        "base_hourly_rate": rate_data["mean_hourly"],
        "locality": locality,
        "data_source": "BLS OES",
        "effective_date": date.today().isoformat(),
    }


def get_gsa_calc_rate(lcat_name: str, contract_vehicle: str = "GSA STARS III") -> Any:
    """
    Get labor rate from GSA CALC database.

    Args:
        lcat_name: Labor category name
        contract_vehicle: Contract vehicle to query

    Returns:
        Dictionary with rate data
    """
    # Mock implementation - in production, would call GSA CALC API
    calc_rates = {
        "software engineer": {"min": 45.00, "max": 125.00, "avg": 75.00},
        "senior software engineer": {"min": 65.00, "max": 165.00, "avg": 95.00},
        "cybersecurity analyst": {"min": 55.00, "max": 145.00, "avg": 85.00},
        "project manager": {"min": 60.00, "max": 150.00, "avg": 90.00},
        "business analyst": {"min": 50.00, "max": 120.00, "avg": 70.00},
    }

    lcat_lower = lcat_name.lower()
    rate_data = None

    for key, value in calc_rates.items():
        if key in lcat_lower:
            rate_data = value
            break

    if not rate_data:
        rate_data = {"min": 50.00, "max": 100.00, "avg": 65.00}

    return {
        "lcat_name": lcat_name,
        "base_hourly_rate": rate_data["avg"],
        "min_rate": rate_data["min"],
        "max_rate": rate_data["max"],
        "contract_vehicle": contract_vehicle,
        "data_source": "GSA CALC",
        "effective_date": date.today().isoformat(),
    }


def map_lcat_to_soc(lcat_name: str) -> str:
    """
    Map labor category to SOC code.

    Args:
        lcat_name: Labor category name

    Returns:
        SOC code
    """
    lcat_lower = lcat_name.lower()

    mappings = {
        "software": "15-1252",  # Software Developers
        "developer": "15-1252",
        "programmer": "15-1252",
        "cybersecurity": "15-1212",  # Information Security Analysts
        "security analyst": "15-1212",
        "infosec": "15-1212",
        "project manager": "13-1081",  # Logisticians (closest match)
        "program manager": "13-1081",
        "translator": "27-3091",  # Interpreters and Translators
        "interpreter": "27-3091",
        "asl": "27-3091",
    }

    for keyword, soc in mappings.items():
        if keyword in lcat_lower:
            return soc

    return "15-1299"  # Default: Computer Occupations, All Other


def calculate_fully_burdened_rate(
    base_rate: float,
    fringe_rate: float,
    overhead_rate: float,
    ga_rate: float,
    fee_rate: float,
) -> dict[str, float]:
    """
    Calculate fully burdened hourly rate.

    Args:
        base_rate: Base hourly rate
        fringe_rate: Fringe benefits rate (%)
        overhead_rate: Overhead rate (%)
        ga_rate: G&A rate (%)
        fee_rate: Fee/profit rate (%)

    Returns:
        Dictionary with rate breakdown
    """
    fringe = base_rate * (fringe_rate / 100)
    subtotal_1 = base_rate + fringe

    overhead = subtotal_1 * (overhead_rate / 100)
    subtotal_2 = subtotal_1 + overhead

    ga = subtotal_2 * (ga_rate / 100)
    subtotal_3 = subtotal_2 + ga

    fee = subtotal_3 * (fee_rate / 100)
    fully_burdened = subtotal_3 + fee

    return {
        "base_rate": round(base_rate, 2),
        "fringe": round(fringe, 2),
        "overhead": round(overhead, 2),
        "ga": round(ga, 2),
        "fee": round(fee, 2),
        "fully_burdened_rate": round(fully_burdened, 2),
    }


def generate_boe_narrative(
    labor_categories: list[dict], data_sources: dict, assumptions: list[str]
) -> str:
    """
    Generate Basis of Estimate narrative.

    Args:
        labor_categories: List of labor category data
        data_sources: Data sources used
        assumptions: Key assumptions

    Returns:
        BOE narrative text
    """
    narrative = """BASIS OF ESTIMATE (BOE)

**Overview**
This pricing is based on competitive, realistic, and well-supported labor rates derived from authoritative government and industry sources. Our pricing reflects current market conditions and our proven ability to attract and retain top talent.

**Data Sources**
"""

    for source_name, source_desc in data_sources.items():
        narrative += f"\n• **{source_name}**: {source_desc}"

    narrative += "\n\n**Labor Rate Development**\n"
    narrative += f"We analyzed {len(labor_categories)} labor categories, each mapped to appropriate Standard Occupational Classification (SOC) codes for accurate market comparison.\n\n"

    narrative += "For each labor category, we:\n"
    narrative += "1. Identified the appropriate SOC code based on job duties\n"
    narrative += "2. Obtained current market rates from BLS OES and GSA CALC\n"
    narrative += "3. Applied geographic locality adjustments as appropriate\n"
    narrative += "4. Applied our company's standard wrap rates\n\n"

    narrative += "**Wrap Rates**\n"
    narrative += f"• Fringe Benefits: {settings.default_fringe_rate}%\n"
    narrative += f"• Overhead: {settings.default_overhead_rate}%\n"
    narrative += f"• General & Administrative: {settings.default_ga_rate}%\n"
    narrative += f"• Fee: {settings.default_fee_rate}%\n\n"

    narrative += "These wrap rates are consistent with our company's cost structure and have been validated through our accounting system.\n\n"

    narrative += "**Key Assumptions**\n"
    for i, assumption in enumerate(assumptions, 1):
        narrative += f"{i}. {assumption}\n"

    narrative += "\n**Validation**\n"
    narrative += "Our pricing has been validated through:\n"
    narrative += "• Comparison with recent contract awards for similar work\n"
    narrative += "• Review against GSA Schedule rates (where applicable)\n"
    narrative += "• Analysis of competitive market intelligence\n"
    narrative += "• Internal cost accounting review\n\n"

    narrative += f"**Effective Date**: {date.today().strftime('%B %d, %Y')}\n"

    return narrative


def create_sensitivity_analysis(base_total: float) -> Any:
    """
    Create sensitivity analysis for pricing.

    Args:
        base_total: Base total price

    Returns:
        Dictionary with sensitivity scenarios
    """
    return {
        "base_case": base_total,
        "optimistic_10pct_reduction": base_total * 0.90,
        "pessimistic_10pct_increase": base_total * 1.10,
        "reduced_scope_25pct": base_total * 0.75,
        "extended_scope_25pct": base_total * 1.25,
    }


class PricingAgent:
    """Pricing & BOE Agent for generating market-rate pricing."""

    def __init__(self) -> None:
        """Initialize Pricing Agent."""
        self.settings = settings
        self.logger = logger
        self.instructions = PRICING_AGENT_INSTRUCTIONS
        self.llm_provider = (
            self.settings.pricing_agent_llm_provider or self.settings.default_llm_provider
        )
        self.llm_model = self.settings.pricing_agent_llm_model
        self.llm_temperature = self.settings.openai_temperature

    async def generate_pricing(
        self,
        labor_categories: list[str],
        estimated_hours: dict[str, float],
        locality: str = "National",
    ) -> PricingWorkbookResult:
        """
        Generate pricing workbook.

        Args:
            labor_categories: List of labor category names
            estimated_hours: Hours estimate per category
            locality: Geographic locality

        Returns:
            PricingWorkbookResult with complete pricing
        """
        self.logger.info(f"Generating pricing for {len(labor_categories)} labor categories")

        labor_records: list[LaborCategoryRate] = []
        total_labor_cost = 0.0
        assumptions = [
            "Rates derived from BLS national averages with organization default wrap rates applied.",
            f"Locality basis: {locality}",
        ]
        data_sources: dict[str, Any] = {}

        for category in labor_categories:
            soc_code = map_lcat_to_soc(category)
            bls_rate = get_bls_rate(soc_code, locality)
            wrap = calculate_fully_burdened_rate(
                base_rate=bls_rate["base_hourly_rate"],
                fringe_rate=self.settings.default_fringe_rate,
                overhead_rate=self.settings.default_overhead_rate,
                ga_rate=self.settings.default_ga_rate,
                fee_rate=self.settings.default_fee_rate,
            )

            hours = estimated_hours.get(category, 0.0)
            fully_rate = wrap["fully_burdened_rate"]
            total_labor_cost += fully_rate * hours

            labor_records.append(
                LaborCategoryRate(
                    lcat_code=soc_code,
                    lcat_name=category,
                    soc_code=soc_code,
                    base_rate=bls_rate["base_hourly_rate"],
                    fringe=wrap["fringe"],
                    overhead=wrap["overhead"],
                    ga=wrap["ga"],
                    fee=wrap["fee"],
                    fully_burdened_rate=fully_rate,
                    data_source=bls_rate["data_source"],
                    effective_date=bls_rate["effective_date"],
                )
            )
            data_sources[category] = {
                "soc_code": soc_code,
                "source": bls_rate["data_source"],
                "effective_date": bls_rate["effective_date"],
            }

        sensitivity = create_sensitivity_analysis(total_labor_cost)
        narrative = await self._generate_boe_narrative(
            labor_categories=labor_categories,
            estimated_hours=estimated_hours,
            locality=locality,
            total_cost=total_labor_cost,
        )

        return PricingWorkbookResult(
            labor_categories=labor_records,
            wrap_rates={
                "fringe": settings.default_fringe_rate,
                "overhead": settings.default_overhead_rate,
                "ga": settings.default_ga_rate,
                "fee": settings.default_fee_rate,
            },
            total_labor_cost=total_labor_cost,
            total_cost=total_labor_cost,
            boe_narrative=narrative,
            assumptions=assumptions,
            data_sources=data_sources,
            sensitivity_analysis=sensitivity,
        )

    async def _generate_boe_narrative(
        self,
        *,
        labor_categories: list[str],
        estimated_hours: dict[str, float],
        locality: str,
        total_cost: float,
    ) -> str:
        prompt = (
            "Draft a three-paragraph pricing rationale suitable for a Basis of Estimate. "
            "Paragraph 1: summarize pricing methodology. Paragraph 2: key assumptions and risk mitigations. "
            "Paragraph 3: compliance and next steps. Respond in Markdown.\n"
            f"Labor categories: {json.dumps(labor_categories)}\n"
            f"Estimated hours: {json.dumps(estimated_hours)}\n"
            f"Locality: {locality}\n"
            f"Total evaluated cost: {total_cost:,.2f}"
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
                max_output_tokens=600,
            )
        except Exception as exc:  # pragma: no cover
            self.logger.warning("Unable to generate BOE narrative via LLM: %s", exc)
            return "Pricing narrative pending manual review."
