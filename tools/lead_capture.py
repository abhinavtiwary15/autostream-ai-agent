"""
tools/lead_capture.py
Mock lead capture tool for AutoStream agent.
Simulates a CRM API call when a high-intent lead is fully qualified.
"""

import json
import datetime


def mock_lead_capture(name: str, email: str, platform: str) -> dict:
    """
    Mock API function to capture a qualified lead.

    Args:
        name (str): Full name of the prospective customer.
        email (str): Email address of the prospective customer.
        platform (str): Creator platform (e.g., YouTube, Instagram, TikTok).

    Returns:
        dict: A success response simulating a CRM API acknowledgment.
    """
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    lead_id = f"LEAD-{abs(hash(email)) % 100000:05d}"

    response = {
        "status": "success",
        "lead_id": lead_id,
        "message": f"Lead captured successfully: {name}, {email}, {platform}",
        "timestamp": timestamp,
        "data": {
            "name": name,
            "email": email,
            "platform": platform,
            "source": "AutoStream Conversational Agent",
            "plan_interest": "Pro"
        }
    }

    # EXACT output required by assignment brief
    print(f"Lead captured successfully: {name}, {email}, {platform}")

    # Console output as required by the assignment
    print("\n" + "=" * 55)
    print("✅  LEAD CAPTURED SUCCESSFULLY")
    print("=" * 55)
    print(f"  Name     : {name}")
    print(f"  Email    : {email}")
    print(f"  Platform : {platform}")
    print(f"  Lead ID  : {lead_id}")
    print(f"  Time     : {timestamp}")
    print("=" * 55 + "\n")

    return response
