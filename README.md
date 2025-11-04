# GovCon AI Pipeline - SDVOSB/VOSB/SB Edition

A production-ready multi-agent system for federal government contracting proposal development, built with the OpenAI Agents SDK.

## Overview

The GovCon AI Pipeline automates the entire federal proposal lifecycle for **The Bronze Shield** (SDVOSB | VOSB | Small Business), from opportunity discovery through submission:

1. **Discovery Agent** - Finds opportunities on SAM.gov, FedConnect, GSA eBuy filtered by NAICS/PSC and set-aside status
2. **Bid/No-Bid Agent** - Scores opportunities with SDVOSB/VOSB/SB preference weighting
3. **Solicitation Review Agent** - Parses RFPs, builds compliance matrices and requirements traceability matrices (RTM)
4. **Proposal Generation Agent** - Drafts all proposal volumes with evidence-based content
5. **Pricing & BOE Agent** - Generates market-rate pricing using BLS/OES, Wage Determinations, GSA CALC
6. **Q&A & Communications Agent** - Drafts vendor questions, emails, and Sources Sought responses
7. **Audit & Security Layer** - RBAC, audit logging, CMMC/NIST 800-171 alignment

## Company Profile

**The Bronze Shield**
- **Designations:** SDVOSB, VOSB, Small Business
- **Core Capabilities:** IT Consulting, Information Security, Data Management, Translation/Interpretation/ASL, Transcription
- **Target Agencies:** VA, DoD, DHS, HHS, DOJ, USDA

### Core NAICS Codes
- 541512 - Computer Systems Design Services
- 541511 - Custom Computer Programming Services
- 541519 - Other Computer Related Services
- 541513 - Computer Facilities Management Services
- 541690 - Scientific & Technical Consulting (InfoSec)
- 541611 - Admin/General Management Consulting
- 541930 - Translation & Interpretation Services (incl. ASL)
- 561410 - Document Preparation/Transcription Services
- 518210 - Computing Infrastructure Providers
- 541990 - All Other Professional/Scientific/Technical Services

### Key PSC/FSC Codes
- D301-D399 - IT & Telecom Services
- R408, R410, R413, R420, R499, R699 - Professional/Program Management
- R608 - Translation & Interpreting Services
- U012, U099 - Training Services

## Quick Start

### Prerequisites
- Python 3.9+
- Docker & Docker Compose
- OpenAI API Key or Anthropic API Key

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd govcon-ai-pipeline
```

2. Install dependencies:
```bash
# Using uv (recommended)
uv sync

# Or using pip
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

4. Start infrastructure services:
```bash
docker-compose up -d
```

5. Initialize database:
```bash
uv run python -m govcon.cli init-db
```

6. Run the discovery agent:
```bash
uv run python -m govcon.cli discover --days-back 7
```

## Web Interface

The system includes a modern React-based web interface for easy operation:

### Starting the Web UI

```bash
# Start the full stack (backend + frontend + infrastructure)
docker-compose up -d

# Access the web interface at http://localhost
```

### Features

- **Dashboard** - Overview of opportunities, proposals, and key metrics
- **Opportunities** - Browse and filter federal opportunities with detailed views
- **Proposals** - Track proposal development with progress monitoring
- **Workflow Execution** - Run discovery and proposal workflows with real-time updates
- **Settings** - Configure API keys, company profile, and notifications

For frontend development setup, see [frontend/README.md](frontend/README.md)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Discovery Agent                          │
│  SAM.gov | FedConnect | GSA eBuy | Beta.SAM.gov             │
│  Filters: NAICS, PSC, Set-Aside (SDVOSB→VOSB→SB)           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Bid/No-Bid Agent                            │
│  Scoring: Set-Aside (25%) | Scope (25%) | Timeline (15%)   │
│  Competition (10%) | Staffing (10%) | Pricing (10%)        │
│  Strategic Fit (5%)                                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ [Pink Team Approval]
                     │
┌─────────────────────────────────────────────────────────────┐
│              Solicitation Review Agent                       │
│  Parse: Sections C/L/M, PWS/SOW, Amendments                │
│  Generate: Compliance Matrix, RTM                           │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
┌──────────────────┐    ┌──────────────────────┐
│  Proposal Agent  │    │   Pricing Agent      │
│  Admin/Tech/PP   │    │   BOE | Rate Cards   │
│  Volumes         │    │   Market Rates       │
└─────────┬────────┘    └──────────┬───────────┘
          │                        │
          └────────┬───────────────┘
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                    Q&A & Comms Agent                         │
│  Draft: Questions, Emails, Cover Letters, NDAs              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ [Gold Team Review]
                     │
┌─────────────────────────────────────────────────────────────┐
│                  Submission Package                          │
│  All volumes | Forms | Reps & Certs | Upload ready          │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Backend
- **Agents Framework:** OpenAI Agents SDK
- **LLMs:** OpenAI GPT-4, Claude 3.5 Sonnet (via Anthropic), Ollama (local)
- **API:** FastAPI with OpenAPI docs
- **Database:** PostgreSQL 16
- **Cache:** Redis 7
- **Vector Store:** Qdrant
- **Object Storage:** MinIO (S3-compatible)
- **Security:** JWT authentication, RBAC, audit logging, encryption at rest

### Frontend
- **Framework:** React 18 + TypeScript
- **Build:** Vite
- **Styling:** TailwindCSS
- **State:** Zustand + React Query
- **Routing:** React Router v6

### Infrastructure
- **Orchestration:** Docker Compose
- **Web Server:** Nginx (production)
- **Deployment:** Multi-stage Docker builds

## Project Structure

```
govcon-ai-pipeline/
├── src/govcon/
│   ├── agents/          # Multi-agent implementations
│   │   ├── discovery.py
│   │   ├── bid_nobid.py
│   │   ├── solicitation_review.py
│   │   ├── proposal_generation.py
│   │   ├── pricing.py
│   │   └── communications.py
│   ├── models/          # Database models
│   │   ├── opportunity.py
│   │   ├── proposal.py
│   │   └── audit.py
│   ├── services/        # External integrations
│   │   ├── sam_gov.py
│   │   ├── bls_oes.py
│   │   └── gsa_calc.py
│   ├── utils/           # Helpers
│   │   ├── naics.py
│   │   ├── psc.py
│   │   └── security.py
│   └── api/             # REST API
│       └── routes.py
├── tests/               # Test suite
├── docs/                # Documentation
├── examples/            # Usage examples
├── config/              # Configuration templates
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

## Key Features

### 1. Set-Aside Awareness
- Prioritizes SDVOSB → VOSB → SB opportunities
- VA procurement triggers Vets First logic
- Validates SAM registration and certifications

### 2. Intelligent Discovery
- Filters by NAICS/PSC codes
- Keyword targeting: Zero Trust, ICAM, RMF, CMMC, cybersecurity, translation, ASL
- Flags Sources Sought/RFI as shapeable opportunities

### 3. Evidence-Based Proposals
- Citations to source chunks
- Compliance matrices with requirement mapping
- RTM (Requirement → Section → Verification)

### 4. Market-Rate Pricing
- BLS/OES data integration
- SCA/Wage Determination compliance
- GSA CALC benchmarking
- Auditable BOE with data sources and dates

### 5. Security & Compliance
- RBAC with sdvosb_officer role
- Audit trail for all tool calls
- CMMC/NIST 800-171 alignment
- Encryption at rest and in transit

## Configuration

### Environment Variables

See [.env.example](.env.example) for all configuration options:

```bash
# Database
POSTGRES_URL=postgresql://bronze:password@postgres:5432/govcon

# Cache & Vector Store
REDIS_URL=redis://redis:6379/0
QDRANT_URL=http://qdrant:6333

# Object Storage
MINIO_ENDPOINT=minio:9000
MINIO_BUCKET=govcon-artifacts

# AI Models
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_HOST=http://ollama:11434

# Company Config
ALLOWED_NAICS=541512,541511,541519,541513,541690,541611,541930,561410,518210,541990
ALLOWED_PSC=D301,D302,D307,D308,D310,D314,D316,D318,D399,R408,R410,R413,R420,R499,R699,R608,U012,U099
SET_ASIDE_PREFS=SDVOSB,VOSB,SB

# Security
AUTH_ISSUER=https://accounts.example.com/
AUTH_AUDIENCE=govcon-api
JWT_SIGNING_KEY=change_me
```

## Usage

### Command Line Interface

```bash
# Discover opportunities
uv run python -m govcon.cli discover --days-back 7 --set-aside SDVOSB

# Run bid/no-bid analysis
uv run python -m govcon.cli analyze-opportunity <opportunity-id>

# Generate proposal
uv run python -m govcon.cli generate-proposal <opportunity-id>

# Generate pricing
uv run python -m govcon.cli price-proposal <opportunity-id>

# Export submission package
uv run python -m govcon.cli export-submission <opportunity-id>
```

### Python API

```python
from govcon.agents import DiscoveryAgent, BidNoBidAgent
from govcon.models import Opportunity

# Initialize agents
discovery = DiscoveryAgent()
bid_agent = BidNoBidAgent()

# Run discovery
opportunities = await discovery.discover(days_back=7)

# Score opportunity
for opp in opportunities:
    score = await bid_agent.score(opp)
    print(f"{opp.title}: {score.total_score:.2f} - {score.recommendation}")
```

## Workflow

1. **Discovery** → Ingest opportunities with `set_aside`, `naics_match`, `psc_match`, `shapeable` tags
2. **Auto-Screen** → Bid/No-Bid scoring with SDVOSB/VOSB/SB weighting
3. **Pink Team** → Human approval gate
4. **Compliance & RTM** → Build matrices; flag VetCert/SDVOSB evidence requirements
5. **Drafting** → Inject Bronze Shield SDVOSB narrative
6. **Pricing** → Workbook + BOE with auditable market rates
7. **Gold Team** → Finalize submission package
8. **Post-Submission** → Track evaluator notices and debrief

## Testing

```bash
# Run all tests
make tests

# Run specific test
uv run pytest -s -k test_discovery_agent

# Update snapshots
make snapshots-fix
```

## Documentation

Full documentation is available in the [docs](docs/) directory:

- [Architecture](docs/architecture.md)
- [Agent Guide](docs/agents.md)
- [API Reference](docs/api.md)
- [Deployment](docs/deployment.md)
- [Security](docs/security.md)

## Contributing

This is a private repository for The Bronze Shield. For internal contributors:

1. Create a feature branch
2. Make changes following the style guide
3. Run tests and linting: `make check`
4. Submit PR with description

## License

Proprietary - The Bronze Shield. All rights reserved.

## Support

For issues or questions:
- Internal: Contact the development team
- Documentation: See [docs](docs/)
- Issues: Use GitHub Issues for bug reports

---

**Built with OpenAI Agents SDK** | **SDVOSB Certified** | **Production Ready**
