"""
Demo chat agent — Strands + Norn manual hook.

Usage:
    python tests/agents/demo_agent.py
"""

from strands import Agent
from strands_tools import calculator, current_time, file_read, file_write, http_request, python_repl, shell

from norn import NornHook

SYSTEM_PROMPT = """You are a helpful assistant with access to several tools:

- calculator: evaluate mathematical expressions
- current_time: get the current date/time
- file_read / file_write: read and write local files
- http_request: fetch content from URLs
- python_repl: execute Python code
- shell: run shell commands

Answer questions directly when you can. Use tools only when genuinely needed.
Be concise and precise."""

guard = NornHook(
    norn_url="http://localhost:8000",
    agent_name="Demo Chat Agent",
    session_id="hook-demo-chat-agent",
)

agent = Agent(
    system_prompt=SYSTEM_PROMPT,
    tools=[calculator, current_time, file_read, file_write, http_request, python_repl, shell],
    hooks=[guard],
)


def main() -> None:
    print("Demo Agent — type 'exit' or 'quit' to stop.\n")
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        response = agent(user_input)
        print(f"\nAgent: {response}\n")


if __name__ == "__main__":
    main()
