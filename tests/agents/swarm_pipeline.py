"""
Swarm Pipeline — 3 Aşamalı Veri Analiz Pipeline'ı
Norn'un swarm özelliklerini test eder:
  - Swarm ID ile bağlantılı 3 agent
  - Handoff: her agent bir öncekinin çıktısını alır
  - Alignment scoring: hepsi aynı konuya mı çalışıyor?
  - Drift detection: farklı konuya kayma var mı?

Aşamalar:
  1. DataFetcher   → Ham veri toplar
  2. DataAnalyzer  → Veriyi analiz eder (DataFetcher'dan handoff alır)
  3. ReportWriter  → Rapor yazar (DataAnalyzer'dan handoff alır)
"""

import json
import uuid
from strands import Agent
from strands.tools import tool
from strands.models import BedrockModel
from strands.handlers import null_callback_handler
from norn import NornHook


SWARM_ID = f"pipeline-{uuid.uuid4().hex[:8]}"
MODEL_ID = "us.amazon.nova-2-lite-v1:0"

print(f"\n{'='*55}")
print(f"  SWARM PIPELINE TEST")
print(f"  Swarm ID: {SWARM_ID}")
print(f"{'='*55}\n")


# ── Stage 1: Data Fetcher ─────────────────────────────────────────

@tool
def fetch_market_data(symbol: str) -> str:
    """Fetch simulated market data for a given stock symbol."""
    simulated_data = {
        "AAPL": {"price": 189.5, "change": +2.3, "volume": 52_000_000, "pe_ratio": 29.4},
        "MSFT": {"price": 415.2, "change": +1.8, "volume": 18_000_000, "pe_ratio": 35.1},
        "NVDA": {"price": 875.4, "change": +5.1, "volume": 42_000_000, "pe_ratio": 68.2},
        "GOOGL": {"price": 175.3, "change": -0.5, "volume": 21_000_000, "pe_ratio": 26.8},
    }
    data = simulated_data.get(symbol.upper(), {"error": f"Symbol {symbol} not found"})
    return json.dumps(data)


@tool
def list_available_symbols() -> str:
    """List all available market symbols for data fetching."""
    return "Available symbols: AAPL, MSFT, NVDA, GOOGL"


def run_stage1():
    hook = NornHook(
        norn_url="http://localhost:8000",
        agent_name="Pipeline_DataFetcher",
        task="Fetch market data for tech stocks",
        swarm_id=SWARM_ID,
        swarm_order=1,
    )
    model = BedrockModel(model_id=MODEL_ID)
    agent = Agent(
        model=model,
        tools=[fetch_market_data, list_available_symbols],
        hooks=[hook],
        callback_handler=null_callback_handler,
    )

    print("Stage 1 — DataFetcher: Collecting market data...")
    result = agent(
        "List available symbols, then fetch market data for AAPL, MSFT, and NVDA. "
        "Return all the data in a structured format."
    )
    output = str(result)
    print(f"  ✓ DataFetcher complete ({len(output)} chars)\n")
    return output[:600]


# ── Stage 2: Data Analyzer ────────────────────────────────────────

@tool
def calculate_metrics(data_json: str) -> str:
    """Calculate financial metrics from raw market data."""
    try:
        data = json.loads(data_json)
        metrics = {}
        for symbol, values in data.items():
            if isinstance(values, dict) and "price" in values:
                metrics[symbol] = {
                    "price": values["price"],
                    "trend": "bullish" if values.get("change", 0) > 0 else "bearish",
                    "valuation": "overvalued" if values.get("pe_ratio", 0) > 40 else "fair",
                    "activity": "high" if values.get("volume", 0) > 30_000_000 else "normal",
                }
        return json.dumps(metrics, indent=2)
    except Exception as e:
        return f"Metrics error: {e}"


@tool
def rank_stocks(metrics_json: str, criterion: str) -> str:
    """Rank stocks by a given criterion (trend, valuation, activity)."""
    try:
        metrics = json.loads(metrics_json)
        ranked = sorted(metrics.items(), key=lambda x: x[1].get(criterion, ""))
        return json.dumps([{"symbol": s, criterion: m.get(criterion)} for s, m in ranked], indent=2)
    except Exception as e:
        return f"Ranking error: {e}"


def run_stage2(stage1_output: str):
    hook = NornHook(
        norn_url="http://localhost:8000",
        agent_name="Pipeline_DataAnalyzer",
        task="Analyze market data and rank stocks",
        swarm_id=SWARM_ID,
        swarm_order=2,
        handoff_input=stage1_output,
    )
    model = BedrockModel(model_id=MODEL_ID)
    agent = Agent(
        model=model,
        tools=[calculate_metrics, rank_stocks],
        hooks=[hook],
        callback_handler=null_callback_handler,
    )

    print("Stage 2 — DataAnalyzer: Analyzing market data...")
    result = agent(
        f"Here is the raw market data collected:\n{stage1_output}\n\n"
        "1. Calculate metrics for each stock using the data above (format as JSON dict with symbol keys)\n"
        "2. Rank stocks by their trend (bullish/bearish)\n"
        "3. Summarize your findings with key insights"
    )
    output = str(result)
    print(f"  ✓ DataAnalyzer complete ({len(output)} chars)\n")
    return output[:600]


# ── Stage 3: Report Writer ────────────────────────────────────────

@tool
def write_investment_report(title: str, executive_summary: str, findings: str) -> str:
    """Write a structured investment report to /tmp."""
    report = f"""# {title}

## Executive Summary
{executive_summary}

## Key Findings
{findings}

## Disclaimer
This is an automated analysis report generated by Norn AI Pipeline.
All data is simulated for testing purposes.
"""
    path = f"/tmp/{title.replace(' ', '_').lower()[:40]}.md"
    with open(path, "w") as f:
        f.write(report)
    return f"Report written to {path} ({len(report)} chars)"


@tool
def evaluate_recommendation(stock: str, metrics_summary: str) -> str:
    """Generate a BUY/HOLD/SELL recommendation based on metrics summary."""
    # Simple rule-based recommendation
    summary = metrics_summary.lower()
    if "bullish" in summary and "fair" in summary:
        rec = "BUY"
        reason = "Positive trend with fair valuation"
    elif "overvalued" in summary:
        rec = "HOLD"
        reason = "Currently overvalued, wait for price correction"
    else:
        rec = "HOLD"
        reason = "Insufficient signal for strong action"
    return f"{stock}: {rec} — {reason}"


def run_stage3(stage2_output: str):
    hook = NornHook(
        norn_url="http://localhost:8000",
        agent_name="Pipeline_ReportWriter",
        task="Write investment report with recommendations",
        swarm_id=SWARM_ID,
        swarm_order=3,
        handoff_input=stage2_output,
    )
    model = BedrockModel(model_id=MODEL_ID)
    agent = Agent(
        model=model,
        tools=[write_investment_report, evaluate_recommendation],
        hooks=[hook],
        callback_handler=null_callback_handler,
    )

    print("Stage 3 — ReportWriter: Writing investment report...")
    result = agent(
        f"Here is the analysis from the previous stage:\n{stage2_output}\n\n"
        "1. Evaluate recommendations for each stock (AAPL, MSFT, NVDA)\n"
        "2. Write a complete investment report titled 'Tech Stocks Q1 Analysis' "
        "with an executive summary and the key findings from the analysis\n"
        "3. Make sure the report includes the recommendations"
    )
    output = str(result)
    print(f"  ✓ ReportWriter complete ({len(output)} chars)\n")
    return output


# ── Main ──────────────────────────────────────────────────────────

def run():
    stage1_result = run_stage1()
    stage2_result = run_stage2(stage1_result)
    run_stage3(stage2_result)

    print(f"{'='*55}")
    print(f"  PIPELINE COMPLETE")
    print(f"  Swarm ID: {SWARM_ID}")
    print(f"  Check dashboard: http://localhost:3000")
    print(f"  3 sessions should appear linked under the same swarm")
    print(f"{'='*55}\n")

    return SWARM_ID


if __name__ == "__main__":
    run()
