"""
main.py
Entry point for the AutoStream Conversational AI Agent.

Run with:
    python main.py

Or for a non-interactive demo:
    python main.py --demo
"""

import sys
import argparse
from dotenv import load_dotenv
from agent.graph import build_graph
from agent.state import AgentState

# Load environment variables from .env file
load_dotenv()

# ── ANSI colour helpers ───────────────────────────────────────────────────────
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def _initial_state() -> AgentState:
    return {
        "messages": [],
        "intent": "other",
        "lead_info": {},
        "lead_captured": False,
        "awaiting_field": None,
    }


def _last_assistant_message(state: AgentState) -> str | None:
    for m in reversed(state["messages"]):
        if m["role"] == "assistant":
            return m["content"]
    return None


def run_interactive():
    """Interactive REPL loop."""
    graph = build_graph()
    state = _initial_state()

    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  AutoStream AI Agent  —  type 'quit' or 'exit' to stop{RESET}")
    print(f"{BOLD}{'='*60}{RESET}\n")
    print(f"{GREEN}Aria:{RESET} Hi there! 👋 I'm Aria, your AutoStream assistant.")
    print(f"       Ask me about pricing, features, or how to get started!\n")

    while True:
        try:
            user_input = input(f"{CYAN}You:{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit", "bye"}:
            print(f"{GREEN}Aria:{RESET} Thanks for chatting! Have a great day. 🎬")
            break

        # Append user message
        state["messages"].append({"role": "user", "content": user_input})

        # Run through the graph
        state = graph.invoke(state)

        # Print the latest assistant message
        reply = _last_assistant_message(state)
        if reply:
            print(f"\n{GREEN}Aria:{RESET} {reply}\n")

        # Stop after successful lead capture
        if state.get("lead_captured"):
            print(f"{YELLOW}[Lead successfully captured — session complete.]{RESET}\n")
            break


def run_demo():
    """Run a scripted multi-turn demo conversation."""
    demo_turns = [
        "Hi there!",
        "Can you tell me about your pricing plans?",
        "What's the difference between Basic and Pro?",
        "That sounds great. I want to sign up for the Pro plan for my YouTube channel.",
        "My name is Alex Johnson",
        "alex.johnson@gmail.com",
        "YouTube",
    ]

    graph = build_graph()
    state = _initial_state()

    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}       AutoStream Agent — DEMO MODE{RESET}")
    print(f"{BOLD}{'='*60}{RESET}\n")

    for user_input in demo_turns:
        print(f"{CYAN}You:{RESET} {user_input}")
        state["messages"].append({"role": "user", "content": user_input})
        import time
        time.sleep(4.5) # Avoid hitting Gemini's 15 RPM free tier rate limit
        state = graph.invoke(state)
        reply = _last_assistant_message(state)
        if reply:
            print(f"{GREEN}Aria:{RESET} {reply}\n")
        if state.get("lead_captured"):
            print(f"{YELLOW}[✅ Lead successfully captured — demo complete.]{RESET}\n")
            break


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoStream Conversational AI Agent")
    parser.add_argument("--demo", action="store_true", help="Run scripted demo instead of interactive mode")
    args = parser.parse_args()

    if args.demo:
        run_demo()
    else:
        run_interactive()
