# agent.py
from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.googlesearch import GoogleSearchTools
from agno.storage.sqlite import SqliteStorage

agent_storage = SqliteStorage(
    table_name="agent_sessions",
    db_file="tmp/persistent_memory.db",
)

def create_agent() -> Agent:
    """
    Creates and configures the Agno agent instance.
    Returns:
        Agent: Configured Agno agent instance
    """
    return Agent(
        name="MyAgnoAgent",
        model=Gemini(id="gemini-2.5-flash-preview-04-17"),
        instructions="You are a helpful assistant",
        tools=[GoogleSearchTools()],
        markdown=True,
        add_datetime_to_instructions=True,
        debug_mode=True,
        storage=agent_storage,
    )