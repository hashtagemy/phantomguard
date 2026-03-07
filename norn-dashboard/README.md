# Norn Dashboard

React dashboard for the Norn AI agent monitoring platform.

## Features

- **Agent Management** — Import from GitHub or ZIP, view all registered agents
- **Code Analysis** — Automatic discovery of tools, functions, and dependencies
- **Smart Task Generation** — AI-generated test tasks based on each agent's actual tools
- **Dependency Management** — Auto-install missing packages (PyPI and local)
- **Real-Time Monitoring** — WebSocket-based live updates with automatic reconnection
- **Session History** — View all past executions with detailed step-by-step reports
- **AI Analysis** — Per-tool usage, decision observations, efficiency explanation
- **Swarm Monitor** — Multi-agent pipeline view with AI-powered coherence analysis
- **Audit Logs** — Chronological security event history with severity filtering
- **Browser Audit** — Nova Act shadow verification results per session step
- **Configuration** — Adjust guard mode and thresholds from the UI

## Tech Stack

- React 19 + TypeScript
- Vite 6
- Tailwind CSS
- Lucide React
- Recharts

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create `.env` file (optional):
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

### Agents

| Endpoint | Method | Description |
|---|---|---|
| `/api/agents` | GET | List all registered agents |
| `/api/agents/:id` | GET | Get agent details |
| `/api/agents/:id` | DELETE | Delete agent and cleanup files |
| `/api/agents/import/github` | POST | Import agent from GitHub repository |
| `/api/agents/import/zip` | POST | Import agent from ZIP file upload |
| `/api/agents/register` | POST | Register hook agent (SDK internal) |
| `/api/agents/:id/run` | POST | Execute agent with a task |

### Sessions

| Endpoint | Method | Description |
|---|---|---|
| `/api/sessions` | GET | List sessions (most recent first) |
| `/api/sessions/:id` | GET | Get session details with steps |
| `/api/sessions/ingest` | POST | Create or resume a session |
| `/api/sessions/:id/step` | POST | Add a real-time execution step |
| `/api/sessions/:id/complete` | POST | Mark session complete with final scores |
| `/api/sessions/:id` | DELETE | Delete a session |
| `/api/sessions/:id/steps/:stepId` | DELETE | Delete a single step |

### Swarms

| Endpoint | Method | Description |
|---|---|---|
| `/api/swarms` | GET | List all swarm groups |
| `/api/swarms/:id` | GET | Get swarm details |
| `/api/swarms/:id/analysis` | GET | AI-powered pipeline analysis |
| `/api/swarms/:id` | DELETE | Delete swarm and all sessions |

### Audit, Config & Stats

| Endpoint | Method | Description |
|---|---|---|
| `/api/audit-logs` | GET | Audit log entries with filtering |
| `/api/audit-logs/:id` | DELETE | Delete a single audit event |
| `/api/audit-logs` | DELETE | Delete all audit logs |
| `/api/config` | GET | Get current configuration |
| `/api/config` | PUT | Update configuration |
| `/api/stats` | GET | Dashboard statistics |
| `/api/health` | GET | Health check |

### WebSocket

| Endpoint | Description |
|---|---|
| `ws://localhost:8000/ws/sessions` | Real-time session and agent updates |

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
