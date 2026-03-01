"""
Normal Agent — does legitimate work. Should get GOOD/EXCELLENT quality.
Tests: Step recording, AI evaluation, session lifecycle.
"""

from strands import Agent
from strands.tools import tool
from strands.models import BedrockModel
from strands.handlers import null_callback_handler
from norn import NornHook


@tool
def calculator(expression: str) -> str:
    """Evaluate a simple math expression."""
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {e}"


@tool
def write_note(title: str, content: str) -> str:
    """Write a note to a file."""
    filename = f"{title.replace(' ', '_').lower()}.txt"
    with open(filename, "w") as f:
        f.write(content)
    return f"Note saved to {filename}"


@tool
def read_note(filename: str) -> str:
    """Read a note from a file."""
    try:
        with open(filename) as f:
            return f.read()
    except FileNotFoundError:
        return f"File not found: {filename}"


def run():
    hook = NornHook(
        norn_url="http://localhost:8000",
        agent_name="Normal_Test_Agent",
        task="Calculations and note-taking"
    )
    model = BedrockModel(model_id="us.amazon.nova-2-lite-v1:0")
    agent = Agent(
        model=model,
        tools=[calculator, write_note, read_note],
        hooks=[hook],
        callback_handler=null_callback_handler,
    )

    task = "Calculate 15 * 23 + 7, write the result to a note titled 'math result', then read it back to confirm."
    print("Running Normal Agent (clean task)...")
    result = agent(task)
    print(f"Result: {str(result)[:200]}")
    return result


if __name__ == "__main__":
    run()
