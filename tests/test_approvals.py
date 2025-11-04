"""Tests for approval gate agents and orchestrator integration."""

import pytest

from govcon.agents.approvals import (
    ApprovalDecision,
    GoldTeamApprovalAgent,
    GoldTeamContext,
    PinkTeamApprovalAgent,
    PinkTeamContext,
)
from govcon.agents.orchestrator import WorkflowOrchestrator, WorkflowStage


def test_pink_team_agent_requires_rework_before_approval() -> None:
    """Ensure the pink team agent requests rework when readiness gaps exist."""
    agent = PinkTeamApprovalAgent()
    initial_context = PinkTeamContext(
        bid_scorecard={"total_score": 72.0, "timeline_score": 58.0, "strategic_score": 68.0},
        capture_plan_ready=False,
        risk_register=[],
        mitigations=[],
        compliance_outline_ready=True,
        staffing_plan_ready=True,
        kickoff_schedule_confirmed=True,
    )

    outcome = agent.evaluate(initial_context)
    assert outcome.decision == ApprovalDecision.REVISE
    assert outcome.required_actions  # Action plan provided

    improved_context = PinkTeamContext(
        bid_scorecard={"total_score": 85.0, "timeline_score": 70.0, "strategic_score": 78.0},
        capture_plan_ready=True,
        risk_register=[],
        mitigations=["Revisit capture strategy to raise bid score above 70."],
        compliance_outline_ready=True,
        staffing_plan_ready=True,
        kickoff_schedule_confirmed=True,
    )
    approval = agent.evaluate(improved_context)
    assert approval.decision == ApprovalDecision.APPROVED


def test_gold_team_agent_requires_rework_before_approval() -> None:
    """Ensure the gold team agent enforces readiness checks."""
    agent = GoldTeamApprovalAgent()
    initial_context = GoldTeamContext(
        proposal_summary={
            "quality_score": 78.0,
            "compliance_score": 92.0,
            "color_team_trend": "steady",
        },
        pricing_summary={"confidence": 0.86, "review_completed": False},
        compliance_gaps=["REQ-0001"],
        red_team_findings_open=["Executive summary clarity"],
        submission_package_ready=False,
        executive_reviewed=False,
        past_performance_updated=False,
    )

    outcome = agent.evaluate(initial_context)
    assert outcome.decision == ApprovalDecision.REVISE
    assert (
        "Finalize compliance matrix sign-off" not in outcome.required_actions
    )  # specific gap noted

    improved_context = GoldTeamContext(
        proposal_summary={
            "quality_score": 90.0,
            "compliance_score": 99.0,
            "color_team_trend": "improving",
        },
        pricing_summary={"confidence": 0.97, "review_completed": True},
        compliance_gaps=[],
        red_team_findings_open=[],
        submission_package_ready=True,
        executive_reviewed=True,
        past_performance_updated=True,
    )
    approval = agent.evaluate(improved_context)
    assert approval.decision == ApprovalDecision.APPROVED


@pytest.mark.asyncio
async def test_orchestrator_handles_pink_and_gold_rework(monkeypatch) -> None:
    """Run the orchestrator end-to-end to ensure approval gates rework successfully."""
    orchestrator = WorkflowOrchestrator()

    async def fake_chat(*args, **kwargs):
        return "Workflow summary placeholder."

    monkeypatch.setattr("govcon.agents.orchestrator.llm_service.chat", fake_chat)

    result = await orchestrator.execute_full_workflow("TEST-APPR-001", auto_approve=False)

    assert result.success is True
    assert WorkflowStage.PINK_TEAM in result.stages_completed
    assert WorkflowStage.GOLD_TEAM in result.stages_completed

    state = orchestrator.get_workflow_state("TEST-APPR-001")
    assert state is not None
    assert "pink_team_decision" in state.artifacts
    assert "gold_team_decision" in state.artifacts
