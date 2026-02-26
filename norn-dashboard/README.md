# Norn Dashboard

React dashboard for the Norn AI agent monitoring platform.

## Features

- **Agent Management** — Import from GitHub or ZIP, view all registered agents
- **Code Analysis** — Automatic discovery of tools, functions, and dependencies
- **Smart Task Generation** — AI-generated test tasks based on each agent's actual tools
- **Dependency Management** — Auto-install missing packages (PyPI and local)
- **Real-Time Monitoring** — WebSocket-based live updates during execution
- **Session History** — View all past executions with detailed reports
- **AI Analysis** — Per-tool usage, decision observations, efficiency explanation
- **Browser Audit** — Nova Act shadow verification (requires `NOVA_ACT_API_KEY`)
- **Configuration** — Adjust guard mode and thresholds from the UI

## Tech Stack

- React 19 + TypeScript
- Vite
- Tailwind CSS
- Lucide Icons
- Recharts

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create `.env` file (optional — defaults to `http://localhost:8000`):
```bash
VITE_API_URL=http://localhost:8000
```

3. Start development server:
```bash
npm run dev
```

The dashboard will be available at **http://localhost:3000**

## Backend

Make sure the Norn backend is running:
```bash
source ../.venv/bin/activate
python -m norn.api
```

Or from the project root:
```bash
python -m norn.api
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Health check |
| `/api/agents` | GET | List all agents |
| `/api/agents/import/github` | POST | Import agent from GitHub |
| `/api/agents/import/zip` | POST | Import agent from ZIP file |
| `/api/agents/:id` | GET | Get agent details |
| `/api/agents/:id` | DELETE | Delete agent |
| `/api/agents/:id/analyze` | POST | Re-analyze agent code |
| `/api/agents/:id/run` | POST | Run agent with a task |
| `/api/sessions` | GET | List all sessions |
| `/api/sessions/:id` | GET | Get session details |
| `/api/stats` | GET | Dashboard statistics |
| `ws://localhost:8000/ws` | WebSocket | Live execution updates |

## Development

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Environment Variables

- `VITE_API_URL` — Backend API URL (default: `http://localhost:8000`)
