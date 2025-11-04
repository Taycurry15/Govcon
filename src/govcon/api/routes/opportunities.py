"""Opportunities API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from govcon.models import Opportunity, OpportunityStatus, SetAsideType
from govcon.utils.database import get_db_session
from govcon.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class OpportunityResponse(BaseModel):
    """Opportunity response model."""

    id: str
    solicitation_number: str
    title: str
    agency: str
    set_aside: Optional[str]
    naics_code: Optional[str]
    status: str
    bid_score_total: Optional[float]
    bid_recommendation: Optional[str]
    response_deadline: Optional[str]

    class Config:
        from_attributes = True


@router.get("/", response_model=list[OpportunityResponse])
async def list_opportunities(
    status: Optional[OpportunityStatus] = None,
    set_aside: Optional[SetAsideType] = None,
    limit: int = Query(default=50, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
) -> list[Opportunity]:
    """
    List opportunities with optional filters.

    Args:
        status: Filter by status
        set_aside: Filter by set-aside type
        limit: Maximum number of results
        offset: Pagination offset
        db: Database session

    Returns:
        List of opportunities
    """
    query = select(Opportunity).where(Opportunity.is_deleted.is_(False))

    if status:
        query = query.where(Opportunity.status == status)

    if set_aside:
        query = query.where(Opportunity.set_aside == set_aside)

    query = query.limit(limit).offset(offset).order_by(Opportunity.posted_date.desc())

    result = await db.execute(query)
    opportunities = result.scalars().all()

    logger.info(f"Retrieved {len(opportunities)} opportunities")
    return list(opportunities)


@router.get("/{opportunity_id}", response_model=OpportunityResponse)
async def get_opportunity(
    opportunity_id: str, db: AsyncSession = Depends(get_db_session)
) -> Opportunity:
    """
    Get a specific opportunity by ID.

    Args:
        opportunity_id: Opportunity ID
        db: Database session

    Returns:
        Opportunity details
    """
    opportunity = await db.get(Opportunity, opportunity_id)

    if not opportunity or opportunity.is_deleted:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    return opportunity


@router.delete("/{opportunity_id}")
async def delete_opportunity(
    opportunity_id: str, db: AsyncSession = Depends(get_db_session)
) -> dict[str, str]:
    """
    Soft delete an opportunity.

    Args:
        opportunity_id: Opportunity ID
        db: Database session

    Returns:
        Success message
    """
    opportunity = await db.get(Opportunity, opportunity_id)

    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    opportunity.soft_delete()
    await db.commit()

    logger.info(f"Opportunity {opportunity_id} deleted")
    return {"status": "success", "message": f"Opportunity {opportunity_id} deleted"}
