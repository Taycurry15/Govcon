
# GovCon AI Pipeline - Architecture Documentation

## Overview

The GovCon AI Pipeline is a production-ready multi-agent system that automates the federal proposal lifecycle from opportunity discovery through submission. Agents run within the GovCon application layer and leverage a shared LLM service capable of targeting OpenAI (default), Anthropic, or self-hosted Ollama models on a per-agent basis.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      External Services                       │
│  SAM.gov | FedConnect | BLS API | GSA CALC | Email/Slack   │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                     API Layer (FastAPI)                      │
│  /opportunities | /proposals | /workflow | /users           │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                 Workflow Orchestrator                        │
│  Coordinates all agents through the proposal lifecycle       │
└───┬──────┬──────┬──────┬──────┬──────┬─────────────────────┘
    │      │      │      │      │      │
    ▼      ▼      ▼      ▼      ▼      ▼
┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐
│Disco-││Bid/  ││Solic-││Propo-││Pric- ││Comms │
│very  ││No-Bid││ita-  ││sal   ││ing   ││Agent │
│Agent ││Agent ││tion  ││Agent ││Agent ││      │
│      ││      ││Agent ││      ││      ││      │
└───┬──┘└───┬──┘└───┬──┘└───┬──┘└───┬──┘└───┬──┘
    │       │       │       │       │       │
┌───▼───────▼───────▼───────▼───────▼───────▼───┐
│              Shared Services                    │
│  Database | Cache | Vector Store | Object Store│
└─────────────────────────────────────────────────┘
```

## Core Components

### 1. Multi-Agent System

Agents are implemented as standard Python classes that share a common LLM abstraction. Each agent loads its instructions, resolves the provider/model to use (falling back to OpenAI unless overridden), and invokes the `LLMService` to produce tailored outputs.

#### Discovery Agent
- **Purpose**: Find and ingest federal opportunities
- **Data Sources**: SAM.gov, FedConnect, GSA eBuy
- **Key Features**:
  - NAICS/PSC code filtering
  - Set-aside prioritization (SDVOSB → VOSB → SB)
  - Sources Sought/RFI identification
  - Vector embeddings for semantic search

#### Bid/No-Bid Agent
- **Purpose**: Score opportunities for pursuit decision
- **Scoring Model** (weighted):
  - Set-Aside Eligibility: 25%
  - Scope Alignment: 25%
  - Timeline Feasibility: 15%
  - Competition & Vehicle: 10%
  - Staffing Realism: 10%
  - Pricing Realism: 10%
  - Strategic Fit: 5%
- **Special Logic**: VA/Vets First prioritization

#### Solicitation Review Agent
- **Purpose**: Parse RFPs and generate compliance artifacts
- **Outputs**:
  - Compliance Matrix
  - Requirements Traceability Matrix (RTM)
  - Submission requirements
  - Required certifications list

#### Proposal Generation Agent
- **Purpose**: Draft all proposal volumes
- **Volumes**: Administrative, Technical, Management, Past Performance
- **Key Features**:
  - Evidence-based content
  - Chunk citations for traceability
  - SDVOSB/VOSB narrative integration
  - Template-based generation

#### Pricing & BOE Agent
- **Purpose**: Generate market-rate pricing
- **Data Sources**:
  - BLS OES (Occupational Employment Statistics)
  - GSA CALC (Contract-Awarded Labor Categories)
  - SCA Wage Determinations
- **Features**:
  - LCAT → SOC mapping
  - Fully burdened rate calculation
  - Auditable BOE with data sources and dates

#### Communications Agent
- **Purpose**: Draft questions, emails, capability statements
- **Outputs**:
  - Vendor questions with precise citations
  - Cover letters
  - Submission emails
  - Teaming invitations
  - RFI/Sources Sought responses

### 2. Shared LLM Service

- Located in `src/govcon/services/llm.py`.
- Supports OpenAI, Anthropic, and Ollama providers with async chat semantics.
- Pulls default models and temperatures from `Settings` (`openai_model`, `anthropic_model`, `ollama_model`).
- Agent-specific overrides are available via environment-backed settings (e.g., `COMMUNICATIONS_AGENT_LLM_PROVIDER`).
- Exposes a `chat` method returning plain text; agents wrap this to request JSON or Markdown as needed.
- Maintains lightweight client caching and provides graceful error handling so agents can surface actionable messages when credentials are missing.

### 3. Workflow Orchestrator

Coordinates agents through the proposal lifecycle and now owns an explicit role description that guides LLM summarization for status reporting. The orchestrator logs stage progress and uses the shared LLM service to generate executive-ready summaries at the end of each run.

```
Discovery → Screening → Pink Team → Solicitation Review →
Proposal Drafting → Pricing → Gold Team → Submission
```

**Key Features**:
- Approval gates (Pink Team, Gold Team)
- Error handling and recovery
- Progress tracking
- Parallel execution where possible
- LLM-powered run summaries that highlight blockers, pending approvals, and recommended next steps.

### 4. Data Layer

#### Database (PostgreSQL)
- **Opportunities**: Full opportunity tracking
- **Proposals**: Multi-volume proposal management
- **Pricing**: Labor categories, rate cards, BOE
- **Audit Logs**: Compliance tracking
- **Users**: RBAC with roles

#### Cache (Redis)
- Session management
- API rate limiting
- Temporary data storage

#### Vector Store (Qdrant)
- Semantic search across solicitations
- Similarity matching for past performance
- Embedding storage for requirements

#### Object Store (MinIO)
- Document storage (PDFs, Word files)
- Proposal volumes
- Certification documents
- Submission packages

### 5. API Layer (FastAPI)

RESTful API with endpoints:

- `GET /api/opportunities` - List opportunities
- `POST /api/workflow/discover` - Run discovery
- `POST /api/workflow/execute` - Execute workflow
- `GET /api/proposals/{id}` - Get proposal
- `POST /api/users/token` - Authentication

**Features**:
- JWT authentication
- RBAC enforcement
- Rate limiting
- CORS support
- OpenAPI documentation

### 6. CLI Tool

Command-line interface for operations:

```bash
govcon discover --days-back 7
govcon analyze-opportunity <id>
govcon generate-proposal <id>
govcon price-proposal <id>
govcon export-submission <id>
```

## Data Flow

### Discovery Flow

```
1. User triggers discovery
2. Discovery Agent queries SAM.gov with filters
3. Opportunities normalized and stored in DB
4. Vector embeddings created in Qdrant
5. Documents stored in MinIO
6. Audit log created
```

### Proposal Generation Flow

```
1. User selects opportunity
2. Bid/No-Bid scoring (approval gate if required)
3. Solicitation Review parses document
4. Compliance Matrix and RTM generated
5. Proposal Agent drafts volumes
6. Pricing Agent generates workbook
7. Communications Agent drafts emails
8. Gold Team review (approval gate if required)
9. Submission package assembled
10. Audit trail completed
```

## Security Architecture

### Authentication & Authorization

- **JWT Tokens**: Secure API access
- **RBAC**: Role-based access control
  - Admin
  - Capture Manager
  - Proposal Writer
  - Pricer
  - Reviewer
  - SDVOSB Officer
  - Viewer

### Audit & Compliance

- **Audit Logging**: All actions tracked
- **Content Hashing**: SHA-256 for integrity
- **Encryption**: At rest and in transit
- **CMMC Alignment**: Level 2 ready
- **NIST 800-171**: Compliant architecture

### Data Protection

- **Encryption at Rest**: MinIO + PostgreSQL
- **Encryption in Transit**: TLS/SSL
- **Secrets Management**: Environment variables
- **Access Controls**: Database-level permissions

## Scalability

### Horizontal Scaling

- **API**: Multiple uvicorn workers
- **Agents**: Background task queues
- **Database**: Read replicas
- **Cache**: Redis cluster

### Performance Optimization

- **Caching**: Redis for frequent queries
- **Vector Search**: Qdrant for fast similarity search
- **Connection Pooling**: Database connection management
- **Async Operations**: Non-blocking I/O throughout

## Deployment Options

### Docker Compose (Development)

```bash
docker-compose up -d
```

### Kubernetes (Production)

- StatefulSet for database
- Deployment for API
- CronJob for discovery
- Secrets for credentials
- PersistentVolumes for data

### Cloud Platforms

- **AWS**: ECS, RDS, ElastiCache, S3
- **Azure**: Container Instances, PostgreSQL, Redis, Blob Storage
- **GCP**: Cloud Run, Cloud SQL, Memorystore, Cloud Storage

## Monitoring & Observability

### Logging

- Structured logging with structlog
- JSON format for parsing
- Log levels: DEBUG, INFO, WARNING, ERROR
- Centralized log aggregation (ELK, Datadog, etc.)

### Metrics

- API response times
- Agent execution times
- Database query performance
- Cache hit rates

### Tracing

- Built-in agent tracing
- OpenTelemetry compatible
- Integration with Logfire, AgentOps, Braintrust

### Health Checks

- `/health` endpoint
- Database connectivity
- External service status
- Disk space monitoring

## Configuration Management

### Environment Variables

All configuration via `.env` file:

- API keys
- Database URLs
- Company profile
- NAICS/PSC codes
- Scoring weights
- Feature flags

### Feature Flags

- `REQUIRE_PINK_TEAM_APPROVAL`
- `REQUIRE_GOLD_TEAM_APPROVAL`
- `AGENT_TRACING_ENABLED`
- `MOCK_SAM_GOV`

## Integration Points

### External APIs

1. **SAM.gov**: Opportunity discovery
2. **BLS API**: Labor rate data
3. **GSA CALC**: Contract pricing
4. **Email/SMTP**: Notifications
5. **Slack**: Alerts (optional)

### Future Integrations

- Document intelligence (Azure Form Recognizer)
- Translation services (for multilingual docs)
- E-signature (DocuSign)
- Contract management systems

## Design Decisions

### Why OpenAI Agents SDK?

- Built-in multi-agent orchestration
- Tool calling with function schemas
- Handoffs between agents
- Streaming support
- Extensible architecture

### Why PostgreSQL?

- ACID compliance for critical data
- JSON support for flexible schemas
- Proven reliability
- Rich ecosystem

### Why FastAPI?

- Async support
- Automatic OpenAPI docs
- Type safety with Pydantic
- High performance

### Why Multi-Agent vs Monolithic?

- **Separation of Concerns**: Each agent has clear responsibility
- **Parallel Execution**: Independent agents run concurrently
- **Testability**: Agents can be tested in isolation
- **Maintainability**: Easier to update individual agents
- **Scalability**: Scale specific agents based on load

## Future Enhancements

1. **Machine Learning**
   - Win/loss prediction
   - Pricing optimization
   - Requirement classification

2. **Advanced Automation**
   - Automated proposal assembly
   - Real-time collaboration
   - Version control integration

3. **Analytics**
   - Win rate dashboards
   - Pipeline metrics
   - Performance analytics

4. **Integrations**
   - CRM systems
   - Project management tools
   - Financial systems

---

For implementation details, see:
- [API Reference](API.md)
- [Agent Guide](AGENTS.md)
- [Deployment Guide](DEPLOYMENT.md)
