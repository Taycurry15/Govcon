"""Workflow API routes."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from govcon.agents.orchestrator import WorkflowOrchestrator
from govcon.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Global orchestrator instance
orchestrator = WorkflowOrchestrator()


class DiscoveryRequest(BaseModel):
    """Discovery request model."""

    days_back: int = 7


class WorkflowRequest(BaseModel):
    """Workflow execution request model."""

    opportunity_id: str
    auto_approve: bool = False


@router.post("/discover")
async def run_discovery(request: DiscoveryRequest) -> dict[str, Any]:
    """
    Run discovery to find new opportunities.

    Args:
        request: Discovery request parameters

    Returns:
        Discovery summary
    """
    logger.info(f"Discovery requested: {request.days_back} days back")

    result = await orchestrator.run_discovery(days_back=request.days_back)

    return {
        "status": "success",
        "result": result,
    }


@router.post("/execute")
async def execute_workflow(request: WorkflowRequest) -> dict[str, Any]:
    """
    Execute complete workflow for an opportunity.

    Args:
        request: Workflow request parameters

    Returns:
        Workflow execution summary
    """
    logger.info(f"Workflow execution requested for opportunity: {request.opportunity_id}")

    result = await orchestrator.execute_full_workflow(
        opportunity_id=request.opportunity_id, auto_approve=request.auto_approve
    )

    return {
        "status": "success" if result.success else "failed",
        "result": result.model_dump(),
    }


@router.get("/status/{opportunity_id}")
async def get_workflow_status(opportunity_id: str) -> dict[str, Any]:
    """
    Get workflow status for an opportunity.

    Args:
        opportunity_id: Opportunity ID

    Returns:
        Workflow state
    """
    workflow_state = orchestrator.get_workflow_state(opportunity_id)

    if not workflow_state:
        raise HTTPException(status_code=404, detail="Workflow not found for this opportunity")

    return {
        "status": "success",
        "workflow_state": workflow_state.model_dump(),
    }
