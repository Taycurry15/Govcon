"""Approval gate agents for Pink and Gold team reviews."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ApprovalDecision(str, Enum):
    """Possible decisions for an approval gate."""

    APPROVED = "approved"
    REVISE = "revise"
    REJECTED = "rejected"


class ApprovalOutcome(BaseModel):
    """Result from an approval evaluation."""

    gate: str
    decision: ApprovalDecision
    approver: str
    decided_at: datetime = Field(default_factory=datetime.utcnow)
    comments: list[str] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)


class PinkTeamContext(BaseModel):
    """Context required for the pink team gate."""

    bid_scorecard: dict[str, Any]
    capture_plan_ready: bool
    risk_register: list[str] = Field(default_factory=list)
    mitigations: list[str] = Field(default_factory=list)
    compliance_outline_ready: bool = False
    staffing_plan_ready: bool = False
    kickoff_schedule_confirmed: bool = False


class GoldTeamContext(BaseModel):
    """Context required for the gold team gate."""

    proposal_summary: dict[str, Any]
    pricing_summary: dict[str, Any]
    compliance_gaps: list[str] = Field(default_factory=list)
    red_team_findings_open: list[str] = Field(default_factory=list)
    submission_package_ready: bool = False
    executive_reviewed: bool = False
    past_performance_updated: bool = False


class PinkTeamApprovalAgent:
    """Evaluates capture readiness during the Pink Team gate."""

    approver_role = "Capture Director"

    def evaluate(self, context: PinkTeamContext) -> ApprovalOutcome:
        """Perform a structured review of capture readiness."""
        comments: list[str] = []
        required_actions: list[str] = []

        total_score = float(context.bid_scorecard.get("total_score", 0.0))
        timeline_score = float(context.bid_scorecard.get("timeline_score", 0.0))
        strategic_score = float(context.bid_scorecard.get("strategic_score", 0.0))

        if total_score < 70:
            comments.append(
                "Composite bid score below Pink Team threshold (70). Additional capture rigor required."
            )
            required_actions.append("Revisit capture strategy to raise bid score above 70.")

        if timeline_score < 60:
            comments.append("Response timeline risk identified; insufficient runway for execution.")
            required_actions.append(
                "Produce a compressed execution schedule with clear decision gates."
            )

        if strategic_score < 60:
            comments.append("Strategic alignment is weak against portfolio priorities.")
            required_actions.append(
                "Document clear differentiators and executive sponsorship commitment."
            )

        if context.risk_register and not context.mitigations:
            comments.append("Risks logged without mitigation plans.")
            required_actions.append("Add mitigation owners and due dates to risk register.")

        if not context.capture_plan_ready:
            comments.append("Capture plan not baselined.")
            required_actions.append("Publish capture plan with approved pursuit strategy.")

        if not context.compliance_outline_ready:
            comments.append("Compliance outline not prepared for proposal team.")
            required_actions.append("Draft compliance outline covering Sections C, L, and M.")

        if not context.staffing_plan_ready:
            comments.append("Staffing plan incomplete; key personnel coverage unclear.")
            required_actions.append("Finalize staffing plan with named leads and availability.")

        if not context.kickoff_schedule_confirmed:
            comments.append("Kickoff schedule not confirmed with stakeholders.")
            required_actions.append(
                "Lock Pink Team to Gold Team calendar with key deliverable dates."
            )

        # Determine outcome
        if total_score < 55 or len(required_actions) >= 4:
            decision = ApprovalDecision.REJECTED
        elif required_actions:
            decision = ApprovalDecision.REVISE
        else:
            decision = ApprovalDecision.APPROVED
            comments.append("Capture is ready to proceed to detailed solicitation review.")

        return ApprovalOutcome(
            gate="pink_team",
            decision=decision,
            approver=self.approver_role,
            comments=comments,
            required_actions=required_actions,
        )


class GoldTeamApprovalAgent:
    """Evaluates proposal readiness during the Gold Team gate."""

    approver_role = "Executive Review Board"

    def evaluate(self, context: GoldTeamContext) -> ApprovalOutcome:
        """Perform final readiness review before submission."""
        comments: list[str] = []
        required_actions: list[str] = []

        proposal_quality = float(context.proposal_summary.get("quality_score", 0.0))
        compliance_score = float(context.proposal_summary.get("compliance_score", 0.0))
        pricing_confidence = float(context.pricing_summary.get("confidence", 0.0))
        color_team_trend = context.proposal_summary.get("color_team_trend")

        if proposal_quality < 80:
            comments.append("Proposal narrative quality below Gold Team expectation (80).")
            required_actions.append(
                "Address executive summary and discriminators based on color-team input."
            )

        if compliance_score < 95:
            comments.append("Compliance traceability below 95% coverage.")
            required_actions.append("Close compliance gaps and update matrix sign-off.")

        if pricing_confidence < 0.9:
            comments.append("Pricing confidence below target (90%).")
            required_actions.append(
                "Validate pricing model with pricing lead and refresh cost realism analysis."
            )

        if context.compliance_gaps:
            comments.append("Open compliance gaps detected.")
            required_actions.extend(
                [f"Resolve compliance gap: {gap}" for gap in context.compliance_gaps]
            )

        if context.red_team_findings_open:
            comments.append("Outstanding red team findings remain open.")
            required_actions.extend(
                [f"Close red team finding: {finding}" for finding in context.red_team_findings_open]
            )

        if not context.submission_package_ready:
            comments.append("Submission package incomplete (forms, attachments, portal readiness).")
            required_actions.append(
                "Complete submission checklist and validate upload credentials."
            )

        if not context.executive_reviewed:
            comments.append("Executive sponsor has not signed off on final content.")
            required_actions.append("Secure executive approval for pricing, staffing, and risks.")

        if not context.past_performance_updated:
            comments.append("Past performance references not refreshed.")
            required_actions.append("Update past performance narratives and customer POCs.")

        if color_team_trend and color_team_trend.lower() == "declining":
            comments.append("Color-team trend indicates declining confidence.")
            required_actions.append(
                "Review color-team findings and incorporate remediation actions."
            )

        # Decide outcome
        if compliance_score < 85 or proposal_quality < 70:
            decision = ApprovalDecision.REJECTED
        elif required_actions:
            decision = ApprovalDecision.REVISE
        else:
            decision = ApprovalDecision.APPROVED
            comments.append("Proposal package is ready for submission pending final production.")

        return ApprovalOutcome(
            gate="gold_team",
            decision=decision,
            approver=self.approver_role,
            comments=comments,
            required_actions=required_actions,
        )


__all__ = [
    "ApprovalDecision",
    "ApprovalOutcome",
    "PinkTeamContext",
    "GoldTeamContext",
    "PinkTeamApprovalAgent",
    "GoldTeamApprovalAgent",
]
