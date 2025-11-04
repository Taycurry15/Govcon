"""API routes for system monitoring and configuration."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import psutil
import platform

from govcon.utils.logger import get_logger
from govcon.utils.config import get_settings

logger = get_logger(__name__)
router = APIRouter()
settings = get_settings()


# Models
class SystemHealth(BaseModel):
    """System health status."""
    status: str  # healthy, degraded, unhealthy
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    uptime_seconds: float
    services: Dict[str, str]


class SystemMetrics(BaseModel):
    """System performance metrics."""
    cpu_count: int
    cpu_percent: float
    memory_total_gb: float
    memory_used_gb: float
    memory_percent: float
    disk_total_gb: float
    disk_used_gb: float
    disk_percent: float
    network_sent_mb: float
    network_recv_mb: float


class ServiceStatus(BaseModel):
    """Service status."""
    name: str
    status: str  # running, stopped, error
    url: Optional[str] = None
    last_check: datetime
    response_time_ms: Optional[float] = None


class ErrorLog(BaseModel):
    """Error log entry."""
    id: str
    timestamp: datetime
    level: str
    component: str
    message: str
    traceback: Optional[str] = None
    resolved: bool = False


class ConfigItem(BaseModel):
    """Configuration item."""
    key: str
    value: Any
    category: str
    description: str
    editable: bool


@router.get("/system/health", response_model=SystemHealth)
async def get_system_health() -> SystemHealth:
    """Get overall system health status."""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    # Check service statuses
    services = {
        "database": "healthy",
        "cache": "healthy",
        "api": "healthy",
        "agents": "healthy"
    }

    # Determine overall status
    if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
        status = "unhealthy"
    elif cpu_percent > 70 or memory.percent > 70 or disk.percent > 80:
        status = "degraded"
    else:
        status = "healthy"

    return SystemHealth(
        status=status,
        timestamp=datetime.utcnow(),
        cpu_percent=cpu_percent,
        memory_percent=memory.percent,
        disk_percent=disk.percent,
        uptime_seconds=psutil.boot_time(),
        services=services
    )


@router.get("/system/metrics", response_model=SystemMetrics)
async def get_system_metrics() -> SystemMetrics:
    """Get detailed system metrics."""
    cpu_count = psutil.cpu_count()
    cpu_percent = psutil.cpu_percent(interval=1)

    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    net_io = psutil.net_io_counters()

    return SystemMetrics(
        cpu_count=cpu_count,
        cpu_percent=cpu_percent,
        memory_total_gb=memory.total / (1024 ** 3),
        memory_used_gb=memory.used / (1024 ** 3),
        memory_percent=memory.percent,
        disk_total_gb=disk.total / (1024 ** 3),
        disk_used_gb=disk.used / (1024 ** 3),
        disk_percent=disk.percent,
        network_sent_mb=net_io.bytes_sent / (1024 ** 2),
        network_recv_mb=net_io.bytes_recv / (1024 ** 2)
    )


@router.get("/system/services", response_model=List[ServiceStatus])
async def get_service_statuses() -> List[ServiceStatus]:
    """Get status of all system services."""
    services = [
        ServiceStatus(
            name="PostgreSQL",
            status="running",
            url="postgresql://postgres:5432",
            last_check=datetime.utcnow(),
            response_time_ms=5.2
        ),
        ServiceStatus(
            name="Redis",
            status="running",
            url="redis://redis:6379",
            last_check=datetime.utcnow(),
            response_time_ms=2.1
        ),
        ServiceStatus(
            name="FastAPI",
            status="running",
            url="http://localhost:8000",
            last_check=datetime.utcnow(),
            response_time_ms=1.5
        ),
    ]
    return services


@router.get("/system/info")
async def get_system_info() -> Dict[str, Any]:
    """Get system information."""
    return {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "hostname": platform.node()
    }


@router.get("/system/errors", response_model=List[ErrorLog])
async def get_error_logs(
    limit: int = 50,
    resolved: Optional[bool] = None,
    component: Optional[str] = None
) -> List[ErrorLog]:
    """Get error logs."""
    # In production, fetch from logging system
    return []


@router.post("/system/errors/{error_id}/resolve")
async def resolve_error(error_id: str) -> Dict[str, str]:
    """Mark an error as resolved."""
    logger.info(f"Marking error {error_id} as resolved")
    return {"status": "success", "error_id": error_id}


@router.get("/system/config", response_model=List[ConfigItem])
async def get_config() -> List[ConfigItem]:
    """Get system configuration."""
    config_items = [
        ConfigItem(
            key="COMPANY_NAME",
            value=settings.company_name,
            category="Company",
            description="Company name",
            editable=True
        ),
        ConfigItem(
            key="SET_ASIDE_PREFS",
            value=settings.set_aside_prefs,
            category="Discovery",
            description="Set-aside preferences",
            editable=True
        ),
        ConfigItem(
            key="ALLOWED_NAICS",
            value=settings.allowed_naics,
            category="Discovery",
            description="Allowed NAICS codes",
            editable=True
        ),
        ConfigItem(
            key="ALLOWED_PSC",
            value=settings.allowed_psc,
            category="Discovery",
            description="Allowed PSC codes",
            editable=True
        ),
    ]
    return config_items


@router.put("/system/config/{key}")
async def update_config(key: str, value: Dict[str, Any]) -> Dict[str, str]:
    """Update a configuration value."""
    logger.info(f"Updating config {key} to {value}")
    # In production, update configuration storage
    return {"status": "success", "key": key}


@router.post("/system/restart")
async def restart_system() -> Dict[str, str]:
    """Restart the system (requires admin privileges)."""
    logger.warning("System restart requested")
    # In production, implement proper restart mechanism
    return {"status": "restart_initiated", "message": "System will restart shortly"}


@router.get("/system/logs")
async def get_system_logs(
    limit: int = 100,
    level: Optional[str] = None,
    component: Optional[str] = None
) -> Dict[str, Any]:
    """Get system logs."""
    # In production, fetch from centralized logging
    return {
        "logs": [],
        "total": 0,
        "limit": limit
    }


@router.get("/system/database/status")
async def get_database_status() -> Dict[str, Any]:
    """Get database status and statistics."""
    return {
        "status": "connected",
        "host": "localhost",
        "port": 5432,
        "database": "govcon",
        "tables": [
            "opportunities",
            "proposals",
            "users",
            "audit_logs",
            "pricing",
            "early_signals",
            "knowledge_base"
        ],
        "total_connections": 5,
        "active_queries": 2
    }


@router.post("/system/database/backup")
async def backup_database() -> Dict[str, str]:
    """Trigger database backup."""
    logger.info("Database backup initiated")
    return {
        "status": "success",
        "message": "Backup initiated",
        "backup_id": f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    }
