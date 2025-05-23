# job-agent.py
from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.googlesearch import GoogleSearchTools
from agno.tools.crawl4ai import Crawl4aiTools
from agno.storage.sqlite import SqliteStorage
from tools.browser_tool import AgnoBrowserToolkit

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
        description="You are a helpful job search and application assistant with the ability to search the internet for jobs, crawl web pages and even have access to browser tool for browsing internet.",
        instructions=[
            "Ask only very limited and relevant question, if required. DO NOT frustrate the user by asking many questions",
            "You job is to search and apply for jobs on behalf of the user. Use Browser tools for browsing and applying for jobs",
            "Prefer browser over search tool, whereever possible",
            "If you are stuck in browsing and need help like captcha solving or login, as user for help",
            "Never say no and try your best to apply for jobs of your own. If you need some information about skills, roles etc, ask user in advance"
        ],

        # Product Info
        # description="You are a helpful product exploration assistant that can search and scrape the web and can display the asked product information in UI using given tools.",
        model=Gemini(id="gemini-2.5-flash-preview-04-17"),
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
        tools=[GoogleSearchTools(), Crawl4aiTools(max_length=5000), AgnoBrowserToolkit()],
        markdown=True,
        add_datetime_to_instructions=True,
        debug_mode=True,
        storage=agent_storage,
    )