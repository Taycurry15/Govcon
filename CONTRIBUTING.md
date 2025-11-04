# Contributing to GovCon AI Pipeline

Thank you for your interest in contributing to the GovCon AI Pipeline! This document provides guidelines for contributing to the project.

## Code of Conduct

This project is internal to The Bronze Shield. All contributors should maintain professional standards and focus on delivering value to our federal clients.

## Development Setup

1. **Clone and Install**

```bash
git clone <repository-url>
cd govcon-ai-pipeline
uv sync --all-extras
```

2. **Set Up Pre-commit Hooks**

```bash
pip install pre-commit
pre-commit install
```

3. **Run Tests**

```bash
make tests
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

### 2. Make Changes

- Write clean, documented code
- Follow existing patterns
- Add tests for new functionality
- Update documentation

### 3. Run Quality Checks

```bash
# Format code
make format

# Run linter
make lint

# Run type checker
make mypy

# Run tests
make tests

# Or run all at once
make check
```

### 4. Commit Changes

```bash
git add .
git commit -m "feat: add new discovery filter for agency targeting"
```

**Commit Message Format:**

- `feat: ` - New feature
- `fix: ` - Bug fix
- `docs: ` - Documentation changes
- `test: ` - Adding or updating tests
- `refactor: ` - Code refactoring
- `chore: ` - Maintenance tasks

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub with:
- Clear description of changes
- Link to related issues
- Screenshots/examples if applicable

## Code Style

### Python Style

We use:
- **Black** for code formatting
- **Ruff** for linting
- **MyPy** for type checking

### Type Hints

Always use type hints:

```python
def process_opportunity(opportunity_id: str, auto_approve: bool = False) -> WorkflowResult:
    """Process an opportunity through the workflow."""
    pass
```

### Docstrings

Use Google-style docstrings:

```python
def calculate_score(value: float, weight: float) -> float:
    """
    Calculate weighted score.

    Args:
        value: Raw score value (0-100)
        weight: Weight percentage (0-100)

    Returns:
        Weighted score

    Raises:
        ValueError: If value or weight out of range
    """
    pass
```

## Testing Guidelines

### Unit Tests

Test individual functions and methods:

```python
def test_opportunity_creation(db_session):
    """Test creating an opportunity."""
    opportunity = Opportunity(
        solicitation_number="TEST-001",
        title="Test",
        agency="VA",
        posted_date=datetime.utcnow(),
    )

    db_session.add(opportunity)
    db_session.commit()

    assert opportunity.id is not None
```

### Integration Tests

Test component interactions:

```python
@pytest.mark.asyncio
async def test_workflow_execution():
    """Test complete workflow execution."""
    orchestrator = WorkflowOrchestrator()
    result = await orchestrator.execute_full_workflow("test-opp-1")

    assert result.success is True
```

### Test Coverage

Maintain > 80% code coverage:

```bash
make coverage
```

## Adding New Agents

### 1. Create Agent File

```python
# src/govcon/agents/new_agent.py
from agents import Agent, function_tool

@function_tool
def new_tool(param: str) -> dict:
    """Tool description."""
    pass

new_agent = Agent(
    name="New Agent",
    model="gpt-4o",
    instructions="Agent instructions",
    tools=[new_tool],
)

class NewAgent:
    """New agent class."""

    def __init__(self):
        self.agent = new_agent

    async def run(self, input_data: dict) -> dict:
        """Run the agent."""
        pass
```

### 2. Add to __init__.py

```python
# src/govcon/agents/__init__.py
from govcon.agents.new_agent import NewAgent

__all__ = [..., "NewAgent"]
```

### 3. Add Tests

```python
# tests/test_new_agent.py
@pytest.mark.asyncio
async def test_new_agent():
    """Test new agent functionality."""
    agent = NewAgent()
    result = await agent.run({"test": "data"})
    assert result is not None
```

### 4. Update Documentation

- Add agent to README.md
- Create agent-specific docs
- Update ARCHITECTURE.md

## Adding New API Endpoints

### 1. Create Route

```python
# src/govcon/api/routes/new_routes.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/items")
async def list_items():
    """List items."""
    return {"items": []}
```

### 2. Register Router

```python
# src/govcon/api/main.py
from govcon.api.routes import new_routes

app.include_router(new_routes.router, prefix="/api/items", tags=["Items"])
```

### 3. Add Tests

```python
# tests/test_api.py
def test_list_items(client):
    """Test items endpoint."""
    response = client.get("/api/items")
    assert response.status_code == 200
```

## Database Changes

### 1. Update Models

```python
# src/govcon/models/new_model.py
class NewModel(Base, TimestampMixin):
    """New model."""

    __tablename__ = "new_table"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
```

### 2. Create Migration

```bash
uv run alembic revision --autogenerate -m "add new table"
```

### 3. Review and Edit Migration

```python
# alembic/versions/xxx_add_new_table.py
def upgrade():
    op.create_table(...)

def downgrade():
    op.drop_table(...)
```

### 4. Apply Migration

```bash
uv run alembic upgrade head
```

## Documentation

### Code Documentation

- All public functions need docstrings
- Complex logic needs inline comments
- Use type hints everywhere

### User Documentation

Update relevant docs in `docs/`:
- QUICKSTART.md - User guide
- ARCHITECTURE.md - Technical design
- API.md - API reference
- DEPLOYMENT.md - Deployment guide

## Performance Considerations

### Database Queries

- Use eager loading for relationships
- Add indexes for frequently queried fields
- Batch operations when possible

### Agent Operations

- Cache expensive operations
- Use async for I/O operations
- Implement timeout handling

### API Responses

- Paginate large result sets
- Use compression for responses
- Implement rate limiting

## Security Checklist

- [ ] No secrets in code
- [ ] Input validation
- [ ] SQL injection prevention
- [ ] XSS prevention
- [ ] CSRF protection
- [ ] Authentication required
- [ ] Authorization checked
- [ ] Audit logging added

## Review Process

### Before Submitting PR

1. All tests pass
2. Code formatted
3. Linter passes
4. Type checker passes
5. Documentation updated
6. Changelog updated (if applicable)

### PR Review

Reviews will check for:
- Code quality
- Test coverage
- Documentation
- Security implications
- Performance impact
- Breaking changes

## Getting Help

- GitHub Issues for bugs
- GitHub Discussions for questions
- Internal Slack for quick questions

## License

This is proprietary software for The Bronze Shield. All contributions become property of The Bronze Shield.

---

Thank you for contributing to GovCon AI Pipeline!
