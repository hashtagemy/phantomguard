"""
Swarm Agents — Multi-agent pipeline test.
README'deki örneğin çalışan hali.

Usage:
    python tests/agents/swarm_agents.py
"""

from datetime import datetime

from strands import Agent
from strands_tools import file_write, http_request

from norn import NornHook


# Unique ID per run — keeps each pipeline execution separate on the dashboard
run_id = datetime.now().strftime("%Y%m%d-%H%M%S")

# Agent 1 — Researcher
hook_a = NornHook(
    norn_url="http://localhost:8000",
    agent_name="Researcher",
    swarm_id=f"research-pipeline-{run_id}",
    swarm_order=1,
)
agent_a = Agent(tools=[http_request], hooks=[hook_a])
result_a = agent_a("Find recent AI safety research trends")

# Agent 2 — Writer (receives output from Agent 1)
hook_b = NornHook(
    norn_url="http://localhost:8000",
    agent_name="Writer",
    swarm_id=f"research-pipeline-{run_id}",
    swarm_order=2,
    handoff_input=str(result_a)[:500],
)
agent_b = Agent(tools=[file_write], hooks=[hook_b])
agent_b(f"Write a report based on: {result_a}")
