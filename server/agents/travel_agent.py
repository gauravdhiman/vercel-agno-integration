# travel_agent.py
import sys
from pathlib import Path

# Add parent directory to Python path for imports
sys.path.append(str(Path(__file__).parent.parent))

from agno.agent import Agent
from agno.models.google import Gemini
# from agno.models.ollama import Ollama
from agno.models.openrouter import OpenRouter
from agno.tools.googlesearch import GoogleSearchTools
from agno.tools.crawl4ai import Crawl4aiTools
from agno.storage.sqlite import SqliteStorage
from agno.tools.mcp import MCPTools  # Keep this import
from tools.browser_tool import AgnoBrowserToolkit

# import asyncio # Not strictly needed here anymore for MCPTools init
from pathlib import Path # Keep if folder_path logic remains, though it's better in main.py now

agent_storage = SqliteStorage(
    table_name="agent_sessions",
    db_file="tmp/persistent_memory.db", # Ensure 'tmp' directory exists or adjust path
)

# Modified: create_agent now accepts mcp_tools
def create_agent(mcp_tools: MCPTools) -> Agent:
    """
    Creates and configures the Agno agent instance.
    Args:
        mcp_tools (MCPTools): An initialized MCPTools instance.
    Returns:
        Agent: Configured Agno agent instance
    """
    # folder_path logic can be removed from here if MCPTools is initialized outside
    # If you still need folder_path for other things, keep it:
    # folder_path = f"{str(Path(__file__).parent.resolve())}/tmp_fs"
    # print(f"Folder path used by agent (if any other part needs it): {folder_path}")

    return Agent(
        name="MyAgnoAgent",
        description="You are a helpful travel assistant with the ability to browse the internet for doing research and planning trips. You can also crawl web pages to get more information.",
        instructions=[
            "Avoid over-talking or repeating information.",
            "Ask only very limited and relevant question, if required. DO NOT frustrate the user by asking many questions",
            "DO NOT make up things, always do research and find the information using browser tools.",
            "Always use Browser tools for browsing the internet to do your research about trips, itenary, places, hotels, flights etc.",
            "Be detailed in your research and prepare a comprehensive travel trip.",
            "Always include some tips and recommendations at the end of the plan.",
            "Provide the references and sources for the information you provide.",
            "If you are stuck in browsing and need help like captcha solving or login, ask the user for help",
            "Never say no and try your best to research and plan trips. If you need some missing information, ask user in advance",
            """How to:
            1. Always first create a detailed plan on how you are going to research and plan the trip. This plan should include the tools you are going to use, what you plan to do at each step.
            2. Start by writing the detailed plan in todo.md file. Each step in the plan should be like `[ ] Step description`. Show the prepared plan to user to keep the user updated.
            3. Do extensive deep research about the transportation options, places to visit, hotels, flights, activities etc. using browser tools (not google search tool) to visit multiple websites and gather all the required information.
            4. After each step plan is executed to your satisfaction, update the todo.md file to keep track of your progress. Reread the todo.md file to know the next step to be executed and continue till all the steps are completed. Also mark the completed steps as done and show the latest todo.md file to the user to keep the user updated, but do not expect user confirmation.
            5. As you go through each step, show the relevant information to user to keep the updated.
            6. Keep on working unless the whole plan is not completed. Complete the plan systematically from top to bottom.
            7. If you are asked to change the plan, update the todo.md file accordingly and then show it to the user and proceed.
            8. Once you are satisfied with plan execution and got all the steps completed, compile your findings / research to create travel_plan.md file with all required details. Final travel plan should include the itinerary, places to visit, hotels details with prices, flights details with airlines, prices and timings, activities to do, restaurants to eat, shopping options, sightseeing, tips and recommendations etc.
            9. Finally present the contents of travel_plan.md file to the user without ```markdown``` syntax.
            """
        ],
        model=Gemini(id="gemini-2.5-flash-preview-05-20"), # Corrected model ID if it was a typo
        # model=Gemini(id="gemma-3-12b-it"), # Corrected model ID if it was a typo
        # model=OpenRouter(id="google/gemini-2.5-flash-preview-05-20"), # Corrected model ID if it was a typo
        # retries=5,
        tools=[mcp_tools, GoogleSearchTools(), Crawl4aiTools(max_length=10000)], # Use the passed mcp_tools
        markdown=True,
        add_datetime_to_instructions=True,
        debug_mode=True,
        storage=agent_storage,
    )

if __name__ == "__main__":
    agent = create_agent(None)
    agent.print_response("Plan a trip to japan from phoenix for a family of 4 (2 kids - 10 and 14 years). Do a deep research on internet for planning the trip. Include the detailed itenary with details of transportation, accommodation, hotels, food, sight seeing, other recommendations, tips etc. For doing deep research use browser tools to visit multiple websites and get info.")
