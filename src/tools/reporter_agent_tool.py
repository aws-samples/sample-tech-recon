import logging
import asyncio
from typing import Any, Annotated
from strands.types.tools import ToolResult, ToolUse
from src.utils.strands_sdk_utils import strands_utils
from src.prompts.template import apply_prompt_template
from src.utils.common_utils import get_message_from_string, start_periodic_status, stop_periodic_status

from src.tools import python_repl_tool, bash_tool
from strands_tools import file_read

# Simple logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TOOL_SPEC = {
    "name": "reporter_agent_tool",
    "description": "Generate comprehensive reports based on analysis results using a specialized reporter agent. This tool provides access to a reporter agent that can read analysis results from artifacts, create structured reports with visualizations, and generate output in multiple formats (HTML, PDF, Markdown).",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The reporting task or instruction for generating the report (e.g., 'Create a comprehensive analysis report', 'Generate PDF report with all findings')."
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
    END = '\033[0m'

def handle_reporter_agent_tool(_task: Annotated[str, "The reporting task or instruction for generating the report."]):
    """
    Generate comprehensive reports based on analysis results using a specialized reporter agent.

    This tool provides access to a reporter agent that can:
    - Read analysis results from artifacts directory
    - Create structured reports with executive summaries, key findings, and detailed analysis
    - Generate reports in multiple formats (HTML, PDF, Markdown)
    - Include visualizations and charts in reports
    - Process accumulated analysis results from all_results.txt

    Args:
        task: The reporting task or instruction for generating the report

    Returns:
        The generated report content and confirmation of file creation
    """
    print()  # Add newline before log
    logger.info(f"\n{Colors.GREEN}Reporter Agent Tool starting{Colors.END}")

    # Start periodic status output
    start_periodic_status("reporter", interval_seconds=60)

    try:
        # Try to extract shared state from global storage
        from src.graph.nodes import _global_node_states
        shared_state = _global_node_states.get('shared', None)

        if not shared_state:
            logger.warning("No shared state found")
            stop_periodic_status("reporter")
            return "Error: No shared state available"

        request_prompt, full_plan = shared_state.get("request_prompt", ""), shared_state.get("full_plan", "")
        clues, messages = shared_state.get("clues", ""), shared_state.get("messages", [])
        artifact_folder = shared_state.get("artifact_folder", "./artifacts/")  # Get part-specific folder
        part1_folder = shared_state.get("part1_folder", "./artifacts/part1")  # For Part2 reference
        user_input = shared_state.get("user_input", "part1")  # Get user input to determine part1 or part2

        # Determine which prompt to use based on user_input (part1 or part2)
        if user_input.lower() == "part2":
            prompt_name = "reporter_part2"
            agent_name = "reporter-2"
            logger.info(f"\n{Colors.GREEN}[Using reporter_part2 prompt for reporter-2]{Colors.END}")
        else:  # part1 is default
            prompt_name = "reporter_part1"
            agent_name = "reporter-1"
            logger.info(f"\n{Colors.GREEN}[Using reporter_part1 prompt for reporter-1]{Colors.END}")

        # Create reporter agent with specialized tools using consistent pattern
        reporter_agent = strands_utils.get_agent(
            agent_name=agent_name,
            system_prompts=apply_prompt_template(
                prompt_name=prompt_name,
                prompt_context={
                    "USER_REQUEST": request_prompt,
                    "FULL_PLAN": full_plan,
                    "ARTIFACT_FOLDER": artifact_folder,
                    "PART1_FOLDER": part1_folder
                }
            ),
            agent_type="claude-sonnet-4-5", # claude-sonnet-3-5-v-2, claude-sonnet-3-7
            enable_reasoning=False,
            prompt_cache_info=(True, "default"), # reasoning agent uses prompt caching
            tools=[python_repl_tool, bash_tool, file_read],
            streaming=True  # Enable streaming for consistency
        )

        # Prepare message with context if available
        message = '\n\n'.join([messages[-1]["content"][-1]["text"], clues])

        # Process streaming response and collect text in one pass
        async def process_reporter_stream():
            full_text = ""
            async for event in strands_utils.process_streaming_response_yield(
                reporter_agent, message, agent_name=agent_name, source="reporter_tool"
            ):
                if event.get("event_type") == "text_chunk": full_text += event.get("data", "")
            return {"text": full_text}

        response = asyncio.run(process_reporter_stream())
        result_text = response['text']
    finally:
        # Always stop periodic status when done
        stop_periodic_status("reporter")

    # # Original code - unlimited clues growth (commented out to prevent token overflow)
    # # Update clues
    # clues = '\n\n'.join([clues, CLUES_FORMAT.format(agent_name, response["text"])])

    # New code - Update clues with size limit to prevent token overflow
    new_clue = CLUES_FORMAT.format(agent_name, response["text"])

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
    history.append({"agent": agent_name, "message": response["text"]})

    # Update shared state with reset messages (only keep last interaction)
    shared_state['messages'] = [get_message_from_string(role="user", string=RESPONSE_FORMAT.format(agent_name, response["text"]), imgs=[])]
    shared_state['clues'] = clues
    shared_state['history'] = history

    logger.info(f"\n{Colors.GREEN}{agent_name} Agent Tool completed{Colors.END}")
    return result_text

# Function name must match tool name
def reporter_agent_tool(tool: ToolUse, **_kwargs: Any) -> ToolResult:
    tool_use_id = tool["toolUseId"]
    task = tool["input"]["task"]
    
    # Use the existing handle_reporter_agent_tool function
    result = handle_reporter_agent_tool(task)
    
    # Check if execution was successful based on the result string
    if "Error in reporter agent tool" in result:
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