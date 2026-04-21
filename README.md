# AutoStream Conversational AI Agent

> **Assignment Project for ServiceHive / Inflx ML Internship**
> Built by: [Your Name]

A production-quality, LangGraph-based conversational AI agent that handles product inquiries, detects purchase intent, and captures leads for **AutoStream** — a fictional AI-powered video editing SaaS for content creators.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [How to Run Locally](#how-to-run-locally)
4. [Project Structure](#project-structure)
5. [WhatsApp Deployment via Webhooks](#whatsapp-deployment-via-webhooks)
6. [Running Tests](#running-tests)

---

## Project Overview

The agent can:

| Capability | Description |
|---|---|
| **Intent Detection** | Classifies every message as greeting / product inquiry / pricing inquiry / high-intent lead |
| **RAG Knowledge Retrieval** | Answers pricing & feature questions from a local JSON knowledge base |
| **Lead Qualification** | Collects name → email → platform in a structured multi-turn flow |
| **Tool Execution** | Calls `mock_lead_capture()` exactly once, only after all three fields are gathered |
| **State Memory** | Persists full conversation context across 5–6+ turns via LangGraph state |

---

## Architecture

### Why LangGraph?

LangGraph was selected for its **explicit, inspectable state management**. Unlike traditional agent loops that can be unpredictable, a `StateGraph` ensures that every transition is deterministic. This is essential for the lead-qualification funnel, where the agent must collect specific data (name, email, platform) in a logical sequence. Using a graph structure makes the logic easy to visualize, test, and adapt for real-world production deployments.

### State Management

The conversation state is maintained using a typed `AgentState` object which persists across all turns:

- **`messages`**: The full history of interactions, providing the agent with robust memory.
- **`intent`**: The LLM's classification of the current user goal.
- **`lead_info`**: An incrementally populated dictionary of qualified user details.
- **`lead_captured`**: A state-guard ensuring the mock API is only called once per session.
- **`awaiting_field`**: Tracks the current step in the qualification flow.

### RAG Strategy

AutoStream's knowledge base is stored in a structured JSON document. At runtime, the agent retrieves this data and injects it into the system prompt as a grounded context block. This ensures Aria’s responses are strictly grounded in official policy and pricing, preventing hallucinations and ensuring the agent remains a reliable source of information.

---

## How to Run Locally

### Prerequisites

- Python 3.9 or higher
- A Google Gemini API key ([get one here at Google AI Studio](https://aistudio.google.com/app/apikey))

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/autostream-agent.git
cd autostream-agent
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set your API key

**Option A — environment variable (recommended):**
```bash
export GOOGLE_API_KEY=AIzaSy...
```

**Option B — .env file:**
```bash
echo "GOOGLE_API_KEY=AIzaSy..." > .env
```
The agent uses `python-dotenv` to pick this up automatically via the `load_dotenv()` call in `main.py`.

### 5. Run the agent

**Option A — Premium Web UI (Recommended for Demo):**
```bash
python app.py
```
Then open `http://localhost:8000` in your browser. This provides a stunning modern interface for interacting with Aria.

**Option B — Interactive CLI:**
```bash
python main.py
```

**Option C — Scripted CLI Demo:**
```bash
python main.py --demo
```

---

## Project Structure

```
autostream-agent/
├── main.py                          # CLI entry point
├── requirements.txt
├── README.md
│
├── knowledge_base/
│   └── autostream_kb.json           # Pricing, features, policies, FAQs
│
├── agent/
│   ├── __init__.py
│   ├── state.py                     # AgentState TypedDict + Intent enum
│   ├── rag.py                       # KB loader + context builder
│   └── graph.py                     # LangGraph nodes + routing
│
├── tools/
│   ├── __init__.py
│   └── lead_capture.py              # mock_lead_capture() function
│
└── tests/
    ├── __init__.py
    └── test_agent.py                # pytest unit tests
```

---

## WhatsApp Deployment via Webhooks

To deploy this agent on WhatsApp you would use the **WhatsApp Business Cloud API** (Meta) with a webhook-based integration. Here is the architecture:

### High-level flow

```
WhatsApp User
     │  (sends message)
     ▼
Meta Cloud API ──► POST /webhook ──► Your FastAPI / Flask server
                                           │
                                     Retrieve session state
                                     from Redis / DB by wa_id
                                           │
                                     graph.invoke(state)
                                           │
                                     Persist updated state
                                           │
                                     POST reply to Meta API
                                           │
                                           ▼
                                     WhatsApp User (receives reply)
```

### Implementation steps

1. **Webhook server** — Create a FastAPI or Flask endpoint at `POST /webhook`. Meta will POST a JSON payload containing the sender's phone number (`wa_id`) and message text.

2. **Verify webhook** — Meta first calls `GET /webhook?hub.mode=subscribe&hub.verify_token=...` to verify ownership. Return the `hub.challenge` value.

3. **Session state persistence** — Since the agent is stateless between HTTP requests, store `AgentState` in **Redis** keyed by `wa_id`. On each webhook call: load state → `graph.invoke()` → save updated state.

4. **Send reply** — Use the Meta Graph API (`POST https://graph.facebook.com/v19.0/<PHONE_NUMBER_ID>/messages`) with a Bearer token to send the agent's response back to the user.

5. **Deployment** — Host the webhook server on any cloud provider (Railway, Render, GCP Cloud Run). It must be HTTPS-accessible for Meta's webhook validation.

### Minimal FastAPI snippet

```python
from fastapi import FastAPI, Request
import redis, json
from agent.graph import build_graph

app = FastAPI()
r = redis.Redis()
graph = build_graph()

@app.post("/webhook")
async def webhook(req: Request):
    body = await req.json()
    msg = body["entry"][0]["changes"][0]["value"]["messages"][0]
    wa_id = msg["from"]
    text  = msg["text"]["body"]

    raw = r.get(wa_id)
    state = json.loads(raw) if raw else initial_state()
    state["messages"].append({"role": "user", "content": text})
    state = graph.invoke(state)
    r.set(wa_id, json.dumps(state))

    reply = last_assistant_message(state)
    send_whatsapp_message(wa_id, reply)   # calls Meta API
    return {"status": "ok"}
```

This approach supports unlimited concurrent WhatsApp conversations with independent, persistent state per user.

---

## Running Tests

```bash
pytest tests/ -v
```

All tests run without an API key (they test state logic and the local KB — no LLM calls needed).

---

## Evaluation Checklist

| Criterion | Implementation |
|---|---|
| Agent reasoning & intent detection | `classify_intent` node — zero-shot LLM classification |
| Correct use of RAG | `build_kb_context()` injected into system prompt; answers grounded in KB |
| Clean state management | `AgentState` TypedDict passed immutably between LangGraph nodes |
| Proper tool calling logic | `call_lead_tool` guarded by `lead_captured` + all-fields check |
| Code clarity & structure | Modular packages: `agent/`, `tools/`, `knowledge_base/`, `tests/` |
| Real-world deployability | WhatsApp webhook design documented; Redis session persistence explained |
