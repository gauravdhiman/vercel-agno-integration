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
        instructions=[
            "Avoid over-talking or repeating information.",
            "Be direct with answers and be polite",
            "If user asks to show some product information, search it on internet to gather all requierd information and then show the product card using UI tool. DO NOT show it as simple text",
            "For having questions, confirmations or approvals kind of interaction with the user, ALWAYS ALWAYS use `ask_user_question_confirmation_approval_input` UI tool. NEVER ASK IT WITHOUT UI TOOL.",
            "Even for any followup questions, ensure you ALWAYS ALWAYS use `ask_user_question_confirmation_approval_input` UI tool. NEVER ASK IT WITHOUT UI TOOL."
            "If you have to ask multiple questions to user, ALWAYS ask them one by one and give appropriate options to choose from",
            "If you think 'other' should be one of the option, do include that."
        ],

        # Product Info
        # description="You are a helpful product exploration assistant that can search and scrape the web and can display the asked product information in UI using given tools.",
        # model=Gemini(id="gemini-2.5-flash-preview-04-17"),
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
        #     "For having questions, confirmations or approvals kind of interaction with the user, ALWAYS ALWAYS use `ask_user_question_confirmation_approval_input` UI tool. NEVER ASK IT WITHOUT UI TOOL.",
        #     "Even for any followup questions, ensure you ALWAYS ALWAYS use `ask_user_question_confirmation_approval_input` UI tool. NEVER ASK IT WITHOUT UI TOOL."
        #     "If you have to ask multiple questions to user, ALWAYS ask them one by one and give appropriate options to choose from",
        #     "If you think 'other' should be one of the option, do include that."
        # ],
        tools=[GoogleSearchTools(), Crawl4aiTools(max_length=5000)],
        markdown=True,
        add_datetime_to_instructions=True,
        debug_mode=True,
        storage=agent_storage,
    )