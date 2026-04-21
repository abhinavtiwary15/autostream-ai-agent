"""
agent/rag.py
Simple RAG (Retrieval-Augmented Generation) pipeline.
Loads the AutoStream knowledge base from JSON and builds a
context string that is injected into every LLM system prompt.
"""

import json
import os
from pathlib import Path


_KB_PATH = Path(__file__).parent.parent / "knowledge_base" / "autostream_kb.json"


def load_knowledge_base() -> dict:
    """Load and return the raw knowledge base dict."""
    with open(_KB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_kb_context() -> str:
    """
    Convert the JSON knowledge base into a human-readable text block
    suitable for injection into the system prompt.
    """
    kb = load_knowledge_base()

    lines = []
    lines.append("=== AutoStream Knowledge Base ===\n")

    # Company overview
    lines.append(f"Company: {kb['company']['name']}")
    lines.append(f"Description: {kb['company']['description']}\n")

    # Pricing plans
    lines.append("--- PRICING PLANS ---")
    for plan in kb["plans"]:
        lines.append(f"\n{plan['name']} — ${plan['price_monthly']}/month")
        lines.append(f"Best for: {plan['best_for']}")
        lines.append("Features:")
        for feat in plan["features"]:
            lines.append(f"  • {feat}")

    # Policies
    lines.append("\n--- COMPANY POLICIES ---")
    for policy in kb["policies"]:
        lines.append(f"\n{policy['topic']}: {policy['detail']}")

    # FAQs
    lines.append("\n--- FREQUENTLY ASKED QUESTIONS ---")
    for faq in kb["faqs"]:
        lines.append(f"\nQ: {faq['question']}")
        lines.append(f"A: {faq['answer']}")

    lines.append("\n=== End of Knowledge Base ===")
    return "\n".join(lines)


if __name__ == "__main__":
    # Quick test: print the context block
    print(build_kb_context())
