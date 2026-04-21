import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Optional
from agent.graph import build_graph
from agent.state import AgentState
from dotenv import load_dotenv

# Load env vars
load_dotenv()

app = FastAPI(title="AutoStream AI Agent")

# Build the LangGraph
graph = build_graph()

# In-memory session storage (simulating a DB for the demo)
sessions: Dict[str, AgentState] = {}

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_demo"

class ChatResponse(BaseModel):
    reply: str
    intent: str
    lead_info: dict
    lead_captured: bool

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

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session_id = req.session_id
    
    # Initialize or retrieve session state
    if session_id not in sessions:
        sessions[session_id] = _initial_state()
    
    state = sessions[session_id]
    
    # Append user message
    state["messages"].append({"role": "user", "content": req.message})
    
    # Check for empty message
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    try:
        # Run through the graph
        updated_state = graph.invoke(state)
        sessions[session_id] = updated_state
        
        reply = _last_assistant_message(updated_state)
        
        return ChatResponse(
            reply=reply or "I'm not sure how to respond to that.",
            intent=updated_state.get("intent", "other"),
            lead_info=updated_state.get("lead_info", {}),
            lead_captured=updated_state.get("lead_captured", False)
        )
    except Exception as e:
        print(f"Error in graph execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reset")
async def reset(req: ChatRequest):
    sessions[req.session_id] = _initial_state()
    return {"status": "reset"}

# Mount static files
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
