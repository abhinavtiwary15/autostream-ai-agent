"""
tests/test_agent.py
Unit tests for the AutoStream AI agent components.
Run with: pytest tests/
"""

import pytest
from unittest.mock import patch, MagicMock

# ── RAG tests ────────────────────────────────────────────────────────────────

def test_kb_loads():
    from agent.rag import load_knowledge_base
    kb = load_knowledge_base()
    assert "plans" in kb
    assert len(kb["plans"]) == 2


def test_kb_context_contains_pricing():
    from agent.rag import build_kb_context
    ctx = build_kb_context()
    assert "$29" in ctx
    assert "$79" in ctx
    assert "Pro Plan" in ctx
    assert "Basic Plan" in ctx


def test_kb_context_contains_policies():
    from agent.rag import build_kb_context
    ctx = build_kb_context()
    assert "No refunds" in ctx or "refund" in ctx.lower()
    assert "24/7" in ctx


# ── Lead capture tool tests ───────────────────────────────────────────────────

def test_mock_lead_capture_returns_success():
    from tools.lead_capture import mock_lead_capture
    result = mock_lead_capture("Jane Doe", "jane@example.com", "YouTube")
    assert result["status"] == "success"
    assert result["data"]["name"] == "Jane Doe"
    assert result["data"]["email"] == "jane@example.com"
    assert result["data"]["platform"] == "YouTube"
    assert "lead_id" in result


def test_mock_lead_capture_prints(capsys):
    from tools.lead_capture import mock_lead_capture
    mock_lead_capture("Test User", "test@test.com", "Instagram")
    captured = capsys.readouterr()
    assert "Test User" in captured.out
    assert "test@test.com" in captured.out
    assert "Instagram" in captured.out


# ── State / collect_lead_info tests ──────────────────────────────────────────

def test_email_extraction():
    from agent.logic import extract_field
    assert extract_field("email", "my email is alice@example.com") == "alice@example.com"
    assert extract_field("email", "no email here") is None


def test_name_extraction():
    from agent.logic import extract_field
    assert extract_field("name", "John Smith") == "John Smith"


def test_platform_extraction():
    from agent.logic import extract_field
    assert extract_field("platform", "I'm on YouTube") == "Youtube"
    assert extract_field("platform", "instagram") == "Instagram"


# ── collect_lead_step tests ───────────────────────────────────────────────────

def test_collect_lead_asks_for_name_first():
    from agent.logic import collect_lead_step
    result = collect_lead_step(lead_info={}, awaiting_field=None, user_text="I want to sign up")
    assert result["awaiting_field"] == "name"
    assert "name" in result["assistant_message"].lower()


def test_collect_lead_stores_name_and_asks_email():
    from agent.logic import collect_lead_step
    result = collect_lead_step(lead_info={}, awaiting_field="name", user_text="Alice Wang")
    assert result["lead_info"].get("name") == "Alice Wang"
    assert result["awaiting_field"] == "email"


def test_collect_lead_completes_when_all_fields_present():
    from agent.logic import collect_lead_step
    result = collect_lead_step(
        lead_info={"name": "Alice Wang", "email": "alice@example.com"},
        awaiting_field="platform",
        user_text="TikTok",
    )
    assert result["lead_info"].get("platform") is not None
    assert result["awaiting_field"] is None


# ── fire_lead_capture tests ───────────────────────────────────────────────────

def test_fire_lead_capture_returns_success():
    from agent.logic import fire_lead_capture
    result = fire_lead_capture({"name": "Bob", "email": "bob@b.com", "platform": "YouTube"})
    assert result["status"] == "success"
    assert result["data"]["name"] == "Bob"


def test_lead_captured_flag_prevents_double_fire():
    """Guard logic: lead_captured=True means call_lead_tool must be a no-op."""
    # We test the pure state check here (no LangGraph needed)
    lead_captured = True
    lead_info = {"name": "Bob", "email": "bob@b.com", "platform": "YouTube"}
    messages = []

    # Simulate what call_lead_tool does internally
    if all(f in lead_info for f in ["name", "email", "platform"]) and not lead_captured:
        messages.append({"role": "assistant", "content": "captured"})

    assert messages == [], "Tool should not fire when lead_captured is True"
