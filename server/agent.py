# agent.py
from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.googlesearch import GoogleSearchTools
from agno.tools.crawl4ai import Crawl4aiTools
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
        description="You are a helpful assistant with the ability to search the internet for anything, crawl web pages for details and help user with required information.",
        model=Gemini(id="gemini-2.5-flash-preview-04-17"),
        instructions=[
            "Avoid over-talking or repeating information.",
            "Be direct with answers and be polite",
        ],
          tools=[GoogleSearchTools(), Crawl4aiTools(max_length=5000)],
        markdown=True,
        add_datetime_to_instructions=True,
        debug_mode=True,
        storage=agent_storage,
    )