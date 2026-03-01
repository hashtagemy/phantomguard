"""
Demo Agent — monitored by Norn.
Run: python tests/agents/demo_agent.py
"""
from strands import Agent
from strands.models import BedrockModel
from strands_tools import calculator, current_time, file_read, file_write, http_request, shell, think

from norn import NornHook

guard = NornHook(
    norn_url="http://localhost:8000",
    agent_name="Demo Agent",
)

agent = Agent(
    model=BedrockModel(model_id="us.amazon.nova-2-lite-v1:0"),
    tools=[calculator, current_time, file_read, file_write, http_request, shell, think],
    hooks=[guard],
)

while True:
    try:
        user_input = input("You: ").strip()
    except (EOFError, KeyboardInterrupt):
        break
    if not user_input:
        continue
    if user_input.lower() in ("quit", "exit", "q"):
        break
    print(agent(user_input))
