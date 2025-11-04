# Early Opportunity Discovery & Knowledge Base Guide

**Find federal opportunities 6-12 months BEFORE they hit SAM.gov RFPs**

This guide shows you how to use GovCon AI Pipeline's advanced features to discover opportunities early and build a knowledge base that enhances your proposals.

---

## Table of Contents

1. [Early Discovery Features](#early-discovery-features)
2. [Knowledge Base (RAG) System](#knowledge-base-rag-system)
3. [CLI Commands](#cli-commands)
4. [Usage Examples](#usage-examples)
5. [Integration Workflows](#integration-workflows)

---

## Early Discovery Features

### What's New

The GovCon AI Pipeline now scans for **pre-RFP signals** that give you 6-12 months of lead time:

| Signal Type | Lead Time | Description |
|------------|-----------|-------------|
| **Sources Sought** | 3-6 months | Agency market research before RFP |
| **RFI (Request for Information)** | 3-9 months | Agency refining requirements |
| **Pre-Solicitation Notices** | 1-3 months | Formal notice before RFP drops |
| **Industry Days** | 3-6 months | Vendor outreach events |
| **Expiring Contracts** | 6-12 months | Guaranteed re-compete opportunities |
| **Agency Forecasts** | 6-12 months | Planned acquisitions (future feature) |

### Why This Matters

**Traditional Approach (SAM.gov RFP only):**
- 30-45 days to respond
- 50+ competitors already watching
- No relationship with PM
- Generic proposal

**Early Discovery Approach:**
- 6+ months to shape the opportunity
- Meet the PM at Industry Day
- Influence requirements during Sources Sought
- Tailored solution when RFP drops
- **3-5x higher win rate**

---

## Knowledge Base (RAG) System

### Overview

Upload your past proposals, technical approaches, past performance descriptions, and win themes. The system uses **Retrieval-Augmented Generation (RAG)** to automatically incorporate relevant examples into new proposals.

### Supported Document Types

- **PDF** - Past proposals, capability statements
- **DOCX** - Technical approaches, past performance
- **TXT/MD** - Boilerplate, win themes, templates

### Document Categories (Auto-detected)

| Category | Use Case | Examples |
|----------|----------|----------|
| `past_performance` | CPARS, project descriptions | "Managed $2M VA cybersecurity contract..." |
| `technical_approach` | Solution architectures | "Our Zero Trust implementation uses..." |
| `management_approach` | Staffing, org charts | "Our agile PMO structure ensures..." |
| `past_proposal` | Full winning proposals | Complete submitted proposals |
| `proposal_template` | Reusable structures | Outline templates, response frameworks |
| `capability_statement` | Company capabilities | Capability statements, one-pagers |
| `boilerplate` | Standard text | Company history, certifications |
| `win_theme` | Differentiators | "Veteran leadership ensures..." |

### How RAG Works

1. **Upload**: Documents are chunked and embedded into vector database (Qdrant)
2. **Search**: When generating proposals, relevant chunks are retrieved
3. **Augment**: LLM uses examples to generate better, more specific content
4. **Generate**: Proposals include proven language from your wins

**Result:** Proposals that sound like YOUR company, not generic AI output.

---

## CLI Commands

### Early Discovery Commands

```bash
# Scan for Sources Sought notices (last 7 days)
python -m govcon.cli scan-early-signals

# Scan for Sources Sought (last 30 days)
python -m govcon.cli scan-early-signals --days-back 30

# Find expiring contracts (re-competes in next 12 months)
python -m govcon.cli scan-expiring-contracts

# Find expiring contracts (next 6 months)
python -m govcon.cli scan-expiring-contracts --months-ahead 6
```

### Knowledge Base Commands

```bash
# Upload a document (category auto-detected)
python -m govcon.cli upload-knowledge \
  "path/to/winning_proposal.pdf" \
  "VA Zero Trust Win - 2024"

# Upload with specific category
python -m govcon.cli upload-knowledge \
  "path/to/technical_approach.docx" \
  "Zero Trust Technical Approach" \
  --category technical_approach \
  --agency "Department of Veterans Affairs" \
  --keywords "zero trust, cybersecurity, RMF"

# Search knowledge base
python -m govcon.cli search-knowledge "zero trust implementation"

# Search specific category
python -m govcon.cli search-knowledge "project management" \
  --category management_approach \
  --limit 10
```

### Existing Commands (Still Available)

```bash
# Initialize database
python -m govcon.cli init-db

# Run discovery (SAM.gov RFPs)
python -m govcon.cli discover --days-back 7

# Generate proposal
python -m govcon.cli generate-proposal OPPORTUNITY_ID --auto-approve

# System info
python -m govcon.cli info
```

---

## Usage Examples

### Example 1: Early Signal Detection Workflow

**Scenario:** Find SDVOSB cybersecurity opportunities before RFP.

```bash
# Step 1: Scan for early signals
python -m govcon.cli scan-early-signals --days-back 30

# Output:
# ┌─────────────────────────────────────────────────────┐
# │ New Early Signals                                   │
# ├──────────┬─────────────────────┬────────────┬───────┤
# │ Type     │ Title               │ Agency     │ Score │
# ├──────────┼─────────────────────┼────────────┼───────┤
# │ sources_ │ Zero Trust Archit.. │ VA         │  92.5 │
# │ sought   │                     │            │       │
# ├──────────┼─────────────────────┼────────────┼───────┤
# │ rfi      │ Cyber Defense Too.. │ DoD        │  85.0 │
# └──────────┴─────────────────────┴────────────┴───────┘
```

**What to do next:**
1. **Respond to Sources Sought**: Show you're capable
2. **Call the PCO**: Introduce yourself as SDVOSB
3. **Register for Industry Day**: Meet the PM
4. **Track in CRM**: This RFP is coming in 3-6 months

### Example 2: Re-compete Strategy

```bash
# Find contracts expiring soon
python -m govcon.cli scan-expiring-contracts --months-ahead 12

# Output shows contracts ending in next 12 months
# These are GUARANTEED opportunities - just need to re-bid
```

**Strategy:**
1. **Identify incumbent** (from USASpending.gov)
2. **Contact for teaming**: "Interested in teaming as SDVOSB sub?"
3. **Or compete directly** if you can match their past performance

### Example 3: Building Your Knowledge Base

```bash
# Upload winning proposal from last year
python -m govcon.cli upload-knowledge \
  "proposals/2024/VA_Cybersecurity_WIN.pdf" \
  "VA Cybersecurity Win 2024" \
  --agency "Department of Veterans Affairs" \
  --keywords "zero trust, cybersecurity, RMF, ATO"

# Upload technical approach that scored well
python -m govcon.cli upload-knowledge \
  "technical/zero_trust_approach.docx" \
  "Zero Trust Technical Approach - High Scorer"  \
  --category technical_approach

# Upload past performance descriptions
python -m govcon.cli upload-knowledge \
  "past_performance/project_descriptions.txt" \
  "Past Performance Database"  \
  --category past_performance

# Upload company boilerplate
python -m govcon.cli upload-knowledge \
  "company/capability_statement.pdf" \
  "Company Capability Statement 2025"  \
  --category capability_statement
```

**After uploading 5-10 documents:**

When you generate proposals, the system will automatically:
- Pull relevant technical language from your wins
- Include actual project examples
- Use your proven win themes
- Match your company's writing style

### Example 4: Generate Proposal with Knowledge Base

```bash
# The knowledge base is automatically used
# No special flags needed - just generate as usual

python -m govcon.cli generate-proposal VA-2025-001 --auto-approve

# Behind the scenes:
# 1. ProposalGenerationAgent searches knowledge base
# 2. Finds relevant chunks from your uploaded docs
# 3. Includes them in prompts to LLM
# 4. Output includes your proven language
```

**Before RAG (Generic):**
> "We will implement a comprehensive Zero Trust architecture using industry best practices..."

**After RAG (Your Voice):**
> "We will implement a Zero Trust architecture following our proven methodology from the VA Medical Center contract (2023-2024), where we successfully deployed identity-centric controls across 15 facilities, achieving 99.8% uptime during implementation..."

---

## Integration Workflows

### Workflow 1: Weekly Early Signal Check

**Automate this as a cron job:**

```bash
#!/bin/bash
# weekly_scan.sh

cd /path/to/govcon-ai-pipeline
source .venv/bin/activate

# Scan for new signals
python -m govcon.cli scan-early-signals --days-back 7

# Scan for expiring contracts (monthly)
if [ $(date +%d) = "01" ]; then
    python -m govcon.cli scan-expiring-contracts --months-ahead 12
fi
```

**Set up cron:**
```bash
# Run every Monday at 8am
0 8 * * 1 /path/to/weekly_scan.sh >> /var/log/govcon_scan.log 2>&1
```

### Workflow 2: Continuous Knowledge Base Building

**After each win:**
1. Upload final proposal: `upload-knowledge proposals/win_2025_123.pdf "Win Title"`
2. Upload lessons learned doc
3. Update past performance with new project

**After each loss (debriefing):**
1. Upload your proposal: `upload-knowledge proposals/loss_2025_456.pdf "Loss Title"`
2. Add notes on evaluator feedback
3. Improve for next time

### Workflow 3: Full Opportunity Pipeline

```
Week 1: Early Signal Detected
  ↓
Week 2: Upload Relevant Knowledge Docs
  ↓
Week 4: Attend Industry Day, Meet PM
  ↓
Week 8: Submit Response to Sources Sought
  ↓
Week 16: RFP Released
  ↓
Week 17: Generate Proposal (with RAG)
  ↓
Week 20: Submit Winning Proposal
```

---

## Advanced Features

### Scoring Algorithm

Early signals are scored 0-100 based on:

- **NAICS Match** (30 points): Exact match with your codes
- **Set-Aside Match** (25 points): SDVOSB/VOSB alignment
- **Agency Alignment** (20 points): Target agencies (VA, DoD, etc.)
- **Signal Type** (15 points): Sources Sought > RFI > Other
- **Est. Value** (10 points): Sweet spot $100K-$10M for small business

**Signals 80+ are "hot leads" - prioritize these!**

### Knowledge Base Search

The RAG system automatically:
1. **Searches by semantic similarity** (not just keywords)
2. **Filters by category** (technical, management, etc.)
3. **Filters by agency** (if specified)
4. **Returns top 3 most relevant chunks**
5. **Includes them in LLM prompts**

---

## Configuration

### Required Environment Variables

```bash
# .env file

# SAM.gov API (for early signals)
SAM_API_KEY=your_sam_api_key_here

# OpenAI (for embeddings and generation)
OPENAI_API_KEY=your_openai_key

# Qdrant (vector database)
QDRANT_URL=http://localhost:6333
# QDRANT_API_KEY=optional_if_cloud

# PostgreSQL (metadata storage)
POSTGRES_URL=postgresql://user:pass@localhost:5432/govcon
```

### Get SAM.gov API Key (FREE)

1. Go to: https://open.gsa.gov/api/sam-api/
2. Click "Get API Key"
3. Register your email
4. Add to `.env` file

---

## Best Practices

### Early Discovery

✅ **DO:**
- Run `scan-early-signals` weekly
- Respond to ALL Sources Sought in your NAICS (even if not perfect match)
- Call the PCO listed on the notice
- Attend every Industry Day you can
- Track signals in a CRM or spreadsheet

❌ **DON'T:**
- Wait for the RFP - you're too late
- Ignore Sources Sought - they want to hear from you
- Skip networking events - relationships win contracts

### Knowledge Base

✅ **DO:**
- Upload 5-10 documents minimum for good results
- Include wins AND losses (learn from both)
- Tag documents with keywords and agencies
- Update regularly (quarterly at minimum)
- Include technical depth (not just marketing fluff)

❌ **DON'T:**
- Upload confidential client data (sanitize first)
- Upload only generic templates (need YOUR voice)
- Forget to organize by category
- Let it get stale (update with new wins)

---

## Troubleshooting

### "No signals found"

**Possible causes:**
- Your NAICS codes are too narrow (expand in config)
- SAM.gov API key not configured
- No recent Sources Sought in your domain

**Solutions:**
- Check `.env` has `SAM_API_KEY`
- Expand `allowed_naics` in config
- Increase `--days-back` to 30 or 60

### "Knowledge base not finding relevant docs"

**Possible causes:**
- Not enough documents uploaded (need 5+ minimum)
- Documents not in relevant categories
- Query too generic

**Solutions:**
- Upload more domain-specific documents
- Use more specific queries: "zero trust implementation" vs. "cybersecurity"
- Check documents uploaded correctly: `search-knowledge "test"`

### "RAG not improving proposals"

**Possible causes:**
- Knowledge base empty
- Documents too generic
- Wrong categories assigned

**Solutions:**
- Upload technical depth, not marketing fluff
- Include past performance project descriptions
- Verify categories: `search-knowledge --category technical_approach`

---

## Next Steps

1. **Set up API keys** in `.env`
2. **Run first early signal scan**: `scan-early-signals`
3. **Upload 3-5 documents** to knowledge base
4. **Test proposal generation** with RAG enabled
5. **Set up weekly automated scans**
6. **Build your pipeline**

---

## Support & Resources

- **Documentation**: Full docs at [internal link]
- **SAM.gov API Docs**: https://open.gsa.gov/api/opportunities-api/
- **USASpending API Docs**: https://api.usaspending.gov/docs/
- **Qdrant Docs**: https://qdrant.tech/documentation/

**Questions?** Open an issue on the GitHub repo.

---

**Built by:** The Bronze Shield
**For:** SDVOSB/VOSB Federal Contractors
**License:** Proprietary

**Win More. Work Smarter. Stay Ahead.**
