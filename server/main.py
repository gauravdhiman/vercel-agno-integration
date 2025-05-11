# main.py
from dotenv  import load_dotenv
load_dotenv()
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# --- Adapter and Agno Imports ---
from agno_adapter import AgnoVercelAdapter
from agno.agent import Agent
from agno.team import Team
from agno.models.google import Gemini

from agent import create_agent
from frontend_tool_schemas import frontend_tools

# --- FastAPI Setup ---
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Initialize Agent and Adapter ---

my_actual_agent = create_agent()

adapter = AgnoVercelAdapter(
    agent=my_actual_agent,
    frontend_tool_schemas=frontend_tools
)

# --- API Endpoints ---
@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint for Docker healthcheck."""
    return {"status": "ok"}

class ChatRequest(BaseModel):
    messages: List[Dict[str, Any]]
    # Include other fields potentially sent by useChat
    sessionId: Optional[str] = None
    userId: Optional[str] = None
    data: Optional[Dict[str, Any]] = None # For custom data from useChat options

@app.post("/api/v1/agent/run")
async def handle_chat(request: ChatRequest):
    """Handles chat requests from the Vercel AI SDK UI."""
    print(f"Received chat request: {request}")  # Debug logging
    # last_message = request.messages[-1] if request.messages else None
    # user_input = last_message.get("content", "") if last_message else ""
    # print(f"Processing message: {user_input}")  # Debug logging

    # Extract session_id and user_id (example: sent via custom data or specific field)
    session_id = request.sessionId or request.data.get("sessionId") if request.data else None
    user_id = request.userId or request.data.get("userId") if request.data else None

    # --- Pass the full message history to the adapter ---
    # The adapter can decide how to use it, or pass it to the agent if needed
    # Also pass any other relevant data from the request body if needed
    print(f"Streaming response with session_id: {session_id}, user_id: {user_id}")  # Debug logging
    vercel_stream = adapter.stream_response(
        messages=request.messages or [], # Pass the full history
        session_id=session_id,
        user_id=user_id
        # Add any other kwargs needed by your agent's arun method
    )

    return StreamingResponse(vercel_stream, media_type="text/event-stream")

# --- Run with Uvicorn (for local testing) ---
if __name__ == "__main__":
    import uvicorn
    # Make sure to reload the adapter code if you change it
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("API_PORT", "8000")), reload=True)