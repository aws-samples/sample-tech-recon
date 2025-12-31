#!/usr/bin/env python3
"""
Integration test for python_repl_tool - simulates actual agent usage.
This tests the tool as it would be used by the coder/reporter agents.
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.tools.python_repl_tool import handle_python_repl_tool

def test_agent_usage_pattern():
    """
    Simulate the actual usage pattern that caused the NameError:
    - Agent defines variables in one call
    - Agent uses those variables in subsequent calls
    """
    print("=" * 60)
    print("Integration Test: Simulating Agent Usage Pattern")
    print("=" * 60)
    
    # Simulate Coder Agent: Technology Assessment Phase
    print("\n[Step 1] Coder agent defines assessments dictionary...")
    result1 = handle_python_repl_tool("""
assessments = {
    'AI/ML': {'maturity': 8, 'impact': 9},
    'Cloud Native': {'maturity': 7, 'impact': 8},
    'DevOps': {'maturity': 9, 'impact': 7}
}
print("Assessments defined successfully")
""")
    print(f"Result:\n{result1}\n")
    
    # Simulate the error case: Agent tries to use assessments in a new call
    print("[Step 2] Coder agent uses assessments in a NEW call (this used to fail)...")
    result2 = handle_python_repl_tool("""
# This would have caused: NameError: name 'assessments' is not defined
for tech, scores in sorted(assessments.items()):
    avg_score = (scores['maturity'] + scores['impact']) / 2
    print(f"{tech}: maturity={scores['maturity']}, impact={scores['impact']}, avg={avg_score:.1f}")
""")
    print(f"Result:\n{result2}\n")
    
    # Simulate Reporter Agent: Report Generation Phase
    print("[Step 3] Reporter agent defines research_content...")
    result3 = handle_python_repl_tool("""
research_content = '''
Key findings from research:
- AI/ML technologies are rapidly evolving
- Cloud native adoption is increasing
- DevOps practices are maturing
'''
print("Research content loaded")
""")
    print(f"Result:\n{result3}\n")
    
    print("[Step 4] Reporter agent uses research_content in a NEW call...")
    result4 = handle_python_repl_tool("""
# This would have caused: NameError: name 'research_content' is not defined
lines = research_content.strip().split('\\n')
print(f"Research content has {len(lines)} lines")
for line in lines:
    if line.strip():
        print(f"  - {line.strip()}")
""")
    print(f"Result:\n{result4}\n")
    
    print("[Step 5] Reporter agent combines both variables...")
    result5 = handle_python_repl_tool("""
# Using both assessments and research_content together
print("=== Technology Assessment Summary ===")
for tech in assessments.keys():
    print(f"- {tech}")
print(f"\\n=== Research Summary ===")
print(f"Research content: {len(research_content)} characters")
""")
    print(f"Result:\n{result5}\n")
    
    # Check for actual errors (not comments mentioning errors)
    # Look for "Error:" at the start of the result content (not in code comments)
    has_errors = any(
        result.startswith("Error:") or 
        ("Failed to execute" in result and "Error:" in result.split("||")[-1] if "||" in result else False)
        for result in [result1, result2, result3, result4, result5]
    )
    
    # Also check if variables were successfully used (positive test)
    variables_worked = (
        "AI/ML: maturity=8" in result2 and  # assessments was used successfully
        "Research content has" in result4 and  # research_content was used successfully
        "Technology Assessment Summary" in result5  # Both variables used together
    )
    
    print("=" * 60)
    if has_errors:
        print("❌ Integration test FAILED - errors detected")
        return False
    elif not variables_worked:
        print("❌ Integration test FAILED - variables not working as expected")
        return False
    else:
        print("✅ Integration test PASSED - variables persist correctly!")
        print("\nThis fixes the issue where agents had to re-execute code blocks")
        print("because variables weren't available in subsequent calls.")
        return True

if __name__ == "__main__":
    success = test_agent_usage_pattern()
    sys.exit(0 if success else 1)

