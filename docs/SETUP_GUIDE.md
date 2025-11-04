# Setup Guide - GovCon AI Pipeline

Complete setup guide for the Apple-inspired full-stack application with autonomous monitoring.

---

## Prerequisites

- Python 3.9+
- Node.js 18+
- Docker & Docker Compose
- Git

---

## Backend Setup

### 1. Install Dependencies

```bash
cd govcon-ai-pipeline

# Using uv (recommended)
uv sync

# Or using pip
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### 2. Install psutil for System Monitoring

```bash
# The monitoring agent requires psutil
uv add psutil
# or
pip install psutil
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Database
POSTGRES_URL=postgresql://bronze:password@localhost:5432/govcon

# Redis Cache
REDIS_URL=redis://localhost:6379/0

# AI Models
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# Company Configuration
COMPANY_NAME="The Bronze Shield"
SET_ASIDE_PREFS=["SDVOSB","VOSB","SB"]
ALLOWED_NAICS=["541512","541511","541519","541513","541690","541611","541930","561410","518210","541990"]
ALLOWED_PSC=["D301","D302","D307","D308","D310","D314","D316","D318","D399","R408","R410","R413","R420","R499","R699","R608","U012","U099"]
```

### 4. Initialize Database

```bash
# Start PostgreSQL (if using Docker)
docker-compose up -d postgres

# Initialize database
uv run python -m govcon.cli init-db
```

### 5. Start Backend API

```bash
# Development mode with auto-reload
uv run uvicorn govcon.api.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uv run uvicorn govcon.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at:
- **Swagger UI:** http://localhost:8000/api/docs
- **ReDoc:** http://localhost:8000/api/redoc
- **API:** http://localhost:8000

---

## Frontend Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Environment

Create `.env` file:

```bash
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

### 3. Start Development Server

```bash
npm run dev
```

The frontend will be available at http://localhost:5173

### 4. Build for Production

```bash
npm run build
npm run preview  # Test production build
```

---

## Docker Deployment

### 1. Start All Services

```bash
docker-compose up -d
```

This starts:
- **Backend API** (port 8000)
- **Frontend** (port 80)
- **PostgreSQL** (port 5432)
- **Redis** (port 6379)
- **Qdrant** (port 6333)
- **MinIO** (port 9000)

### 2. View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 3. Stop Services

```bash
docker-compose down

# Remove volumes (WARNING: deletes data)
docker-compose down -v
```

---

## Verification

### 1. Check Backend Health

```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy"}

curl http://localhost:8000/
# Expected: {"name":"GovCon AI Pipeline","version":"1.0.0","status":"operational"}
```

### 2. Test API Endpoints

```bash
# List all agents
curl http://localhost:8000/api/agents

# Get system health
curl http://localhost:8000/api/system/health

# Get system metrics
curl http://localhost:8000/api/system/metrics
```

### 3. Test WebSocket Connection

Open browser console on http://localhost:5173 and run:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/system');
ws.onopen = () => console.log('Connected');
ws.onmessage = (e) => console.log('Message:', JSON.parse(e.data));
```

### 4. Access Frontend

Navigate to http://localhost:5173 (dev) or http://localhost (production)

You should see:
- Home page with feature overview
- Navigation to Dashboard and Admin Panel
- "System Online" indicator in header

---

## Using the System

### 1. System Dashboard

Navigate to `/dashboard` or click "Dashboard" in navigation.

**Features:**
- Real-time system metrics (CPU, Memory, Disk)
- Active agent count
- Agent status grid with live updates
- Monitoring agent control panel

**Start Monitoring:**
1. Click "Start Monitoring" button
2. Watch status change to "Running" with green indicator
3. See detected errors count update in real-time

### 2. Admin Panel

Navigate to `/admin` or click "Admin" in navigation.

**Features:**
- System information (platform, architecture)
- Database status and backup
- Configuration editor
- Service restart controls

**Edit Configuration:**
1. Find the config item you want to edit
2. Change the value in the input field
3. Click "Save" button
4. Configuration is updated immediately

**Create Database Backup:**
1. In the Database card, click "Create Backup"
2. Backup ID will be displayed in toast notification

### 3. Start Monitoring Agent

**Via API:**
```bash
curl -X POST http://localhost:8000/api/monitoring/start
```

**Via Frontend:**
1. Go to Dashboard
2. Find "Autonomous Monitoring Agent" card
3. Click "Start Monitoring"

**The monitoring agent will:**
- Check system health every 30 seconds
- Detect errors automatically
- Attempt to fix errors on the fly
- Broadcast updates via WebSocket
- Generate error reports

### 4. View Monitoring Report

**Via API:**
```bash
curl http://localhost:8000/api/monitoring/report
```

**Response:**
```json
{
  "total_errors": 5,
  "errors_by_severity": {
    "low": 2,
    "medium": 2,
    "high": 1,
    "critical": 0
  },
  "errors_by_type": {
    "api_error": 3,
    "database_error": 1,
    "system_error": 1
  },
  "fix_success_rate": 0.8,
  "recent_errors": [...]
}
```

### 5. Execute an Agent

**Via API:**
```bash
curl -X POST http://localhost:8000/api/agents/discovery/execute \
  -H "Content-Type: application/json" \
  -d '{"agent_name":"discovery","parameters":{"days_back":7}}'
```

**Watch in Dashboard:**
- Agent status changes from "idle" to "running"
- Execution count increments
- Status updates in real-time via WebSocket

### 6. View Agent Metrics

```bash
curl http://localhost:8000/api/agents/discovery/metrics
```

**Response:**
```json
{
  "agent_name": "discovery",
  "total_executions": 15,
  "successful_executions": 14,
  "failed_executions": 1,
  "average_duration_seconds": 45.3,
  "last_24h_executions": 5,
  "error_rate": 0.067
}
```

---

## Troubleshooting

### Backend Issues

**Problem:** API not starting
```bash
# Check logs
uv run python -m govcon.api.main

# Check if port is in use
lsof -i :8000

# Try different port
uv run uvicorn govcon.api.main:app --port 8001
```

**Problem:** Database connection error
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Test connection
psql postgresql://bronze:password@localhost:5432/govcon
```

**Problem:** Import errors
```bash
# Reinstall dependencies
uv sync --reinstall

# Check Python path
echo $PYTHONPATH
```

### Frontend Issues

**Problem:** Cannot connect to API
- Check `VITE_API_URL` in `.env`
- Verify backend is running
- Check CORS configuration in backend

**Problem:** WebSocket connection fails
- Check `VITE_WS_URL` in `.env`
- Verify WebSocket endpoints are accessible
- Check browser console for errors

**Problem:** Build errors
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Check TypeScript errors
npm run type-check
```

### Monitoring Agent Issues

**Problem:** Monitoring not starting
```bash
# Check if already running
curl http://localhost:8000/api/monitoring/status

# Check logs for errors
docker-compose logs backend | grep monitoring
```

**Problem:** No errors detected
- This is normal if system is healthy
- Try causing an error (e.g., stop database)
- Check monitoring cycle interval

---

## Development Tips

### Hot Reload

Both backend and frontend support hot reload:
- Backend: Uses `--reload` flag
- Frontend: Vite dev server watches files

### API Documentation

Access interactive API docs:
- **Swagger UI:** http://localhost:8000/api/docs
- Test endpoints directly in browser
- View request/response schemas

### WebSocket Testing

Use browser console or tools like:
- **websocat:** `websocat ws://localhost:8000/ws/system`
- **wscat:** `wscat -c ws://localhost:8000/ws/system`

### Database Inspection

```bash
# Connect to database
docker exec -it govcon-postgres psql -U bronze -d govcon

# List tables
\dt

# View opportunities
SELECT * FROM opportunities LIMIT 10;

# View audit logs
SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 20;
```

---

## Production Deployment

### Security Checklist

- [ ] Change default passwords
- [ ] Set strong JWT secret
- [ ] Enable HTTPS/WSS
- [ ] Configure firewall rules
- [ ] Set up SSL certificates
- [ ] Enable rate limiting
- [ ] Configure CORS properly
- [ ] Set up monitoring alerts

### Performance Optimization

- [ ] Enable database connection pooling
- [ ] Configure Redis caching
- [ ] Set up CDN for static assets
- [ ] Enable gzip compression
- [ ] Configure load balancing
- [ ] Set up horizontal scaling

### Monitoring Setup

- [ ] Configure log aggregation
- [ ] Set up error tracking (Sentry)
- [ ] Configure metrics collection
- [ ] Set up alerting (PagerDuty)
- [ ] Configure uptime monitoring

---

## Support

For issues or questions:
- Check logs: `docker-compose logs -f`
- Review API docs: http://localhost:8000/api/docs
- Check system health: http://localhost:8000/health
- View monitoring report: http://localhost:8000/api/monitoring/report

---

## Next Steps

1. **Customize Design**
   - Edit design tokens in `frontend/src/styles/tokens.ts`
   - Modify components in `frontend/src/components/ui/`

2. **Add Custom Agents**
   - Create new agent in `src/govcon/agents/`
   - Add routes in `src/govcon/api/routes/agents.py`
   - Update frontend service layer

3. **Extend Monitoring**
   - Add custom error patterns in `monitoring.py`
   - Create fix strategies for specific errors
   - Configure alerting rules

4. **Deploy to Production**
   - Follow production deployment checklist
   - Set up CI/CD pipeline
   - Configure monitoring and logging

Happy coding! 🚀
