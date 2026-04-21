"""
agent/state.py
Defines the conversation state schema and intent enum used by the
LangGraph-based agent.
"""

from enum import Enum
from typing import Optional
from typing_extensions import TypedDict


class Intent(str, Enum):
    """Possible user intent categories."""
    GREETING = "greeting"
    PRODUCT_INQUIRY = "product_inquiry"
    PRICING_INQUIRY = "pricing_inquiry"
    HIGH_INTENT_LEAD = "high_intent_lead"
    OTHER = "other"


class LeadInfo(TypedDict, total=False):
    """Collected lead data. Fields are optional until fully gathered."""
    name: Optional[str]
    email: Optional[str]
    platform: Optional[str]


class AgentState(TypedDict):
    """
    Full conversation state passed between LangGraph nodes.

    Fields
    ------
    messages : list[dict]
        Full chat history as [{role, content}, ...] dicts.
    intent : str
        Latest detected intent label (see Intent enum).
    lead_info : LeadInfo
        Incrementally populated with name / email / platform.
    lead_captured : bool
        True once mock_lead_capture() has been successfully called.
    awaiting_field : str | None
        The next lead field the agent is actively asking for,
        or None if no collection is in progress.
    """
    messages: list
    intent: str
    lead_info: LeadInfo
    lead_captured: bool
    awaiting_field: Optional[str]
