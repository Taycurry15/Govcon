"""API routes for the monitoring agent."""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from govcon.agents.monitoring import MonitoringAgent
from govcon.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Global monitoring agent instance
monitoring_agent: MonitoringAgent | None = None


class MonitoringConfig(BaseModel):
    """Monitoring agent configuration."""
    check_interval_seconds: int = 30
    auto_fix_enabled: bool = True


@router.post("/monitoring/start")
async def start_monitoring() -> Dict[str, str]:
    """Start the monitoring agent."""
    global monitoring_agent

    if monitoring_agent and monitoring_agent.is_running:
        return {"status": "already_running", "message": "Monitoring agent is already running"}

    monitoring_agent = MonitoringAgent()

    # Start in background
    import asyncio
    asyncio.create_task(monitoring_agent.start())

    logger.info("Monitoring agent started")
    return {"status": "started", "message": "Monitoring agent has been started"}


@router.post("/monitoring/stop")
async def stop_monitoring() -> Dict[str, str]:
    """Stop the monitoring agent."""
    global monitoring_agent

    if not monitoring_agent or not monitoring_agent.is_running:
        raise HTTPException(status_code=400, detail="Monitoring agent is not running")

    await monitoring_agent.stop()
    logger.info("Monitoring agent stopped")

    return {"status": "stopped", "message": "Monitoring agent has been stopped"}


@router.get("/monitoring/status")
async def get_monitoring_status() -> Dict[str, Any]:
    """Get monitoring agent status."""
    global monitoring_agent

    if not monitoring_agent:
        return {
            "is_running": False,
            "message": "Monitoring agent has not been initialized"
        }

    return {
        "is_running": monitoring_agent.is_running,
        "check_interval_seconds": monitoring_agent.check_interval_seconds,
        "detected_errors_count": len(monitoring_agent.detected_errors)
    }


@router.get("/monitoring/report")
async def get_monitoring_report() -> Dict[str, Any]:
    """Get monitoring agent error report."""
    global monitoring_agent

    if not monitoring_agent:
        raise HTTPException(status_code=400, detail="Monitoring agent has not been initialized")

    return monitoring_agent.get_error_report()


@router.put("/monitoring/config")
async def update_monitoring_config(config: MonitoringConfig) -> Dict[str, str]:
    """Update monitoring agent configuration."""
    global monitoring_agent

    if not monitoring_agent:
        raise HTTPException(status_code=400, detail="Monitoring agent has not been initialized")

    monitoring_agent.check_interval_seconds = config.check_interval_seconds

    logger.info(f"Monitoring agent configuration updated: {config}")
    return {"status": "success", "message": "Configuration updated"}


@router.get("/monitoring/errors")
async def get_detected_errors(limit: int = 50) -> Dict[str, Any]:
    """Get recently detected errors."""
    global monitoring_agent

    if not monitoring_agent:
        return {"errors": [], "total": 0}

    errors = sorted(
        monitoring_agent.detected_errors,
        key=lambda x: x.timestamp,
        reverse=True
    )[:limit]

    return {
        "errors": [
            {
                "error_id": e.error_id,
                "type": e.error_type.value,
                "severity": e.severity.value,
                "component": e.component,
                "message": e.message,
                "details": e.details,
                "timestamp": e.timestamp.isoformat(),
                "fix_attempted": e.fix_attempted,
                "fix_successful": e.fix_successful,
                "fix_actions": e.fix_actions
            }
            for e in errors
        ],
        "total": len(monitoring_agent.detected_errors)
    }
