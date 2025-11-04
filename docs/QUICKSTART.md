# GovCon AI Pipeline - Quick Start Guide

This guide will help you get started with the GovCon AI Pipeline in minutes.

## Prerequisites

- Python 3.9 or higher
- Docker and Docker Compose
- OpenAI API key or Anthropic API key
- Git

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd govcon-ai-pipeline
```

### 2. Install Dependencies

Using uv (recommended):

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies
uv sync
```

Or using pip:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```env
# Required
OPENAI_API_KEY=sk-...  # Or ANTHROPIC_API_KEY

# Company Info (Important!)
COMPANY_UEI=your-uei-here
COMPANY_CAGE=your-cage-here
```

### 4. Start Infrastructure

```bash
docker-compose up -d
```

This starts:
- PostgreSQL (database)
- Redis (cache)
- Qdrant (vector store)
- MinIO (object storage)
- Ollama (optional local LLM)

### 5. Initialize Database

```bash
uv run python -m govcon.cli init-db
```

## Your First Discovery

Run discovery to find federal opportunities:

```bash
uv run python -m govcon.cli discover --days-back 7
```

This will:
1. Search SAM.gov for opportunities from the last 7 days
2. Filter by your NAICS/PSC codes
3. Prioritize SDVOSB/VOSB/SB set-asides
4. Store results in the database

## Analyze an Opportunity

Once you have opportunities, run bid/no-bid analysis:

```bash
uv run python -m govcon.cli analyze-opportunity <opportunity-id>
```

This scores the opportunity across 7 criteria and provides a BID/NO_BID/REVIEW recommendation.

## Generate a Proposal

To generate a complete proposal:

```bash
uv run python -m govcon.cli generate-proposal <opportunity-id>
```

This executes the full workflow:
1. Bid/No-Bid analysis
2. Solicitation review
3. Compliance matrix generation
4. Proposal drafting (all volumes)
5. Pricing & BOE
6. Submission packaging

## Using the API

Start the API server:

```bash
uv run uvicorn govcon.api.main:app --reload
```

API documentation is available at: http://localhost:8000/api/docs

### Example API Calls

**Run Discovery:**
```bash
curl -X POST http://localhost:8000/api/workflow/discover \
  -H "Content-Type: application/json" \
  -d '{"days_back": 7}'
```

**List Opportunities:**
```bash
curl http://localhost:8000/api/opportunities/
```

**Get Workflow Status:**
```bash
curl http://localhost:8000/api/workflow/status/<opportunity-id>
```

## Common Tasks

### View System Info

```bash
uv run python -m govcon.cli info
```

### Reset Database (Warning: Deletes All Data)

```bash
uv run python -m govcon.cli reset-db --confirm
```

### Run Tests

```bash
uv run pytest tests/
```

### View Logs

```bash
docker-compose logs -f
```

## Configuration Tips

### Using Anthropic Claude

Set in `.env`:

```env
DEFAULT_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

### Using Local Models (Ollama)

```bash
# Pull a model
docker-compose exec ollama ollama pull llama3.2

# Set in .env
DEFAULT_LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2
```

### Customizing Scoring Weights

Edit `.env`:

```env
SCORE_WEIGHT_SET_ASIDE=25
SCORE_WEIGHT_SCOPE=25
SCORE_WEIGHT_TIMELINE=15
SCORE_WEIGHT_COMPETITION=10
SCORE_WEIGHT_STAFFING=10
SCORE_WEIGHT_PRICING=10
SCORE_WEIGHT_STRATEGIC=5
```

## Troubleshooting

### Database Connection Error

```bash
# Check if PostgreSQL is running
docker-compose ps

# Restart services
docker-compose restart postgres
```

### API Key Issues

```bash
# Verify your API key is set
echo $OPENAI_API_KEY

# Or check .env file
cat .env | grep OPENAI_API_KEY
```

### Import Errors

```bash
# Make sure you're in the virtual environment
source .venv/bin/activate

# Reinstall in development mode
pip install -e .
```

## Next Steps

- Read [Architecture Documentation](./ARCHITECTURE.md)
- Review [Agent Guide](./AGENTS.md)
- Check [API Reference](./API.md)
- See [Deployment Guide](./DEPLOYMENT.md)

## Getting Help

- GitHub Issues: [Create an issue](https://github.com/your-org/govcon-ai-pipeline/issues)
- Documentation: [Full docs](./README.md)
- Examples: See `examples/` directory

---

**You're now ready to automate federal proposal development with AI!**
