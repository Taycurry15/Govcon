"""API routes for agent management and execution."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime
import asyncio

from govcon.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


# Request/Response Models
class AgentExecutionRequest(BaseModel):
    """Request to execute an agent."""
    agent_name: str
    parameters: Dict[str, Any] = {}
    async_execution: bool = False


class AgentStatus(BaseModel):
    """Agent status information."""
    agent_name: str
    status: str  # idle, running, error, completed
    last_run: Optional[datetime] = None
    last_error: Optional[str] = None
    execution_count: int = 0
    average_duration_seconds: Optional[float] = None


class AgentMetrics(BaseModel):
    """Agent performance metrics."""
    agent_name: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    average_duration_seconds: float
    last_24h_executions: int
    error_rate: float


class AgentConfig(BaseModel):
    """Agent configuration."""
    agent_name: str
    enabled: bool
    max_retries: int
    timeout_seconds: int
    parameters: Dict[str, Any]


# In-memory storage for agent statuses (replace with database in production)
agent_statuses: Dict[str, AgentStatus] = {}
agent_execution_tasks: Dict[str, asyncio.Task] = {}


@router.get("/agents", response_model=List[str])
async def list_agents() -> List[str]:
    """List all available agents."""
    return [
        "discovery",
        "bid_nobid",
        "solicitation_review",
        "proposal_generation",
        "pricing",
        "communications",
        "orchestrator",
        "approvals"
    ]


@router.get("/agents/{agent_name}/status", response_model=AgentStatus)
async def get_agent_status(agent_name: str) -> AgentStatus:
    """Get status of a specific agent."""
    if agent_name not in agent_statuses:
        agent_statuses[agent_name] = AgentStatus(
            agent_name=agent_name,
            status="idle",
            execution_count=0
        )
    return agent_statuses[agent_name]


@router.get("/agents/status/all", response_model=List[AgentStatus])
async def get_all_agent_statuses() -> List[AgentStatus]:
    """Get status of all agents."""
    agents = await list_agents()
    statuses = []
    for agent_name in agents:
        status = await get_agent_status(agent_name)
        statuses.append(status)
    return statuses


@router.post("/agents/{agent_name}/execute")
async def execute_agent(
    agent_name: str,
    request: AgentExecutionRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Execute an agent with given parameters."""
    logger.info(f"Executing agent: {agent_name} with params: {request.parameters}")

    # Update status
    if agent_name not in agent_statuses:
        agent_statuses[agent_name] = AgentStatus(
            agent_name=agent_name,
            status="idle",
            execution_count=0
        )

    agent_statuses[agent_name].status = "running"
    agent_statuses[agent_name].last_run = datetime.utcnow()

    try:
        # Import and execute the appropriate agent
        if agent_name == "discovery":
            from govcon.agents.discovery import DiscoveryAgent
            agent = DiscoveryAgent()
            result = await agent.discover(**request.parameters)
        elif agent_name == "bid_nobid":
            from govcon.agents.bid_nobid import BidNoBidAgent
            agent = BidNoBidAgent()
            result = await agent.analyze(**request.parameters)
        elif agent_name == "solicitation_review":
            from govcon.agents.solicitation_review import SolicitationReviewAgent
            agent = SolicitationReviewAgent()
            result = await agent.review(**request.parameters)
        elif agent_name == "proposal_generation":
            from govcon.agents.proposal_generation import ProposalGenerationAgent
            agent = ProposalGenerationAgent()
            result = await agent.generate(**request.parameters)
        elif agent_name == "pricing":
            from govcon.agents.pricing import PricingAgent
            agent = PricingAgent()
            result = await agent.price(**request.parameters)
        elif agent_name == "communications":
            from govcon.agents.communications import CommunicationsAgent
            agent = CommunicationsAgent()
            result = await agent.draft(**request.parameters)
        else:
            raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")

        agent_statuses[agent_name].status = "completed"
        agent_statuses[agent_name].execution_count += 1

        return {
            "status": "success",
            "agent": agent_name,
            "result": result,
            "execution_time": datetime.utcnow()
        }

    except Exception as e:
        logger.error(f"Error executing agent {agent_name}: {e}")
        agent_statuses[agent_name].status = "error"
        agent_statuses[agent_name].last_error = str(e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{agent_name}/stop")
async def stop_agent(agent_name: str) -> Dict[str, str]:
    """Stop a running agent."""
    if agent_name in agent_execution_tasks:
        task = agent_execution_tasks[agent_name]
        task.cancel()
        del agent_execution_tasks[agent_name]
        agent_statuses[agent_name].status = "idle"
        return {"status": "stopped", "agent": agent_name}
    else:
        raise HTTPException(status_code=404, detail=f"No running task for agent {agent_name}")


@router.get("/agents/{agent_name}/metrics", response_model=AgentMetrics)
async def get_agent_metrics(agent_name: str) -> AgentMetrics:
    """Get performance metrics for an agent."""
    # This would fetch from database in production
    status = await get_agent_status(agent_name)

    return AgentMetrics(
        agent_name=agent_name,
        total_executions=status.execution_count,
        successful_executions=status.execution_count,
        failed_executions=0,
        average_duration_seconds=status.average_duration_seconds or 0,
        last_24h_executions=status.execution_count,
        error_rate=0.0
    )


@router.get("/agents/{agent_name}/config", response_model=AgentConfig)
async def get_agent_config(agent_name: str) -> AgentConfig:
    """Get agent configuration."""
    return AgentConfig(
        agent_name=agent_name,
        enabled=True,
        max_retries=3,
        timeout_seconds=300,
        parameters={}
    )


@router.put("/agents/{agent_name}/config")
async def update_agent_config(agent_name: str, config: AgentConfig) -> Dict[str, str]:
    """Update agent configuration."""
    logger.info(f"Updating config for agent {agent_name}: {config}")
    # In production, save to database
    return {"status": "success", "message": f"Configuration updated for {agent_name}"}


@router.get("/agents/{agent_name}/logs")
async def get_agent_logs(
    agent_name: str,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """Get execution logs for an agent."""
    # In production, fetch from log storage
    return {
        "agent": agent_name,
        "logs": [],
        "total": 0,
        "limit": limit,
        "offset": offset
    }
