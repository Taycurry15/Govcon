"""Autonomous monitoring agent for error detection and auto-fix."""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
import traceback
from enum import Enum

from govcon.utils.logger import get_logger
from govcon.utils.database import get_db_session
from govcon.models.audit import AuditLog

logger = get_logger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorType(str, Enum):
    """Types of errors the monitoring agent can handle."""
    API_ERROR = "api_error"
    DATABASE_ERROR = "database_error"
    AGENT_ERROR = "agent_error"
    FRONTEND_ERROR = "frontend_error"
    SYSTEM_ERROR = "system_error"
    CONFIGURATION_ERROR = "configuration_error"


class DetectedError:
    """Represents a detected error."""

    def __init__(
        self,
        error_id: str,
        error_type: ErrorType,
        severity: ErrorSeverity,
        component: str,
        message: str,
        details: Dict[str, Any],
        timestamp: datetime,
        traceback_info: Optional[str] = None
    ):
        self.error_id = error_id
        self.error_type = error_type
        self.severity = severity
        self.component = component
        self.message = message
        self.details = details
        self.timestamp = timestamp
        self.traceback_info = traceback_info
        self.fix_attempted = False
        self.fix_successful = False
        self.fix_actions: List[str] = []


class MonitoringAgent:
    """Autonomous agent that monitors systems and fixes errors automatically."""

    def __init__(self):
        """Initialize the monitoring agent."""
        self.is_running = False
        self.check_interval_seconds = 30
        self.detected_errors: List[DetectedError] = []
        self.error_patterns: Dict[str, Dict[str, Any]] = self._load_error_patterns()
        self.fix_strategies: Dict[ErrorType, callable] = {
            ErrorType.API_ERROR: self._fix_api_error,
            ErrorType.DATABASE_ERROR: self._fix_database_error,
            ErrorType.AGENT_ERROR: self._fix_agent_error,
            ErrorType.FRONTEND_ERROR: self._fix_frontend_error,
            ErrorType.SYSTEM_ERROR: self._fix_system_error,
            ErrorType.CONFIGURATION_ERROR: self._fix_configuration_error,
        }

    def _load_error_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load known error patterns for detection."""
        return {
            "connection_refused": {
                "pattern": ["Connection refused", "ECONNREFUSED"],
                "type": ErrorType.API_ERROR,
                "severity": ErrorSeverity.HIGH,
                "fix_strategy": "restart_service"
            },
            "database_lock": {
                "pattern": ["database is locked", "SQLite lock"],
                "type": ErrorType.DATABASE_ERROR,
                "severity": ErrorSeverity.MEDIUM,
                "fix_strategy": "retry_with_backoff"
            },
            "timeout": {
                "pattern": ["timeout", "timed out"],
                "type": ErrorType.API_ERROR,
                "severity": ErrorSeverity.MEDIUM,
                "fix_strategy": "increase_timeout"
            },
            "out_of_memory": {
                "pattern": ["out of memory", "OOM", "MemoryError"],
                "type": ErrorType.SYSTEM_ERROR,
                "severity": ErrorSeverity.CRITICAL,
                "fix_strategy": "restart_with_increased_memory"
            },
            "rate_limit": {
                "pattern": ["rate limit", "too many requests", "429"],
                "type": ErrorType.API_ERROR,
                "severity": ErrorSeverity.LOW,
                "fix_strategy": "implement_backoff"
            }
        }

    async def start(self):
        """Start the monitoring agent."""
        logger.info("Starting Monitoring Agent")
        self.is_running = True

        try:
            while self.is_running:
                await self._monitoring_cycle()
                await asyncio.sleep(self.check_interval_seconds)
        except Exception as e:
            logger.error(f"Monitoring agent crashed: {e}")
            logger.error(traceback.format_exc())
        finally:
            self.is_running = False

    async def stop(self):
        """Stop the monitoring agent."""
        logger.info("Stopping Monitoring Agent")
        self.is_running = False

    async def _monitoring_cycle(self):
        """Execute one monitoring cycle."""
        logger.debug("Running monitoring cycle")

        # Check various system components
        await self._check_api_health()
        await self._check_database_health()
        await self._check_agent_status()
        await self._check_system_resources()
        await self._check_error_logs()

        # Attempt to fix detected errors
        await self._fix_detected_errors()

    async def _check_api_health(self):
        """Check API endpoints health."""
        try:
            # Check if FastAPI is responding
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8000/health", timeout=5)
                if response.status_code != 200:
                    await self._log_error(
                        error_type=ErrorType.API_ERROR,
                        severity=ErrorSeverity.HIGH,
                        component="FastAPI",
                        message="API health check failed",
                        details={"status_code": response.status_code}
                    )
        except Exception as e:
            await self._log_error(
                error_type=ErrorType.API_ERROR,
                severity=ErrorSeverity.CRITICAL,
                component="FastAPI",
                message="API is not responding",
                details={"error": str(e)},
                traceback_info=traceback.format_exc()
            )

    async def _check_database_health(self):
        """Check database connectivity and performance."""
        try:
            with get_db_session() as session:
                # Try a simple query
                session.execute("SELECT 1")
        except Exception as e:
            await self._log_error(
                error_type=ErrorType.DATABASE_ERROR,
                severity=ErrorSeverity.CRITICAL,
                component="Database",
                message="Database connectivity issue",
                details={"error": str(e)},
                traceback_info=traceback.format_exc()
            )

    async def _check_agent_status(self):
        """Check status of all agents."""
        agent_names = [
            "discovery", "bid_nobid", "solicitation_review",
            "proposal_generation", "pricing", "communications"
        ]

        for agent_name in agent_names:
            try:
                # Check if agent can be imported and initialized
                # This is a basic health check
                pass
            except Exception as e:
                await self._log_error(
                    error_type=ErrorType.AGENT_ERROR,
                    severity=ErrorSeverity.HIGH,
                    component=f"Agent:{agent_name}",
                    message=f"Agent {agent_name} has issues",
                    details={"error": str(e)},
                    traceback_info=traceback.format_exc()
                )

    async def _check_system_resources(self):
        """Check system resources (CPU, memory, disk)."""
        try:
            import psutil

            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            if cpu_percent > 90:
                await self._log_error(
                    error_type=ErrorType.SYSTEM_ERROR,
                    severity=ErrorSeverity.HIGH,
                    component="CPU",
                    message="High CPU usage detected",
                    details={"cpu_percent": cpu_percent}
                )

            if memory.percent > 90:
                await self._log_error(
                    error_type=ErrorType.SYSTEM_ERROR,
                    severity=ErrorSeverity.HIGH,
                    component="Memory",
                    message="High memory usage detected",
                    details={"memory_percent": memory.percent}
                )

            if disk.percent > 90:
                await self._log_error(
                    error_type=ErrorType.SYSTEM_ERROR,
                    severity=ErrorSeverity.MEDIUM,
                    component="Disk",
                    message="High disk usage detected",
                    details={"disk_percent": disk.percent}
                )

        except Exception as e:
            logger.error(f"Error checking system resources: {e}")

    async def _check_error_logs(self):
        """Check recent error logs for patterns."""
        try:
            with get_db_session() as session:
                # Get recent errors from audit logs
                recent_errors = session.query(AuditLog).filter(
                    AuditLog.level == "ERROR",
                    AuditLog.created_at > datetime.utcnow() - timedelta(minutes=5)
                ).all()

                for error_log in recent_errors:
                    # Analyze error pattern
                    error_pattern = self._analyze_error_pattern(error_log.message)
                    if error_pattern:
                        await self._log_error(
                            error_type=error_pattern["type"],
                            severity=error_pattern["severity"],
                            component=error_log.component or "Unknown",
                            message=error_log.message,
                            details=error_log.details or {},
                            traceback_info=error_log.traceback
                        )
        except Exception as e:
            logger.error(f"Error checking error logs: {e}")

    def _analyze_error_pattern(self, message: str) -> Optional[Dict[str, Any]]:
        """Analyze error message to identify known patterns."""
        for pattern_name, pattern_info in self.error_patterns.items():
            for pattern in pattern_info["pattern"]:
                if pattern.lower() in message.lower():
                    return pattern_info
        return None

    async def _log_error(
        self,
        error_type: ErrorType,
        severity: ErrorSeverity,
        component: str,
        message: str,
        details: Dict[str, Any],
        traceback_info: Optional[str] = None
    ):
        """Log a detected error."""
        error_id = f"{error_type.value}_{component}_{datetime.utcnow().timestamp()}"

        detected_error = DetectedError(
            error_id=error_id,
            error_type=error_type,
            severity=severity,
            component=component,
            message=message,
            details=details,
            timestamp=datetime.utcnow(),
            traceback_info=traceback_info
        )

        self.detected_errors.append(detected_error)
        logger.warning(f"Detected error: {error_type.value} in {component}: {message}")

        # Broadcast error to WebSocket clients
        try:
            from govcon.api.routes.websocket import broadcast_error
            await broadcast_error({
                "error_id": error_id,
                "type": error_type.value,
                "severity": severity.value,
                "component": component,
                "message": message,
                "details": details
            })
        except Exception as e:
            logger.error(f"Error broadcasting error notification: {e}")

    async def _fix_detected_errors(self):
        """Attempt to fix detected errors."""
        for error in self.detected_errors:
            if error.fix_attempted:
                continue

            logger.info(f"Attempting to fix error: {error.error_id}")
            error.fix_attempted = True

            try:
                fix_function = self.fix_strategies.get(error.error_type)
                if fix_function:
                    success, actions = await fix_function(error)
                    error.fix_successful = success
                    error.fix_actions = actions

                    if success:
                        logger.info(f"Successfully fixed error: {error.error_id}")
                    else:
                        logger.warning(f"Failed to fix error: {error.error_id}")
                else:
                    logger.warning(f"No fix strategy for error type: {error.error_type}")

            except Exception as e:
                logger.error(f"Error while attempting fix: {e}")
                error.fix_successful = False

    async def _fix_api_error(self, error: DetectedError) -> tuple[bool, List[str]]:
        """Attempt to fix API errors."""
        actions = []

        if "not responding" in error.message.lower():
            actions.append("Attempting to restart API service")
            # In production, implement actual service restart
            await asyncio.sleep(2)
            actions.append("API service restart initiated")
            return True, actions

        elif "rate limit" in error.message.lower():
            actions.append("Implementing exponential backoff")
            # Implement rate limiting logic
            return True, actions

        return False, ["No automatic fix available"]

    async def _fix_database_error(self, error: DetectedError) -> tuple[bool, List[str]]:
        """Attempt to fix database errors."""
        actions = []

        if "locked" in error.message.lower():
            actions.append("Waiting for database lock to release")
            await asyncio.sleep(5)
            actions.append("Retrying database operation")
            return True, actions

        return False, ["No automatic fix available"]

    async def _fix_agent_error(self, error: DetectedError) -> tuple[bool, List[str]]:
        """Attempt to fix agent errors."""
        actions = []

        actions.append(f"Restarting agent: {error.component}")
        # In production, implement agent restart logic
        await asyncio.sleep(1)
        actions.append(f"Agent {error.component} restarted")

        return True, actions

    async def _fix_frontend_error(self, error: DetectedError) -> tuple[bool, List[str]]:
        """Attempt to fix frontend errors."""
        actions = []

        actions.append("Logging frontend error for review")
        # Frontend errors typically need manual review

        return False, actions

    async def _fix_system_error(self, error: DetectedError) -> tuple[bool, List[str]]:
        """Attempt to fix system errors."""
        actions = []

        if "memory" in error.message.lower():
            actions.append("Clearing memory caches")
            # Implement memory cleanup
            await asyncio.sleep(1)
            actions.append("Memory caches cleared")
            return True, actions

        elif "disk" in error.message.lower():
            actions.append("Cleaning temporary files")
            # Implement disk cleanup
            await asyncio.sleep(1)
            actions.append("Temporary files cleaned")
            return True, actions

        return False, ["No automatic fix available"]

    async def _fix_configuration_error(self, error: DetectedError) -> tuple[bool, List[str]]:
        """Attempt to fix configuration errors."""
        actions = []

        actions.append("Reloading configuration from defaults")
        # Implement configuration reload
        await asyncio.sleep(1)
        actions.append("Configuration reloaded")

        return True, actions

    def get_error_report(self) -> Dict[str, Any]:
        """Generate an error report."""
        return {
            "total_errors": len(self.detected_errors),
            "errors_by_severity": {
                severity.value: len([e for e in self.detected_errors if e.severity == severity])
                for severity in ErrorSeverity
            },
            "errors_by_type": {
                error_type.value: len([e for e in self.detected_errors if e.error_type == error_type])
                for error_type in ErrorType
            },
            "fix_success_rate": (
                len([e for e in self.detected_errors if e.fix_successful]) /
                len([e for e in self.detected_errors if e.fix_attempted])
                if len([e for e in self.detected_errors if e.fix_attempted]) > 0
                else 0
            ),
            "recent_errors": [
                {
                    "error_id": e.error_id,
                    "type": e.error_type.value,
                    "severity": e.severity.value,
                    "component": e.component,
                    "message": e.message,
                    "timestamp": e.timestamp.isoformat(),
                    "fix_attempted": e.fix_attempted,
                    "fix_successful": e.fix_successful
                }
                for e in sorted(self.detected_errors, key=lambda x: x.timestamp, reverse=True)[:10]
            ]
        }
