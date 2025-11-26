"""
Web Application for Tech Recon Project
Web interface supporting real-time log streaming and file downloads
"""

from flask import Flask, render_template, jsonify, send_file, request, Response
from flask_socketio import SocketIO, emit
import asyncio
import threading
import os
import shutil
import zipfile
import io
from datetime import datetime
import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import from main.py
from main import graph_streaming_execution
from src.utils.strands_sdk_utils import strands_utils

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tech-recon-secret-key-2025'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for static files
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Disable caching for all responses
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# Global state
execution_state = {
    'running': False,
    'logs': [],
    'current_part': None,
    'reasoning_buffer': ''  # Buffer for accumulating reasoning chunks
}


class WebLogger:
    """Logger that captures terminal output and sends it to websocket - only complete lines"""

    def __init__(self, socketio_instance):
        self.socketio = socketio_instance
        self.terminal = sys.stdout
        self.current_line_buffer = ""  # Buffer for current line being built

    def write(self, message):
        """Override write method - only send complete lines (those ending with newline)"""
        # Always write to terminal immediately
        self.terminal.write(message)
        # Do NOT flush terminal to allow better buffering

        # Add to buffer
        self.current_line_buffer += message

        # Only send when we have newlines
        if '\n' in self.current_line_buffer:
            # Split by newlines
            lines = self.current_line_buffer.split('\n')

            # All lines except the last are complete
            for line in lines[:-1]:
                if line.strip():  # Only send non-empty lines
                    log_entry = {
                        'timestamp': datetime.now().isoformat(),
                        'message': line,
                        'type': 'info',
                        'category': 'text'
                    }
                    execution_state['logs'].append(log_entry)
                    self.socketio.emit('log', log_entry)

            # Keep the last part (incomplete line) in buffer
            self.current_line_buffer = lines[-1]

    def flush(self):
        """Flush any remaining buffer"""
        self.terminal.flush()

        # Send any remaining buffered content as a complete line
        if self.current_line_buffer.strip():
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'message': self.current_line_buffer,
                'type': 'info',
                'category': 'text'
            }
            execution_state['logs'].append(log_entry)
            self.socketio.emit('log', log_entry)
            self.current_line_buffer = ""


def process_event_for_web(event, socketio_instance):
    """Function to send events to websocket - Shows reasoning, tool use, tool result, and text chunks

    This function processes and displays:
    - Text chunks (agent responses, INFO logs)
    - Reasoning events (buffered and sent on sentence boundaries)
    - Tool use events
    - Tool result events
    All other events are ignored.
    """
    if not event:
        return

    if event.get("event_type") == "text_chunk":
        # Output text chunks directly to stdout (captured by WebLogger)
        text_data = event.get('data', '')
        if text_data:
            print(text_data, end='')

    elif event.get("event_type") == "reasoning":
        # Accumulate reasoning chunks and only send on sentence boundaries
        reasoning_text = event.get('reasoning_text', '')
        if reasoning_text:
            execution_state['reasoning_buffer'] += reasoning_text

            # Check if we have a sentence ending (., !, ?, or newline)
            # Or if buffer is getting too long (> 200 chars), send it anyway
            buffer = execution_state['reasoning_buffer']

            # Find the last sentence boundary
            last_period = max(buffer.rfind('.'), buffer.rfind('!'), buffer.rfind('?'), buffer.rfind('\n'))

            if last_period != -1 or len(buffer) > 200:
                # Send everything up to and including the sentence boundary
                if last_period != -1:
                    to_send = buffer[:last_period + 1]
                    execution_state['reasoning_buffer'] = buffer[last_period + 1:]
                else:
                    # Buffer too long, send everything
                    to_send = buffer
                    execution_state['reasoning_buffer'] = ''

                # Output to stdout (captured by WebLogger)
                print(to_send, end='')

    elif event.get("event_type") == "tool_use":
        # Skip tool_use events - don't display them
        pass

    elif event.get("event_type") == "tool_result":
        tool_name = event.get("tool_name", "unknown")

        # Skip bash_tool results - don't display them
        if tool_name == "bash_tool":
            return

        output = event.get("output", "")

        # Limit output length
        if len(output) > 500:
            output = output[:500] + "..."

        log_data = {
            'timestamp': datetime.now().isoformat(),
            'message': f"[TOOL RESULT - {tool_name}]\n{output}",
            'type': 'event',
            'category': 'tool_result'
        }
        execution_state['logs'].append(log_data)
        socketio_instance.emit('log', log_data)


async def run_graph_execution(user_query, socketio_instance):
    """Handle graph execution asynchronously"""

    # Save original stdout
    original_stdout = sys.stdout

    try:
        execution_state['running'] = True
        execution_state['current_part'] = user_query
        execution_state['logs'] = []
        execution_state['reasoning_buffer'] = ''  # Reset reasoning buffer

        socketio_instance.emit('status', {'status': 'running', 'part': user_query})

        # Emit initial planner running status
        socketio_instance.emit('log', {
            'timestamp': datetime.now().isoformat(),
            'message': '=== Planner Agent Started ===',
            'type': 'info',
            'category': 'system'
        })

        # Redirect stdout to WebLogger to capture print() statements
        web_logger = WebLogger(socketio_instance)
        sys.stdout = web_logger

        payload = {"user_query": user_query}

        # Process events: show reasoning, tool_use, tool_result, and text_chunk
        async for event in graph_streaming_execution(payload):
            if event:
                event_type = event.get("event_type")

                # Process reasoning, tool_use, tool_result, and text_chunk
                if event_type in ["reasoning", "tool_use", "tool_result", "text_chunk"]:
                    process_event_for_web(event, socketio_instance)

            await asyncio.sleep(0.001)  # Much faster processing for quicker response

        # Flush any remaining reasoning buffer
        if execution_state['reasoning_buffer']:
            print(execution_state['reasoning_buffer'], end='')
            execution_state['reasoning_buffer'] = ''

        # Flush the logger to ensure all buffered print() content is sent
        web_logger.flush()

        socketio_instance.emit('status', {'status': 'completed', 'part': user_query})
        socketio_instance.emit('log', {
            'timestamp': datetime.now().isoformat(),
            'message': f'\n=== {user_query} Execution Completed ===',
            'type': 'success',
            'category': 'system'
        })

    except Exception as e:
        error_msg = f"Error during execution: {str(e)}"
        socketio_instance.emit('log', {
            'timestamp': datetime.now().isoformat(),
            'message': error_msg,
            'type': 'error',
            'category': 'error'
        })
        socketio_instance.emit('status', {'status': 'error', 'error': str(e)})

    finally:
        # Restore original stdout
        sys.stdout = original_stdout
        execution_state['running'] = False


def run_async_execution(user_query, socketio_instance):
    """Wrapper for executing async functions in a synchronous environment"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_graph_execution(user_query, socketio_instance))
    finally:
        loop.close()


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/api/start', methods=['POST'])
def start_execution():
    """API to start execution"""

    if execution_state['running']:
        return jsonify({'error': 'Execution already running'}), 400

    data = request.json
    user_query = data.get('part', 'Part1')

    if user_query not in ['Part1', 'Part2']:
        return jsonify({'error': 'Invalid part. Must be Part1 or Part2'}), 400

    # Execute in background thread
    thread = threading.Thread(
        target=run_async_execution,
        args=(user_query, socketio)
    )
    thread.daemon = True
    thread.start()

    return jsonify({'status': 'started', 'part': user_query})


@app.route('/api/status')
def get_status():
    """Query current execution status"""
    return jsonify({
        'running': execution_state['running'],
        'current_part': execution_state['current_part'],
        'log_count': len(execution_state['logs'])
    })


@app.route('/api/logs')
def get_logs():
    """Query logs"""
    return jsonify({
        'logs': execution_state['logs']
    })


@app.route('/api/files')
def list_files():
    """Query list of generated files"""
    artifacts_path = Path('./artifacts')

    if not artifacts_path.exists():
        return jsonify({'files': []})

    files = []

    # Explore Part1 and Part2 folders
    for part_folder in ['part1', 'part2']:
        part_path = artifacts_path / part_folder
        if part_path.exists():
            for file_path in part_path.rglob('*'):
                if file_path.is_file():
                    relative_path = file_path.relative_to(artifacts_path)
                    files.append({
                        'name': file_path.name,
                        'path': str(relative_path),
                        'size': file_path.stat().st_size,
                        'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                        'part': part_folder
                    })

    return jsonify({'files': files})


@app.route('/api/download/<path:file_path>')
def download_file(file_path):
    """Download individual file"""
    full_path = Path('./artifacts') / file_path

    if not full_path.exists() or not full_path.is_file():
        return jsonify({'error': 'File not found'}), 404

    return send_file(full_path, as_attachment=True, download_name=full_path.name)


@app.route('/api/download-all/<part>')
def download_all_files(part):
    """Download all files as ZIP"""

    if part not in ['part1', 'part2', 'all']:
        return jsonify({'error': 'Invalid part'}), 400

    artifacts_path = Path('./artifacts')

    if not artifacts_path.exists():
        return jsonify({'error': 'No artifacts found'}), 404

    # Create ZIP file in memory
    memory_file = io.BytesIO()

    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        if part == 'all':
            folders = ['part1', 'part2']
        else:
            folders = [part]

        for folder in folders:
            folder_path = artifacts_path / folder
            if folder_path.exists():
                for file_path in folder_path.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(artifacts_path)
                        zf.write(file_path, arcname)

    memory_file.seek(0)

    download_name = f'tech_recon_{part}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'

    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=download_name
    )


@socketio.on('connect')
def handle_connect():
    """On client connection"""
    emit('status', {
        'status': 'connected',
        'running': execution_state['running'],
        'current_part': execution_state['current_part']
    })


@socketio.on('disconnect')
def handle_disconnect():
    """On client disconnection"""
    pass


if __name__ == '__main__':
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Tech Recon Web Application')
    parser.add_argument('--port', type=int, default=8050, help='Port to run the server on (default: 8050)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    args = parser.parse_args()

    # Create templates folder
    templates_dir = Path('templates')
    templates_dir.mkdir(exist_ok=True)

    print("="*60)
    print("Tech Recon Web Application")
    print("="*60)
    print(f"Server starting at: http://{args.host}:{args.port}")

    # Detect SageMaker Studio environment
    import os
    if 'SAGEMAKER_INTERNAL_IMAGE_URI' in os.environ:
        print("\n*** Running in SageMaker Studio ***")
        print(f"Access the app via JupyterLab proxy:")
        print(f"  /proxy/{args.port}/")
        print(f"  Or try: /proxy/absolute/{args.port}/")
    else:
        print(f"Access from browser: http://localhost:{args.port}")

    print("Press Ctrl+C to stop the server")
    print("="*60)

    # Run web server
    socketio.run(app, host=args.host, port=args.port, debug=False, allow_unsafe_werkzeug=True)
