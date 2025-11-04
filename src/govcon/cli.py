"""Command-line interface for GovCon AI Pipeline."""

import asyncio

import click
from rich.console import Console
from rich.table import Table

from govcon.agents.orchestrator import WorkflowOrchestrator
from govcon.utils.config import get_settings
from govcon.utils.database import create_tables, drop_tables
from govcon.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()
console = Console()


@click.group()
def main() -> None:
    """GovCon AI Pipeline - Multi-agent system for federal proposals."""
    pass


@main.command()
def init_db() -> None:
    """Initialize database tables."""
    console.print("[bold blue]Initializing database...[/bold blue]")

    try:
        create_tables()
        console.print("[bold green]✓ Database tables created successfully[/bold green]")
    except Exception as e:
        console.print(f"[bold red]✗ Error: {e}[/bold red]")
        raise click.Abort() from e


@main.command()
@click.option("--confirm", is_flag=True, help="Confirm database reset")
def reset_db(confirm: bool) -> None:
    """Reset database (WARNING: destroys all data)."""
    if not confirm:
        console.print("[bold yellow]WARNING: This will delete all data![/bold yellow]")
        if not click.confirm("Are you sure you want to continue?"):
            console.print("Aborted.")
            return

    console.print("[bold red]Resetting database...[/bold red]")

    try:
        drop_tables()
        create_tables()
        console.print("[bold green]✓ Database reset successfully[/bold green]")
    except Exception as e:
        console.print(f"[bold red]✗ Error: {e}[/bold red]")
        raise click.Abort() from e


@main.command()
@click.option("--days-back", default=7, help="Number of days to search back")
def discover(days_back: int) -> None:
    """Run discovery to find federal opportunities."""
    console.print(f"[bold blue]Running discovery for last {days_back} days...[/bold blue]")

    orchestrator = WorkflowOrchestrator()

    async def run() -> None:
        result = await orchestrator.run_discovery(days_back=days_back)

        # Display results in table
        table = Table(title="Discovery Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Opportunities Found", str(result["opportunities_found"]))
        table.add_row("Opportunities Ingested", str(result["opportunities_ingested"]))
        table.add_row("Shapeable Opportunities", str(result["opportunities_shapeable"]))
        table.add_row("Execution Time", f"{result['execution_time']:.2f}s")

        console.print(table)

    asyncio.run(run())


@main.command()
@click.argument("opportunity_id")
def analyze_opportunity(opportunity_id: str) -> None:
    """Run bid/no-bid analysis on an opportunity."""
    console.print(f"[bold blue]Analyzing opportunity: {opportunity_id}[/bold blue]")

    from datetime import datetime

    from govcon.agents.bid_nobid import BidNoBidAgent
    from govcon.models import Opportunity, SetAsideType

    async def run() -> None:
        agent = BidNoBidAgent()

        # Mock opportunity - in production, load from database
        opportunity = Opportunity(
            id=opportunity_id,
            solicitation_number="TEST-001",
            title="Test Opportunity",
            agency="VA",
            posted_date=datetime.utcnow(),
            naics_match=0.9,
            psc_match=0.8,
            set_aside=SetAsideType.SDVOSB,
        )

        score = await agent.score(opportunity)

        # Display results
        table = Table(title="Bid/No-Bid Analysis")
        table.add_column("Criteria", style="cyan")
        table.add_column("Score", style="green")

        table.add_row("Set-Aside Eligibility", f"{score.set_aside_score:.2f}")
        table.add_row("Scope Alignment", f"{score.scope_score:.2f}")
        table.add_row("Timeline Feasibility", f"{score.timeline_score:.2f}")
        table.add_row("Competition & Vehicle", f"{score.competition_score:.2f}")
        table.add_row("Staffing Realism", f"{score.staffing_score:.2f}")
        table.add_row("Pricing Realism", f"{score.pricing_score:.2f}")
        table.add_row("Strategic Fit", f"{score.strategic_score:.2f}")
        table.add_row("", "")  # Separator
        table.add_row("[bold]TOTAL SCORE[/bold]", f"[bold]{score.total_score:.2f}[/bold]")
        table.add_row("[bold]RECOMMENDATION[/bold]", f"[bold]{score.recommendation}[/bold]")

        console.print(table)
        console.print(f"\n[italic]{score.rationale}[/italic]")

    asyncio.run(run())


@main.command()
@click.argument("opportunity_id")
@click.option("--auto-approve", is_flag=True, help="Auto-approve gates (testing only)")
def generate_proposal(opportunity_id: str, auto_approve: bool) -> None:
    """Generate complete proposal for an opportunity."""
    console.print(f"[bold blue]Generating proposal for: {opportunity_id}[/bold blue]")

    orchestrator = WorkflowOrchestrator()

    async def run() -> None:
        with console.status("[bold green]Executing workflow...[/bold green]"):
            result = await orchestrator.execute_full_workflow(
                opportunity_id=opportunity_id, auto_approve=auto_approve
            )

        if result.success:
            console.print("[bold green]✓ Proposal generated successfully![/bold green]")

            table = Table(title="Workflow Execution")
            table.add_column("Stage", style="cyan")
            table.add_column("Status", style="green")

            for stage in result.stages_completed:
                table.add_row(stage.value, "✓ Completed")

            console.print(table)
            console.print(f"\nExecution time: {result.execution_time:.2f}s")
        else:
            console.print("[bold red]✗ Workflow failed![/bold red]")
            for error in result.errors:
                console.print(f"[red]  • {error}[/red]")

    asyncio.run(run())


@main.command()
@click.argument("opportunity_id")
def price_proposal(opportunity_id: str) -> None:
    """Generate pricing for a proposal."""
    console.print(f"[bold blue]Generating pricing for: {opportunity_id}[/bold blue]")

    from govcon.agents.pricing import PricingAgent

    async def run() -> None:
        agent = PricingAgent()

        labor_categories = ["Senior Cybersecurity Analyst", "Software Engineer", "Project Manager"]
        estimated_hours = {
            "Senior Cybersecurity Analyst": 2000.0,
            "Software Engineer": 1500.0,
            "Project Manager": 500.0,
        }

        with console.status("[bold green]Generating pricing...[/bold green]"):
            result = await agent.generate_pricing(
                labor_categories=labor_categories, estimated_hours=estimated_hours
            )

        table = Table(title="Pricing Summary")
        table.add_column("Category", style="cyan")
        table.add_column("Rate", style="green")

        for lcat in result.labor_categories:
            table.add_row(lcat.lcat_name, f"${lcat.fully_burdened_rate:.2f}/hr")

        table.add_row("", "")  # Separator
        table.add_row("[bold]TOTAL COST[/bold]", f"[bold]${result.total_cost:,.2f}[/bold]")

        console.print(table)

    asyncio.run(run())


@main.command()
@click.argument("opportunity_id")
def export_submission(opportunity_id: str) -> None:
    """Export submission package for an opportunity."""
    console.print(f"[bold blue]Exporting submission package for: {opportunity_id}[/bold blue]")
    console.print("[yellow]This feature is not yet implemented.[/yellow]")
    # TODO: Implement submission package export


@main.command()
@click.option("--email", default="admin@bronzeshield.com", help="User email")
@click.option("--password", default="admin123", help="User password")
@click.option("--full-name", default="Admin User", help="Full name")
@click.option("--role", default="admin", help="User role (admin, capture_manager, proposal_writer, pricer, reviewer, viewer, sdvosb_officer)")
def create_user(email: str, password: str, full_name: str, role: str) -> None:
    """Create a new user account."""
    console.print(f"[bold blue]Creating user: {email}[/bold blue]")

    from sqlalchemy import select

    from govcon.models import Role, User
    from govcon.utils.database import get_async_db
    from govcon.utils.security import hash_password

    # Map role string to enum
    role_map = {
        "admin": Role.ADMIN,
        "capture_manager": Role.CAPTURE_MANAGER,
        "proposal_writer": Role.PROPOSAL_WRITER,
        "pricer": Role.PRICER,
        "reviewer": Role.REVIEWER,
        "viewer": Role.VIEWER,
        "sdvosb_officer": Role.SDVOSB_OFFICER,
    }

    user_role = role_map.get(role.lower(), Role.VIEWER)

    async def run() -> None:
        async with get_async_db() as db:
            # Check if user already exists
            query = select(User).where(User.email == email, User.is_deleted.is_(False))
            result = await db.execute(query)
            existing_user = result.scalar_one_or_none()

            if existing_user:
                console.print(f"[yellow]⚠ User {email} already exists![/yellow]")
                console.print(f"[green]✓ You can login with:[/green]")
                console.print(f"  Email: {email}")
                console.print(f"  Password: {password}")
                return

            # Create user
            user = User(
                email=email,
                full_name=full_name,
                hashed_password=hash_password(password),
                role=user_role,
                is_active=True,
                is_superuser=(user_role == Role.ADMIN),
            )

            db.add(user)
            await db.commit()

            console.print("[bold green]✓ User created successfully![/bold green]")
            console.print(f"  Email: {email}")
            console.print(f"  Password: {password}")
            console.print(f"  Role: {user_role.value}")
            console.print("\n[green]You can now login to the frontend with these credentials.[/green]")

    asyncio.run(run())


@main.command()
def info() -> None:
    """Display system information."""
    table = Table(title="GovCon AI Pipeline - System Information")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Company Name", settings.company_name)
    table.add_row("UEI", settings.company_uei)
    table.add_row("CAGE", settings.company_cage)
    table.add_row("Designations", ", ".join(settings.set_aside_prefs))
    table.add_row("NAICS Codes", ", ".join(settings.allowed_naics))
    table.add_row("PSC Codes", ", ".join(settings.allowed_psc))
    table.add_row("Target Agencies", ", ".join(settings.target_agencies))
    table.add_row("LLM Provider", settings.default_llm_provider)
    table.add_row(
        "Database", settings.postgres_url.split("@")[1] if "@" in settings.postgres_url else "N/A"
    )

    console.print(table)


@main.command()
@click.option("--days-back", default=7, help="Days back to search")
def scan_early_signals(days_back: int) -> None:
    """Scan for early opportunity signals (Sources Sought, RFIs, etc.)."""
    console.print(f"[bold blue]Scanning for early signals (last {days_back} days)...[/bold blue]")

    from govcon.services.early_discovery import early_discovery_service

    async def run() -> None:
        # Scan Sources Sought
        console.print("\n[cyan]→ Scanning SAM.gov for Sources Sought notices...[/cyan]")
        signals = await early_discovery_service.scan_sources_sought(days_back=days_back)
        console.print(f"  Found {len(signals)} new signals")

        # Scan Industry Days
        console.print("\n[cyan]→ Scanning for Industry Day events...[/cyan]")
        events = await early_discovery_service.scan_industry_days(days_ahead=90)
        console.print(f"  Found {len(events)} upcoming events")

        # Display results
        if signals:
            table = Table(title="New Early Signals")
            table.add_column("Type", style="cyan")
            table.add_column("Title", style="green", width=50)
            table.add_column("Agency", style="yellow")
            table.add_column("Score", justify="right")

            for signal in signals[:10]:  # Show top 10
                table.add_row(
                    signal.signal_type,
                    signal.title[:47] + "..." if len(signal.title) > 50 else signal.title,
                    signal.agency,
                    f"{signal.relevance_score:.1f}" if signal.relevance_score else "N/A",
                )

            console.print("\n", table)
        else:
            console.print("\n[yellow]No new signals found[/yellow]")

        await early_discovery_service.aclose()

    asyncio.run(run())


@main.command()
@click.option("--months-ahead", default=12, help="Months ahead to look for expiring contracts")
def scan_expiring_contracts(months_ahead: int) -> None:
    """Find expiring contracts (re-compete opportunities)."""
    console.print(
        f"[bold blue]Scanning for contracts expiring in next {months_ahead} months...[/bold blue]"
    )

    from govcon.services.early_discovery import early_discovery_service

    async def run() -> None:
        signals = await early_discovery_service.scan_expiring_contracts(months_ahead=months_ahead)

        if signals:
            table = Table(title="Expiring Contracts (Re-compete Opportunities)")
            table.add_column("Title", style="green", width=50)
            table.add_column("Agency", style="yellow")
            table.add_column("Value", justify="right")
            table.add_column("Expected RFP", style="cyan")

            for signal in signals[:10]:
                table.add_row(
                    signal.title[:47] + "..." if len(signal.title) > 50 else signal.title,
                    signal.agency,
                    f"${signal.estimated_value:,.0f}" if signal.estimated_value else "N/A",
                    (
                        signal.expected_rfp_date.strftime("%Y-%m-%d")
                        if signal.expected_rfp_date
                        else "Unknown"
                    ),
                )

            console.print("\n", table)
            console.print(
                f"\n[green]✓ Found {len(signals)} re-compete opportunities[/green]"
            )
        else:
            console.print("\n[yellow]No expiring contracts found[/yellow]")

        await early_discovery_service.aclose()

    asyncio.run(run())


@main.command()
@click.argument("file_path")
@click.argument("title")
@click.option("--category", help="Document category (auto-detected if not provided)")
@click.option("--agency", help="Related agency")
@click.option("--keywords", help="Comma-separated keywords")
def upload_knowledge(
    file_path: str, title: str, category: str | None, agency: str | None, keywords: str | None
) -> None:
    """Upload a document to the knowledge base."""
    console.print(f"[bold blue]Uploading document to knowledge base...[/bold blue]")

    from govcon.services.knowledge import knowledge_service

    try:
        doc = knowledge_service.upload_document(
            file_path=file_path, title=title, category=category, agency=agency, keywords=keywords
        )

        console.print(f"\n[green]✓ Successfully uploaded document[/green]")
        console.print(f"  ID: {doc.id}")
        console.print(f"  Title: {doc.title}")
        console.print(f"  Category: {doc.category}")
        console.print(f"  Chunks: {doc.chunk_count}")
        console.print(f"  Collection: {doc.vector_collection}")

    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise click.Abort()


@main.command()
@click.argument("query")
@click.option("--category", help="Filter by category")
@click.option("--limit", default=5, help="Maximum results")
def search_knowledge(query: str, category: str | None, limit: int) -> None:
    """Search the knowledge base."""
    console.print(f'[bold blue]Searching knowledge base for: "{query}"[/bold blue]')

    from govcon.services.knowledge import knowledge_service

    results = knowledge_service.search_knowledge(query=query, category=category, limit=limit)

    if results:
        for idx, result in enumerate(results, 1):
            console.print(f"\n[cyan]Result {idx} (score: {result['score']:.2f})[/cyan]")
            console.print(f"[yellow]From: {result['metadata'].get('title', 'Unknown')}[/yellow]")
            console.print(f"Category: {result['metadata'].get('category', 'Unknown')}")
            console.print(f"\n{result['text'][:300]}...")
            console.print("[dim]" + "─" * 80 + "[/dim]")

        console.print(f"\n[green]✓ Found {len(results)} results[/green]")
    else:
        console.print("\n[yellow]No results found[/yellow]")


if __name__ == "__main__":
    main()
