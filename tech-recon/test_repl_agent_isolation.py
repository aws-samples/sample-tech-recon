#!/usr/bin/env python3
"""
Test script to verify per-agent namespace isolation in Python REPL.
This verifies that different agents have isolated variable namespaces.
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.tools.python_repl_tool import PythonREPL, handle_python_repl_tool

def test_agent_isolation():
    """Test that different agents have isolated namespaces."""
    print("=" * 60)
    print("Testing Per-Agent Namespace Isolation")
    print("=" * 60)
    
    # Test 1: Coder agent defines a variable
    print("\n[Test 1] Coder agent defines 'assessments' variable...")
    PythonREPL.set_current_agent_name("coder")
    result1 = handle_python_repl_tool("assessments = {'tech1': 85, 'tech2': 92}")
    print(f"Result: {result1}")
    
    # Test 2: Reporter agent defines a DIFFERENT 'assessments' variable
    print("\n[Test 2] Reporter agent defines its own 'assessments' variable...")
    PythonREPL.set_current_agent_name("reporter")
    result2 = handle_python_repl_tool("assessments = {'report_tech1': 90, 'report_tech2': 88}")
    print(f"Result: {result2}")
    
    # Test 3: Coder agent uses its own assessments (should still have original values)
    print("\n[Test 3] Coder agent uses 'assessments' (should have coder's values)...")
    PythonREPL.set_current_agent_name("coder")
    result3 = handle_python_repl_tool("""
for tech, score in assessments.items():
    print(f"{tech}: {score}")
""")
    print(f"Result:\n{result3}")
    
    # Test 4: Reporter agent uses its own assessments (should have reporter's values)
    print("\n[Test 4] Reporter agent uses 'assessments' (should have reporter's values)...")
    PythonREPL.set_current_agent_name("reporter")
    result4 = handle_python_repl_tool("""
for tech, score in assessments.items():
    print(f"{tech}: {score}")
""")
    print(f"Result:\n{result4}")
    
    # Test 5: Validator agent has its own namespace
    print("\n[Test 5] Validator agent defines its own variables...")
    PythonREPL.set_current_agent_name("validator")
    result5 = handle_python_repl_tool("validation_results = {'check1': 'pass', 'check2': 'pass'}")
    print(f"Result: {result5}")
    
    # Test 6: Coder agent should NOT see validator's variables
    print("\n[Test 6] Coder agent tries to access validator's variable (should fail)...")
    PythonREPL.set_current_agent_name("coder")
    result6 = handle_python_repl_tool("print(validation_results)")
    print(f"Result:\n{result6}")
    # Extract the actual result content (after the code preview)
    result6_content = result6.split("||")[-1] if "||" in result6 else result6
    
    # Test 7: Verify coder still has its own variables
    print("\n[Test 7] Coder agent still has its own variables...")
    PythonREPL.set_current_agent_name("coder")
    result7 = handle_python_repl_tool("print(f'Coder has {len(assessments)} assessments')")
    print(f"Result:\n{result7}")
    # Extract the actual result content
    result7_content = result7.split("||")[-1] if "||" in result7 else result7
    
    # Verify isolation
    print("\n" + "=" * 60)
    
    # Check if isolation worked
    coder_has_own_data = ("tech1: 85" in result3 or "tech2: 92" in result3) and "tech1" in result3
    reporter_has_own_data = ("report_tech1: 90" in result4 or "report_tech2: 88" in result4) and "report_tech1" in result4
    # Check if result6 contains error - should have NameError about validation_results
    validator_isolated = ("Error:" in result6_content or "NameError" in result6_content or 
                         ("validation_results" in result6_content and "not defined" in result6_content) or
                         result6_content.strip() == "")
    # Coder should still have its assessments
    coder_still_works = ("Coder has 2 assessments" in result7_content or 
                        ("2" in result7_content and "assessments" in result7_content) and
                        "Error:" not in result7_content)
    
    if coder_has_own_data and reporter_has_own_data and validator_isolated and coder_still_works:
        print("✅ All isolation tests PASSED!")
        print("\n✅ Coder agent has its own namespace")
        print("✅ Reporter agent has its own namespace")
        print("✅ Validator agent has its own namespace")
        print("✅ Variables are isolated between agents")
        print("✅ Coder's variables persist within its namespace")
        return True
    else:
        print("❌ Isolation tests FAILED!")
        if not coder_has_own_data:
            print("❌ Coder agent namespace not isolated (doesn't have own data)")
        if not reporter_has_own_data:
            print("❌ Reporter agent namespace not isolated (doesn't have own data)")
        if not validator_isolated:
            print("❌ Validator agent namespace not isolated (coder can access validator's vars)")
        if not coder_still_works:
            print("❌ Coder agent lost its variables")
        return False

if __name__ == "__main__":
    success = test_agent_isolation()
    sys.exit(0 if success else 1)

