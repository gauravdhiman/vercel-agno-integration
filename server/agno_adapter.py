# agno_adapter.py
import asyncio
import json
import logging
from typing import AsyncGenerator, Any, Dict, List, Optional, Union
from uuid import uuid4

# --- Pydantic ---
from pydantic import BaseModel, Field

# --- Agno Imports ---
from agno.agent import Agent
from agno.models.message import Message as AgnoMessage
from agno.run.response import RunEvent, RunResponse
from agno.run.team import TeamRunResponse # Keep for potential future use
from agno.tools.function import Function

# --- Vercel AI SDK Data Stream Protocol Type IDs ---
TEXT_PART = "0"
DATA_PART = "2"
ERROR_PART = "3"
ANNOTATION_PART = "8"
TOOL_CALL_PART = "9"
TOOL_RESULT_PART = "a"
FINISH_MESSAGE_PART = "d"
REASONING_PART = "g"
SOURCE_PART = "h"
# ... add other type IDs as needed ...

logger = logging.getLogger("AgnoVercelAdapter")
logging.basicConfig(level=logging.INFO) # Or DEBUG for more verbosity

class AgnoVercelAdapter:
    """
    Adapts the output stream of an Agno Agent to the
    Vercel AI SDK Data Stream Protocol, using a proxy tool pattern
    to trigger frontend actions.
    """
    PROXY_TOOL_NAME = "call_frontend_action"

    def __init__(self, agent: Agent):
        if not isinstance(agent, Agent): # Simplified to just Agent for clarity
            raise TypeError("Input must be an instance of agno.Agent")
        self.agent = agent
        # Ensure the proxy tool is registered with the agent instance immediately
        self._ensure_proxy_tool_registered()

    def _ensure_proxy_tool_registered(self):
        """Ensures the proxy tool is part of the agent's tools."""
        proxy_tool_func = self._get_proxy_tool_definition()
        if not self.agent.tools:
            self.agent.tools = []

        # Check if a tool with the same name already exists
        if not any(getattr(t, 'name', None) == self.PROXY_TOOL_NAME for t in self.agent.tools):
            self.agent.tools.append(proxy_tool_func)
            logger.info(f"Registered proxy tool '{self.PROXY_TOOL_NAME}' with the agent.")
            # Optionally force model update if Agno requires it after adding tools
            # self.agent.update_model(session_id="init_session")
        else:
             logger.debug(f"Proxy tool '{self.PROXY_TOOL_NAME}' already registered.")


    @staticmethod
    def _format_vercel_data_stream(type_id: str, data: Any) -> str:
        """Formats data according to the Vercel AI SDK Data Stream Protocol."""
        try:
            if type_id in [TEXT_PART, ERROR_PART, REASONING_PART]:
                 payload = json.dumps(str(data))
            else:
                 payload = json.dumps(data, default=str)
        except TypeError as e:
            logger.error(f"Serialization error for type {type_id}: {data}. Error: {e}")
            payload = json.dumps({"error": "Serialization failed", "details": str(e)})
            type_id = ERROR_PART
        return f"{type_id}:{payload}\n"

    # --- Proxy Tool Definition and Handler ---

    def _get_proxy_tool_definition(self) -> Function:
        """Creates the definition for the proxy tool Agno will call."""
        return Function(
            name=self.PROXY_TOOL_NAME,
            description="Use this function to request an action or UI update on the frontend application. Specify the exact frontend action name and necessary arguments.",
            parameters={
                "type": "object",
                "properties": {
                    "frontend_tool_name": {
                        "type": "string",
                        "description": "The specific name of the action the frontend should perform (e.g., 'show_confirmation_modal', 'display_product_card')."
                    },
                    "frontend_tool_args": {
                        "type": "object",
                        "description": "A JSON object containing the arguments required by the frontend action."
                    }
                },
                "required": ["frontend_tool_name", "frontend_tool_args"]
            },
            entrypoint=self._handle_proxy_tool_call,
            show_result=False, # Don't show dummy result
            stop_after_tool_call=False # Agent should continue after proxy call
        )

    async def _handle_proxy_tool_call(self, frontend_tool_name: str, frontend_tool_args: Dict[str, Any]) -> str:
        """
        Executed by Agno when the agent calls PROXY_TOOL_NAME.
        Returns a simple confirmation string *to the Agno agent*.
        The actual frontend trigger happens in _agno_to_vercel_stream.
        """
        logger.info(f"Proxy tool '{self.PROXY_TOOL_NAME}' called by agent for frontend action: '{frontend_tool_name}'")
        # This simple string is the result fed back into the Agno agent's internal loop
        return f"Frontend action '{frontend_tool_name}' requested."

    # --- Stream Translation Logic ---

    async def _agno_to_vercel_stream(
        self,
        agno_response_stream: AsyncGenerator[RunResponse, None]
    ) -> AsyncGenerator[bytes, None]:
        """
        Translates the Agno RunResponse stream to Vercel AI SDK Data Stream,
        intercepting the proxy tool start event.
        """
        async for agno_response in agno_response_stream:
            event = agno_response.event
            content = agno_response.content
            tools = agno_response.tools
            metrics = agno_response.metrics
            citations = agno_response.citations
            thinking = agno_response.thinking

            # --- Intercept Proxy Tool Start ---
            if event == RunEvent.tool_call_started and tools:
                proxy_tool_called = False
                for tool_call in tools:
                    # Check if this specific tool call is our proxy tool
                    if tool_call.get("tool_name") == self.PROXY_TOOL_NAME:
                        proxy_tool_called = True
                        logger.debug(f"Intercepted start of proxy tool call: {tool_call.get('tool_call_id')}")

                        # Extract the *actual* frontend details from the proxy tool's arguments
                        proxy_args_raw = tool_call.get("tool_args", {})
                        frontend_tool_name = proxy_args_raw.get("frontend_tool_name", "unknown_frontend_action")
                        frontend_tool_args = proxy_args_raw.get("frontend_tool_args", {})
                        proxy_tool_call_id = tool_call.get("tool_call_id", f"proxy_{uuid4()}") # Use Agno's ID

                        # Format the Vercel Type 9 message for the *frontend* action
                        vercel_tool_call_request = {
                            "toolCallId": proxy_tool_call_id, # Use the proxy's ID for tracking
                            "toolName": frontend_tool_name,
                            "args": frontend_tool_args,
                        }
                        yield self._format_vercel_data_stream(TOOL_CALL_PART, vercel_tool_call_request).encode("utf-8")
                        # We have now translated this event, skip further processing of it below
                        break # Assuming only one tool call per event for simplicity here

                if proxy_tool_called:
                    continue # Skip the rest of the loop for this specific Agno event

                # Handle start of *other* (backend) tools if necessary
                # else:
                #     # Decide how to represent backend tool calls in Vercel stream
                #     # e.g., yield DATA_PART or ignore
                #     pass

            # --- Handle Other Agno Events ---
            elif event == RunEvent.run_response and content:
                yield self._format_vercel_data_stream(TEXT_PART, content).encode("utf-8")

            # We explicitly IGNORE the completion event for the proxy tool itself
            elif event == RunEvent.tool_call_completed and tools:
                 if not any(tool.get("tool_name") == self.PROXY_TOOL_NAME for tool in tools):
                     # Handle completion of *other* backend tools if needed
                     pass # e.g., yield DATA_PART

            elif event == RunEvent.run_error and content:
                 yield self._format_vercel_data_stream(ERROR_PART, str(content)).encode("utf-8")

            elif event == RunEvent.run_completed:
                finish_data: Dict[str, Any] = {"finishReason": "stop"}
                if metrics:
                     finish_data["usage"] = {
                         "promptTokens": int(metrics.get("input_tokens", 0)),
                         "completionTokens": int(metrics.get("output_tokens", 0)),
                         "totalTokens": int(metrics.get("total_tokens", 0)),
                     }
                     if finish_data["usage"]["totalTokens"] == 0:
                         finish_data["usage"]["totalTokens"] = finish_data["usage"]["promptTokens"] + finish_data["usage"]["completionTokens"]
                yield self._format_vercel_data_stream(FINISH_MESSAGE_PART, finish_data).encode("utf-8")

            elif event == RunEvent.reasoning_step and content: # Example
                 if isinstance(content, str):
                      yield self._format_vercel_data_stream(REASONING_PART, content).encode("utf-8")

            elif thinking:
                 yield self._format_vercel_data_stream(REASONING_PART, thinking).encode("utf-8")

            # ... map other events as needed ...

            await asyncio.sleep(0.01) # Yield control

    async def stream_response(
        self,
        message: str,
        messages: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        # Accept other kwargs that might be needed by agent.arun
        **kwargs: Any
    ) -> AsyncGenerator[bytes, None]:
        """
        Runs the Agno agent and yields the response stream formatted for Vercel AI SDK.
        Parses incoming tool results and passes them to the agent.
        """
        # --- Ensure Proxy Tool is Registered ---
        # (This is now done in __init__ or can be ensured here if adapter is short-lived)
        self._ensure_proxy_tool_registered()
        # Force model update if necessary after registration (depends on Agno implementation)
        # self.agent.update_model(session_id=session_id or "temp_session")

        # --- Prepare Messages & Extract Tool Results ---
        agno_input_message = message
        tool_results_for_agno = []
        agno_message_history = [] # Build history for Agno if needed

        for msg in messages:
            # Convert Vercel message format to Agno Message if necessary for history
            # agno_msg = AgnoMessage(role=msg['role'], content=msg['content'], ...)
            # agno_message_history.append(agno_msg)

            if msg.get("role") == "tool":
                 # Map Vercel tool result back to Agno's expected format
                 # This assumes Agno needs a list of dicts with 'tool_call_id' and 'content'/'result'
                 tool_results_for_agno.append({
                     "tool_call_id": msg.get("tool_call_id"),
                     "content": msg.get("content") # Or "result" depending on Agno
                 })
                 logger.debug(f"Passing tool result back to Agno: {msg.get('tool_call_id')}")

        if tool_results_for_agno:
             kwargs["tool_results"] = tool_results_for_agno # Add to agent kwargs

        # --- Start the Agno agent stream ---
        # Pass the latest message and potentially the history + tool results
        agno_stream_generator = await self.agent.arun(
            message=agno_input_message,
            # messages=agno_message_history, # Pass history if agent uses it
            session_id=session_id,
            user_id=user_id,
            stream=True,
            stream_intermediate_steps=True, # Important to catch tool events
            **kwargs # Includes tool_results if any
        )

        # --- Yield the translated stream ---
        async for chunk in self._agno_to_vercel_stream(agno_stream_generator):
            yield chunk