# agent.py
from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.googlesearch import GoogleSearchTools
from agno.tools.crawl4ai import Crawl4aiTools
from agno.storage.sqlite import SqliteStorage
from tools.browser_tool import AgnoBrowserToolkit

from agno.tools.mcp import MCPTools

agent_storage = SqliteStorage(
    table_name="agent_sessions",
    db_file="tmp/persistent_memory.db",
)

def create_agent(mcp_tools: MCPTools) -> Agent:
    """
    Creates and configures the Agno agent instance.
    Returns:
        Agent: Configured Agno agent instance
    """
    return Agent(
        name="MyAgnoAgent",
        description="You are a helpful assistant with the ability to search the internet for anything, crawl web pages for details and help user with required information.",
        instructions=[
            "Avoid over-talking or repeating information.",
            "Be direct with answers and be polite",
            "If user asks to show some product information, search it on internet to gather all requierd information and then show the product card using UI tool. DO NOT show it as simple text",
            "For having questions, confirmations or approvals kind of interaction with the user, ALWAYS ALWAYS use `ask_user_confirmation` UI tool. NEVER ASK IT WITHOUT UI TOOL.",
            "Even for any followup questions, ensure you ALWAYS ALWAYS use `ask_user_confirmation` UI tool. NEVER ASK IT WITHOUT UI TOOL."
            "If you have to ask multiple questions to user, ALWAYS ask them one by one and give appropriate options to choose from",
            "If you think 'other' should be one of the option, do include that."
            """Use browser tool for anything related to internet browsing and taking actions on websites. Use it for:
            1. Searching and researching about anything
            2. Navigating to any website
            3. Taking action on websites like clicking buttons, filling forms, etc.
            4. For reading social media platforms and posting to them like Twitter, LinkedIn, etc.
            5. If use authentication is required, ask user for help.
            """
        ],

        # Product Info
        # description="You are a helpful product exploration assistant that can search and scrape the web and can display the asked product information in UI using given tools.",
        model=Gemini(id="gemini-2.5-flash-preview-05-20"),
        retries=5,
        # instructions=[
        #     "Avoid over-talking or repeating information.",
        #     "Be direct with answers and be polite",
        #     "If user asks to show some product information, search it on internet to gather all requierd information and then show the product card using UI tool. DO NOT show it as simple text",
        # ],

        # Q&A
        # description="You are a helpful assistant that asks the user prefrences one by one. With your questions, try to understand the user, likings, dislikings, prefrences and build a personality profile.",
        # instructions=[
        #     "Avoid over-talking or repeating information.",
        #     "Be direct with answers and be polite",
        #     "For having questions, confirmations or approvals kind of interaction with the user, ALWAYS ALWAYS use `ask_user_confirmation` UI tool. NEVER ASK IT WITHOUT UI TOOL.",
        #     "Even for any followup questions, ensure you ALWAYS ALWAYS use `ask_user_confirmation` UI tool. NEVER ASK IT WITHOUT UI TOOL."
        #     "If you have to ask multiple questions to user, ALWAYS ask them one by one and give appropriate options to choose from",
        #     "If you think 'other' should be one of the option, do include that."
        # ],
        tools=[Crawl4aiTools(max_length=10000), AgnoBrowserToolkit()],
        markdown=True,
        add_datetime_to_instructions=True,
        debug_mode=True,
        storage=agent_storage,
    )