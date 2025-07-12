# main.py
from dotenv import load_dotenv
load_dotenv()
import os
from contextlib import asynccontextmanager
from pathlib import Path # <-- Add this import

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# --- Adapter and Agno Imports ---
from agno_adapter import AgnoVercelAdapter
from agno.tools.mcp import MCPTools # <-- Add this import

from agents.generic_agent import create_agent
# from agents.job_agent import create_agent
# from agents.travel_agent import create_agent
from frontend_tool_schemas import frontend_tools

# --- Initialize Agent and Adapter ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup event to run initialization code."""
    # Define folder_path for MCPTools here
    # Ensure the 'server/tmp_fs' directory exists relative to where main.py is run,
    # or use an absolute path.
    # Assuming main.py is in 'server/' directory:
    base_dir = Path(__file__).parent.resolve()
    folder_path = base_dir / "tmp_fs"
    # Ensure the directory exists, create if not (optional, good practice)
    folder_path.mkdir(parents=True, exist_ok=True)
    print(f"MCPTools filesystem path: {folder_path}")

    async with MCPTools(
        f"npx -y @modelcontextprotocol/server-filesystem {str(folder_path)}"
    ) as mcp_tools_instance: # Renamed for clarity
        print("MCPTools initialized.")
        my_actual_agent = create_agent(mcp_tools_instance) # Pass mcp_tools_instance
        print("Agent created.")

        adapter = AgnoVercelAdapter(
            agent=my_actual_agent,
            frontend_tool_schemas=frontend_tools
        )
        app.state.adapter = adapter # store adapter in app state.
        print(f"Application startup: MCPTools, Agent, and adapter initialized. app.state.adapter: {app.state.adapter}")
        yield
    # This block below (after yield) will be executed on application shutdown
    print("Application shutdown: MCPTools resources (if any managed by 'async with' outside the 'yield') will be released.")


# --- FastAPI Setup ---
app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- API Endpoints ---
@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint for Docker healthcheck."""
    return {"status": "ok"}

class ChatRequest(BaseModel):
    messages: List[Dict[str, Any]]
    sessionId: Optional[str] = None
    userId: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

@app.post("/api/v1/agent/run")
async def handle_chat(request: ChatRequest):
    session_id = request.sessionId or request.data.get("sessionId") if request.data else None
    user_id = request.userId or request.data.get("userId") if request.data else None

    print(f"Streaming response with session_id: {session_id}, user_id: {user_id}")
    vercel_stream = app.state.adapter.stream_response(
        messages=request.messages or [],
        session_id=session_id,
        user_id=user_id
    )
    return StreamingResponse(vercel_stream, media_type="text/event-stream")

# --- Run with Uvicorn (for local testing) ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("API_PORT", "8000")), reload=True)