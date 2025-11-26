
import json
import logging
from src.utils.strands_sdk_utils import strands_utils
from src.prompts.template import apply_prompt_template
from src.utils.common_utils import get_message_from_string

# Tools
from src.tools import coder_agent_tool, reporter_agent_tool, tracker_agent_tool, researcher_agent_tool

# Simple logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    END = '\033[0m'

def log_node_start(node_name: str):
    """Log the start of a node execution."""
    print()  # Add newline before log
    logger.info(f"{Colors.GREEN}===== {node_name} started ====={Colors.END}")

def log_node_complete(node_name: str):
    """Log the completion of a node."""
    print()  # Add newline before log
    logger.info(f"{Colors.GREEN}===== {node_name} completed ====={Colors.END}")

# Global state storage for sharing between nodes
_global_node_states = {}

RESPONSE_FORMAT = "Response from {}:\n\n<response>\n{}\n</response>\n\n*Please execute the next step.*"
FEEDBACK_FORMAT = "Feedback from {}:\n\n<user_feedback>\n{}\n</user_feedback>\n\n"
FULL_PLAN_FORMAT = "Here is full plan :\n\n<full_plan>\n{}\n</full_plan>\n\n*Please consider this to select the next step.*"
CLUES_FORMAT = "Here is clues from {}:\n\n<clues>\n{}\n</clues>\n\n"

async def clarification_node(task=None, **kwargs):
    
    """Coordinator node that communicate with customers."""
    global _global_node_states

    log_node_start("Clarification")

    # Extract user request from task (now passed as dictionary)
    if isinstance(task, dict):
        request = task.get("request", "")
        request_prompt = task.get("request_prompt", request)
    else:
        request = str(task) if task else ""
        request_prompt = request

    agent = strands_utils.get_agent(
        agent_name="clarifier",
        system_prompts=apply_prompt_template(prompt_name="clarifier", prompt_context={}), # apply_prompt_template(prompt_name="task_agent", prompt_context={"TEST": "sdsd"})
        agent_type="claude-sonnet-4", #claude-sonnet-3-7
        enable_reasoning=False,
        prompt_cache_info=(False, None), #(False, None), (True, "default")
        streaming=True,
    )

    # Process streaming response and collect text in one pass
    full_text = ""
    async for event in strands_utils.process_streaming_response_yield(
        agent, request_prompt, agent_name="clarifier", source="clarification_node"):
        if event.get("event_type") == "text_chunk": full_text += event.get("data", "")
    response = {"text": full_text}
    # follow_up_questions = json.loads(response["text"])

    # Store data directly in shared global storage
    if 'shared' not in _global_node_states: _global_node_states['shared'] = {}
    shared_state = _global_node_states['shared']

    # Update shared global state
    shared_state['messages'] = agent.messages
    shared_state['request'] = request
    shared_state['request_prompt'] = request_prompt
    # shared_state['follow_up_questions'] = follow_up_questions["questions"]

    # Build and update history
    if 'history' not in shared_state: 
        shared_state['history'] = []
    shared_state['history'].append({"agent":"clarifier", "message": response["text"]})

    log_node_complete("Coordinator")

    # Return response only
    return response

async def planner_node(task=None, **kwargs):
    """Planner node for Part 1 - uses planner_part1.md prompt."""
    log_node_start("Planner-1")
    global _global_node_states

    # Initialize shared state if not exists
    if 'shared' not in _global_node_states:
        _global_node_states['shared'] = {}

    shared_state = _global_node_states['shared']

    # Extract user request from task
    if isinstance(task, dict):
        request = task.get("request", "")
        request_prompt = task.get("request_prompt", request)
    else:
        request = str(task) if task else ""
        request_prompt = request

    # Get request from shared state if available
    if not request and shared_state:
        request = shared_state.get("request", "")
        request_prompt = shared_state.get("request_prompt", request)

    if not request:
        logger.warning("No request found in task or shared state")
        return {"text": "No request available"}

    # Create agent with planner_part1.md prompt
    agent = strands_utils.get_agent(
        agent_name="planner-1",
        system_prompts=apply_prompt_template(
            prompt_name="planner_part1",
            prompt_context={"USER_REQUEST": request}
        ),
        agent_type="claude-sonnet-4-5",
        enable_reasoning=True,
        prompt_cache_info=(False, None),
        streaming=True,
    )

    # Initialize history if not exists
    if 'history' not in shared_state:
        shared_state['history'] = []

    # Get full_plan and messages from shared state if available
    full_plan = shared_state.get("full_plan", "")
    messages = shared_state.get("messages", [])

    # Build message based on whether we have previous messages
    if messages and len(messages) > 0:
        message = '\n\n'.join([messages[-1]["content"][-1]["text"], FULL_PLAN_FORMAT.format(full_plan)])
    else:
        message = request_prompt if full_plan == "" else '\n\n'.join([request_prompt, FULL_PLAN_FORMAT.format(full_plan)])

    # Process streaming response and collect text in one pass
    full_text = ""
    async for event in strands_utils.process_streaming_response_yield(
        agent, message, agent_name="planner-1", source="planner_node"
    ):
        if event.get("event_type") == "text_chunk":
            full_text += event.get("data", "")
    response = {"text": full_text}

    # Update shared global state
    shared_state['messages'] = [get_message_from_string(role="user", string=response["text"], imgs=[])]
    shared_state['full_plan'] = response["text"]
    shared_state['request'] = request
    shared_state['request_prompt'] = request_prompt
    shared_state['history'].append({"agent": "planner-1", "message": response["text"]})

    log_node_complete("Planner-1")
    return response

async def planner_node_2(task=None, **kwargs):
    """Planner node for Part 2 - uses part_2_template.md prompt."""
    log_node_start("Planner-2")
    global _global_node_states

    # Initialize shared state if not exists
    if 'shared' not in _global_node_states:
        _global_node_states['shared'] = {}

    shared_state = _global_node_states['shared']

    # Extract user request from task
    if isinstance(task, dict):
        request = task.get("request", "")
        request_prompt = task.get("request_prompt", request)
    else:
        request = str(task) if task else ""
        request_prompt = request

    # Get request from shared state if available
    if not request and shared_state:
        request = shared_state.get("request", "")
        request_prompt = shared_state.get("request_prompt", request)

    if not request:
        logger.warning("No request found in task or shared state")
        return {"text": "No request available"}

    # Create agent with part_2_template prompt
    agent = strands_utils.get_agent(
        agent_name="planner-2",
        system_prompts=apply_prompt_template(
            prompt_name="part_2_template",
            prompt_context={"USER_REQUEST": request}
        ),
        agent_type="claude-sonnet-4-5",
        enable_reasoning=True,
        prompt_cache_info=(False, None),
        streaming=True,
    )

    # Initialize history if not exists
    if 'history' not in shared_state:
        shared_state['history'] = []

    # Get full_plan and messages from shared state if available
    full_plan = shared_state.get("full_plan", "")
    messages = shared_state.get("messages", [])

    # Build message based on whether we have previous messages
    if messages and len(messages) > 0:
        message = '\n\n'.join([messages[-1]["content"][-1]["text"], FULL_PLAN_FORMAT.format(full_plan)])
    else:
        message = request_prompt if full_plan == "" else '\n\n'.join([request_prompt, FULL_PLAN_FORMAT.format(full_plan)])

    # Process streaming response and collect text in one pass
    full_text = ""
    async for event in strands_utils.process_streaming_response_yield(
        agent, message, agent_name="planner-2", source="planner_node_2"
    ):
        if event.get("event_type") == "text_chunk":
            full_text += event.get("data", "")
    response = {"text": full_text}

    # Update shared global state
    shared_state['messages'] = [get_message_from_string(role="user", string=response["text"], imgs=[])]
    shared_state['full_plan'] = response["text"]
    shared_state['request'] = request
    shared_state['request_prompt'] = request_prompt
    shared_state['history'].append({"agent": "planner-2", "message": response["text"]})

    log_node_complete("Planner-2")
    return response

async def router_planner_node(task=None, **kwargs):
    """Router node that calls planner with part1 or part2 prompt based on user input."""
    log_node_start("Router_Planner")
    global _global_node_states

    # Initialize shared state if not exists
    if 'shared' not in _global_node_states:
        _global_node_states['shared'] = {}

    shared_state = _global_node_states['shared']

    # Extract user request and input from task
    if isinstance(task, dict):
        request = task.get("request", "")
        request_prompt = task.get("request_prompt", request)
        user_input = task.get("user_input", "part1")  # Default to part1
    else:
        request = str(task) if task else ""
        request_prompt = request
        user_input = "part1"  # Default to part1

    # Get request from shared state if available
    if not request and shared_state:
        request = shared_state.get("request", "")
        request_prompt = shared_state.get("request_prompt", request)

    if not request:
        logger.warning("No request found in task or shared state")
        return {"text": "No request available"}

    # Determine which prompt to use based on user_input (part1 or part2)
    # No inference needed - user_input is always "part1" or "part2"
    if user_input.lower() == "part2":
        prompt_name = "planner_part2"
        agent_name = "planner-2"
        agent_type = "claude-sonnet-4-5"
        logger.info(f"{Colors.YELLOW}[Using part_2_template prompt for planner-2]{Colors.END}")
    else:  # part1 is default
        prompt_name = "planner_part1"
        agent_name = "planner-1"
        agent_type = "claude-sonnet-4-5"
        logger.info(f"{Colors.YELLOW}[Using planner_part1 prompt for planner-1]{Colors.END}")

    # Create agent with appropriate prompt
    agent = strands_utils.get_agent(
        agent_name=agent_name,
        system_prompts=apply_prompt_template(
            prompt_name=prompt_name,
            prompt_context={"USER_REQUEST": request}
        ),
        agent_type=agent_type,
        enable_reasoning=True,
        prompt_cache_info=(False, None),
        streaming=True,
    )

    # Initialize history if not exists
    if 'history' not in shared_state:
        shared_state['history'] = []

    # Get full_plan and messages from shared state if available
    full_plan = shared_state.get("full_plan", "")
    messages = shared_state.get("messages", [])

    # Build message based on whether we have previous messages
    if messages and len(messages) > 0:
        message = '\n\n'.join([messages[-1]["content"][-1]["text"], FULL_PLAN_FORMAT.format(full_plan)])
    else:
        message = request_prompt if full_plan == "" else '\n\n'.join([request_prompt, FULL_PLAN_FORMAT.format(full_plan)])

    # Process streaming response and collect text in one pass
    full_text = ""
    async for event in strands_utils.process_streaming_response_yield(
        agent, message, agent_name=agent_name, source="router_planner_node"
    ):
        if event.get("event_type") == "text_chunk":
            full_text += event.get("data", "")
    response = {"text": full_text}

    # Update shared global state
    shared_state['messages'] = [get_message_from_string(role="user", string=response["text"], imgs=[])]
    shared_state['full_plan'] = response["text"]
    shared_state['request'] = request
    shared_state['request_prompt'] = request_prompt
    shared_state['user_input'] = user_input  # Store for future reference
    shared_state['is_part1'] = (user_input.lower() == "part1")  # Set is_part1 flag for artifact cleanup
    shared_state['history'].append({"agent": agent_name, "message": response["text"]})

    log_node_complete("Router_Planner")
    return response

async def supervisor_node(task=None, **kwargs):
    """Supervisor node that decides which agent should act next."""
    log_node_start("Supervisor")
    global _global_node_states

    # task and kwargs parameters are unused - supervisor relies on global state
    # Extract shared state from global storage
    shared_state = _global_node_states.get('shared', None)

    if not shared_state:
        logger.warning("No shared state found in global storage")
        return None, {"text": "No shared state available"}

    # Count researcher calls from history
    history = shared_state.get("history", [])
    researcher_call_count = sum(1 for entry in history if entry.get("agent") == "researcher")

    # Build context information about researcher usage
    researcher_usage_info = f"\n\n[RESEARCHER USAGE]: Researcher has been called {researcher_call_count} time(s) out of maximum 3 allowed. "
    if researcher_call_count >= 3:
        researcher_usage_info += "**LIMIT REACHED - DO NOT CALL RESEARCHER AGAIN.**"
    else:
        researcher_usage_info += f"You can call researcher {3 - researcher_call_count} more time(s)."

    agent = strands_utils.get_agent(
        agent_name="supervisor",
        system_prompts=apply_prompt_template(prompt_name="supervisor", prompt_context={}),
        agent_type="claude-sonnet-4-5", # claude-sonnet-3-7
        enable_reasoning=False,
        prompt_cache_info=(True, "default"),  # enable prompt caching for reasoning agent
        tools=[coder_agent_tool, reporter_agent_tool, tracker_agent_tool, researcher_agent_tool],
        streaming=True,
    )

    clues, full_plan, messages = shared_state.get("clues", ""), shared_state.get("full_plan", ""), shared_state["messages"]
    message = '\n\n'.join([messages[-1]["content"][-1]["text"], FULL_PLAN_FORMAT.format(full_plan), clues, researcher_usage_info])

    # Process streaming response and collect text in one pass
    full_text = ""
    async for event in strands_utils.process_streaming_response_yield(
        agent, message, agent_name="supervisor", source="supervisor_node"
    ):
        if event.get("event_type") == "text_chunk": full_text += event.get("data", "")
    response = {"text": full_text}

    # Update shared global state
    shared_state['history'].append({"agent":"supervisor", "message": response["text"]})

    log_node_complete("Supervisor")
    logger.info("Workflow completed")
    # Return response only
    return response


    



   
# #########################################################

# def should_handoff_to_planner():
#     """Check if coordinator requested handoff to planner."""

#     # Check coordinator's response for handoff request
#     global _global_node_states
#     shared_state = _global_node_states.get('shared', {})
#     history = shared_state.get('history', [])

#     # Look for coordinator's last message
#     for entry in reversed(history):
#         if entry.get('agent') == 'coordinator':
#             message = entry.get('message', '')
#             return 'handoff_to_planner' in message

#     return False

# async def coordinator_node(task=None, **kwargs):
    
#     """Coordinator node that communicate with customers."""
#     global _global_node_states

#     log_node_start("Coordinator")

#     # Extract user request from task (now passed as dictionary)
#     if isinstance(task, dict):
#         request = task.get("request", "")
#         request_prompt = task.get("request_prompt", request)
#     else:
#         request = str(task) if task else ""
#         request_prompt = request

#     agent = strands_utils.get_agent(
#         agent_name="coordinator",
#         system_prompts=apply_prompt_template(prompt_name="coordinator", prompt_context={}), # apply_prompt_template(prompt_name="task_agent", prompt_context={"TEST": "sdsd"})
#         agent_type="claude-sonnet-4", # claude-sonnet-3-5-v-2, claude-sonnet-3-7
#         enable_reasoning=False,
#         prompt_cache_info=(False, None), #(False, None), (True, "default")
#         streaming=True,
#     )

#     # Process streaming response and collect text in one pass
#     full_text = ""
#     async for event in strands_utils.process_streaming_response_yield(
#         agent, request_prompt, agent_name="coordinator", source="coordinator_node"
#     ):
#         if event.get("event_type") == "text_chunk": 
#             full_text += event.get("data", "")
#     response = {"text": full_text}

#     # Store data directly in shared global storage
#     if 'shared' not in _global_node_states: _global_node_states['shared'] = {}
#     shared_state = _global_node_states['shared']

#     # Update shared global state
#     shared_state['messages'] = agent.messages
#     shared_state['request'] = request
#     shared_state['request_prompt'] = request_prompt

#     # Build and update history
#     if 'history' not in shared_state: 
#         shared_state['history'] = []
#     shared_state['history'].append({"agent":"coordinator", "message": response["text"]})

#     log_node_complete("Coordinator")
#     # Return response only
#     return response

# async def planner_node(task=None, **kwargs):

#     """Planner node that generates detailed plans for task execution."""
#     log_node_start("Planner")
#     global _global_node_states

#     # Extract shared state from global storage
#     shared_state = _global_node_states.get('shared', None)

#     # Get request from shared state (task parameter not used in planner)
#     request = shared_state.get("request", "") if shared_state else ""

#     if not shared_state:
#         logger.warning("No shared state found in global storage")
#         return None, {"text": "No shared state available"}

#     agent = strands_utils.get_agent(
#         agent_name="planner",
#         system_prompts=apply_prompt_template(prompt_name="planner", prompt_context={"USER_REQUEST": request}),
#         agent_type="claude-sonnet-4", # claude-sonnet-3-5-v-2, claude-sonnet-3-7
#         enable_reasoning=True,
#         prompt_cache_info=(False, None),  # enable prompt caching for reasoning agent, (False, None), (True, "default")
#         streaming=True,
#     )

#     full_plan, messages = shared_state.get("full_plan", ""), shared_state["messages"]
#     message = '\n\n'.join([messages[-1]["content"][-1]["text"], FULL_PLAN_FORMAT.format(full_plan)])

#     # Process streaming response and collect text in one pass
#     full_text = ""
#     async for event in strands_utils.process_streaming_response_yield(
#         agent, message, agent_name="planner", source="planner_node"
#     ):
#         if event.get("event_type") == "text_chunk": full_text += event.get("data", "")
#     response = {"text": full_text}

#     # Update shared global state
#     shared_state['messages'] = [get_message_from_string(role="user", string=response["text"], imgs=[])]
#     shared_state['full_plan'] = response["text"]
#     shared_state['history'].append({"agent":"planner", "message": response["text"]})

#     log_node_complete("Planner")
#     # Return response only
#     return response

# async def supervisor_node(task=None, **kwargs):
#     """Supervisor node that decides which agent should act next."""
#     log_node_start("Supervisor")
#     global _global_node_states

#     # task and kwargs parameters are unused - supervisor relies on global state
#     # Extract shared state from global storage
#     shared_state = _global_node_states.get('shared', None)

#     if not shared_state:
#         logger.warning("No shared state found in global storage")
#         return None, {"text": "No shared state available"}

#     agent = strands_utils.get_agent(
#         agent_name="supervisor",
#         system_prompts=apply_prompt_template(prompt_name="supervisor", prompt_context={}),
#         agent_type="claude-sonnet-4", # claude-sonnet-3-5-v-2, claude-sonnet-3-7
#         enable_reasoning=False,
#         prompt_cache_info=(True, "default"),  # enable prompt caching for reasoning agent
#         tools=[coder_agent_tool, reporter_agent_tool, tracker_agent_tool, validator_agent_tool],  # Add coder, reporter, tracker and validator agents as tools
#         streaming=True,
#     )

#     clues, full_plan, messages = shared_state.get("clues", ""), shared_state.get("full_plan", ""), shared_state["messages"]
#     message = '\n\n'.join([messages[-1]["content"][-1]["text"], FULL_PLAN_FORMAT.format(full_plan), clues])

#     # Process streaming response and collect text in one pass
#     full_text = ""
#     async for event in strands_utils.process_streaming_response_yield(
#         agent, message, agent_name="supervisor", source="supervisor_node"
#     ):
#         if event.get("event_type") == "text_chunk": full_text += event.get("data", "")
#     response = {"text": full_text}

#     # Update shared global state
#     shared_state['history'].append({"agent":"supervisor", "message": response["text"]})

#     log_node_complete("Supervisor")
#     logger.info("Workflow completed")
#     # Return response only
#     return response
