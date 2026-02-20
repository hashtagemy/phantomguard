# PhantomGuard — Quick Start Guide

> Get PhantomGuard running locally in under 10 minutes.

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10+ | Backend |
| Node.js | 18+ | Frontend dashboard |
| AWS account | — | Required for Amazon Bedrock (Nova Lite / Micro) |
| Nova Act API key | — | Shadow Browser verification (optional) |

---

## 1. Clone & Install

```bash
git clone https://github.com/hashtagemy/phantomguard.git
cd phantomguard

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -e ".[api]"

# Optional: enable Nova Act shadow browser verification
pip install -e ".[browser]"
# Then set NOVA_ACT_API_KEY in your .env file

cd phantomguard-dashboard
npm install
cd ..
```

---

## 2. Configure Environment

```bash
cp .env.example .env
```

Open `.env` and fill in your AWS credentials:

```dotenv
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_DEFAULT_REGION=us-east-1

# Optional — for shadow browser verification
# NOVA_ACT_API_KEY=your-nova-act-api-key
```

---

## 3. Start the Backend

```bash
source .venv/bin/activate
python -m phantomguard.api
```

Confirm it is running:

```bash
curl http://localhost:8000/
# {"status":"online","service":"PhantomGuard API"}
```

---

## 4. Start the Dashboard

Open a new terminal:

```bash
cd phantomguard-dashboard
npm run dev
```

Navigate to **http://localhost:3000**.

The **"System Online"** indicator in the top bar should be green. If it shows offline, make sure the backend is running.

---

## 5. Run Your First Agent

1. Click **"+ Add Agent"** in the left sidebar
2. Paste a GitHub repository URL **or** upload a ZIP file containing your agent
3. Wait for PhantomGuard to import and analyze it
4. Click **"Run"** on the agent card
5. Enter a task description and click **Run**
6. Watch the live execution feed — scores and issues appear in real time

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError: phantomguard` | Run `pip install -e ".[api]"` inside the virtual environment |
| Port 8000 already in use | `lsof -i :8000` to find the process, then `kill <PID>` |
| Dashboard shows "Connection Error" | Confirm the backend is running: `curl localhost:8000/` |
| AWS credentials error | Check `.env` values and verify Bedrock access in your AWS account |
| Scores show "N/A" | AWS Bedrock connection may be failing — check credentials and region |
| Agent import fails | Confirm the GitHub URL is public and accessible |
| Shadow browser shows "UNAVAILABLE" | Set `NOVA_ACT_API_KEY` in `.env` and run `pip install -e ".[browser]"` |

---

## Next Steps

- **Configuration** — Adjust guard mode and thresholds in the dashboard **Settings** panel
- **Integration** — See [README.md](README.md) to embed PhantomGuard directly into your agent code
