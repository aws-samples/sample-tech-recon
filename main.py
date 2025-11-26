
"""
Entry point script for the Strands Agent Demo.
"""
# Load environment variables FIRST before any other imports
from dotenv import load_dotenv
load_dotenv()

import os
import shutil
import asyncio
import argparse
import glob
from src.utils.strands_sdk_utils import strands_utils
from src.graph.builder import build_graph

# Import event queue for unified event processing
from src.utils.event_queue import clear_queue

def remove_artifact_folder(folder_path="./artifacts/"):
    """
    ./artifact/ 폴더가 존재하면 삭제하는 함수

    Args:
        folder_path (str): 삭제할 폴더 경로
    """
    if os.path.exists(folder_path):
        print(f"'{folder_path}' deleting folder...")
        try:
            shutil.rmtree(folder_path)
            print(f"'{folder_path}' successfully deleted folder.")
        except Exception as e: print(f"error occured: {e}")
    else:
        print(f"'{folder_path}' folder doesn't exist")

def conditional_artifact_cleanup(is_part1: bool):
    """
    Part 판별 결과에 따라 artifacts 폴더를 처리

    Args:
        is_part1 (bool): Part1이면 True (part1 폴더 생성), Part2면 False (part2 폴더 생성, part1 참조)

    Returns:
        str: 현재 작업에 사용할 artifacts 폴더 경로 (artifacts/part1 또는 artifacts/part2)
    """
    base_folder = "./artifacts/"
    part1_folder = os.path.join(base_folder, "part1")
    part2_folder = os.path.join(base_folder, "part2")

    if is_part1:
        # Part 1: 전체 artifacts 폴더 삭제 후 part1 폴더 생성
        print(f"\n[Part 1 detected] deleted artifacts folder and initializing...")

        # 전체 artifacts 폴더 삭제 (part1, part2 및 모든 하위 파일 삭제)
        if os.path.exists(base_folder):
            try:
                shutil.rmtree(base_folder)
                print(f"기존 '{base_folder}' deleted")
            except Exception as e:
                print(f"Artifacts folder deleting error: {e}")

        # part1 폴더 새로 생성
        os.makedirs(part1_folder, exist_ok=True)
        print(f"'{part1_folder}' folder created.\n")
        return part1_folder
    else:
        # Part 2: part1 폴더 유지, part2 폴더만 삭제 후 재생성
        print(f"\n[Part 2 detected] artifacts/part2 created and reference part1.")

        # part1 폴더 존재 확인
        if os.path.exists(part1_folder):
            # part1 파일 목록 확인
            part1_files = os.listdir(part1_folder)
            if part1_files:
                print(f"files will be referenced from '{part1_folder}':")
                for f in part1_files[:5]:  # 최대 5개만 표시
                    print(f"  - {f}")
                if len(part1_files) > 5:
                    print(f"  ... {len(part1_files) - 5} files")
            else:
                print(f"[경고] '{part1_folder}' is empty.")
        else:
            print(f"[경고] '{part1_folder}' folder doesn't exist. I need to run Part1 first.")

        # 기존 part2 폴더가 있으면 삭제
        if os.path.exists(part2_folder):
            try:
                shutil.rmtree(part2_folder)
                print(f"기존 '{part2_folder}' deleted for fresh start.")
            except Exception as e:
                print(f"Part2 folder deleting error: {e}")

        # part2 폴더 생성
        os.makedirs(part2_folder, exist_ok=True)
        print(f"'{part2_folder}' folder created.\n")
        return part2_folder

def _print_conversation_history():
    """Print final conversation history"""
    print("\n=== Conversation History ===")
    from src.graph.nodes import _global_node_states
    shared_state = _global_node_states.get('shared', {})
    history = shared_state.get('history', [])

    if history:
        for hist_item in history:
            print(f"[{hist_item['agent']}] {hist_item['message']}")
    else:
        print("No conversation history found")

async def graph_streaming_execution(payload):
    """Execute full graph streaming workflow using new graph.stream_async method"""

    # Initialize execution environment (without artifact cleanup)
    clear_queue()
    print("\n=== Starting Queue-Only Event Stream ===")

    # Get user query from payload
    user_query = payload.get("user_query", "")

    # Build graph and use stream_async method
    graph = build_graph()

    #########################
    ## modification START  ##
    #########################

    # Track whether we've processed planner's response
    planner_processed = False

    # Stream events from graph execution
    async for event in graph.stream_async(
        {
            "request": user_query,
            "request_prompt": f"Here is a user request: <user_request>{user_query}</user_request>",
            "user_input": user_query.lower()  # Pass "part1" or "part2" to router_planner_node
        }
    ):
        # After planner completes, check Part1/Part2 and conditionally cleanup artifacts
        if not planner_processed:
            # Check if this is a planner completion event or if planner has completed
            from src.graph.nodes import _global_node_states
            shared_state = _global_node_states.get('shared', {})

            # If planner has set is_part1 flag, perform conditional cleanup
            if 'is_part1' in shared_state:
                is_part1 = shared_state.get('is_part1', True)
                artifact_folder = conditional_artifact_cleanup(is_part1)

                # Store artifact folder path in shared state for agents to use
                shared_state['artifact_folder'] = artifact_folder
                shared_state['part1_folder'] = './artifacts/part1'  # reference from Part2

                planner_processed = True

        yield event

    #########################
    ## modification END    ##
    #########################

    _print_conversation_history()
    print("=== Queue-Only Event Stream Complete ===")

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Strands Agent Demo')
    parser.add_argument('--user_query', type=str, help='User query for the agent')
    
    args, unknown = parser.parse_known_args()

    #########################
    ## modification START  ##
    #########################

    # Use argparse values if provided, otherwise use predefined values
    if args.user_query:
        payload = {
            "user_query": args.user_query,
        }
    else:
        while True:
            user_input = input("Which report do you want to create? Enter between 'Part1' or 'Part2': ")
            if user_input == "Part1":
                payload = {
                    "user_query": "Part1"
                }
                break
            elif user_input == "Part2":
                payload = {
                    "user_query": "Part2"
                }
                break
            print("You need to enter Part1 or Part2")
        

    #########################
    ## modification END    ##
    #########################

    # Artifact cleanup is now handled inside graph_streaming_execution after planner runs
    # remove_artifact_folder()  # Commented out - cleanup now done conditionally based on Part1/Part2

    # Use full graph streaming execution for real-time streaming with graph structure
    async def run_streaming():
        async for event in graph_streaming_execution(payload):
            strands_utils.process_event_for_display(event)

    asyncio.run(run_streaming())