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

LangGraph was chosen over AutoGen because it provides **explicit, inspectable state management** via a typed `StateGraph`. Every node receives a snapshot of the full conversation state and returns an updated one — there are no implicit side effects or opaque agent loops. This makes the lead-qualification flow (which must sequence name → email → platform without skipping or double-firing the tool) easy to reason about, test, and debug.

### State Management

The `AgentState` TypedDict holds:

- `messages` — full chat history as `[{role, content}]` dicts, providing multi-turn memory
- `intent` — the classified intent label for the latest user turn
- `lead_info` — incrementally populated dict (`name`, `email`, `platform`)
- `lead_captured` — boolean guard that prevents the mock API from firing twice
- `awaiting_field` — tracks which field we are currently asking for, so the agent correctly interprets plain answers like "John Smith" as a name rather than re-classifying them

### Graph Nodes and Routing

```
User message
     │
     ▼
classify_intent ──► high_intent / mid-collection ──► collect_lead_info
     │                                                      │
     │ (greeting / inquiry)                   all fields?  │
     ▼                                             Yes ▼    No ▼
generate_response                           call_lead_tool  END (ask next field)
     │                                             │
     └──────────────────────────────────────────► END
```

1. **classify_intent** — LLM zero-shot classifies user message into one of five buckets.
2. **collect_lead_info** — Step-by-step field collector. Stores the answered field, advances `awaiting_field` to the next missing one, and appends a question to the message history.
3. **call_lead_tool** — Fires `mock_lead_capture()` and appends a success message. Guarded by `lead_captured` flag.
4. **generate_response** — Standard RAG-augmented response. The full KB is injected into the system prompt on every call (context-window RAG).

### RAG Approach

AutoStream's knowledge base is a structured JSON file (`knowledge_base/autostream_kb.json`). At startup it is rendered into a human-readable text block and injected into the LLM system prompt. This approach is appropriate for a small, stable KB (< 2 KB). For a larger or frequently-updated KB, a vector database (Chroma, Pinecone) with embedding-based retrieval would be the correct upgrade path.

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

**Interactive mode:**
```bash
python main.py
```

**Scripted demo (7-turn walkthrough):**
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
