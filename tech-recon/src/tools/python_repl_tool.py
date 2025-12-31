import sys
import logging
import subprocess
import threading
import queue
import os
import atexit
from typing import Any, Annotated, Optional
from strands.types.tools import ToolResult, ToolUse
from src.tools.decorators import log_io

# Thread-local storage for agent context
_thread_local = threading.local()


# Simple logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TOOL_SPEC = {
    "name": "python_repl_tool",
    "description": "Use this to execute python code and do data analysis or calculation. Variables defined in previous calls are preserved. If you want to see the output of a value, you should print it out with `print(...)`. This is visible to the user.",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The python code to execute to do further analysis or calculation."
                }
            },
            "required": ["code"]
        }
    }
}

class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

class PythonREPL:
    """
    Persistent Python REPL that maintains state between calls.
    Uses a persistent subprocess with per-agent namespaces to preserve variables and imports
    while isolating state between different agents.
    """
    # Execution marker to detect when code execution completes
    EXECUTION_MARKER = "__REPL_EXECUTION_COMPLETE_MARKER__"
    
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.stdout_queue: queue.Queue = queue.Queue()
        self.stderr_queue: queue.Queue = queue.Queue()
        self.stdout_thread: Optional[threading.Thread] = None
        self.stderr_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        self._initialize_process()
        # Register cleanup on exit
        atexit.register(self.cleanup)
    
    @staticmethod
    def get_current_agent_name() -> str:
        """Get the current agent name from thread-local storage."""
        return getattr(_thread_local, 'agent_name', 'default')
    
    @staticmethod
    def set_current_agent_name(agent_name: str):
        """Set the current agent name in thread-local storage."""
        _thread_local.agent_name = agent_name
    
    def _initialize_process(self):
        """Initialize the persistent Python subprocess with a persistent namespace."""
        try:
            # Create a Python script that maintains per-agent namespaces
            init_script = f"""
import sys
import io
import traceback
from contextlib import redirect_stdout, redirect_stderr

# Per-agent namespaces - each agent has its own isolated namespace
_namespaces = {{}}

# Marker for execution completion
EXEC_MARKER = "{self.EXECUTION_MARKER}"

def get_namespace(agent_name):
    '''Get or create namespace for an agent.'''
    if agent_name not in _namespaces:
        _namespaces[agent_name] = {{}}
    return _namespaces[agent_name]

while True:
    try:
        # Read agent name first
        agent_name_line = sys.stdin.readline()
        if not agent_name_line:
            sys.exit(0)
        agent_name = agent_name_line.rstrip('\\n')
        
        # Read code from stdin (until newline with just EXEC_MARKER)
        code_lines = []
        while True:
            line = sys.stdin.readline()
            if not line:
                sys.exit(0)
            line = line.rstrip('\\n')
            if line == EXEC_MARKER:
                break
            code_lines.append(line)
        
        if not code_lines:
            continue
            
        code = '\\n'.join(code_lines)
        
        # Get agent-specific namespace
        namespace = get_namespace(agent_name)
        
        # Capture stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Execute code in agent-specific namespace
                exec(compile(code, '<string>', 'exec'), namespace)
        except Exception as e:
            # Print error to stderr
            traceback.print_exc(file=stderr_capture)
        
        # Output results
        stdout_text = stdout_capture.getvalue()
        stderr_text = stderr_capture.getvalue()
        
        if stdout_text:
            print(stdout_text, end='', flush=True)
        if stderr_text:
            print(stderr_text, end='', file=sys.stderr, flush=True)
        
        # Signal completion
        print(EXEC_MARKER, flush=True)
        
    except EOFError:
        sys.exit(0)
    except Exception as e:
        print(f"REPL Error: {{e}}", file=sys.stderr, flush=True)
        print(EXEC_MARKER, flush=True)
"""
            
            # Start Python with the init script
            self.process = subprocess.Popen(
                [sys.executable, "-u", "-c", init_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0,  # Unbuffered
                env=os.environ.copy()
            )
            
            # Start threads to read stdout and stderr
            self.stdout_thread = threading.Thread(
                target=self._read_stream,
                args=(self.process.stdout, self.stdout_queue),
                daemon=True
            )
            self.stderr_thread = threading.Thread(
                target=self._read_stream,
                args=(self.process.stderr, self.stderr_queue),
                daemon=True
            )
            self.stdout_thread.start()
            self.stderr_thread.start()
            
            logger.debug(f"{Colors.BLUE}Python REPL process initialized with persistent namespace{Colors.END}")
        except Exception as e:
            logger.error(f"{Colors.RED}Failed to initialize Python REPL: {e}{Colors.END}")
            self.process = None
    
    def _read_stream(self, stream, output_queue):
        """Read from stream and put into queue."""
        try:
            for line in iter(stream.readline, ''):
                if not line:
                    break
                output_queue.put(line)
        except Exception as e:
            logger.debug(f"Error reading stream: {e}")
        finally:
            output_queue.put(None)  # Sentinel to indicate end
    
    def _clear_queues(self):
        """Clear output queues."""
        while not self.stdout_queue.empty():
            try:
                self.stdout_queue.get_nowait()
            except queue.Empty:
                break
        while not self.stderr_queue.empty():
            try:
                self.stderr_queue.get_nowait()
            except queue.Empty:
                break
    
    def run(self, command, agent_name: Optional[str] = None):
        """Execute Python code in the persistent session with agent-specific namespace.
        
        Args:
            command: Python code to execute
            agent_name: Name of the agent (if None, uses thread-local agent_name or 'default')
        """
        if not self.process or self.process.poll() is not None:
            # Process died, reinitialize
            logger.warning(f"{Colors.YELLOW}Python REPL process died, reinitializing...{Colors.END}")
            self._initialize_process()
            if not self.process:
                return f"Error: Failed to initialize Python REPL process"
        
        # Get agent name from parameter, thread-local, or default
        if agent_name is None:
            agent_name = self.get_current_agent_name()
        
        with self.lock:
            try:
                # Clear previous output
                self._clear_queues()
                
                # Send agent name first, then code, then marker
                self.process.stdin.write(agent_name + '\n')
                code_lines = command.split('\n')
                for line in code_lines:
                    self.process.stdin.write(line + '\n')
                self.process.stdin.write(self.EXECUTION_MARKER + '\n')
                self.process.stdin.flush()
                
                # Collect output until we see the marker
                stdout_lines = []
                stderr_lines = []
                marker_found = False
                timeout = 600  # 10 minutes max
                import time
                start_time = time.time()
                
                while not marker_found and (time.time() - start_time) < timeout:
                    # Check stdout
                    try:
                        line = self.stdout_queue.get(timeout=0.1)
                        if line is None:
                            # Stream ended
                            break
                        line = line.rstrip('\n')
                        if self.EXECUTION_MARKER in line:
                            marker_found = True
                            # Remove marker from output
                            line = line.replace(self.EXECUTION_MARKER, '').strip()
                            if line:
                                stdout_lines.append(line)
                        else:
                            stdout_lines.append(line)
                    except queue.Empty:
                        pass
                    
                    # Check stderr
                    try:
                        line = self.stderr_queue.get_nowait()
                        if line is None:
                            continue
                        stderr_lines.append(line.rstrip('\n'))
                    except queue.Empty:
                        pass
                
                # Get any remaining output
                while not self.stdout_queue.empty():
                    try:
                        line = self.stdout_queue.get_nowait()
                        if line and line is not None:
                            line = line.rstrip('\n')
                            if self.EXECUTION_MARKER not in line:
                                stdout_lines.append(line)
                            else:
                                marker_found = True
                    except queue.Empty:
                        break
                
                while not self.stderr_queue.empty():
                    try:
                        line = self.stderr_queue.get_nowait()
                        if line and line is not None:
                            stderr_lines.append(line.rstrip('\n'))
                    except queue.Empty:
                        break
                
                # Combine results
                stdout_text = '\n'.join(stdout_lines).strip()
                stderr_text = '\n'.join(stderr_lines).strip()
                
                if stderr_text:
                    # If there's stderr, it's likely an error
                    return f"Error: {stderr_text}"
                elif not marker_found:
                    return f"Error: Execution timeout or process died"
                else:
                    return stdout_text if stdout_text else ""
                    
            except Exception as e:
                return f"Exception: {str(e)}"
    
    def cleanup(self):
        """Clean up the subprocess."""
        if self.process:
            try:
                self.process.stdin.close()
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

# Global singleton instance
repl = PythonREPL()

@log_io
def handle_python_repl_tool(code: Annotated[str, "The python code to execute to do further analysis or calculation."], agent_name: Optional[str] = None):
    """
    Use this to execute python code and do data analysis or calculation. Variables defined in previous calls
    by the same agent are preserved. If you want to see the output of a value, you should print it out with 
    `print(...)`. This is visible to the user.
    
    Args:
        code: Python code to execute
        agent_name: Name of the agent (automatically detected from context if not provided)
    """
    print()  # Add newline before log
    
    # Get agent name from parameter or thread-local context
    if agent_name is None:
        agent_name = PythonREPL.get_current_agent_name()
    
    logger.info(f"{Colors.GREEN}===== Executing Python code (agent: {agent_name}) ====={Colors.END}")
    try:
        result = repl.run(code, agent_name=agent_name)
    except BaseException as e:
        error_msg = f"Failed to execute. Error: {repr(e)}"
        logger.debug(f"{Colors.RED}Failed to execute. Error: {repr(e)}{Colors.END}")
        return error_msg

    # Truncate code to first 7 lines for context efficiency
    code_lines = code.split('\n')
    if len(code_lines) > 7:
        code_preview = '\n'.join(code_lines[:7])
        code_summary = f"{code_preview}\n... ({len(code_lines) - 7} more lines omitted)"
    else:
        code_summary = code

    result_str = f"Successfully executed:\n||{code_summary}||{result}"
    logger.info(f"{Colors.GREEN}===== Code execution successful ====={Colors.END}")
    return result_str

# Function name must match tool name
def python_repl_tool(tool: ToolUse, **kwargs: Any) -> ToolResult:
    tool_use_id = tool["toolUseId"]
    code = tool["input"]["code"]

    # Use the existing handle_python_repl_tool function
    result = handle_python_repl_tool(code)

    # Check if execution was successful based on the result string
    if "Failed to execute" in result:
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
