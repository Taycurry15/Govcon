"""Audit logging utilities for compliance tracking."""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from govcon.models.audit import AuditAction, AuditLog
from govcon.models.user import User
from govcon.utils.logger import get_logger
from govcon.utils.security import hash_content

logger = get_logger(__name__)


async def create_audit_log(
    db: AsyncSession,
    action: AuditAction,
    user: Optional[User] = None,
    agent_name: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    action_description: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None,
    is_security_event: bool = False,
    is_compliance_event: bool = False,
) -> AuditLog:
    """
    Create an audit log entry.

    Args:
        db: Database session
        action: Action type
        user: User performing action (if human)
        agent_name: Agent performing action (if AI)
        resource_type: Type of resource affected
        resource_id: ID of resource affected
        details: Additional details dictionary
        action_description: Human-readable description
        ip_address: IP address of request
        user_agent: User agent string
        request_id: Request ID for tracing
        is_security_event: Flag for security events
        is_compliance_event: Flag for compliance events

    Returns:
        Created AuditLog entry
    """
    # Generate content hash for integrity
    content_to_hash = (
        f"{action.value}:{resource_type}:{resource_id}:{datetime.utcnow().isoformat()}"
    )
    content_hash = hash_content(content_to_hash)

    audit_log = AuditLog(
        timestamp=datetime.utcnow(),
        action=action,
        action_description=action_description,
        user_id=user.id if user else None,
        user_email=user.email if user else None,
        user_role=user.role.value if user else None,
        agent_name=agent_name,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
        is_security_event=is_security_event,
        is_compliance_event=is_compliance_event,
        content_hash=content_hash,
    )

    db.add(audit_log)
    await db.commit()

    logger.info(
        f"Audit log created: {action.value} by {user.email if user else agent_name} "
        f"on {resource_type}:{resource_id}"
    )

    return audit_log


class AuditLogger:
    """Helper class for audit logging."""

    def __init__(self, db: AsyncSession, user: Optional[User] = None) -> None:
        """
        Initialize audit logger.

        Args:
            db: Database session
            user: Current user (if applicable)
        """
        self.db = db
        self.user = user

    async def log_opportunity_discovered(self, opportunity_id: str, details: dict) -> None:
        """Log opportunity discovery."""
        await create_audit_log(
            db=self.db,
            action=AuditAction.OPPORTUNITY_DISCOVERED,
            agent_name="Discovery Agent",
            resource_type="opportunity",
            resource_id=opportunity_id,
            details=details,
            action_description=f"Opportunity {opportunity_id} discovered",
            is_compliance_event=True,
        )

    async def log_bid_decision(
        self, opportunity_id: str, decision: str, score: float, details: dict
    ) -> None:
        """Log bid/no-bid decision."""
        await create_audit_log(
            db=self.db,
            action=AuditAction.BID_DECISION_MADE,
            user=self.user,
            agent_name="Bid/No-Bid Agent",
            resource_type="opportunity",
            resource_id=opportunity_id,
            details={"decision": decision, "score": score, **details},
            action_description=f"Bid decision: {decision} (score: {score:.2f})",
            is_compliance_event=True,
        )

    async def log_approval(self, opportunity_id: str, approval_type: str, approved: bool) -> None:
        """Log pink/gold team approval."""
        action = (
            AuditAction.PINK_TEAM_APPROVED
            if approval_type == "pink"
            else AuditAction.GOLD_TEAM_APPROVED
        )
        if not approved:
            action = (
                AuditAction.PINK_TEAM_REJECTED
                if approval_type == "pink"
                else AuditAction.GOLD_TEAM_REJECTED
            )

        await create_audit_log(
            db=self.db,
            action=action,
            user=self.user,
            resource_type="opportunity",
            resource_id=opportunity_id,
            details={"approval_type": approval_type, "approved": approved},
            action_description=f"{approval_type.title()} team {'approved' if approved else 'rejected'}",
            is_compliance_event=True,
        )

    async def log_proposal_created(self, proposal_id: str, opportunity_id: str) -> None:
        """Log proposal creation."""
        await create_audit_log(
            db=self.db,
            action=AuditAction.PROPOSAL_CREATED,
            user=self.user,
            agent_name="Proposal Generation Agent",
            resource_type="proposal",
            resource_id=proposal_id,
            details={"opportunity_id": opportunity_id},
            action_description=f"Proposal {proposal_id} created",
            is_compliance_event=True,
        )

    async def log_proposal_submitted(self, proposal_id: str, submission_details: dict) -> None:
        """Log proposal submission."""
        await create_audit_log(
            db=self.db,
            action=AuditAction.PROPOSAL_SUBMITTED,
            user=self.user,
            resource_type="proposal",
            resource_id=proposal_id,
            details=submission_details,
            action_description=f"Proposal {proposal_id} submitted",
            is_compliance_event=True,
            is_security_event=True,
        )

    async def log_certification_access(self, certification_type: str, accessed_by: str) -> None:
        """Log access to certification documents."""
        await create_audit_log(
            db=self.db,
            action=AuditAction.CERTIFICATION_ACCESSED,
            user=self.user,
            resource_type="certification",
            resource_id=certification_type,
            details={"accessed_by": accessed_by},
            action_description=f"Certification {certification_type} accessed",
            is_security_event=True,
            is_compliance_event=True,
        )

    async def log_agent_tool_call(
        self, agent_name: str, tool_name: str, parameters: dict, result: Any
    ) -> None:
        """Log agent tool calls for traceability."""
        await create_audit_log(
            db=self.db,
            action=AuditAction.AGENT_TOOL_CALLED,
            agent_name=agent_name,
            details={
                "tool_name": tool_name,
                "parameters": parameters,
                "result_summary": str(result)[:500],  # Truncate large results
            },
            action_description=f"{agent_name} called {tool_name}",
        )

    async def log_security_event(
        self, event_type: str, details: dict, severity: str = "medium"
    ) -> None:
        """Log security events."""
        await create_audit_log(
            db=self.db,
            action=(
                AuditAction.PERMISSION_DENIED
                if event_type == "permission_denied"
                else AuditAction.OTHER
            ),
            user=self.user,
            details={"event_type": event_type, "severity": severity, **details},
            action_description=f"Security event: {event_type}",
            is_security_event=True,
        )
