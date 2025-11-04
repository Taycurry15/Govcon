"""FastAPI main application."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from govcon.api.routes import opportunities, proposals, users, workflow, agents, system, websocket, monitoring
from govcon.utils.config import get_settings
from govcon.utils.database import create_tables
from govcon.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    # Startup
    logger.info("Starting GovCon AI Pipeline API for app '%s'", app.title)

    # Create database tables
    try:
        create_tables()
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

    yield

    # Shutdown
    logger.info("Shutting down GovCon AI Pipeline API")


# Create FastAPI app
app = FastAPI(
    title="GovCon AI Pipeline",
    description="Multi-agent system for federal government contracting proposals (SDVOSB/VOSB/SB)",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(opportunities.router, prefix="/api/opportunities", tags=["Opportunities"])
app.include_router(proposals.router, prefix="/api/proposals", tags=["Proposals"])
app.include_router(workflow.router, prefix="/api/workflow", tags=["Workflow"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(agents.router, prefix="/api", tags=["Agents"])
app.include_router(system.router, prefix="/api", tags=["System"])
app.include_router(monitoring.router, prefix="/api", tags=["Monitoring"])
app.include_router(websocket.router, tags=["WebSocket"])


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": "GovCon AI Pipeline",
        "version": "1.0.0",
        "status": "operational",
        "company": settings.company_name,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/info")
async def info() -> dict[str, Any]:
    """API information endpoint."""
    return {
        "name": "GovCon AI Pipeline",
        "version": "1.0.0",
        "company": settings.company_name,
        "designations": settings.set_aside_prefs,
        "capabilities": [
            "IT Consulting & Services",
            "Information Security",
            "Data Management",
            "Translation/Interpretation/ASL",
            "Transcription Services",
        ],
        "agents": [
            "Discovery Agent",
            "Bid/No-Bid Agent",
            "Solicitation Review Agent",
            "Proposal Generation Agent",
            "Pricing & BOE Agent",
            "Communications Agent",
        ],
    }
