# GovCon AI Pipeline - Frontend

Modern web interface for The Bronze Shield GovCon AI Pipeline system.

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **TailwindCSS** - Utility-first styling
- **React Router** - Client-side routing
- **React Query** - Server state management
- **Zustand** - Client state management
- **Axios** - HTTP client
- **Lucide React** - Icon library
- **date-fns** - Date formatting
- **React Hot Toast** - Notifications

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn
- Backend API running on http://localhost:8000

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The application will be available at http://localhost:5173

### Build for Production

```bash
# Create production build
npm run build

# Preview production build
npm run preview
```

## Features

### Dashboard
- Overview of opportunities and proposals
- Key metrics: total opportunities, SDVOSB set-asides, active proposals, pipeline value
- Recent opportunities and active proposals
- Pending approvals

### Opportunities
- List view with search and filters
- Detailed opportunity view with:
  - Agency, set-aside, NAICS/PSC codes
  - Posted and response deadline dates
  - Bid/No-Bid analysis scores
  - Match scores with visual progress bars
- Direct link to execute workflow for opportunity

### Proposals
- List view of all proposals with progress tracking
- Detailed proposal view with:
  - Workflow progress timeline
  - Proposal volumes and sections
  - Pricing breakdown
  - Team members
  - Related opportunity link

### Workflow Execution
- Run discovery workflows to find new opportunities
- Execute full proposal workflows
- Real-time progress monitoring with stage indicators
- Auto-approve option for automation
- Recent execution history

### Settings
- **General**: Company info, set-aside designations, target NAICS/PSC codes
- **API Keys**: SAM.gov, OpenAI, BLS integration
- **Notifications**: Email and in-app preferences
- **Security**: Password management, 2FA, compliance status

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   └── Layout.tsx          # Main app layout with sidebar
│   ├── lib/
│   │   ├── api.ts              # API client and endpoints
│   │   └── axios.ts            # Axios instance configuration
│   ├── pages/
│   │   ├── Dashboard.tsx       # Home dashboard
│   │   ├── Login.tsx           # Authentication
│   │   ├── Opportunities.tsx   # Opportunities list
│   │   ├── OpportunityDetail.tsx
│   │   ├── Proposals.tsx       # Proposals list
│   │   ├── ProposalDetail.tsx
│   │   ├── Workflow.tsx        # Workflow execution
│   │   └── Settings.tsx        # System configuration
│   ├── store/
│   │   └── authStore.ts        # Authentication state
│   ├── types/
│   │   └── index.ts            # TypeScript interfaces
│   ├── App.tsx                 # Root component with routing
│   ├── main.tsx                # Application entry point
│   └── index.css               # Global styles
├── index.html
├── package.json
├── tsconfig.json               # TypeScript configuration
├── tailwind.config.js          # TailwindCSS configuration
└── vite.config.ts              # Vite configuration
```

## API Integration

The frontend communicates with the FastAPI backend via REST endpoints:

- `POST /auth/login` - User authentication
- `GET /api/v1/opportunities` - List opportunities
- `GET /api/v1/opportunities/{id}` - Get opportunity details
- `GET /api/v1/proposals` - List proposals
- `GET /api/v1/proposals/{id}` - Get proposal details
- `POST /api/v1/workflow/execute` - Execute full workflow
- `POST /api/v1/workflow/discover` - Run discovery only
- `GET /api/v1/workflow/status` - Get workflow status
- `GET /api/v1/system/health` - Health check
- `GET /api/v1/system/config` - Get system configuration

## Authentication

The app uses JWT-based authentication:

1. User logs in with email/password
2. Backend returns JWT token
3. Token stored in localStorage and Zustand store
4. Axios interceptor adds token to all API requests
5. Automatic redirect to login on 401 responses

## Styling

### Brand Colors

- **Primary (Bronze)**: `#CD7F32` - The Bronze Shield brand color
- **Success (Green)**: For completed states and approvals
- **Info (Blue)**: For in-progress and informational states
- **Warning (Yellow)**: For pending and attention states
- **Danger (Red)**: For rejected and error states

### Component Classes

Pre-defined utility classes in `index.css`:

- `.card` - White card with shadow and rounded corners
- `.btn-primary` - Primary action button (bronze)
- `.btn-secondary` - Secondary action button (gray)
- `.badge` - Status badge with variants (success, danger, info, warning)
- `.input` - Form input styling

## Development

### Running Tests

```bash
npm run test
```

### Linting

```bash
npm run lint
```

### Type Checking

```bash
npm run type-check
```

## Deployment

### Docker

The frontend can be deployed with the included Dockerfile:

```bash
docker build -t govcon-frontend .
docker run -p 80:80 govcon-frontend
```

### Static Hosting

Build the production bundle and serve the `dist/` folder:

```bash
npm run build
# Deploy dist/ to your hosting provider (Netlify, Vercel, S3, etc.)
```

### Environment Variables

Create a `.env` file for environment-specific configuration:

```env
VITE_API_URL=http://localhost:8000
```

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## License

Proprietary - The Bronze Shield
