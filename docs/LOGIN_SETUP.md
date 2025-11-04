# Login Setup Guide

## Quick Start (Development Mode)

### Option 1: Demo Login Button (Easiest)

When running in development mode (`npm run dev`), you'll see a **"Demo Login"** button on the login screen.

1. Start the frontend:
   ```bash
   cd frontend
   npm run dev
   ```

2. Navigate to http://localhost:5173

3. Click the **"🚀 Demo Login (Skip Authentication)"** button

4. You'll be logged in immediately with demo credentials!

This bypasses the backend authentication entirely for quick development testing.

---

## Option 2: Create a Real User (For Full Testing)

If you want to test the full authentication flow with the backend:

### Step 1: Ensure Database is Running

```bash
# Start PostgreSQL
docker-compose up -d postgres

# Or if using Docker Compose for everything:
docker-compose up -d
```

### Step 2: Create a Demo Admin User

Run the CLI command:

```bash
cd govcon-ai-pipeline
uv run python -m govcon.cli create-user
```

This will create:
- **Email:** `admin@bronzeshield.com`
- **Password:** `admin123`
- **Role:** Admin with full permissions

### Step 3: Login with Real Credentials

1. Go to http://localhost:5173/login
2. Enter:
   - Email: `admin@bronzeshield.com`
   - Password: `admin123`
3. Click "Sign In"

The system will:
1. Authenticate with the backend API
2. Receive a JWT token
3. Store the token in localStorage
4. Redirect you to the dashboard

---

## Authentication Flow

### Development Mode Flow (Demo Login)
```
Click "Demo Login"
    ↓
Create demo user object in frontend
    ↓
Store in Zustand auth store
    ↓
Redirect to dashboard
    ↓
✓ Logged in (no backend required)
```

### Production Flow (Real Authentication)
```
Enter email & password
    ↓
POST /api/users/token
    ↓
Backend validates credentials
    ↓
Returns JWT access token
    ↓
GET /api/users/me (with token)
    ↓
Returns user profile
    ↓
Store token & user in auth store
    ↓
Redirect to dashboard
    ↓
✓ Logged in (authenticated with backend)
```

---

## Creating Additional Users

### Via CLI (Easiest)

Create users with custom email, password, and role:

```bash
# Create an analyst user
uv run python -m govcon.cli create-user \
  --email analyst@bronzeshield.com \
  --password secure123 \
  --full-name "Proposal Analyst" \
  --role analyst

# Create a writer user
uv run python -m govcon.cli create-user \
  --email writer@bronzeshield.com \
  --password writer456 \
  --full-name "Proposal Writer" \
  --role writer

# View all options
uv run python -m govcon.cli create-user --help
```

**Available roles:**
- `admin` - Full system access
- `analyst` - Analyze opportunities
- `writer` - Write proposals
- `reviewer` - Review proposals
- `viewer` - Read-only access
- `sdvosb_officer` - Manage certifications

### Via API (When Logged In as Admin)

```bash
curl -X POST http://localhost:8000/api/users \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@bronzeshield.com",
    "full_name": "New User",
    "password": "password123",
    "role": "viewer"
  }'
```

### Via Python Script

Create a script `create_user.py`:

```python
import asyncio
from govcon.models import User, Role
from govcon.utils.database import get_db_session
from govcon.utils.security import hash_password

async def create_user(email, password, full_name, role=Role.VIEWER):
    async with get_db_session() as db:
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            role=role,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        print(f"✓ User {email} created")

asyncio.run(create_user(
    email="analyst@bronzeshield.com",
    password="secure123",
    full_name="Proposal Analyst",
    role=Role.ANALYST
))
```

Run it:
```bash
uv run python create_user.py
```

---

## User Roles

The system supports different user roles:

- **ADMIN** - Full access, can create users
- **SDVOSB_OFFICER** - Manage certifications
- **ANALYST** - Analyze opportunities
- **WRITER** - Write proposals
- **REVIEWER** - Review proposals
- **VIEWER** - Read-only access

---

## Troubleshooting

### Demo Login Button Not Showing

**Problem:** The demo login button doesn't appear.

**Solution:** Make sure you're running in development mode:
```bash
npm run dev  # NOT npm run build + npm run preview
```

The button only appears when `import.meta.env.DEV` is `true`.

### "Invalid email or password" Error

**Problem:** Real login fails with invalid credentials.

**Solutions:**
1. Make sure you created the demo user:
   ```bash
   uv run python src/govcon/cli_create_user.py
   ```

2. Check the credentials:
   - Email: `admin@bronzeshield.com`
   - Password: `admin123`

3. Verify database is running:
   ```bash
   docker-compose ps postgres
   ```

### "Could not validate credentials" Error

**Problem:** Token validation fails.

**Solutions:**
1. Clear localStorage:
   ```javascript
   // In browser console
   localStorage.clear()
   window.location.reload()
   ```

2. Check backend is running:
   ```bash
   curl http://localhost:8000/health
   ```

### Stuck on Login Screen (Real Auth)

**Problem:** Login seems to work but stays on login screen.

**Solutions:**
1. Check browser console for errors (F12)
2. Verify API URL in `.env`:
   ```bash
   cat frontend/.env
   # Should show: VITE_API_URL=http://localhost:8000
   ```
3. Check CORS settings in backend
4. Try demo login to rule out backend issues

---

## Security Notes

### Development Mode

The demo login button:
- ✅ Only appears in development (`npm run dev`)
- ✅ Automatically removed in production builds
- ✅ Uses `import.meta.env.DEV` to detect environment
- ⚠️ Does NOT connect to backend
- ⚠️ Uses fake credentials (no real authentication)

### Production Mode

For production deployment:

1. **Remove Demo Login:**
   - Demo button won't appear (automatically handled)
   - Or remove the code entirely for extra security

2. **Change Default Credentials:**
   ```bash
   # Delete demo user
   DELETE FROM users WHERE email = 'admin@bronzeshield.com';

   # Create production admin with strong password
   ```

3. **Enable HTTPS:**
   - Configure SSL/TLS certificates
   - Update `VITE_API_URL` to use `https://`

4. **Set Secure JWT Secret:**
   - Change `JWT_SECRET` in `.env`
   - Use a long, random string

5. **Configure CORS:**
   - Limit `CORS_ORIGINS` to your production domain
   - Remove `http://localhost` origins

---

## Quick Reference

### Development Login

**Fastest:** Click "Demo Login" button
- No backend required
- Instant access
- Perfect for frontend development

**Full Stack:** Use `admin@bronzeshield.com` / `admin123`
- Tests full authentication flow
- Requires backend running
- Creates real session

### Production Login

1. Create production users via admin panel
2. Use strong passwords
3. Enable MFA (if implemented)
4. Monitor authentication logs

---

## Next Steps

After logging in:

1. **Explore the Dashboard**
   - Go to `/system` for system monitoring
   - Go to `/admin` for backend configuration

2. **Start the Monitoring Agent**
   - Navigate to System Dashboard
   - Click "Start Monitoring"
   - Watch autonomous error detection in action

3. **Try the Features**
   - View opportunities and proposals
   - Execute agents
   - Monitor system health

---

Enjoy your Apple-inspired GovCon AI Pipeline! 🚀
