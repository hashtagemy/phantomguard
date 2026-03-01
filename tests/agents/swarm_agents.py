"""
Swarm Agents — Multi-agent pipeline test.
Tests: swarm_id tracking, handoff, drift detection.
Agent 1: Research → Agent 2: Summarize
"""

from strands import Agent
from strands.tools import tool
from strands.models import BedrockModel
from strands.handlers import null_callback_handler
from norn import NornHook
import uuid


@tool
def search_topic(query: str) -> str:
    """Search for information about a topic."""
    return f"Research results for '{query}': AI agents are software programs that can autonomously perform tasks. They use LLMs for reasoning and tools for actions."


@tool
def write_summary(content: str) -> str:
    """Write a summary to a file."""
    with open("research_summary.txt", "w") as f:
        f.write(content)
    return "Summary written to research_summary.txt"


def run():
    swarm_id = f"swarm-{uuid.uuid4().hex[:8]}"
    model = BedrockModel(model_id="us.amazon.nova-2-lite-v1:0")

    # Agent 1: Researcher
    hook1 = NornHook(
        norn_url="http://localhost:8000",
        agent_name="Swarm_Researcher",
        task="Research AI agents",
        swarm_id=swarm_id,
        swarm_order=1,
    )
    agent1 = Agent(
        model=model,
        tools=[search_topic],
        hooks=[hook1],
        callback_handler=null_callback_handler,
    )

    print(f"Running Swarm [{swarm_id}] — Agent 1: Researcher...")
    result1 = agent1("Search for 'AI agents' and return the findings.")
    research_output = str(result1)[:300]
    print(f"  Researcher output: {research_output[:100]}...")

    # Agent 2: Summarizer (receives handoff from Agent 1)
    hook2 = NornHook(
        norn_url="http://localhost:8000",
        agent_name="Swarm_Summarizer",
        task="Summarize research findings",
        swarm_id=swarm_id,
        swarm_order=2,
        handoff_input=research_output,
    )
    agent2 = Agent(
        model=model,
        tools=[write_summary],
        hooks=[hook2],
        callback_handler=null_callback_handler,
    )

    print(f"Running Swarm [{swarm_id}] — Agent 2: Summarizer...")
    result2 = agent2(f"Summarize the following research and write it to a file: {research_output}")
    print(f"  Summarizer output: {str(result2)[:100]}...")

    return swarm_id


if __name__ == "__main__":
    run()
