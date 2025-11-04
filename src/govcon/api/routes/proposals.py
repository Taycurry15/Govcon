"""Proposals API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from govcon.models import Proposal, ProposalStatus
from govcon.utils.database import get_db_session
from govcon.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class ProposalResponse(BaseModel):
    """Proposal response model."""

    id: str
    opportunity_id: str
    title: str
    version: str
    status: str
    vetcert_required: bool
    submitted_at: Optional[str]

    class Config:
        from_attributes = True


@router.get("/", response_model=list[ProposalResponse])
async def list_proposals(
    status: Optional[ProposalStatus] = None,
    opportunity_id: Optional[str] = None,
    limit: int = Query(default=50, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
) -> list[Proposal]:
    """
    List proposals with optional filters.

    Args:
        status: Filter by status
        opportunity_id: Filter by opportunity ID
        limit: Maximum number of results
        offset: Pagination offset
        db: Database session

    Returns:
        List of proposals
    """
    query = select(Proposal).where(Proposal.is_deleted.is_(False))

    if status:
        query = query.where(Proposal.status == status)

    if opportunity_id:
        query = query.where(Proposal.opportunity_id == opportunity_id)

    query = query.limit(limit).offset(offset).order_by(Proposal.created_at.desc())

    result = await db.execute(query)
    proposals = result.scalars().all()

    logger.info(f"Retrieved {len(proposals)} proposals")
    return list(proposals)


@router.get("/{proposal_id}", response_model=ProposalResponse)
async def get_proposal(proposal_id: str, db: AsyncSession = Depends(get_db_session)) -> Proposal:
    """
    Get a specific proposal by ID.

    Args:
        proposal_id: Proposal ID
        db: Database session

    Returns:
        Proposal details
    """
    proposal = await db.get(Proposal, proposal_id)

    if not proposal or proposal.is_deleted:
        raise HTTPException(status_code=404, detail="Proposal not found")

    return proposal
