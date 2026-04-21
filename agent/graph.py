"""
agent/graph.py
LangGraph-based conversational agent for AutoStream.

Graph nodes
-----------
1. classify_intent   – uses LLM to label user intent
2. retrieve_context  – injects KB context for product/pricing queries
3. collect_lead_info – step-by-step lead qualification
4. call_lead_tool    – fires mock_lead_capture() when all fields present
5. generate_response – final LLM response to the user

Routing logic decides which nodes to activate per turn.
"""

import os
import json
import re
from typing import Literal

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from agent.state import AgentState, Intent
from agent.rag import build_kb_context
from agent.logic import (
    FIELD_ORDER, FIELD_QUESTIONS, extract_field,
    collect_lead_step, fire_lead_capture,
)

# ── LLM setup ────────────────────────────────────────────────────────────────

def _get_llm():
    api_key = os.environ.get("GOOGLE_API_KEY", "YOUR_GOOGLE_API_KEY")
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=api_key,
        temperature=0.3,
        max_tokens=1024,
    )


# ── KB context (built once) ───────────────────────────────────────────────────

_KB_CONTEXT = build_kb_context()


# ── Helper: convert state messages → LangChain message objects ────────────────

def _to_lc_messages(messages: list) -> list:
    result = []
    for m in messages:
        if m["role"] == "user":
            result.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            result.append(AIMessage(content=m["content"]))
    return result


# ─────────────────────────────────────────────────────────────────────────────
# NODE 1 – classify_intent
# ─────────────────────────────────────────────────────────────────────────────

def classify_intent(state: AgentState) -> AgentState:
    """
    Ask the LLM to classify the latest user message into one of the
    Intent categories. Returns the updated state with `intent` set.
    """
    llm = _get_llm()
    last_user_msg = next(
        (m["content"] for m in reversed(state["messages"]) if m["role"] == "user"),
        "",
    )

    classification_prompt = f"""You are an intent classifier for AutoStream, a SaaS video editing tool.
Classify the following user message into EXACTLY ONE of these categories:
- greeting          : casual hello, hi, hey, how are you
- product_inquiry   : questions about features, capabilities, how the product works
- pricing_inquiry   : questions about price, cost, plans, subscription
- high_intent_lead  : user expresses desire to sign up, try, buy, start, or is clearly ready to purchase
- other             : anything else

Respond with ONLY the category name (lowercase, no punctuation).

User message: "{last_user_msg}"
"""

    response = llm.invoke([HumanMessage(content=classification_prompt)])
    raw = response.content.strip().lower()

    # Map to valid Intent values
    intent_map = {
        "greeting": Intent.GREETING,
        "product_inquiry": Intent.PRODUCT_INQUIRY,
        "pricing_inquiry": Intent.PRICING_INQUIRY,
        "high_intent_lead": Intent.HIGH_INTENT_LEAD,
        "other": Intent.OTHER,
    }
    intent = intent_map.get(raw, Intent.OTHER)
    return {**state, "intent": intent}


# ─────────────────────────────────────────────────────────────────────────────
# NODE 2 – collect_lead_info  (only reached for high-intent users)
# ─────────────────────────────────────────────────────────────────────────────

# Field helpers are defined in agent/logic.py and imported above.


def collect_lead_info(state: AgentState) -> AgentState:
    """
    Determine which lead field to ask for next.
    If the user's last message answers the awaiting_field, store it.
    Then queue the next missing field.
    """
    messages = state["messages"]
    last_user_msg = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"),
        "",
    )

    result = collect_lead_step(
        lead_info=state.get("lead_info", {}),
        awaiting_field=state.get("awaiting_field"),
        user_text=last_user_msg,
    )

    return {
        **state,
        "lead_info": result["lead_info"],
        "awaiting_field": result["awaiting_field"],
        "messages": messages + [{"role": "assistant", "content": result["assistant_message"]}],
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 3 – call_lead_tool
# ─────────────────────────────────────────────────────────────────────────────

def call_lead_tool(state: AgentState) -> AgentState:
    """Fire mock_lead_capture() once all three lead fields are present."""
    lead_info = state.get("lead_info", {})

    if all(f in lead_info for f in FIELD_ORDER) and not state.get("lead_captured"):
        result = fire_lead_capture(lead_info)
        success_msg = (
            f"✅ You're all set, **{lead_info['name']}**! "
            f"Your AutoStream Pro account has been created. "
            f"Check your inbox at **{lead_info['email']}** for login details. "
            f"Welcome aboard — let's supercharge your {lead_info['platform']} content! 🎬"
        )
        return {
            **state,
            "lead_captured": True,
            "messages": state["messages"] + [{"role": "assistant", "content": success_msg}],
        }

    return state


# ─────────────────────────────────────────────────────────────────────────────
# NODE 4 – generate_response  (general knowledge / greeting turns)
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_TEMPLATE = """You are Aria, the friendly and knowledgeable sales assistant for AutoStream — an AI-powered video editing SaaS platform for content creators.

Your job:
1. Answer product and pricing questions accurately using the knowledge base below.
2. Be warm, concise, and helpful.
3. If a user seems interested in signing up, gently encourage them but do NOT ask for their details yourself — the system handles that separately.
4. Never make up features or prices not listed in the knowledge base.
5. Keep responses to 3–5 sentences unless the user asks for more detail.

{kb_context}
"""


def generate_response(state: AgentState) -> AgentState:
    """General-purpose LLM response node for greetings and product/pricing queries."""
    llm = _get_llm()

    system_prompt = _SYSTEM_TEMPLATE.format(kb_context=_KB_CONTEXT)
    lc_messages = [SystemMessage(content=system_prompt)] + _to_lc_messages(state["messages"])

    response = llm.invoke(lc_messages)
    reply = response.content.strip()

    return {
        **state,
        "messages": state["messages"] + [{"role": "assistant", "content": reply}],
    }


# ─────────────────────────────────────────────────────────────────────────────
# ROUTING
# ─────────────────────────────────────────────────────────────────────────────

def route_after_classify(state: AgentState) -> str:
    """Decide which node to call after intent classification."""
    intent = state.get("intent", Intent.OTHER)
    lead_captured = state.get("lead_captured", False)

    if lead_captured:
        # Lead already captured; just chat normally
        return "generate_response"

    if intent == Intent.HIGH_INTENT_LEAD:
        return "collect_lead_info"

    # Check if we're mid-collection (user answered a field question)
    if state.get("awaiting_field") is not None:
        return "collect_lead_info"

    return "generate_response"


def route_after_collect(state: AgentState) -> str:
    """After collecting info, either fire the tool or stay in the graph."""
    lead_info = state.get("lead_info", {})
    if all(f in lead_info for f in FIELD_ORDER):
        return "call_lead_tool"
    return END  # ask for next field; wait for user reply


# ─────────────────────────────────────────────────────────────────────────────
# BUILD GRAPH
# ─────────────────────────────────────────────────────────────────────────────

def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("classify_intent", classify_intent)
    builder.add_node("collect_lead_info", collect_lead_info)
    builder.add_node("call_lead_tool", call_lead_tool)
    builder.add_node("generate_response", generate_response)

    builder.set_entry_point("classify_intent")

    builder.add_conditional_edges(
        "classify_intent",
        route_after_classify,
        {
            "collect_lead_info": "collect_lead_info",
            "generate_response": "generate_response",
        },
    )

    builder.add_conditional_edges(
        "collect_lead_info",
        route_after_collect,
        {
            "call_lead_tool": "call_lead_tool",
            END: END,
        },
    )

    builder.add_edge("call_lead_tool", END)
    builder.add_edge("generate_response", END)

    return builder.compile()
