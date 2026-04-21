"""
agent/logic.py
Pure Python helper functions with no LangChain/LangGraph dependencies.
These are imported by both graph.py (at runtime) and tests (without needing
the full framework installed).
"""

import re
from tools.lead_capture import mock_lead_capture

# ── Field ordering and prompts ────────────────────────────────────────────────

FIELD_ORDER = ["name", "email", "platform"]

FIELD_QUESTIONS = {
    "name": "Great! To get you started with AutoStream Pro, could you share your **full name**?",
    "email": "Perfect! What **email address** should we use for your account?",
    "platform": "Awesome! Which creator platform are you primarily on? (e.g., YouTube, Instagram, TikTok, Facebook…)",
}

_EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_KNOWN_PLATFORMS = ["youtube", "instagram", "tiktok", "facebook", "twitter", "linkedin", "twitch"]


def extract_field(field: str, text: str) -> str | None:
    """
    Try to extract a specific lead field value from free-form user text.

    Returns the extracted string or None if extraction fails.
    """
    text = text.strip()
    if field == "email":
        match = _EMAIL_RE.search(text)
        return match.group(0) if match else None
    if field == "name":
        if "@" not in text and len(text.split()) <= 5 and len(text) > 1:
            return text.title()
        return None
    if field == "platform":
        lower = text.lower()
        for p in _KNOWN_PLATFORMS:
            if p in lower:
                return p.capitalize()
        if len(text) > 1:
            return text.strip().title()
        return None
    return None


def collect_lead_step(lead_info: dict, awaiting_field: str | None, user_text: str) -> dict:
    """
    Given current lead_info, the field we were awaiting, and the latest user text:
    - Store the answered field (if extractable)
    - Return updated lead_info and the next awaiting_field (or None if complete)

    Returns a dict:
      {
        "lead_info": {...},
        "awaiting_field": str | None,   # None means all fields collected
        "assistant_message": str        # the question / confirmation to send
      }
    """
    lead_info = dict(lead_info)

    # Store answer to the awaited field
    if awaiting_field and awaiting_field not in lead_info:
        value = extract_field(awaiting_field, user_text)
        if value:
            lead_info[awaiting_field] = value

    # Find next missing field
    next_field = next((f for f in FIELD_ORDER if f not in lead_info), None)

    if next_field is None:
        # All collected — build confirmation
        msg = (
            f"Thank you, **{lead_info['name']}**! I have everything I need. "
            f"I'll set up your AutoStream Pro account and send the details to "
            f"**{lead_info['email']}**. We'll make sure it's optimised for "
            f"**{lead_info['platform']}** creators. Hang tight while I register you now… 🚀"
        )
    else:
        msg = FIELD_QUESTIONS[next_field]

    return {
        "lead_info": lead_info,
        "awaiting_field": next_field,
        "assistant_message": msg,
    }


def fire_lead_capture(lead_info: dict) -> dict:
    """
    Call mock_lead_capture() and return the API response.
    Caller is responsible for checking all fields are present and
    that the lead hasn't been captured already.
    """
    return mock_lead_capture(
        name=lead_info["name"],
        email=lead_info["email"],
        platform=lead_info["platform"],
    )
