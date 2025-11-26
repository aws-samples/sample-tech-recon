import logging
import asyncio
from typing import Any, Annotated
from strands.types.tools import ToolResult, ToolUse
from src.utils.strands_sdk_utils import strands_utils
from src.prompts.template import apply_prompt_template
from src.utils.common_utils import get_message_from_string, start_periodic_status, stop_periodic_status
from src.tools import python_repl_tool, bash_tool, tavily_tool, crawl_tool


# Simple logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TOOL_SPEC = {
    "name": "researcher_agent_tool",
    "description": "Perform internet research using web search and crawling capabilities. This tool provides access to a researcher agent that can search the web for real-time information, crawl detailed content from URLs, analyze research findings, and save structured research results to files. The researcher focuses on gathering comprehensive information for the current research step only.",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The research task or question that needs to be investigated by the researcher agent."
                }
            },
            "required": ["task"]
        }
    }
}

RESPONSE_FORMAT = "Response from {}:\n\n<response>\n{}\n</response>\n\n*Please execute the next step.*"
FULL_PLAN_FORMAT = "Here is full plan :\n\n<full_plan>\n{}\n</full_plan>\n\n*Please consider this to select the next step.*"
CLUES_FORMAT = "Here is clues from {}:\n\n<clues>\n{}\n</clues>\n\n"

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    END = '\033[0m'

def handle_researcher_agent_tool(task: Annotated[str, "The research task or question that needs to be investigated by the researcher agent."]):
    """
    Perform internet research using web search and crawling capabilities.

    This tool provides access to a researcher agent that can:
    - Search the web for real-time information using Tavily
    - Crawl detailed content from specific URLs
    - Analyze and synthesize research findings
    - Save structured research results to './artifacts/{artifacts}/research_info.txt'

    Args:
        task: The research task or question that needs to be investigated

    Returns:
        The structured research findings and analysis
    """
    print()  # Add newline before log
    logger.info(f"\n{Colors.GREEN}Researcher Agent Tool starting task{Colors.END}")

    # Start periodic status output
    start_periodic_status("researcher", interval_seconds=60)

    try:
        # Try to extract shared state from global storage
        from src.graph.nodes import _global_node_states
        shared_state = _global_node_states.get('shared', None)

        if not shared_state:
            logger.warning("No shared state found")
            stop_periodic_status("researcher")
            return "Error: No shared state available"

        request_prompt, full_plan = shared_state.get("request_prompt", ""), shared_state.get("full_plan", "")
        clues, messages = shared_state.get("clues", ""), shared_state.get("messages", [])
        artifact_folder = shared_state.get("artifact_folder", "./artifacts/")  # Get part-specific folder
        part1_folder = shared_state.get("part1_folder", "./artifacts/part1")  # For Part2 reference

        # Create researcher agent with specialized tools using consistent pattern
        researcher_agent = strands_utils.get_agent(
            agent_name="researcher",
            system_prompts=apply_prompt_template(
                prompt_name="researcher",
                prompt_context={
                    "USER_REQUEST": request_prompt,
                    "FULL_PLAN": full_plan,
                    "ARTIFACT_FOLDER": artifact_folder,
                    "PART1_FOLDER": part1_folder
                }
            ),
            agent_type="claude-sonnet-4-5", #claude-sonnet-3-7, claude-sonnet-4
            enable_reasoning=False,
            prompt_cache_info=(True, "default"),  # reasoning agent uses prompt caching
            tools=[tavily_tool, python_repl_tool, bash_tool, crawl_tool],
            streaming=True  # Enable streaming for consistency
        )

        # Prepare message with context if available
        message = '\n\n'.join([messages[-1]["content"][-1]["text"], clues])

        # Process streaming response and collect text in one pass
        async def process_researcher_stream():
            full_text = ""
            async for event in strands_utils.process_streaming_response_yield(
                researcher_agent, message, agent_name="researcher", source="researcher_tool"
            ):
                if event.get("event_type") == "text_chunk": full_text += event.get("data", "")
            return {"text": full_text}

        response = asyncio.run(process_researcher_stream())
        result_text = response['text']
    finally:
        # Always stop periodic status when done
        stop_periodic_status("researcher")

    # # Original code - unlimited clues growth (commented out to prevent token overflow)
    # # Update clues
    # clues = '\n\n'.join([clues, CLUES_FORMAT.format("researcher", response["text"])])

    # New code - Update clues with size limit to prevent token overflow
    new_clue = CLUES_FORMAT.format("researcher", response["text"])

    # Keep only the last 3 clues to prevent unlimited growth
    clues_list = clues.split(CLUES_FORMAT.format("", "").split("</clues>")[0]) if clues else []
    clues_list = [c for c in clues_list if c.strip()]  # Remove empty strings
    clues_list.append(new_clue)

    # Keep only last 3 agent responses in clues
    if len(clues_list) > 3:
        clues_list = clues_list[-3:]

    clues = '\n\n'.join(clues_list)

    # Update history
    history = shared_state.get("history", [])
    history.append({"agent":"researcher", "message": response["text"]})

    # Update shared state with reset messages (only keep last interaction)
    shared_state['messages'] = [get_message_from_string(role="user", string=RESPONSE_FORMAT.format("researcher", response["text"]), imgs=[])]
    shared_state['clues'] = clues
    shared_state['history'] = history

    logger.info(f"\n{Colors.GREEN}Researcher Agent Tool completed successfully{Colors.END}")
    return result_text

# Function name must match tool name
def researcher_agent_tool(tool: ToolUse, **_kwargs: Any) -> ToolResult:
    tool_use_id = tool["toolUseId"]
    task = tool["input"]["task"]

    # Use the existing handle_researcher_agent_tool function
    result = handle_researcher_agent_tool(task)

    # Check if execution was successful based on the result string
    if "Error in researcher agent tool" in result or "Error: No shared state" in result:
        return {
            "toolUseId": tool_use_id,
            "status": "error",
            "content": [{"text": result}]
        }
    else:
        return {
            "toolUseId": tool_use_id,
            "status": "success",
            "content": [{"text": result}]
        }
