#!/usr/bin/env python3
"""
Test script for persistent Python REPL functionality.
This tests that variables persist between separate REPL calls.
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.tools.python_repl_tool import PythonREPL

def test_persistent_variables():
    """Test that variables persist between calls."""
    print("=" * 60)
    print("Testing Persistent Python REPL")
    print("=" * 60)
    
    repl = PythonREPL()
    
    # Test 1: Define a variable
    print("\n[Test 1] Defining variable 'assessments'...")
    result1 = repl.run("assessments = {'tech1': 85, 'tech2': 92, 'tech3': 78}")
    print(f"Result: {result1}")
    
    # Test 2: Use the variable in a subsequent call
    print("\n[Test 2] Using 'assessments' in a new call...")
    result2 = repl.run("""
for tech, score in assessments.items():
    print(f"{tech}: {score}")
""")
    print(f"Result:\n{result2}")
    
    # Test 3: Modify the variable
    print("\n[Test 3] Modifying 'assessments'...")
    result3 = repl.run("assessments['tech4'] = 88")
    print(f"Result: {result3}")
    
    # Test 4: Verify the modification persisted
    print("\n[Test 4] Verifying modification persisted...")
    result4 = repl.run("print(f'Total technologies: {len(assessments)}')")
    print(f"Result:\n{result4}")
    
    # Test 5: Import a module and use it
    print("\n[Test 5] Importing and using a module...")
    result5 = repl.run("import json")
    print(f"Result: {result5}")
    
    result6 = repl.run("json_str = json.dumps(assessments)")
    print(f"Result: {result6}")
    
    result7 = repl.run("print(json_str)")
    print(f"Result:\n{result7}")
    
    # Test 6: Test with research_content (from the actual error case)
    print("\n[Test 6] Testing 'research_content' variable (from actual error case)...")
    result8 = repl.run("research_content = 'This is research data about AI and ML'")
    print(f"Result: {result8}")
    
    result9 = repl.run("print(f'Research content length: {len(research_content)}')")
    print(f"Result:\n{result9}")
    
    # Test 7: Test error handling
    print("\n[Test 7] Testing error handling...")
    result10 = repl.run("undefined_variable")
    print(f"Result: {result10}")
    
    # Test 8: Verify variables still exist after error
    print("\n[Test 8] Verifying variables still exist after error...")
    result11 = repl.run("print(f'assessments still exists: {len(assessments)} items')")
    print(f"Result:\n{result11}")
    
    # Cleanup
    repl.cleanup()
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
    
    # Check if all tests passed
    if "Error:" in result2 or "Error:" in result4 or "Error:" in result7 or "Error:" in result9:
        print("\n❌ Some tests failed - variables may not be persisting correctly")
        return False
    else:
        print("\n✅ All tests passed - variables are persisting correctly!")
        return True

if __name__ == "__main__":
    success = test_persistent_variables()
    sys.exit(0 if success else 1)

